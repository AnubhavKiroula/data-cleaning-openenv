"""
Experience Replay Buffer for DQN training.

This module implements a replay buffer to store and sample transitions
for off-policy learning in Deep Q-Networks.
"""
import numpy as np
import random
from typing import List, Tuple, Dict, Any, Optional
import logging
from collections import deque
from .dqn_model import Transition


class ReplayBuffer:
    """
    Experience Replay Buffer for DQN training.
    
    Stores transitions (state, action, reward, next_state, done) and
    provides random sampling for training stability.
    """
    
    def __init__(self, capacity: int = 10000):
        """
        Initialize replay buffer.
        
        Args:
            capacity: Maximum number of transitions to store
        """
        self.capacity = capacity
        self.buffer = deque(maxlen=capacity)
        self.logger = logging.getLogger("ReplayBuffer")
        
        # Statistics
        self.total_added = 0
        self.total_sampled = 0
        
        self.logger.info(f"ReplayBuffer initialized with capacity: {capacity}")
    
    def add(self, state: np.ndarray, action: int, reward: float, 
            next_state: np.ndarray, done: bool) -> None:
        """
        Add a transition to the buffer.
        
        Args:
            state: Current state observation
            action: Action taken
            reward: Reward received
            next_state: Next state observation
            done: Whether episode is done
        """
        transition = Transition(state, action, reward, next_state, done)
        self.buffer.append(transition)
        self.total_added += 1
        
        # Log periodically
        if self.total_added % 1000 == 0:
            self.logger.debug(f"Added {self.total_added} transitions to buffer")
    
    def sample(self, batch_size: int) -> List[Transition]:
        """
        Sample a batch of transitions from the buffer.
        
        Args:
            batch_size: Number of transitions to sample
            
        Returns:
            List of sampled transitions
            
        Raises:
            ValueError: If buffer doesn't contain enough transitions
        """
        if len(self.buffer) < batch_size:
            raise ValueError(f"Not enough transitions in buffer. "
                           f"Have {len(self.buffer)}, need {batch_size}")
        
        transitions = random.sample(list(self.buffer), batch_size)
        self.total_sampled += batch_size
        
        return transitions
    
    def sample_tensors(self, batch_size: int):
        """
        Sample a batch and convert to tensors for training.
        
        Args:
            batch_size: Number of transitions to sample
            
        Returns:
            Tuple of tensors (states, actions, rewards, next_states, dones)
        """
        transitions = self.sample(batch_size)
        
        # Batch the transitions
        batch = Transition(*zip(*transitions))
        
        # Convert to numpy arrays first, then to tensors
        states = np.array(batch.state, dtype=np.float32)
        actions = np.array(batch.action, dtype=np.int64)
        rewards = np.array(batch.reward, dtype=np.float32)
        next_states = np.array(batch.next_state, dtype=np.float32)
        dones = np.array(batch.done, dtype=np.float32)
        
        return states, actions, rewards, next_states, dones
    
    def is_full(self) -> bool:
        """Check if buffer is at capacity."""
        return len(self.buffer) >= self.capacity
    
    def size(self) -> int:
        """Get current buffer size."""
        return len(self.buffer)
    
    def clear(self) -> None:
        """Clear all transitions from buffer."""
        self.buffer.clear()
        self.total_added = 0
        self.total_sampled = 0
        self.logger.info("ReplayBuffer cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get buffer statistics.
        
        Returns:
            Dictionary with buffer statistics
        """
        if not self.buffer:
            return {
                "size": 0,
                "capacity": self.capacity,
                "utilization": 0.0,
                "total_added": self.total_added,
                "total_sampled": self.total_sampled
            }
        
        # Calculate reward statistics
        rewards = [t.reward for t in self.buffer]
        
        return {
            "size": len(self.buffer),
            "capacity": self.capacity,
            "utilization": len(self.buffer) / self.capacity,
            "total_added": self.total_added,
            "total_sampled": self.total_sampled,
            "reward_mean": np.mean(rewards),
            "reward_std": np.std(rewards),
            "reward_min": np.min(rewards),
            "reward_max": np.max(rewards),
            "done_rate": np.mean([t.done for t in self.buffer])
        }
    
    def save_buffer(self, filepath: str) -> None:
        """
        Save buffer to file.
        
        Args:
            filepath: Path to save buffer
        """
        import pickle
        
        buffer_data = {
            'buffer': list(self.buffer),
            'capacity': self.capacity,
            'total_added': self.total_added,
            'total_sampled': self.total_sampled
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(buffer_data, f)
        
        self.logger.info(f"Buffer saved to {filepath}")
    
    def load_buffer(self, filepath: str) -> None:
        """
        Load buffer from file.
        
        Args:
            filepath: Path to load buffer from
        """
        import pickle
        
        with open(filepath, 'rb') as f:
            buffer_data = pickle.load(f)
        
        self.buffer = deque(buffer_data['buffer'], maxlen=buffer_data['capacity'])
        self.capacity = buffer_data['capacity']
        self.total_added = buffer_data['total_added']
        self.total_sampled = buffer_data['total_sampled']
        
        self.logger.info(f"Buffer loaded from {filepath}")


class PrioritizedReplayBuffer(ReplayBuffer):
    """
    Prioritized Experience Replay Buffer.
    
    Samples transitions based on their TD-error priority for more efficient learning.
    """
    
    def __init__(self, capacity: int = 10000, alpha: float = 0.6, beta: float = 0.4):
        """
        Initialize prioritized replay buffer.
        
        Args:
            capacity: Maximum number of transitions to store
            alpha: Priority exponent (how much to prioritize)
            beta: Importance sampling exponent
        """
        super().__init__(capacity)
        self.alpha = alpha
        self.beta = beta
        self.priorities = deque(maxlen=capacity)
        self.max_priority = 1.0
        
    def add(self, state: np.ndarray, action: int, reward: float,
            next_state: np.ndarray, done: bool) -> None:
        """
        Add a transition with maximum priority.
        
        Args:
            state: Current state observation
            action: Action taken
            reward: Reward received
            next_state: Next state observation
            done: Whether episode is done
        """
        transition = Transition(state, action, reward, next_state, done)
        self.buffer.append(transition)
        self.priorities.append(self.max_priority)
        self.total_added += 1
    
    def sample(self, batch_size: int) -> Tuple[List[Transition], np.ndarray, np.ndarray]:
        """
        Sample based on priorities.
        
        Args:
            batch_size: Number of transitions to sample
            
        Returns:
            Tuple of (transitions, indices, weights)
        """
        if len(self.buffer) < batch_size:
            raise ValueError(f"Not enough transitions in buffer. "
                           f"Have {len(self.buffer)}, need {batch_size}")
        
        # Calculate sampling probabilities
        priorities = np.array(self.priorities)
        probs = priorities ** self.alpha
        probs /= probs.sum()
        
        # Sample indices
        indices = np.random.choice(len(self.buffer), batch_size, p=probs)
        
        # Calculate importance sampling weights
        weights = (len(self.buffer) * probs[indices]) ** (-self.beta)
        weights /= weights.max()  # Normalize for stability
        
        # Get transitions
        transitions = [self.buffer[i] for i in indices]
        
        self.total_sampled += batch_size
        
        return transitions, indices, weights
    
    def update_priorities(self, indices: List[int], td_errors: np.ndarray) -> None:
        """
        Update priorities based on TD-errors.
        
        Args:
            indices: Indices of sampled transitions
            td_errors: TD-errors for those transitions
        """
        for idx, td_error in zip(indices, td_errors):
            priority = abs(td_error) + 1e-6  # Small epsilon to avoid zero priority
            self.priorities[idx] = priority
            self.max_priority = max(self.max_priority, priority)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get buffer statistics including priority information."""
        stats = super().get_statistics()
        
        if self.priorities:
            priorities = np.array(self.priorities)
            stats.update({
                "priority_mean": np.mean(priorities),
                "priority_std": np.std(priorities),
                "priority_min": np.min(priorities),
                "priority_max": np.max(priorities),
                "alpha": self.alpha,
                "beta": self.beta
            })
        
        return stats
