"""
Reward Shaper for multi-agent data cleaning system.

This module implements sophisticated reward calculation beyond simple
bonuses, incorporating progress, consistency, and performance metrics.
"""

from typing import Dict, Any
import logging
from collections import defaultdict


class RewardShaper:
    """
    Calculates sophisticated rewards for agent actions.

    Logic:
    - Base reward: action-specific (+0.3, etc)
    - Progress bonus: +0.05 per 20% episode completion
    - Consistency bonus: +0.1 if this action type fixed similar issues before
    - Penalty: -0.2 if action contradicts previous decisions
    - Perfect run bonus: +0.5 if episode completes with score >= 0.9
    """

    def __init__(self):
        """Initialize the reward shaper."""
        self.logger = logging.getLogger("RewardShaper")

        # Base rewards for different action types
        self.base_rewards = {
            "fill_missing": 0.3,
            "remove_duplicate": 0.35,
            "remove_outlier": 0.3,
            "fix_category": 0.3,
            "fix_type": 0.25,
            "fix_formatting": 0.25,
            "skip": -0.15,  # Penalty for not acting
        }

        # Track action history for consistency bonuses/penalties
        self.action_history = []
        self.action_success_rates = defaultdict(list)
        self.episode_progress = 0.0
        self.total_steps_estimate = 50  # Default estimate

        # Track issue resolution patterns
        self.issue_action_mapping = defaultdict(list)

    def reset_episode(self, total_steps_estimate: int = 50) -> None:
        """
        Reset reward shaper for new episode.

        Args:
            total_steps_estimate: Estimated total steps for progress calculation
        """
        self.action_history = []
        self.episode_progress = 0.0
        self.total_steps_estimate = total_steps_estimate

        self.logger.info("RewardShaper reset for new episode")

    def calculate_reward(
        self,
        action: Dict[str, Any],
        observation: Dict[str, Any],
        episode_state: Dict[str, Any],
    ) -> float:
        """
        Calculate sophisticated reward for an action.

        Args:
            action: Action taken by agent
            observation: Current environment observation
            episode_state: Current episode state information

        Returns:
            Calculated reward value
        """
        action_type = action.get("action_type", "skip")

        # 1. Base reward
        base_reward = self._get_base_reward(action_type)

        # 2. Progress bonus
        progress_bonus = self._calculate_progress_bonus(episode_state)

        # 3. Consistency bonus
        consistency_bonus = self._calculate_consistency_bonus(action, observation)

        # 4. Contradiction penalty
        contradiction_penalty = self._calculate_contradiction_penalty(
            action, observation
        )

        # 5. Issue-specific adjustments
        issue_adjustment = self._calculate_issue_adjustment(action, observation)

        # 6. Skip action bonus (for not breaking data)
        skip_bonus = self._calculate_skip_bonus(action, observation)

        # Total reward
        total_reward = (
            base_reward
            + progress_bonus
            + consistency_bonus
            + contradiction_penalty
            + issue_adjustment
            + skip_bonus
        )

        # Clamp reward to reasonable range
        total_reward = max(-1.0, min(1.0, total_reward))

        # Update tracking
        self._update_tracking(action, observation, total_reward)

        self.logger.debug(
            f"Reward calculation for {action_type}: {total_reward:.3f} "
            f"(base: {base_reward:.3f}, progress: {progress_bonus:.3f}, "
            "consistency: "
            f"{consistency_bonus:.3f}, contradiction: "
            f"{contradiction_penalty:.3f})"
        )

        return total_reward

    def calculate_episode_completion_bonus(self, final_score: float) -> float:
        """
        Calculate bonus for episode completion.

        Args:
            final_score: Final episode score in [0, 1] range

        Returns:
            Completion bonus
        """
        if final_score >= 0.9:
            return 0.5  # Perfect run bonus
        elif final_score >= 0.8:
            return 0.3  # Excellent run bonus
        elif final_score >= 0.7:
            return 0.2  # Good run bonus
        elif final_score >= 0.6:
            return 0.1  # Acceptable run bonus
        else:
            return 0.0  # No bonus for poor performance

    def _get_base_reward(self, action_type: str) -> float:
        """Get base reward for action type."""
        return self.base_rewards.get(action_type, 0.0)

    def _calculate_progress_bonus(self, episode_state: Dict[str, Any]) -> float:
        """
        Calculate progress bonus based on episode completion.

        Args:
            episode_state: Current episode state

        Returns:
            Progress bonus
        """
        current_step = episode_state.get("step", 0)
        total_steps = episode_state.get("total_steps", self.total_steps_estimate)

        if total_steps <= 0:
            return 0.0

        # Calculate progress percentage
        progress = current_step / total_steps

        # Bonus for every 20% of episode completed
        progress_segments = int(progress * 5)  # 5 segments of 20% each
        return progress_segments * 0.05

    def _calculate_consistency_bonus(
        self, action: Dict[str, Any], observation: Dict[str, Any]
    ) -> float:
        """
        Calculate consistency bonus for successful action patterns.

        Args:
            action: Current action
            observation: Current observation

        Returns:
            Consistency bonus
        """
        action_type = action.get("action_type", "skip")
        # Look for similar issue-action pairs in history
        successful_patterns = 0
        total_patterns = 0

        for hist_action, hist_observation, hist_reward in self.action_history:
            if hist_action.get("action_type") == action_type:
                total_patterns += 1
                if hist_reward > 0:  # Successful action
                    successful_patterns += 1

        if total_patterns == 0:
            return 0.0

        # Bonus based on success rate
        success_rate = successful_patterns / total_patterns
        if success_rate >= 0.8:
            return 0.1  # High consistency bonus
        elif success_rate >= 0.6:
            return 0.05  # Medium consistency bonus
        else:
            return 0.0  # No consistency bonus

    def _calculate_contradiction_penalty(
        self, action: Dict[str, Any], observation: Dict[str, Any]
    ) -> float:
        """
        Calculate penalty for actions that contradict previous decisions.

        Args:
            action: Current action
            observation: Current observation

        Returns:
            Contradiction penalty
        """
        action_type = action.get("action_type", "skip")
        column = action.get("column", "")

        # Check for contradictions in recent history
        recent_actions = self.action_history[-5:]  # Last 5 actions

        for hist_action, hist_observation, _ in recent_actions:
            # Contradiction: same column was recently modified differently.
            if (
                hist_action.get("column") == column
                and hist_action.get("action_type") != action_type
                and hist_action.get("action_type") != "skip"
            ):
                return -0.2  # Contradiction penalty

        return 0.0

    def _calculate_issue_adjustment(
        self, action: Dict[str, Any], observation: Dict[str, Any]
    ) -> float:
        """
        Calculate issue-specific reward adjustments.

        Args:
            action: Current action
            observation: Current observation

        Returns:
            Issue adjustment
        """
        action_type = action.get("action_type", "skip")
        issues = observation.get("issues_detected", [])

        adjustment = 0.0

        for issue in issues:
            if action_type == "fill_missing" and "missing:" in issue:
                adjustment += 0.1  # Bonus for addressing missing values
            elif action_type == "remove_duplicate" and "duplicate" in issue:
                adjustment += 0.1  # Bonus for addressing duplicates
            elif action_type == "remove_outlier" and "outlier" in issue:
                adjustment += 0.1  # Bonus for addressing outliers
            elif action_type == "fix_category" and (
                "category" in issue or "formatting" in issue
            ):
                adjustment += 0.05  # Smaller bonus for category issues
            elif action_type == "fix_type" and "type" in issue:
                adjustment += 0.05  # Smaller bonus for type issues

        return adjustment

    def _calculate_skip_bonus(
        self, action: Dict[str, Any], observation: Dict[str, Any]
    ) -> float:
        """
        Calculate bonus for skip actions when appropriate.

        Args:
            action: Current action
            observation: Current observation

        Returns:
            Skip bonus
        """
        if action.get("action_type") != "skip":
            return 0.0

        issues = observation.get("issues_detected", [])

        # Bonus for skipping when there are no major issues
        major_issues = ["missing:", "duplicate", "outlier"]
        has_major_issues = any(
            issue.startswith(prefix) for issue in issues for prefix in major_issues
        )

        if not has_major_issues:
            return 0.1  # Bonus for appropriate skipping

        return 0.0

    def _update_tracking(
        self, action: Dict[str, Any], observation: Dict[str, Any], reward: float
    ) -> None:
        """
        Update internal tracking for future reward calculations.

        Args:
            action: Action taken
            observation: Current observation
            reward: Calculated reward
        """
        # Add to action history
        self.action_history.append((action, observation, reward))

        # Keep history manageable (last 100 actions)
        if len(self.action_history) > 100:
            self.action_history = self.action_history[-100:]

        # Update issue-action mapping
        action_type = action.get("action_type", "skip")
        column = action.get("column", "")
        issues = observation.get("issues_detected", [])

        for issue in issues:
            issue_key = f"{issue}:{column}"
            self.issue_action_mapping[issue_key].append(
                {
                    "action": action_type,
                    "reward": reward,
                    "timestamp": len(self.action_history),
                }
            )

    def get_reward_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about reward distribution.

        Returns:
            Reward statistics
        """
        if not self.action_history:
            return {"total_actions": 0}

        rewards = [reward for _, _, reward in self.action_history]

        return {
            "total_actions": len(rewards),
            "average_reward": sum(rewards) / len(rewards),
            "max_reward": max(rewards),
            "min_reward": min(rewards),
            "positive_actions": sum(1 for r in rewards if r > 0),
            "negative_actions": sum(1 for r in rewards if r < 0),
            "action_type_distribution": self._get_action_type_distribution(),
        }

    def _get_action_type_distribution(self) -> Dict[str, Dict[str, float]]:
        """Get reward distribution by action type."""
        distribution = defaultdict(lambda: {"count": 0, "total_reward": 0.0})

        for action, _, reward in self.action_history:
            action_type = action.get("action_type", "skip")
            distribution[action_type]["count"] += 1
            distribution[action_type]["total_reward"] += reward

        # Convert to averages
        result = {}
        for action_type, stats in distribution.items():
            result[action_type] = {
                "count": stats["count"],
                "average_reward": stats["total_reward"] / stats["count"],
                "total_reward": stats["total_reward"],
            }

        return result
