"""
Deep Q-Network (DQN) model for data cleaning reinforcement learning.

This module implements the Q-network architecture and DQN agent for learning
optimal data cleaning policies through experience replay.
"""
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
import logging
from collections import namedtuple
from .base_agent import Agent

# Transition tuple for experience replay
Transition = namedtuple('Transition', ['state', 'action', 'reward', 'next_state', 'done'])


class QNetwork(nn.Module):
    """
    Deep Q-Network for approximating Q-values.
    
    Architecture:
    - Input layer: (state_dim)
    - Hidden layer 1: 128 neurons, ReLU
    - Hidden layer 2: 64 neurons, ReLU  
    - Output layer: (action_dim) - Q-values for each possible action
    """
    
    def __init__(self, state_dim: int, action_dim: int, hidden_dims: List[int] = [128, 64]):
        """
        Initialize Q-network.
        
        Args:
            state_dim: Dimension of state representation
            action_dim: Number of possible actions
            hidden_dims: List of hidden layer dimensions
        """
        super(QNetwork, self).__init__()
        self.logger = logging.getLogger("QNetwork")
        
        # Build network layers
        layers = []
        input_dim = state_dim
        
        # Hidden layers
        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(input_dim, hidden_dim))
            layers.append(nn.ReLU())
            input_dim = hidden_dim
        
        # Output layer
        layers.append(nn.Linear(input_dim, action_dim))
        
        self.network = nn.Sequential(*layers)
        self.state_dim = state_dim
        self.action_dim = action_dim
        
        # Initialize weights
        self._initialize_weights()
        
        self.logger.info(f"QNetwork initialized: state_dim={state_dim}, action_dim={action_dim}")
    
    def _initialize_weights(self):
        """Initialize network weights using Xavier initialization."""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                nn.init.constant_(m.bias, 0)
    
    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through network.
        
        Args:
            state: Input state tensor
            
        Returns:
            Q-values for each action
        """
        return self.network(state)
    
    def get_q_values(self, state: torch.Tensor) -> np.ndarray:
        """
        Get Q-values as numpy array.
        
        Args:
            state: Input state tensor
            
        Returns:
            Q-values as numpy array
        """
        with torch.no_grad():
            q_values = self.forward(state)
            return q_values.cpu().numpy().flatten()


class DQNAgent(Agent):
    """
    DQN Agent that learns optimal data cleaning policies.
    
    Uses epsilon-greedy exploration during training and greedy selection
    during inference for fast action selection.
    """
    
    def __init__(self, state_dim: int, action_dim: int, device: str = "cpu"):
        """
        Initialize DQN agent.
        
        Args:
            state_dim: Dimension of state representation
            action_dim: Number of possible actions
            device: PyTorch device ('cpu' or 'cuda')
        """
        super().__init__("DQNAgent")
        
        self.device = torch.device(device)
        self.state_dim = state_dim
        self.action_dim = action_dim
        
        # Q-networks (main and target)
        self.q_network = QNetwork(state_dim, action_dim).to(self.device)
        self.target_network = QNetwork(state_dim, action_dim).to(self.device)
        
        # Copy weights to target network
        self.target_network.load_state_dict(self.q_network.state_dict())
        
        # Training parameters
        self.epsilon = 1.0
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.gamma = 0.99
        
        # Action mapping (index to action dictionary)
        self.action_mapping = {}
        self.reverse_action_mapping = {}
        
        self.logger = logging.getLogger("DQNAgent")
        self.logger.info(f"DQNAgent initialized on device: {self.device}")
    
    def reset(self, observation: Dict[str, Any]) -> None:
        """Reset agent state for new episode."""
        self._confidence = 0.0
        # Update action mapping based on legal actions
        self._update_action_mapping(observation.get("legal_actions", []))
    
    def get_action(self, observation: Dict[str, Any], legal_actions: List[str]) -> Dict[str, Any]:
        """
        Select action using epsilon-greedy policy.
        
        Args:
            observation: Current environment observation
            legal_actions: List of legally available actions
            
        Returns:
            Selected action dictionary
        """
        # Update action mapping
        self._update_action_mapping(legal_actions)
        
        # Encode observation to state vector
        state = self._encode_observation(observation)
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        
        # Get Q-values
        with torch.no_grad():
            q_values = self.q_network(state_tensor).cpu().numpy()[0]
        
        # Filter Q-values for legal actions only
        legal_q_values = []
        for action_str in legal_actions:
            if action_str in self.reverse_action_mapping:
                action_idx = self.reverse_action_mapping[action_str]
                if action_idx < len(q_values):
                    legal_q_values.append((action_idx, q_values[action_idx]))
        
        if not legal_q_values:
            # Fallback to skip action
            return self._create_skip_action(observation)
        
        # Epsilon-greedy selection
        if np.random.random() < self.epsilon:
            # Explore: random legal action
            action_idx = np.random.choice([idx for idx, _ in legal_q_values])
            self._confidence = 0.1  # Low confidence for random actions
        else:
            # Exploit: action with highest Q-value
            action_idx = max(legal_q_values, key=lambda x: x[1])[0]
            max_q = max(q_values)
            self._confidence = min(1.0, max_q / 10.0)  # Normalize confidence
        
        # Convert index back to action dictionary
        return self._index_to_action(action_idx, observation)
    
    def get_confidence(self) -> float:
        """Get agent's confidence in last action."""
        return self._confidence
    
    def update_reward(self, reward: float) -> None:
        """Update agent's internal state based on received reward."""
        self._last_reward = reward
        self.logger.debug(f"DQNAgent received reward: {reward}")
    
    def _update_action_mapping(self, legal_actions: List[str]):
        """Update mapping between action indices and action dictionaries."""
        self.action_mapping = {}
        self.reverse_action_mapping = {}
        
        for idx, action_str in enumerate(legal_actions):
            # Create a simple action dictionary for each legal action
            if action_str == "skip":
                action_dict = {"action_type": "skip", "column": "id", "value": None}
            elif action_str == "fill_missing":
                action_dict = {"action_type": "fill_missing", "column": "age", "value": 30}
            elif action_str == "remove_duplicate":
                action_dict = {"action_type": "remove_duplicate", "column": "id", "value": None}
            elif action_str == "remove_outlier":
                action_dict = {"action_type": "remove_outlier", "column": "age", "value": 35}
            elif action_str == "fix_category":
                action_dict = {"action_type": "fix_category", "column": "dept", "value": "engineering"}
            elif action_str == "fix_type":
                action_dict = {"action_type": "fix_type", "column": "score", "value": None}
            elif action_str == "fix_formatting":
                action_dict = {"action_type": "fix_formatting", "column": "email", "value": None}
            else:
                action_dict = {"action_type": "skip", "column": "id", "value": None}
            
            self.action_mapping[idx] = action_dict
            self.reverse_action_mapping[action_str] = idx
    
    def _encode_observation(self, observation: Dict[str, Any]) -> np.ndarray:
        """
        Encode observation to state vector.
        
        Args:
            observation: Environment observation
            
        Returns:
            State vector
        """
        # Simple encoding - can be enhanced
        features = []
        
        # Current data features (simplified)
        current_data = observation.get("current_data", {})
        
        # Numeric features
        for col in ["age", "salary", "score"]:
            val = current_data.get(col, 0)
            if val is None:
                features.append(0.0)  # Missing value indicator
            else:
                try:
                    features.append(float(val))
                except (ValueError, TypeError):
                    features.append(0.0)  # Handle string values as missing
        
        # Categorical features (one-hot simplified)
        for col in ["dept", "name", "email"]:
            val = current_data.get(col, "")
            features.append(1.0 if val else 0.0)  # Presence indicator
        
        # Issues detected (binary features)
        all_issues = ["missing:age", "missing:salary", "missing:score", "missing:name",
                      "duplicate:row", "outlier:age", "outlier:salary", "outlier:score",
                      "category:dept", "formatting:email", "formatting:name", "wrong_type:score"]
        issues_detected = observation.get("issues_detected", [])
        
        for issue in all_issues:
            features.append(1.0 if issue in issues_detected else 0.0)
        
        # Legal actions (binary features)
        all_actions = ["skip", "fill_missing", "remove_duplicate", "remove_outlier", 
                      "fix_category", "fix_type", "fix_formatting"]
        legal_actions = observation.get("legal_actions", [])
        
        for action in all_actions:
            features.append(1.0 if action in legal_actions else 0.0)
        
        # Ensure fixed size
        state_vector = np.array(features, dtype=np.float32)
        
        # Pad or truncate to expected size
        expected_size = self.state_dim
        if len(state_vector) < expected_size:
            state_vector = np.pad(state_vector, (0, expected_size - len(state_vector)))
        elif len(state_vector) > expected_size:
            state_vector = state_vector[:expected_size]
        
        return state_vector
    
    def _index_to_action(self, action_idx: int, observation: Dict[str, Any]) -> Dict[str, Any]:
        """Convert action index to action dictionary."""
        if action_idx in self.action_mapping:
            return self.action_mapping[action_idx].copy()
        else:
            return self._create_skip_action(observation)
    
    def _create_skip_action(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """Create skip action."""
        current_data = observation.get("current_data", {})
        first_col = list(current_data.keys())[0] if current_data else "id"
        return {"action_type": "skip", "column": first_col, "value": None}
    
    def decay_epsilon(self):
        """Decay epsilon for exploration."""
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
    
    def update_target_network(self):
        """Update target network with current network weights."""
        self.target_network.load_state_dict(self.q_network.state_dict())
    
    def set_training_mode(self, training: bool = True):
        """Set training/inference mode."""
        self.q_network.train(training)
        self.target_network.train(training)
        
        if not training:
            self.epsilon = 0.0  # No exploration during inference
    
    def save_model(self, filepath: str):
        """Save model state."""
        torch.save({
            'q_network_state_dict': self.q_network.state_dict(),
            'target_network_state_dict': self.target_network.state_dict(),
            'epsilon': self.epsilon,
            'state_dim': self.state_dim,
            'action_dim': self.action_dim
        }, filepath)
        self.logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """Load model state."""
        checkpoint = torch.load(filepath, map_location=self.device)
        self.q_network.load_state_dict(checkpoint['q_network_state_dict'])
        self.target_network.load_state_dict(checkpoint['target_network_state_dict'])
        self.epsilon = checkpoint.get('epsilon', 0.0)
        
        # Validate dimensions
        assert checkpoint['state_dim'] == self.state_dim
        assert checkpoint['action_dim'] == self.action_dim
        
        self.logger.info(f"Model loaded from {filepath}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        total_params = sum(p.numel() for p in self.q_network.parameters())
        trainable_params = sum(p.numel() for p in self.q_network.parameters() if p.requires_grad)
        
        return {
            "model_type": "DQN",
            "state_dim": self.state_dim,
            "action_dim": self.action_dim,
            "total_parameters": total_params,
            "trainable_parameters": trainable_params,
            "epsilon": self.epsilon,
            "device": str(self.device)
        }
