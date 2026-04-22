"""
DQN Training Script for Data Cleaning.

This module implements the complete DQN training pipeline including
data generation, training loop, and model evaluation.
"""
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd
import argparse
import logging
import time
import os
import json
from typing import Dict, List, Any, Tuple
from datetime import datetime
import matplotlib.pyplot as plt
from tqdm import tqdm

# Import our modules
from .dqn_model import DQNAgent, Transition
from .experience_replay import ReplayBuffer
from .reward_shaper import RewardShaper
from .agent_coordinator import AgentCoordinator

# Import data generator (handle both relative and absolute imports)
try:
    from data.synthetic_datasets import SyntheticDatasetGenerator, DifficultyLevel, DatasetConfig
except ImportError:
    from ..data.synthetic_datasets import SyntheticDatasetGenerator, DifficultyLevel, DatasetConfig


class DQNTrainer:
    """
    DQN Training pipeline for data cleaning agents.
    
    Handles data generation, training loop, evaluation, and model saving.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize trainer.
        
        Args:
            config: Training configuration
        """
        self.config = config
        self.logger = self._setup_logging()
        
        # Set device
        self.device = torch.device(config.get('device', 'cuda' if torch.cuda.is_available() else 'cpu'))
        self.logger.info(f"Using device: {self.device}")
        
        # Initialize components
        self.state_dim = config.get('state_dim', 50)  # Adjust based on encoding
        self.action_dim = config.get('action_dim', 7)  # 7 possible actions
        
        # Initialize DQN agent
        self.agent = DQNAgent(self.state_dim, self.action_dim, device=str(self.device))
        
        # Initialize replay buffer
        buffer_capacity = config.get('buffer_capacity', 10000)
        self.replay_buffer = ReplayBuffer(buffer_capacity)
        
        # Initialize optimizer
        learning_rate = config.get('learning_rate', 0.001)
        self.optimizer = optim.Adam(self.agent.q_network.parameters(), lr=learning_rate)
        
        # Training hyperparameters
        self.gamma = config.get('gamma', 0.99)
        self.epsilon = config.get('epsilon', 1.0)
        self.epsilon_min = config.get('epsilon_min', 0.01)
        self.epsilon_decay = config.get('epsilon_decay', 0.995)
        self.batch_size = config.get('batch_size', 32)
        self.target_update_freq = config.get('target_update_frequency', 10)
        
        # Initialize reward shaper
        self.reward_shaper = RewardShaper()
        
        # Initialize synthetic data generator
        self.data_generator = SyntheticDatasetGenerator(seed=config.get('seed', 42))
        
        # Training metrics
        self.training_metrics = {
            'episode_rewards': [],
            'episode_lengths': [],
            'losses': [],
            'epsilon_values': [],
            'avg_rewards': []
        }
        
        self.logger.info("DQNTrainer initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger("DQNTrainer")
        logger.setLevel(logging.INFO)
        
        # Create console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Create file handler
        os.makedirs('logs', exist_ok=True)
        fh = logging.FileHandler(f'logs/dqn_training_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        fh.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)
        
        logger.addHandler(ch)
        logger.addHandler(fh)
        
        return logger
    
    def generate_training_data(self, difficulty: DifficultyLevel, num_episodes: int) -> List[Dict[str, Any]]:
        """
        Generate training episodes.
        
        Args:
            difficulty: Difficulty level for data generation
            num_episodes: Number of episodes to generate
            
        Returns:
            List of training episodes
        """
        self.logger.info(f"Generating {num_episodes} training episodes for {difficulty.value} difficulty")
        
        config = self.data_generator.get_config_for_difficulty(difficulty)
        config.num_rows = self.config.get('episode_rows', 50)
        
        episodes = self.data_generator.create_training_episodes(config, num_episodes)
        
        self.logger.info(f"Generated {len(episodes)} episodes")
        return episodes
    
    def calculate_td_loss(self, batch: List[Transition]) -> torch.Tensor:
        """
        Calculate TD loss for a batch of transitions.
        
        Args:
            batch: Batch of transitions
            
        Returns:
            TD loss tensor
        """
        # Extract batch components
        states = torch.FloatTensor([t.state for t in batch]).to(self.device)
        actions = torch.LongTensor([t.action for t in batch]).to(self.device)
        rewards = torch.FloatTensor([t.reward for t in batch]).to(self.device)
        next_states = torch.FloatTensor([t.next_state for t in batch]).to(self.device)
        dones = torch.FloatTensor([t.done for t in batch]).to(self.device)
        
        # Current Q-values
        current_q_values = self.agent.q_network(states).gather(1, actions.unsqueeze(1))
        
        # Next Q-values from target network
        next_q_values = self.agent.target_network(next_states).max(1)[0].detach()
        target_q_values = rewards + (1 - dones) * self.gamma * next_q_values
        
        # Calculate loss (MSE)
        loss = nn.MSELoss()(current_q_values.squeeze(), target_q_values)
        
        return loss
    
    def train_episode(self, episode: Dict[str, Any]) -> Tuple[float, int]:
        """
        Train on a single episode.
        
        Args:
            episode: Training episode data
            
        Returns:
            Tuple of (total_reward, episode_length)
        """
        self.agent.reset(episode['rows'][0])  # Reset with first observation
        self.reward_shaper.reset_episode(len(episode['rows']))
        
        total_reward = 0.0
        episode_length = 0
        
        for step_idx, observation in enumerate(episode['rows']):
            # Get legal actions
            legal_actions = observation['legal_actions']
            
            # Select action
            action_dict = self.agent.get_action(observation, legal_actions)
            
            # Simulate environment response (simplified)
            # In real implementation, this would call the actual environment
            next_observation = episode['rows'][step_idx + 1] if step_idx + 1 < len(episode['rows']) else None
            done = next_observation is None
            
            # Calculate reward
            episode_state = {'step': step_idx, 'total_steps': len(episode['rows'])}
            reward = self.reward_shaper.calculate_reward(action_dict, observation, episode_state)
            
            # Encode states
            current_state = self.agent._encode_observation(observation)
            next_state = self.agent._encode_observation(next_observation) if next_observation else current_state
            
            # Convert action to index
            action_str = action_dict['action_type']
            action_idx = self.agent.reverse_action_mapping.get(action_str, 0)  # Default to skip
            
            # Store transition
            self.replay_buffer.add(current_state, action_idx, reward, next_state, done)
            
            # Update agent
            self.agent.update_reward(reward)
            
            total_reward += reward
            episode_length += 1
            
            # Train if we have enough samples
            if self.replay_buffer.size() >= self.batch_size:
                self.train_step()
            
            if done:
                break
        
        return total_reward, episode_length
    
    def train_step(self) -> float:
        """
        Perform one training step.
        
        Returns:
            Training loss
        """
        # Sample batch
        batch = self.replay_buffer.sample(self.batch_size)
        
        # Calculate loss
        loss = self.calculate_td_loss(batch)
        
        # Backpropagation
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.agent.q_network.parameters(), 1.0)  # Gradient clipping
        self.optimizer.step()
        
        return loss.item()
    
    def train(self, difficulty: DifficultyLevel, epochs: int, save_model: bool = True) -> Dict[str, Any]:
        """
        Main training loop.
        
        Args:
            difficulty: Difficulty level for training
            epochs: Number of training epochs
            save_model: Whether to save the trained model
            
        Returns:
            Training results
        """
        self.logger.info(f"Starting DQN training: {epochs} epochs, difficulty={difficulty.value}")
        
        # Generate training data
        episodes = self.generate_training_data(difficulty, epochs)
        
        start_time = time.time()
        
        for epoch in tqdm(range(epochs), desc="Training"):
            # Select episode
            episode = episodes[epoch % len(episodes)]
            
            # Train on episode
            total_reward, episode_length = self.train_episode(episode)
            
            # Record metrics
            self.training_metrics['episode_rewards'].append(total_reward)
            self.training_metrics['episode_lengths'].append(episode_length)
            self.training_metrics['epsilon_values'].append(self.agent.epsilon)
            
            # Calculate average reward over last 10 episodes
            if len(self.training_metrics['episode_rewards']) >= 10:
                avg_reward = np.mean(self.training_metrics['episode_rewards'][-10:])
                self.training_metrics['avg_rewards'].append(avg_reward)
            
            # Update target network
            if epoch % self.target_update_freq == 0:
                self.agent.update_target_network()
            
            # Decay epsilon
            self.agent.decay_epsilon()
            
            # Log progress
            if epoch % 10 == 0:
                avg_reward = np.mean(self.training_metrics['episode_rewards'][-10:]) if len(self.training_metrics['episode_rewards']) >= 10 else total_reward
                self.logger.info(f"Epoch {epoch}: Avg Reward={avg_reward:.3f}, Epsilon={self.agent.epsilon:.3f}")
        
        training_time = time.time() - start_time
        self.logger.info(f"Training completed in {training_time:.2f} seconds")
        
        # Save model if requested
        if save_model:
            self.save_model(difficulty, epochs)
        
        # Generate training report
        results = self.generate_training_report(difficulty, epochs, training_time)
        
        return results
    
    def save_model(self, difficulty: DifficultyLevel, epochs: int) -> str:
        """
        Save trained model.
        
        Args:
            difficulty: Training difficulty
            epochs: Number of training epochs
            
        Returns:
            Model file path
        """
        os.makedirs('models', exist_ok=True)
        
        # Create model filename
        avg_reward = np.mean(self.training_metrics['episode_rewards'][-10:]) if len(self.training_metrics['episode_rewards']) >= 10 else 0.0
        model_name = f"dqn_{difficulty.value}_v1.0_epochs{epochs}_reward{avg_reward:.3f}.pt"
        model_path = os.path.join('models', model_name)
        
        # Save model
        self.agent.save_model(model_path)
        
        # Save training metrics
        metrics_path = model_path.replace('.pt', '_metrics.json')
        with open(metrics_path, 'w') as f:
            json.dump(self.training_metrics, f, indent=2)
        
        self.logger.info(f"Model saved to {model_path}")
        return model_path
    
    def generate_training_report(self, difficulty: DifficultyLevel, epochs: int, training_time: float) -> Dict[str, Any]:
        """
        Generate training report.
        
        Args:
            difficulty: Training difficulty
            epochs: Number of epochs
            training_time: Training time in seconds
            
        Returns:
            Training results
        """
        if not self.training_metrics['episode_rewards']:
            return {'error': 'No training data available'}
        
        # Calculate statistics
        final_rewards = self.training_metrics['episode_rewards'][-10:] if len(self.training_metrics['episode_rewards']) >= 10 else self.training_metrics['episode_rewards']
        
        results = {
            'difficulty': difficulty.value,
            'epochs': epochs,
            'training_time_seconds': training_time,
            'final_avg_reward': np.mean(final_rewards),
            'final_std_reward': np.std(final_rewards),
            'best_reward': np.max(self.training_metrics['episode_rewards']),
            'worst_reward': np.min(self.training_metrics['episode_rewards']),
            'final_epsilon': self.training_metrics['epsilon_values'][-1],
            'total_transitions': self.replay_buffer.size(),
            'model_info': self.agent.get_model_info(),
            'training_metrics': self.training_metrics
        }
        
        # Save report
        os.makedirs('reports', exist_ok=True)
        report_path = f'reports/dqn_training_report_{difficulty.value}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.logger.info(f"Training report saved to {report_path}")
        
        # Plot training curves
        self.plot_training_curves(difficulty)
        
        return results
    
    def plot_training_curves(self, difficulty: DifficultyLevel):
        """
        Plot training curves.
        
        Args:
            difficulty: Training difficulty
        """
        os.makedirs('plots', exist_ok=True)
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle(f'DQN Training Curves - {difficulty.value.upper()} Difficulty')
        
        # Episode rewards
        axes[0, 0].plot(self.training_metrics['episode_rewards'])
        axes[0, 0].set_title('Episode Rewards')
        axes[0, 0].set_xlabel('Episode')
        axes[0, 0].set_ylabel('Reward')
        axes[0, 0].grid(True)
        
        # Average rewards (moving average)
        if self.training_metrics['avg_rewards']:
            axes[0, 1].plot(self.training_metrics['avg_rewards'])
            axes[0, 1].set_title('Average Reward (10-episode moving average)')
            axes[0, 1].set_xlabel('Episode')
            axes[0, 1].set_ylabel('Average Reward')
            axes[0, 1].grid(True)
        
        # Epsilon decay
        axes[1, 0].plot(self.training_metrics['epsilon_values'])
        axes[1, 0].set_title('Epsilon Decay')
        axes[1, 0].set_xlabel('Episode')
        axes[1, 0].set_ylabel('Epsilon')
        axes[1, 0].grid(True)
        
        # Episode lengths
        axes[1, 1].plot(self.training_metrics['episode_lengths'])
        axes[1, 1].set_title('Episode Lengths')
        axes[1, 1].set_xlabel('Episode')
        axes[1, 1].set_ylabel('Steps')
        axes[1, 1].grid(True)
        
        plt.tight_layout()
        
        plot_path = f'plots/dqn_training_curves_{difficulty.value}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info(f"Training curves saved to {plot_path}")
    
    def evaluate_model(self, model_path: str, test_episodes: int = 50) -> Dict[str, Any]:
        """
        Evaluate trained model.
        
        Args:
            model_path: Path to trained model
            test_episodes: Number of test episodes
            
        Returns:
            Evaluation results
        """
        self.logger.info(f"Evaluating model: {model_path}")
        
        # Load model
        self.agent.load_model(model_path)
        self.agent.set_training_mode(False)  # Set to inference mode
        
        # Generate test data
        difficulty = DifficultyLevel.EASY  # Test on easy difficulty
        test_episodes_data = self.generate_training_data(difficulty, test_episodes)
        
        evaluation_results = {
            'test_rewards': [],
            'test_lengths': [],
            'success_rate': 0.0,
            'avg_reward': 0.0,
            'avg_steps': 0.0
        }
        
        for episode in test_episodes_data:
            total_reward, episode_length = self.evaluate_episode(episode)
            evaluation_results['test_rewards'].append(total_reward)
            evaluation_results['test_lengths'].append(episode_length)
        
        # Calculate statistics
        evaluation_results['avg_reward'] = np.mean(evaluation_results['test_rewards'])
        evaluation_results['avg_steps'] = np.mean(evaluation_results['test_lengths'])
        evaluation_results['success_rate'] = np.mean([r > 0 for r in evaluation_results['test_rewards']])
        
        self.logger.info(f"Evaluation completed: Avg Reward={evaluation_results['avg_reward']:.3f}")
        
        return evaluation_results
    
    def evaluate_episode(self, episode: Dict[str, Any]) -> Tuple[float, int]:
        """
        Evaluate on a single episode (inference mode).
        
        Args:
            episode: Test episode
            
        Returns:
            Tuple of (total_reward, episode_length)
        """
        self.agent.reset(episode['rows'][0])
        self.reward_shaper.reset_episode(len(episode['rows']))
        
        total_reward = 0.0
        episode_length = 0
        
        for step_idx, observation in enumerate(episode['rows']):
            # Get action (no exploration)
            action_dict = self.agent.get_action(observation, observation['legal_actions'])
            
            # Calculate reward
            episode_state = {'step': step_idx, 'total_steps': len(episode['rows'])}
            reward = self.reward_shaper.calculate_reward(action_dict, observation, episode_state)
            
            total_reward += reward
            episode_length += 1
            
            if step_idx >= len(episode['rows']) - 1:
                break
        
        return total_reward, episode_length


def main():
    """Main training script."""
    parser = argparse.ArgumentParser(description='Train DQN for data cleaning')
    parser.add_argument('--epochs', type=int, default=1000, help='Number of training epochs')
    parser.add_argument('--task', type=str, choices=['easy', 'medium', 'hard'], default='easy', help='Task difficulty')
    parser.add_argument('--save', action='store_true', help='Save trained model')
    parser.add_argument('--device', type=str, default='auto', help='Device (cpu/cuda/auto)')
    parser.add_argument('--batch-size', type=int, default=32, help='Batch size')
    parser.add_argument('--learning-rate', type=float, default=0.001, help='Learning rate')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    
    args = parser.parse_args()
    
    # Setup device
    if args.device == 'auto':
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
    else:
        device = args.device
    
    # Training configuration
    config = {
        'device': device,
        'state_dim': 50,
        'action_dim': 7,
        'learning_rate': args.learning_rate,
        'batch_size': args.batch_size,
        'gamma': 0.99,
        'epsilon': 1.0,
        'epsilon_min': 0.01,
        'epsilon_decay': 0.995,
        'target_update_frequency': 10,
        'buffer_capacity': 10000,
        'episode_rows': 50,
        'seed': args.seed
    }
    
    # Initialize trainer
    trainer = DQNTrainer(config)
    
    # Convert task to difficulty
    difficulty_map = {
        'easy': DifficultyLevel.EASY,
        'medium': DifficultyLevel.MEDIUM,
        'hard': DifficultyLevel.HARD
    }
    difficulty = difficulty_map[args.task]
    
    # Train model
    results = trainer.train(difficulty, args.epochs, save_model=args.save)
    
    # Print results
    print("\n" + "="*60)
    print("TRAINING RESULTS")
    print("="*60)
    print(f"Difficulty: {results['difficulty'].upper()}")
    print(f"Epochs: {results['epochs']}")
    print(f"Training Time: {results['training_time_seconds']:.2f} seconds")
    print(f"Final Average Reward: {results['final_avg_reward']:.3f}")
    print(f"Best Reward: {results['best_reward']:.3f}")
    print(f"Final Epsilon: {results['final_epsilon']:.3f}")
    print(f"Total Transitions: {results['total_transitions']}")
    print("="*60)


if __name__ == "__main__":
    main()
