"""
Magnitude-aware reward shaping for streaming sensor denoising.

This implements the reward of ``docs/RESEARCH_PIVOT_MASTER_PLAN.md`` section 2.3:

    R_t = R_base + min(0.45, 0.2 * (e_raw - e_clean))        if error decreased
          -0.15  - min(0.35, 0.2 * (e_clean - e_raw))        if error increased
          +0.15                                               if skip and e_raw < 0.2

where ``e_raw = |y_t - y*_t|`` is the error of leaving the reading alone and
``e_clean = |y_clean - y*_t|`` is the error after the action.

Two properties matter for the research claim:

* The reward is **outcome-based**. It is a function of how much error the action
  actually removed, never of the generator's fault label. An earlier revision
  gated each action's reward on ``row["fault_type"]``, which rewarded matching
  an oracle annotation rather than improving the signal, and produced a policy
  that had learned nothing transferable.
* The reward is **bounded**. Both magnitude terms are clipped, so a single
  extreme spike cannot dominate an episode's return and destabilise the
  Bellman targets.

An optional ``action_cost`` extends the specification: a fixed penalty charged
for any non-skip action, whether or not it helped. The published reward uses
0.0, which reproduces section 2.3 exactly. A positive cost prices intervention,
so the policy must expect to gain more than the cost before acting -- the direct
remedy for over-correcting streams that need nothing. See
``backend/ml/sweep_action_cost.py``.

The reward uses ground truth and is therefore a *training-time* signal only. It
is not available at deployment, and nothing in it reaches the agent's
observation — see ``DataCleaningEnvironment._make_observation``.
"""

import logging
from collections import defaultdict
from typing import Any, Dict, Optional

# Section 2.3 constants.
SKIP_TOLERANCE = 0.2
SKIP_REWARD = 0.15
FALSE_CORRECTION_PENALTY = -0.15
MAGNITUDE_SCALE = 0.2
MAX_IMPROVEMENT_BONUS = 0.45
MAX_DEGRADATION_PENALTY = 0.35
REWARD_CLIP = 1.0

#: Default cost charged for any corrective action, in reward units.
#: 0.0 reproduces the master plan's reward exactly.
DEFAULT_ACTION_COST = 0.0


class RewardShaper:
    """Computes the magnitude-aware streaming denoising reward."""

    #: Per-action base reward, paid only when the action reduced the error.
    base_rewards = {
        "fill_missing": 0.30,
        "remove_outlier": 0.30,
        "remove_duplicate": 0.35,
        "fix_type": 0.25,
        "fix_category": 0.25,
        "skip": -0.15,
    }

    def __init__(self, action_cost: float = DEFAULT_ACTION_COST):
        """
        Args:
            action_cost: Fixed penalty subtracted from every non-skip reward,
                charged whether or not the action helped. Section 2.3 of the
                master plan specifies no such cost, so 0.0 is the published
                configuration. A positive cost makes intervention a decision
                with a price rather than a free option, which is the direct
                remedy for a policy that over-corrects streams needing nothing.
        """
        self.action_cost = float(action_cost)
        self.logger = logging.getLogger("RewardShaper")
        self.action_history = []
        self.reward_history = []
        self.action_rewards = defaultdict(list)

    def reset_episode(self, total_steps_estimate: int = 24) -> None:
        """Clear per-episode bookkeeping."""
        self.action_history = []
        self.reward_history = []
        self.total_steps_estimate = total_steps_estimate

    def compute_stream_reward(
        self,
        action_type: str,
        error_raw: float,
        error_cleaned: float,
        record: bool = True,
    ) -> float:
        """
        Score one denoising decision.

        Args:
            action_type: The action taken, one of :attr:`base_rewards`.
            error_raw: ``|y_t - y*_t|``, the error of doing nothing. For a
                dropout this is the error of the carry-forward value, so
                imputation is rewarded exactly for beating carry-forward.
            error_cleaned: ``|y_clean - y*_t|`` after applying the action.
            record: Whether to append to the episode's reward statistics.

        Returns:
            The clipped reward.
        """
        if action_type == "skip":
            reward = SKIP_REWARD if error_raw < SKIP_TOLERANCE else FALSE_CORRECTION_PENALTY
        else:
            delta = error_raw - error_cleaned
            if delta > 1e-9:
                base = self.base_rewards.get(action_type, 0.0)
                reward = base + min(MAX_IMPROVEMENT_BONUS, MAGNITUDE_SCALE * delta)
            else:
                # No improvement, or an actively harmful correction.
                reward = FALSE_CORRECTION_PENALTY - min(
                    MAX_DEGRADATION_PENALTY, MAGNITUDE_SCALE * (-delta)
                )

        if action_type != "skip":
            reward -= self.action_cost

        reward = float(max(-REWARD_CLIP, min(REWARD_CLIP, reward)))

        if record:
            self.action_history.append(action_type)
            self.reward_history.append(reward)
            self.action_rewards[action_type].append(reward)

        return round(reward, 4)

    def calculate_episode_completion_bonus(self, final_score: float) -> float:
        """Terminal bonus for a well-denoised episode."""
        if final_score >= 0.9:
            return 0.5
        if final_score >= 0.7:
            return 0.2
        return 0.0

    def get_reward_statistics(self) -> Dict[str, Any]:
        """Per-action reward summary for training diagnostics."""
        return {
            "total_reward": float(sum(self.reward_history)),
            "steps": len(self.reward_history),
            "mean_reward": (
                float(sum(self.reward_history) / len(self.reward_history))
                if self.reward_history
                else 0.0
            ),
            "action_counts": {
                a: len(rs) for a, rs in sorted(self.action_rewards.items())
            },
            "action_mean_reward": {
                a: float(sum(rs) / len(rs))
                for a, rs in sorted(self.action_rewards.items())
                if rs
            },
        }
