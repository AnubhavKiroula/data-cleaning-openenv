"""
Base Agent class for multi-agent data cleaning system.

This module defines the abstract base class that all specialist agents
must inherit from, providing a common interface for agent operations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import logging


class Agent(ABC):
    """
    Abstract base class for all specialist data cleaning agents.

    All agents must implement the required methods to participate
    in the multi-agent coordination system.
    """

    def __init__(self, name: str):
        """
        Initialize the agent with a name.

        Args:
            name: Human-readable name for the agent
        """
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")
        self._confidence = 0.0
        self._last_reward = 0.0

    @abstractmethod
    def reset(self, observation: Dict[str, Any]) -> None:
        """
        Reset agent state for a new episode.

        Args:
            observation: Initial observation from environment
        """
        pass

    @abstractmethod
    def get_action(
        self, observation: Dict[str, Any], legal_actions: list
    ) -> Dict[str, Any]:
        """
        Select an action based on current observation.

        Args:
            observation: Current environment observation
            legal_actions: List of legally available actions

        Returns:
            Dict with keys: action_type, column, value
        """
        pass

    @abstractmethod
    def get_confidence(self) -> float:
        """
        Get agent's confidence in its last action.

        Returns:
            Confidence score between 0.0 and 1.0
        """
        pass

    def update_reward(self, reward: float) -> None:
        """
        Update agent's internal state based on received reward.

        Args:
            reward: Reward value from environment
        """
        self._last_reward = reward
        self.logger.debug(f"Agent {self.name} received reward: {reward}")

    def can_handle(self, observation: Dict[str, Any]) -> bool:
        """
        Check if agent can handle the current observation.

        Args:
            observation: Current environment observation

        Returns:
            True if agent believes it can help with this observation
        """
        # Default implementation - override in subclasses
        return True

    def get_name(self) -> str:
        """Get agent name."""
        return self.name

    def get_last_reward(self) -> float:
        """Get the last reward received by this agent."""
        return self._last_reward


class AgentFactory:
    """Factory class for creating agent instances."""

    @staticmethod
    def create_agent(agent_type: str, **kwargs) -> Agent:
        """
        Create an agent instance of the specified type.

        Args:
            agent_type: Type of agent to create
            **kwargs: Additional arguments for agent initialization

        Returns:
            Agent instance

        Raises:
            ValueError: If agent_type is not recognized
        """
        # Import specialist agents
        from .specialist_agents import (
            FillMissingAgent,
            DuplicateDetector,
            OutlierHandler,
            CategoryStandardizer,
            SkipAgent
        )
        
        # Import DQN agent
        try:
            from .dqn_model import DQNAgent
        except ImportError:
            DQNAgent = None
        
        agent_classes = {
            "fill_missing": FillMissingAgent,
            "duplicate_detector": DuplicateDetector,
            "outlier_handler": OutlierHandler,
            "category_standardizer": CategoryStandardizer,
            "skip": SkipAgent
        }
        
        # Add DQN agent if available
        if DQNAgent is not None:
            agent_classes["dqn"] = DQNAgent
        
        if agent_type not in agent_classes:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        return agent_classes[agent_type](**kwargs)
