"""
Agent Coordinator for multi-agent data cleaning system.

This module implements the coordinator that selects the best specialist
agent for each observation based on confidence and expected rewards.
"""

from typing import Dict, Any, List
import logging
from collections import defaultdict
from .base_agent import Agent
from .specialist_agents import (
    FillMissingAgent,
    DuplicateDetector,
    OutlierHandler,
    CategoryStandardizer,
    SkipAgent,
)


class AgentCoordinator:
    """
    Coordinates multiple specialist agents to select the best action.

    Logic:
    1. Analyze current_row and issues_detected
    2. Get recommendations from all agents
    3. Select agent with highest confidence + best expected reward
    4. Execute selected agent's action
    5. Track success rate for future decisions
    """

    def __init__(self):
        """Initialize the coordinator with all specialist agents."""
        self.logger = logging.getLogger("AgentCoordinator")
        self.agents = self._initialize_agents()
        self.agent_success_rates = defaultdict(list)
        self.agent_usage_counts = defaultdict(int)
        self.episode_history = []

    def _initialize_agents(self) -> List[Agent]:
        """Initialize all specialist agents."""
        return [
            FillMissingAgent(),
            DuplicateDetector(),
            OutlierHandler(),
            CategoryStandardizer(),
            SkipAgent(),  # Always include as fallback
        ]

    def reset(self, observation: Dict[str, Any]) -> None:
        """Reset coordinator and all agents for new episode."""
        self.episode_history = []

        for agent in self.agents:
            agent.reset(observation)

        self.logger.info("AgentCoordinator reset for new episode")

    def get_best_action(
        self, observation: Dict[str, Any], legal_actions: List[str]
    ) -> Dict[str, Any]:
        """
        Select the best action from all available agents.

        Args:
            observation: Current environment observation
            legal_actions: List of legally available actions

        Returns:
            Dict with keys: action_type, column, value
        """
        # Get recommendations from all agents
        agent_recommendations = self._get_agent_recommendations(
            observation, legal_actions
        )

        if not agent_recommendations:
            self.logger.warning("No agent recommendations available, using SkipAgent")
            return self._get_skip_action(observation)

        # Select best agent based on confidence and expected reward
        best_agent, best_action = self._select_best_agent(
            agent_recommendations, observation
        )

        # Track usage
        self.agent_usage_counts[best_agent.get_name()] += 1

        # Store in episode history
        self.episode_history.append(
            {
                "agent": best_agent.get_name(),
                "action": best_action,
                "confidence": best_agent.get_confidence(),
                "observation": observation,
            }
        )

        self.logger.info(
            "Selected %s with confidence %.2f",
            best_agent.get_name(),
            best_agent.get_confidence(),
        )

        return best_action

    def update_agent_performance(self, agent_name: str, reward: float) -> None:
        """
        Update agent performance tracking based on received reward.

        Args:
            agent_name: Name of the agent that performed the action
            reward: Reward received from environment
        """
        self.agent_success_rates[agent_name].append(reward)
        self.agent_usage_counts[agent_name] += 1  # Also track usage

        # Keep only recent performance data (last 100 rewards)
        if len(self.agent_success_rates[agent_name]) > 100:
            self.agent_success_rates[agent_name] = self.agent_success_rates[agent_name][
                -100:
            ]

    def get_agent_statistics(self) -> Dict[str, Dict[str, float]]:
        """
        Get performance statistics for all agents.

        Returns:
            Dict mapping agent names to their statistics
        """
        stats = {}
        total_actions = sum(self.agent_usage_counts.values())

        # Include all agents, even those without usage
        all_agent_names = [agent.get_name() for agent in self.agents]

        for agent_name in all_agent_names:
            rewards = self.agent_success_rates.get(agent_name, [])
            avg_reward = sum(rewards) / len(rewards) if rewards else 0.0
            usage_count = self.agent_usage_counts.get(agent_name, 0)

            stats[agent_name] = {
                "usage_count": usage_count,
                "average_reward": avg_reward,
                "total_actions": len(rewards),
                "success_rate": (
                    sum(1 for r in rewards if r > 0) / len(rewards) if rewards else 0.0
                ),
            }

        # Add total actions summary
        stats["total_actions"] = total_actions

        return stats

    def _get_agent_recommendations(
        self, observation: Dict[str, Any], legal_actions: List[str]
    ) -> List[tuple]:
        """
        Get recommendations from all capable agents.

        Returns:
            List of (agent, action) tuples
        """
        recommendations = []

        for agent in self.agents:
            try:
                # Check if agent can handle this observation
                if not agent.can_handle(observation):
                    continue

                # Get action recommendation
                action = agent.get_action(observation, legal_actions)

                # Only consider if action is not skip (unless it's the only option)
                if action["action_type"] != "skip" or agent.get_name() == "SkipAgent":
                    recommendations.append((agent, action))

            except Exception as e:
                self.logger.error(
                    f"Error getting recommendation from {agent.get_name()}: {e}"
                )
                continue

        return recommendations

    def _select_best_agent(
        self, recommendations: List[tuple], observation: Dict[str, Any]
    ) -> tuple:
        """
        Select the best agent from recommendations.

        Args:
            recommendations: List of (agent, action) tuples
            observation: Current observation for context

        Returns:
            Tuple of (best_agent, best_action)
        """
        if not recommendations:
            return self.agents[-1], self._get_skip_action(
                observation
            )  # SkipAgent is last

        # Calculate scores for each agent
        scored_recommendations = []
        for agent, action in recommendations:
            score = self._calculate_agent_score(agent, observation)
            scored_recommendations.append((agent, action, score))

        # Sort by score (descending)
        scored_recommendations.sort(key=lambda x: x[2], reverse=True)

        # Return best recommendation
        best_agent, best_action, best_score = scored_recommendations[0]

        self.logger.debug(
            "Agent scores: %s",
            [(agent.get_name(), score) for agent, _, score in scored_recommendations],
        )

        return best_agent, best_action

    def _calculate_agent_score(
        self, agent: Agent, observation: Dict[str, Any]
    ) -> float:
        """
        Calculate a composite score for agent selection.

        Score combines:
        - Agent confidence (0.0 to 1.0)
        - Historical performance (average reward)
        - Issue-specific expertise
        """
        confidence = agent.get_confidence()
        agent_name = agent.get_name()

        # Get historical performance
        rewards = self.agent_success_rates[agent_name]
        avg_reward = sum(rewards) / len(rewards) if rewards else 0.0

        # Normalize average reward to [0, 1] range.
        # Assumes rewards are usually in the range [-0.5, 0.5].
        normalized_performance = avg_reward + 0.5  # Shift to [0, 1]
        normalized_performance = max(0.0, min(1.0, normalized_performance))

        # Issue-specific expertise bonus
        expertise_bonus = self._calculate_expertise_bonus(agent, observation)

        # Composite score
        score = (
            0.4 * confidence  # Current confidence
            + 0.3 * normalized_performance  # Historical performance
            + 0.3 * expertise_bonus  # Issue-specific expertise
        )

        return score

    def _calculate_expertise_bonus(
        self, agent: Agent, observation: Dict[str, Any]
    ) -> float:
        """
        Calculate expertise bonus based on issue types.

        Different agents have expertise in different types of issues.
        """
        issues = observation.get("issues_detected", [])
        agent_name = agent.get_name()

        # Issue-to-agent mapping
        issue_expertise = {
            "FillMissingAgent": ["missing:"],
            "DuplicateDetector": ["duplicate"],
            "OutlierHandler": ["outlier"],
            "CategoryStandardizer": ["category", "formatting"],
            "SkipAgent": [],  # No specific expertise
        }

        if agent_name not in issue_expertise:
            return 0.0

        agent_issues = issue_expertise[agent_name]
        if not agent_issues:
            return 0.0  # SkipAgent gets no expertise bonus

        # Check if agent's expertise matches current issues
        matching_issues = 0
        for issue in issues:
            for expertise in agent_issues:
                if expertise in issue:
                    matching_issues += 1
                    break

        # Bonus based on number of matching issues
        if matching_issues > 0:
            return min(1.0, 0.3 + (matching_issues * 0.2))

        return 0.0

    def _get_skip_action(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """Get skip action from SkipAgent."""
        current_data = observation.get("current_data", {})
        first_col = list(current_data.keys())[0] if current_data else "id"

        return {"action_type": "skip", "column": first_col, "value": None}

    def get_episode_summary(self) -> Dict[str, Any]:
        """
        Get summary of the current episode.

        Returns:
            Dict with episode statistics
        """
        agent_counts = defaultdict(int)
        total_confidence = 0.0

        for step in self.episode_history:
            agent_counts[step["agent"]] += 1
            total_confidence += step["confidence"]

        avg_confidence = (
            total_confidence / len(self.episode_history)
            if self.episode_history
            else 0.0
        )

        return {
            "total_steps": len(self.episode_history),
            "agent_usage": dict(agent_counts),
            "average_confidence": avg_confidence,
            "episode_history": self.episode_history,
        }
