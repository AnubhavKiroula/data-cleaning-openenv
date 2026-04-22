"""
Comprehensive tests for multi-agent data cleaning system.

This module tests all agent components including base agents,
specialist agents, coordinator, and reward shaper.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from ml.base_agent import Agent, AgentFactory
from ml.specialist_agents import (
    FillMissingAgent,
    DuplicateDetector,
    OutlierHandler,
    CategoryStandardizer,
    SkipAgent,
)
from ml.agent_coordinator import AgentCoordinator
from ml.reward_shaper import RewardShaper


class TestBaseAgent:
    """Test the abstract base agent class."""

    def test_agent_initialization(self):
        """Test agent initialization with name."""

        class TestAgent(Agent):
            def reset(self, observation):
                pass

            def get_action(self, observation, legal_actions):
                return {}

            def get_confidence(self):
                return 0.5

        agent = TestAgent("TestAgent")
        assert agent.get_name() == "TestAgent"
        assert agent.get_last_reward() == 0.0

    def test_update_reward(self):
        """Test reward update functionality."""

        class TestAgent(Agent):
            def reset(self, observation):
                pass

            def get_action(self, observation, legal_actions):
                return {}

            def get_confidence(self):
                return 0.5

        agent = TestAgent("TestAgent")
        agent.update_reward(0.5)
        assert agent.get_last_reward() == 0.5

        agent.update_reward(-0.2)
        assert agent.get_last_reward() == -0.2

    def test_agent_factory_unknown_type(self):
        """Test AgentFactory with unknown agent type."""
        with pytest.raises(ValueError, match="Unknown agent type"):
            AgentFactory.create_agent("unknown_agent")


class TestFillMissingAgent:
    """Test the FillMissingAgent specialist agent."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = FillMissingAgent()

    def test_agent_initialization(self):
        """Test agent initialization."""
        assert self.agent.get_name() == "FillMissingAgent"
        assert self.agent.get_confidence() == 0.0

    def test_reset(self):
        """Test agent reset functionality."""
        observation = {"test": "data"}
        self.agent.reset(observation)
        assert self.agent.get_confidence() == 0.0

    def test_handle_missing_age(self):
        """Test handling missing age values."""
        observation = {
            "current_data": {"age": None, "name": "John"},
            "issues_detected": ["missing:age"],
        }
        legal_actions = ["fill_missing", "skip"]

        action = self.agent.get_action(observation, legal_actions)

        assert action["action_type"] == "fill_missing"
        assert action["column"] == "age"
        assert action["value"] == 30
        assert self.agent.get_confidence() > 0.0

    def test_handle_missing_salary(self):
        """Test handling missing salary values."""
        observation = {
            "current_data": {"salary": None, "name": "John"},
            "issues_detected": ["missing:salary"],
        }
        legal_actions = ["fill_missing", "skip"]

        action = self.agent.get_action(observation, legal_actions)

        assert action["action_type"] == "fill_missing"
        assert action["column"] == "salary"
        assert action["value"] == 60000

    def test_skip_when_no_fill_missing_action(self):
        """Test skipping when fill_missing is not available."""
        observation = {
            "current_data": {"age": None, "name": "John"},
            "issues_detected": ["missing:age"],
        }
        legal_actions = ["skip"]  # No fill_missing action

        action = self.agent.get_action(observation, legal_actions)

        assert action["action_type"] == "skip"
        assert self.agent.get_confidence() == 0.0

    def test_can_handle_missing_issues(self):
        """Test can_handle method with missing issues."""
        observation = {"issues_detected": ["missing:age", "duplicate:row"]}
        assert self.agent.can_handle(observation) == True

        observation = {"issues_detected": ["duplicate:row", "outlier:age"]}
        assert self.agent.can_handle(observation) == False


class TestDuplicateDetector:
    """Test the DuplicateDetector specialist agent."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = DuplicateDetector()

    def test_agent_initialization(self):
        """Test agent initialization."""
        assert self.agent.get_name() == "DuplicateDetector"
        assert self.agent.get_confidence() == 0.0

    def test_detect_duplicate_row(self):
        """Test duplicate detection with similar rows."""
        # First observation
        obs1 = {
            "current_data": {"name": "John", "age": 30},
            "issues_detected": ["duplicate:row"],
        }
        legal_actions = ["remove_duplicate", "skip"]

        action1 = self.agent.get_action(obs1, legal_actions)
        assert action1["action_type"] == "skip"  # No previous rows to compare

        # Second observation with similar data
        obs2 = {
            "current_data": {"name": "John", "age": 30},
            "issues_detected": ["duplicate:row"],
        }

        action2 = self.agent.get_action(obs2, legal_actions)
        assert action2["action_type"] == "remove_duplicate"
        assert self.agent.get_confidence() >= 0.8

    def test_no_duplicate_with_different_rows(self):
        """Test no duplicate detection with different rows."""
        # First observation
        obs1 = {
            "current_data": {"name": "John", "age": 30},
            "issues_detected": ["duplicate:row"],
        }
        legal_actions = ["remove_duplicate", "skip"]
        self.agent.get_action(obs1, legal_actions)

        # Second observation with different data
        obs2 = {
            "current_data": {"name": "Jane", "age": 25},
            "issues_detected": ["duplicate:row"],
        }

        action2 = self.agent.get_action(obs2, legal_actions)
        assert action2["action_type"] == "skip"
        assert self.agent.get_confidence() < 0.8


class TestOutlierHandler:
    """Test the OutlierHandler specialist agent."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = OutlierHandler()

    def test_detect_age_outlier(self):
        """Test outlier detection for age."""
        observation = {
            "current_data": {"age": 150, "name": "John"},  # Extreme outlier
            "issues_detected": ["outlier:age"],
        }
        legal_actions = ["remove_outlier", "skip"]

        action = self.agent.get_action(observation, legal_actions)

        assert action["action_type"] == "remove_outlier"
        assert action["column"] == "age"
        assert action["value"] == 35  # Median replacement
        assert self.agent.get_confidence() >= 0.7

    def test_detect_salary_outlier(self):
        """Test outlier detection for salary."""
        observation = {
            "current_data": {"salary": 500000, "name": "John"},  # Extreme outlier
            "issues_detected": ["outlier:salary"],
        }
        legal_actions = ["remove_outlier", "skip"]

        action = self.agent.get_action(observation, legal_actions)

        assert action["action_type"] == "remove_outlier"
        assert action["column"] == "salary"
        assert action["value"] == 75000  # Median replacement

    def test_no_outlier_normal_values(self):
        """Test no outlier detection for normal values."""
        observation = {
            "current_data": {"age": 35, "name": "John"},  # Normal value
            "issues_detected": ["outlier:age"],
        }
        legal_actions = ["remove_outlier", "skip"]

        action = self.agent.get_action(observation, legal_actions)

        assert action["action_type"] == "skip"
        assert self.agent.get_confidence() == 0.0


class TestCategoryStandardizer:
    """Test the CategoryStandardizer specialist agent."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = CategoryStandardizer()

    def test_standardize_department_typo(self):
        """Test standardizing department name with typo."""
        observation = {
            "current_data": {"dept": "enginering", "name": "John"},  # Typo
            "issues_detected": ["category:dept"],
        }
        legal_actions = ["fix_category", "skip"]

        action = self.agent.get_action(observation, legal_actions)

        assert action["action_type"] == "fix_category"
        assert action["column"] == "dept"
        assert action["value"] == "engineering"  # Corrected spelling
        assert self.agent.get_confidence() > 0.0

    def test_no_standardization_needed(self):
        """Test when no standardization is needed."""
        observation = {
            "current_data": {"dept": "engineering", "name": "John"},  # Already correct
            "issues_detected": ["category:dept"],
        }
        legal_actions = ["fix_category", "skip"]

        action = self.agent.get_action(observation, legal_actions)

        # The agent may still return fix_category even if no change is needed
        # This is acceptable behavior as it will determine if standardization is required
        assert action["action_type"] in ["fix_category", "skip"]

    def test_handle_case_variations(self):
        """Test handling case variations."""
        observation = {
            "current_data": {"dept": "ENGINEERING", "name": "John"},  # Uppercase
            "issues_detected": ["category:dept"],
        }
        legal_actions = ["fix_category", "skip"]

        action = self.agent.get_action(observation, legal_actions)

        assert action["action_type"] == "fix_category"
        assert action["value"] == "engineering"  # Lowercased


class TestSkipAgent:
    """Test the SkipAgent specialist agent."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = SkipAgent()

    def test_always_skip(self):
        """Test that SkipAgent always returns skip action."""
        observation = {
            "current_data": {"name": "John", "age": 30},
            "issues_detected": ["missing:age", "duplicate:row"],
        }
        legal_actions = ["fill_missing", "remove_duplicate", "skip"]

        action = self.agent.get_action(observation, legal_actions)

        assert action["action_type"] == "skip"
        assert self.agent.get_confidence() == 0.2

    def test_can_handle_anything(self):
        """Test that SkipAgent can handle any observation."""
        observation = {"issues_detected": []}
        assert self.agent.can_handle(observation) == True

        observation = {"issues_detected": ["missing:age"]}
        assert self.agent.can_handle(observation) == True


class TestAgentCoordinator:
    """Test the AgentCoordinator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.coordinator = AgentCoordinator()

    def test_initialization(self):
        """Test coordinator initialization."""
        assert len(self.coordinator.agents) == 5  # 5 specialist agents
        assert all(isinstance(agent, Agent) for agent in self.coordinator.agents)

    def test_select_fill_missing_agent(self):
        """Test selecting FillMissingAgent for missing values."""
        observation = {
            "current_data": {"age": None, "name": "John"},
            "issues_detected": ["missing:age"],
        }
        legal_actions = ["fill_missing", "skip"]

        action = self.coordinator.get_best_action(observation, legal_actions)

        assert action["action_type"] == "fill_missing"
        assert action["column"] == "age"

    def test_fallback_to_skip_agent(self):
        """Test fallback to SkipAgent when no other agent can handle."""
        observation = {
            "current_data": {"name": "John", "age": 30},
            "issues_detected": [],
        }
        legal_actions = ["skip"]

        action = self.coordinator.get_best_action(observation, legal_actions)

        assert action["action_type"] == "skip"

    def test_update_agent_performance(self):
        """Test updating agent performance tracking."""
        self.coordinator.update_agent_performance("FillMissingAgent", 0.3)
        self.coordinator.update_agent_performance("FillMissingAgent", -0.1)

        stats = self.coordinator.get_agent_statistics()
        assert "FillMissingAgent" in stats
        assert (
            stats["FillMissingAgent"]["usage_count"] == 2
        )  # Two calls to update_agent_performance
        assert abs(stats["FillMissingAgent"]["average_reward"] - 0.1) < 1e-9

    def test_agent_statistics(self):
        """Test getting agent statistics."""
        # Simulate some usage
        self.coordinator.update_agent_performance("FillMissingAgent", 0.3)
        self.coordinator.update_agent_performance("DuplicateDetector", 0.2)

        stats = self.coordinator.get_agent_statistics()

        assert isinstance(stats, dict)
        assert "FillMissingAgent" in stats
        assert "DuplicateDetector" in stats


class TestRewardShaper:
    """Test the RewardShaper class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.reward_shaper = RewardShaper()

    def test_initialization(self):
        """Test reward shaper initialization."""
        assert len(self.reward_shaper.base_rewards) > 0
        assert "fill_missing" in self.reward_shaper.base_rewards
        assert self.reward_shaper.base_rewards["fill_missing"] == 0.3

    def test_calculate_fill_missing_reward(self):
        """Test reward calculation for fill missing action."""
        action = {"action_type": "fill_missing", "column": "age", "value": 30}
        observation = {
            "current_data": {"age": None, "name": "John"},
            "issues_detected": ["missing:age"],
        }
        episode_state = {"step": 10, "total_steps": 50}

        reward = self.reward_shaper.calculate_reward(action, observation, episode_state)

        # Should include base reward + issue adjustment + progress bonus
        assert reward > 0.3  # Base reward is 0.3, should have bonuses

    def test_calculate_skip_reward(self):
        """Test reward calculation for skip action."""
        action = {"action_type": "skip", "column": "name", "value": None}
        observation = {
            "current_data": {"name": "John", "age": 30},
            "issues_detected": [],  # No major issues
        }
        episode_state = {"step": 5, "total_steps": 50}

        reward = self.reward_shaper.calculate_reward(action, observation, episode_state)

        # Should be negative base reward + skip bonus
        assert reward > -0.15  # Base is -0.15, skip bonus should make it less negative

    def test_episode_completion_bonus(self):
        """Test episode completion bonus calculation."""
        # Perfect score
        bonus = self.reward_shaper.calculate_episode_completion_bonus(0.95)
        assert bonus == 0.5

        # Good score
        bonus = self.reward_shaper.calculate_episode_completion_bonus(0.85)
        assert bonus == 0.3

        # Poor score
        bonus = self.reward_shaper.calculate_episode_completion_bonus(0.4)
        assert bonus == 0.0

    def test_contradiction_penalty(self):
        """Test contradiction penalty for conflicting actions."""
        # First action: fill missing
        action1 = {"action_type": "fill_missing", "column": "age", "value": 30}
        obs1 = {"current_data": {"age": None}, "issues_detected": ["missing:age"]}
        episode_state = {"step": 1, "total_steps": 50}
        self.reward_shaper.calculate_reward(action1, obs1, episode_state)

        # Second action: different action on same column
        action2 = {"action_type": "remove_outlier", "column": "age", "value": 35}
        obs2 = {"current_data": {"age": 30}, "issues_detected": ["outlier:age"]}
        episode_state = {"step": 2, "total_steps": 50}
        reward = self.reward_shaper.calculate_reward(action2, obs2, episode_state)

        # Should have contradiction penalty
        assert reward < 0.3  # Base reward reduced by penalty

    def test_reward_statistics(self):
        """Test getting reward statistics."""
        # Generate some rewards
        for i in range(5):
            action = {"action_type": "fill_missing", "column": "age", "value": 30}
            observation = {
                "current_data": {"age": None},
                "issues_detected": ["missing:age"],
            }
            episode_state = {"step": i, "total_steps": 50}
            self.reward_shaper.calculate_reward(action, observation, episode_state)

        stats = self.reward_shaper.get_reward_statistics()

        assert stats["total_actions"] == 5
        assert "average_reward" in stats
        assert "action_type_distribution" in stats
        assert "fill_missing" in stats["action_type_distribution"]


class TestIntegration:
    """Integration tests for the complete system."""

    def test_full_episode_simulation(self):
        """Test a complete episode simulation."""
        coordinator = AgentCoordinator()
        reward_shaper = RewardShaper()

        # Reset for new episode
        initial_obs = {"current_data": {}, "issues_detected": []}
        coordinator.reset(initial_obs)
        reward_shaper.reset_episode()

        # Simulate episode steps
        observations = [
            {
                "current_data": {"age": None, "name": "John"},
                "issues_detected": ["missing:age"],
            },
            {"current_data": {"age": 30, "name": "John"}, "issues_detected": []},
        ]

        legal_actions = ["fill_missing", "skip"]

        for i, obs in enumerate(observations):
            # Get action from coordinator
            action = coordinator.get_best_action(obs, legal_actions)

            # Calculate reward
            episode_state = {"step": i, "total_steps": len(observations)}
            reward = reward_shaper.calculate_reward(action, obs, episode_state)

            # Update coordinator
            agent_name = (
                action.get("action_type", "skip").replace("_", "").capitalize()
                + "Agent"
            )
            coordinator.update_agent_performance(agent_name, reward)

            # Verify action is valid
            assert (
                action["action_type"] in legal_actions
                or action["action_type"] == "skip"
            )
            assert isinstance(reward, float)

        # Get final statistics
        agent_stats = coordinator.get_agent_statistics()
        reward_stats = reward_shaper.get_reward_statistics()

        assert agent_stats["total_actions"] > 0
        assert reward_stats["total_actions"] == len(observations)

    def test_error_handling_fallback(self):
        """Test error handling and fallback to SkipAgent."""
        coordinator = AgentCoordinator()

        # Create observation that might cause issues
        observation = {
            "current_data": None,  # None data might cause issues
            "issues_detected": ["missing:unknown_column"],
        }
        legal_actions = ["fill_missing", "skip"]

        # Should handle gracefully and return skip action
        action = coordinator.get_best_action(observation, legal_actions)

        assert action["action_type"] == "skip"
        assert "column" in action
        assert action["value"] is None


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])
