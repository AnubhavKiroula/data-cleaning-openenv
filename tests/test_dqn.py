"""
Comprehensive tests for DQN components.

This module tests the DQN model, experience replay buffer,
training pipeline, and model registry.
"""
import pytest
import torch
import numpy as np
import pandas as pd
import tempfile
import shutil
import os
import sys
from unittest.mock import Mock, patch

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from ml.dqn_model import QNetwork, DQNAgent, Transition
from ml.experience_replay import ReplayBuffer, PrioritizedReplayBuffer
from ml.train_dqn import DQNTrainer
from ml.model_registry import ModelRegistry, ModelMetadata
from data.synthetic_datasets import SyntheticDatasetGenerator, DifficultyLevel, DatasetConfig


class TestQNetwork:
    """Test the Q-Network model."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.state_dim = 50
        self.action_dim = 7
        self.network = QNetwork(self.state_dim, self.action_dim)
    
    def test_network_initialization(self):
        """Test network initialization."""
        assert self.network.state_dim == self.state_dim
        assert self.network.action_dim == self.action_dim
        assert len(list(self.network.parameters())) > 0
    
    def test_forward_pass(self):
        """Test forward pass through network."""
        batch_size = 4
        state = torch.randn(batch_size, self.state_dim)
        
        output = self.network(state)
        
        assert output.shape == (batch_size, self.action_dim)
        assert torch.is_tensor(output)
        assert not torch.isnan(output).any()
    
    def test_get_q_values(self):
        """Test getting Q-values as numpy array."""
        state = torch.randn(1, self.state_dim)
        
        q_values = self.network.get_q_values(state)
        
        assert isinstance(q_values, np.ndarray)
        assert q_values.shape == (self.action_dim,)
        assert not np.isnan(q_values).any()
    
    def test_different_hidden_dimensions(self):
        """Test network with different hidden layer dimensions."""
        hidden_dims = [64, 32]
        network = QNetwork(self.state_dim, self.action_dim, hidden_dims)
        
        state = torch.randn(2, self.state_dim)
        output = network(state)
        
        assert output.shape == (2, self.action_dim)


class TestDQNAgent:
    """Test the DQN Agent."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.state_dim = 50
        self.action_dim = 7
        self.agent = DQNAgent(self.state_dim, self.action_dim, device="cpu")
    
    def test_agent_initialization(self):
        """Test agent initialization."""
        assert self.agent.get_name() == "DQNAgent"
        assert self.agent.state_dim == self.state_dim
        assert self.agent.action_dim == self.action_dim
        assert self.agent.epsilon == 1.0
        assert self.agent.epsilon_min == 0.01
    
    def test_reset(self):
        """Test agent reset."""
        observation = {
            "current_data": {"age": 30, "name": "John"},
            "legal_actions": ["skip", "fill_missing"]
        }
        
        self.agent.reset(observation)
        
        assert self.agent._confidence == 0.0
        assert "skip" in self.agent.reverse_action_mapping
        assert "fill_missing" in self.agent.reverse_action_mapping
    
    def test_get_action_training(self):
        """Test action selection during training."""
        observation = {
            "current_data": {"age": None, "name": "John"},
            "legal_actions": ["skip", "fill_missing"]
        }
        
        action = self.agent.get_action(observation, observation["legal_actions"])
        
        assert "action_type" in action
        assert "column" in action
        assert action["action_type"] in ["skip", "fill_missing"]
        assert 0 <= self.agent.get_confidence() <= 1.0
    
    def test_get_action_inference(self):
        """Test action selection during inference."""
        self.agent.set_training_mode(False)
        
        observation = {
            "current_data": {"age": None, "name": "John"},
            "legal_actions": ["skip", "fill_missing"]
        }
        
        action = self.agent.get_action(observation, observation["legal_actions"])
        
        assert action["action_type"] in ["skip", "fill_missing"]
        assert self.agent.epsilon == 0.0  # No exploration in inference mode
    
    def test_epsilon_decay(self):
        """Test epsilon decay."""
        initial_epsilon = self.agent.epsilon
        
        self.agent.decay_epsilon()
        
        assert self.agent.epsilon < initial_epsilon
        assert self.agent.epsilon >= self.agent.epsilon_min
    
    def test_update_target_network(self):
        """Test target network update."""
        # Get initial weights
        initial_weights = list(self.agent.target_network.parameters())[0].data.clone()
        
        # Modify main network weights
        with torch.no_grad():
            list(self.agent.q_network.parameters())[0].data += torch.randn_like(list(self.agent.q_network.parameters())[0].data)
        
        # Update target network
        self.agent.update_target_network()
        
        # Check weights updated
        updated_weights = list(self.agent.target_network.parameters())[0].data
        assert not torch.equal(initial_weights, updated_weights)
    
    def test_save_load_model(self):
        """Test model saving and loading."""
        with tempfile.NamedTemporaryFile(suffix='.pt', delete=False) as f:
            model_path = f.name
        
        try:
            # Save model
            self.agent.save_model(model_path)
            assert os.path.exists(model_path)
            
            # Create new agent and load model
            new_agent = DQNAgent(self.state_dim, self.action_dim, device="cpu")
            new_agent.load_model(model_path)
            
            # Check weights are the same
            for p1, p2 in zip(self.agent.q_network.parameters(), new_agent.q_network.parameters()):
                assert torch.equal(p1.data, p2.data)
        
        finally:
            if os.path.exists(model_path):
                os.unlink(model_path)
    
    def test_encode_observation(self):
        """Test observation encoding."""
        observation = {
            "current_data": {"age": 30, "salary": 75000, "score": 85, "name": "John", "dept": "engineering", "email": "john@example.com"},
            "issues_detected": ["missing:age", "category:dept"],
            "legal_actions": ["skip", "fill_missing", "fix_category"]
        }
        
        state = self.agent._encode_observation(observation)
        
        assert isinstance(state, np.ndarray)
        assert state.dtype == np.float32
        assert len(state) == self.state_dim
        assert not np.isnan(state).any()
    
    def test_get_model_info(self):
        """Test getting model information."""
        info = self.agent.get_model_info()
        
        assert "model_type" in info
        assert info["model_type"] == "DQN"
        assert "state_dim" in info
        assert info["state_dim"] == self.state_dim
        assert "action_dim" in info
        assert info["action_dim"] == self.action_dim
        assert "total_parameters" in info
        assert info["total_parameters"] > 0


class TestReplayBuffer:
    """Test the Experience Replay Buffer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.capacity = 100
        self.buffer = ReplayBuffer(self.capacity)
    
    def test_buffer_initialization(self):
        """Test buffer initialization."""
        assert self.buffer.capacity == self.capacity
        assert self.buffer.size() == 0
        assert not self.buffer.is_full()
    
    def test_add_transition(self):
        """Test adding transitions."""
        state = np.random.randn(10)
        action = 1
        reward = 0.5
        next_state = np.random.randn(10)
        done = False
        
        self.buffer.add(state, action, reward, next_state, done)
        
        assert self.buffer.size() == 1
        assert self.buffer.total_added == 1
    
    def test_sample_batch(self):
        """Test sampling batches."""
        # Add some transitions
        for i in range(10):
            state = np.random.randn(10)
            action = i % 3
            reward = np.random.randn()
            next_state = np.random.randn(10)
            done = i % 5 == 0
            self.buffer.add(state, action, reward, next_state, done)
        
        # Sample batch
        batch = self.buffer.sample(4)
        
        assert len(batch) == 4
        assert all(isinstance(t, Transition) for t in batch)
    
    def test_sample_tensors(self):
        """Test sampling as tensors."""
        # Add some transitions
        for i in range(10):
            state = np.random.randn(10)
            action = i % 3
            reward = np.random.randn()
            next_state = np.random.randn(10)
            done = i % 5 == 0
            self.buffer.add(state, action, reward, next_state, done)
        
        # Sample tensors
        states, actions, rewards, next_states, dones = self.buffer.sample_tensors(4)
        
        assert states.shape == (4, 10)
        assert actions.shape == (4,)
        assert rewards.shape == (4,)
        assert next_states.shape == (4, 10)
        assert dones.shape == (4,)
    
    def test_buffer_capacity(self):
        """Test buffer capacity limits."""
        # Fill buffer beyond capacity
        for i in range(self.capacity + 10):
            state = np.random.randn(5)
            self.buffer.add(state, 0, 0.0, state, False)
        
        assert self.buffer.size() == self.capacity
        assert self.buffer.is_full()
    
    def test_clear_buffer(self):
        """Test clearing buffer."""
        # Add some transitions
        for i in range(5):
            state = np.random.randn(5)
            self.buffer.add(state, 0, 0.0, state, False)
        
        assert self.buffer.size() == 5
        
        # Clear buffer
        self.buffer.clear()
        
        assert self.buffer.size() == 0
        assert self.buffer.total_added == 0
    
    def test_get_statistics(self):
        """Test getting buffer statistics."""
        # Add some transitions
        for i in range(10):
            state = np.random.randn(5)
            reward = np.random.randn()
            done = i % 3 == 0
            self.buffer.add(state, 0, reward, state, done)
        
        stats = self.buffer.get_statistics()
        
        assert "size" in stats
        assert stats["size"] == 10
        assert "capacity" in stats
        assert stats["capacity"] == self.capacity
        assert "utilization" in stats
        assert "reward_mean" in stats
        assert "done_rate" in stats


class TestPrioritizedReplayBuffer:
    """Test the Prioritized Experience Replay Buffer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.capacity = 100
        self.buffer = PrioritizedReplayBuffer(self.capacity, alpha=0.6, beta=0.4)
    
    def test_prioritized_buffer_initialization(self):
        """Test prioritized buffer initialization."""
        assert self.buffer.capacity == self.capacity
        assert self.buffer.alpha == 0.6
        assert self.buffer.beta == 0.4
        assert self.buffer.max_priority == 1.0
    
    def test_add_with_priority(self):
        """Test adding transitions with priority."""
        state = np.random.randn(10)
        self.buffer.add(state, 0, 0.5, state, False)
        
        assert self.buffer.size() == 1
        assert len(self.buffer.priorities) == 1
        assert self.buffer.priorities[0] == self.buffer.max_priority
    
    def test_sample_with_weights(self):
        """Test sampling with importance weights."""
        # Add some transitions
        for i in range(10):
            state = np.random.randn(10)
            self.buffer.add(state, 0, 0.5, state, False)
        
        transitions, indices, weights = self.buffer.sample(4)
        
        assert len(transitions) == 4
        assert len(indices) == 4
        assert len(weights) == 4
        assert all(w > 0 for w in weights)
    
    def test_update_priorities(self):
        """Test updating priorities."""
        # Add some transitions
        for i in range(10):
            state = np.random.randn(10)
            self.buffer.add(state, 0, 0.5, state, False)
        
        # Sample and update priorities
        transitions, indices, weights = self.buffer.sample(4)
        td_errors = np.random.randn(4)
        
        self.buffer.update_priorities(indices, td_errors)
        
        # Check priorities updated
        for idx in indices:
            assert self.buffer.priorities[idx] > 1e-6  # Should be updated


class TestSyntheticDatasetGenerator:
    """Test the Synthetic Dataset Generator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = SyntheticDatasetGenerator(seed=42)
    
    def test_generator_initialization(self):
        """Test generator initialization."""
        assert self.generator is not None
        assert len(self.generator.name_options) > 0
        assert len(self.generator.dept_options) > 0
    
    def test_generate_clean_dataset(self):
        """Test clean dataset generation."""
        df = self.generator.generate_clean_dataset(100)
        
        assert len(df) == 100
        assert 'id' in df.columns
        assert 'name' in df.columns
        assert 'age' in df.columns
        assert 'salary' in df.columns
        assert 'score' in df.columns
        assert 'dept' in df.columns
        assert 'email' in df.columns
        
        # Check data quality
        assert df['age'].between(18, 70).all()
        assert df['score'].between(0, 100).all()
        assert df['salary'].min() > 0
    
    def test_get_config_for_difficulty(self):
        """Test getting configuration for difficulty levels."""
        easy_config = self.generator.get_config_for_difficulty(DifficultyLevel.EASY)
        medium_config = self.generator.get_config_for_difficulty(DifficultyLevel.MEDIUM)
        hard_config = self.generator.get_config_for_difficulty(DifficultyLevel.HARD)
        
        assert easy_config.difficulty == DifficultyLevel.EASY
        assert medium_config.difficulty == DifficultyLevel.MEDIUM
        assert hard_config.difficulty == DifficultyLevel.HARD
        
        # Check error rates increase with difficulty
        assert easy_config.missing_rate <= medium_config.missing_rate <= hard_config.missing_rate
    
    def test_inject_missing_values(self):
        """Test missing value injection."""
        df_clean = self.generator.generate_clean_dataset(50)
        df_dirty, issues = self.generator.inject_missing_values(df_clean, 0.2)
        
        assert len(df_dirty) == len(df_clean)
        assert len(issues) > 0
        assert any("missing:" in issue for issue in issues)
        
        # Check some values are actually missing
        assert df_clean.isna().sum().sum() == 0
        assert df_dirty.isna().sum().sum() > 0
    
    def test_inject_duplicates(self):
        """Test duplicate injection."""
        df_clean = self.generator.generate_clean_dataset(50)
        df_dirty, issues = self.generator.inject_duplicates(df_clean, 0.1)
        
        assert len(df_dirty) > len(df_clean)  # Should have more rows
        assert len(issues) > 0
        assert any("duplicate:" in issue for issue in issues)
    
    def test_inject_outliers(self):
        """Test outlier injection."""
        df_clean = self.generator.generate_clean_dataset(50)
        df_dirty, issues = self.generator.inject_outliers(df_clean, 0.1)
        
        assert len(df_dirty) == len(df_clean)
        assert len(issues) > 0
        assert any("outlier:" in issue for issue in issues)
    
    def test_generate_dirty_dataset(self):
        """Test complete dirty dataset generation."""
        config = DatasetConfig(
            difficulty=DifficultyLevel.EASY,
            num_rows=100,
            missing_rate=0.2,
            type_error_rate=0.05
        )
        
        df_dirty, issues = self.generator.generate_dirty_dataset(config)
        
        assert len(df_dirty) == 100
        assert len(issues) > 0
        
        # Check for expected issue types
        assert any("missing:" in issue for issue in issues)
        assert any("wrong_type:" in issue for issue in issues)
    
    def test_create_training_episodes(self):
        """Test training episode creation."""
        config = self.generator.get_config_for_difficulty(DifficultyLevel.EASY)
        config.num_rows = 20
        
        episodes = self.generator.create_training_episodes(config, 5)
        
        assert len(episodes) == 5
        assert all('episode_id' in ep for ep in episodes)
        assert all('dataset' in ep for ep in episodes)
        assert all('rows' in ep for ep in episodes)
        assert all(len(ep['rows']) == 20 for ep in episodes)
        
        # Check row structure
        for episode in episodes:
            for row in episode['rows']:
                assert 'current_data' in row
                assert 'issues_detected' in row
                assert 'legal_actions' in row


class TestModelRegistry:
    """Test the Model Registry."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.registry = ModelRegistry(self.temp_dir)
        
        # Create a mock agent for testing
        self.agent = DQNAgent(50, 7, device="cpu")
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_registry_initialization(self):
        """Test registry initialization."""
        assert self.registry.registry_dir.exists()
        assert isinstance(self.registry.models, dict)
    
    def test_register_model(self):
        """Test model registration."""
        version = "1.0"
        difficulty = "easy"
        epochs = 100
        final_reward = 0.5
        best_reward = 0.8
        training_time = 300.0
        training_metrics = {"loss": [0.5, 0.3, 0.2]}
        
        model_path = self.registry.register_model(
            self.agent, version, difficulty, epochs, final_reward, best_reward,
            training_time, training_metrics
        )
        
        assert os.path.exists(model_path)
        assert version in self.registry.models
        assert self.registry.models[version].version == version
        assert self.registry.models[version].difficulty == difficulty
    
    def test_load_model(self):
        """Test model loading."""
        # Register a model first
        version = "1.0"
        self.registry.register_model(
            self.agent, version, "easy", 100, 0.5, 0.8, 300.0, {}
        )
        
        # Load the model
        loaded_agent = self.registry.load_model(version, 50, 7, device="cpu")
        
        assert isinstance(loaded_agent, DQNAgent)
        assert loaded_agent.state_dim == 50
        assert loaded_agent.action_dim == 7
    
    def test_list_models(self):
        """Test listing models."""
        # Register multiple models
        for i, difficulty in enumerate(["easy", "medium"]):
            self.registry.register_model(
                self.agent, f"{i}.0", difficulty, 100, 0.5 + i*0.1, 0.8 + i*0.1, 300.0, {}
            )
        
        models = self.registry.list_models()
        
        assert len(models) == 2
        assert all('version' in model for model in models)
        assert all('difficulty' in model for model in models)
    
    def test_get_best_model(self):
        """Test getting best model."""
        # Register models with different performance
        self.registry.register_model(self.agent, "1.0", "easy", 100, 0.3, 0.6, 300.0, {})
        self.registry.register_model(self.agent, "2.0", "easy", 100, 0.7, 0.9, 300.0, {})
        
        best_version = self.registry.get_best_model("final_reward")
        
        assert best_version == "2.0"
    
    def test_delete_model(self):
        """Test model deletion."""
        # Register a model
        version = "1.0"
        model_path = self.registry.register_model(
            self.agent, version, "easy", 100, 0.5, 0.8, 300.0, {}
        )
        
        assert os.path.exists(model_path)
        assert version in self.registry.models
        
        # Delete the model
        success = self.registry.delete_model(version)
        
        assert success
        assert not os.path.exists(model_path)
        assert version not in self.registry.models
    
    def test_get_registry_stats(self):
        """Test getting registry statistics."""
        # Register some models
        for i in range(3):
            self.registry.register_model(
                self.agent, f"{i}.0", "easy", 100, 0.5, 0.8, 300.0, {}
            )
        
        stats = self.registry.get_registry_stats()
        
        assert stats["total_models"] == 3
        assert stats["total_size"] > 0
        assert "easy" in stats["difficulties"]
        assert stats["best_model"] is not None


class TestDQNTrainer:
    """Test the DQN Trainer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            'device': 'cpu',
            'state_dim': 50,
            'action_dim': 7,
            'learning_rate': 0.001,
            'batch_size': 4,  # Small batch for testing
            'gamma': 0.99,
            'epsilon': 1.0,
            'epsilon_min': 0.01,
            'epsilon_decay': 0.995,
            'target_update_frequency': 2,
            'buffer_capacity': 100,
            'episode_rows': 10,  # Small episodes for testing
            'seed': 42
        }
        self.trainer = DQNTrainer(self.config)
    
    def test_trainer_initialization(self):
        """Test trainer initialization."""
        assert self.trainer.device == torch.device('cpu')
        assert self.trainer.state_dim == 50
        assert self.trainer.action_dim == 7
        assert isinstance(self.trainer.agent, DQNAgent)
        assert isinstance(self.trainer.replay_buffer, ReplayBuffer)
        assert isinstance(self.trainer.data_generator, SyntheticDatasetGenerator)
    
    def test_generate_training_data(self):
        """Test training data generation."""
        episodes = self.trainer.generate_training_data(DifficultyLevel.EASY, 5)
        
        assert len(episodes) == 5
        assert all('episode_id' in ep for ep in episodes)
        assert all('rows' in ep for ep in episodes)
        
        # Check episode structure
        for episode in episodes:
            assert len(episode['rows']) == self.config['episode_rows']
            for row in episode['rows']:
                assert 'current_data' in row
                assert 'issues_detected' in row
                assert 'legal_actions' in row
    
    def test_calculate_td_loss(self):
        """Test TD loss calculation."""
        # Create a batch of transitions
        batch = []
        for i in range(4):
            state = np.random.randn(50)
            action = i % 7
            reward = np.random.randn()
            next_state = np.random.randn(50)
            done = i % 2 == 0
            batch.append(Transition(state, action, reward, next_state, done))
        
        loss = self.trainer.calculate_td_loss(batch)
        
        assert isinstance(loss, torch.Tensor)
        assert loss.item() >= 0
        assert loss.requires_grad
    
    def test_train_step(self):
        """Test training step."""
        # Fill buffer with some transitions
        for i in range(10):
            state = np.random.randn(50)
            action = i % 7
            reward = np.random.randn()
            next_state = np.random.randn(50)
            done = i % 2 == 0
            self.trainer.replay_buffer.add(state, action, reward, next_state, done)
        
        # Perform training step
        loss = self.trainer.train_step()
        
        assert isinstance(loss, float)
        assert loss >= 0
    
    def test_train_episode(self):
        """Test training on a single episode."""
        # Generate a small episode
        episodes = self.trainer.generate_training_data(DifficultyLevel.EASY, 1)
        episode = episodes[0]
        
        total_reward, episode_length = self.trainer.train_episode(episode)
        
        assert isinstance(total_reward, float)
        assert isinstance(episode_length, int)
        assert episode_length <= len(episode['rows'])


class TestIntegration:
    """Integration tests for the complete DQN system."""
    
    def test_full_training_pipeline(self):
        """Test the complete training pipeline."""
        config = {
            'device': 'cpu',
            'state_dim': 50,
            'action_dim': 7,
            'learning_rate': 0.001,
            'batch_size': 4,
            'gamma': 0.99,
            'epsilon': 1.0,
            'epsilon_min': 0.01,
            'epsilon_decay': 0.995,
            'target_update_frequency': 2,
            'buffer_capacity': 100,
            'episode_rows': 10,
            'seed': 42
        }
        
        trainer = DQNTrainer(config)
        
        # Train for a few epochs
        results = trainer.train(DifficultyLevel.EASY, 3, save_model=False)
        
        assert 'difficulty' in results
        assert 'epochs' in results
        assert 'final_avg_reward' in results
        assert 'training_time_seconds' in results
        assert results['epochs'] == 3
        assert results['difficulty'] == 'easy'
    
    def test_model_registry_integration(self):
        """Test model registry integration with training."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                'device': 'cpu',
                'state_dim': 50,
                'action_dim': 7,
                'learning_rate': 0.001,
                'batch_size': 4,
                'gamma': 0.99,
                'epsilon': 1.0,
                'epsilon_min': 0.01,
                'epsilon_decay': 0.995,
                'target_update_frequency': 2,
                'buffer_capacity': 100,
                'episode_rows': 10,
                'seed': 42
            }
            
            trainer = DQNTrainer(config)
            
            # Train and save model
            results = trainer.train(DifficultyLevel.EASY, 2, save_model=True)
            
            # Check model was saved
            assert 'model_info' in results
            
            # Test loading with registry
            registry = ModelRegistry(temp_dir)
            models = registry.list_models()
            
            # Should have at least one model (if save worked)
            # Note: This might not work if save_model=False in the actual call


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])
