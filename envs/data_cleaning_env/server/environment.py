"""
Streaming IoT sensor-denoising RL environment (OpenEnv-compatible).

The agent observes one sensor reading at a time together with a rolling window
of the last ``N`` values it has already emitted, chooses one of six corrective
actions, and receives a magnitude-aware reward. It never sees a future reading,
and it never sees the reference signal.

Two invariants carry the research claim, and both are enforced here rather than
left to convention:

**Streaming.** ``_make_observation`` reads only ``self.dataset[i]`` for
``i == current_row_index`` and only ``self.emitted`` for already-processed
steps. There is no path by which a future sample can enter an observation.

**No oracle leakage.** The task generator annotates each row with
``ground_truth``, ``fault_type``, ``reference_imputed`` and ``is_corrupted``.
These are needed to compute the training reward, but they are stripped from
``current_data`` before the observation is returned, so a downstream encoder
physically cannot read them even by accident. A previous revision passed the
raw row straight through, leaving the no-leakage property dependent on the
encoder's choice of keys.

**Action semantics live here.** Each of the six actions has exactly one
definition, expressed over the rolling history, so it can be unit-tested
independently of any agent. An agent may supply an explicit ``value`` to
override the canonical correction, but is not required to compute one.
"""

import os
import sys
import uuid
from copy import deepcopy
from typing import Any, Dict, List, Optional

import numpy as np

# Make the repository root importable when this module is loaded directly by
# the standalone environment server rather than as part of the package.
_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if _REPO_ROOT not in sys.path:
    sys.path.append(_REPO_ROOT)

from backend.ml.metrics import carry_forward  # noqa: E402
from backend.ml.reward_shaper import RewardShaper  # noqa: E402

# Fully qualified, so that a same-named module elsewhere on sys.path cannot
# shadow the environment's own task definitions.
from envs.data_cleaning_env.tasks.graders import (  # noqa: E402
    NON_OBSERVABLE_FIELDS,
    ORACLE_FIELDS,
    TASKS,
)

HIDDEN_FIELDS = tuple(ORACLE_FIELDS) + tuple(NON_OBSERVABLE_FIELDS)

#: The six-action discrete space of master plan section 2.2, in index order.
ACTION_SPACE = [
    "skip",
    "remove_outlier",
    "fill_missing",
    "fix_type",
    "remove_duplicate",
    "fix_category",
]

DEFAULT_HISTORY_LEN = 5


class DataCleaningEnvironment:
    """Sequential, online sensor-stream denoising environment."""

    def __init__(
        self,
        history_len: int = DEFAULT_HISTORY_LEN,
        action_cost: float = 0.0,
    ):
        self.history_len = history_len
        self.action_cost = action_cost
        self.reward_shaper = RewardShaper(action_cost=action_cost)

        self.episode_id: Optional[str] = None
        self.task_name: Optional[str] = None
        self.dataset: List[Dict[str, Any]] = []
        self.cleaned_data: List[Dict[str, Any]] = []
        #: Values actually emitted so far, carry-forward filled. This is the
        #: agent's entire memory of the past and the basis of every action.
        self.emitted: List[float] = []
        self.current_row_index = 0
        self.step_count = 0
        self.total_reward = 0.0
        self.done = False
        self.grader = None

    # ------------------------------------------------------------------ core

    def reset(self, task_name: str = "iot_stream", **kwargs) -> Dict[str, Any]:
        """Start a new streaming episode."""
        if task_name not in TASKS:
            raise ValueError(
                f"Unknown task: {task_name}. Choose from {list(TASKS.keys())}"
            )

        task = TASKS[task_name]
        self.episode_id = str(uuid.uuid4())[:8]
        self.task_name = task_name
        self.dataset = task["generate"](**kwargs)
        self.grader = task["grade"]

        self.cleaned_data = []
        self.emitted = []
        self.current_row_index = 0
        self.step_count = 0
        self.total_reward = 0.0
        self.done = False
        self.reward_shaper.reset_episode(len(self.dataset))

        return self._make_observation(reward=0.0)

    def step(
        self, action_type: str, column: str = "value", value: Any = None
    ) -> Dict[str, Any]:
        """Apply one action to the current reading and advance the stream."""
        if self.done:
            raise ValueError("Episode is done. Call reset() first.")
        if action_type not in ACTION_SPACE:
            raise ValueError(
                f"Unknown action '{action_type}'. Choose from {ACTION_SPACE}."
            )

        row = deepcopy(self.dataset[self.current_row_index])
        gt = float(row["ground_truth"])
        raw = row.get("value")
        stats = self._rolling_stats()

        # The do-nothing error. For a dropout there is no reading, so the
        # reference policy is carry-forward, which is what a real pipeline does.
        raw_present = raw is not None and np.isfinite(float(raw))
        do_nothing = float(raw) if raw_present else self._carry_value(gt)
        error_raw = abs(do_nothing - gt)

        cleaned_value = self._apply_action(action_type, raw, value, stats)
        # Only 'skip' may leave a dropout un-imputed; the metrics charge for it.
        if cleaned_value is None:
            error_cleaned = abs(self._carry_value(gt) - gt)
        else:
            error_cleaned = abs(float(cleaned_value) - gt)

        reward = self.reward_shaper.compute_stream_reward(
            action_type, error_raw, error_cleaned
        )

        row["value"] = None if cleaned_value is None else float(cleaned_value)
        row["action_taken"] = action_type
        row["reward"] = reward

        self.cleaned_data.append(row)
        self.emitted.append(
            float(cleaned_value) if cleaned_value is not None else self._carry_value(gt)
        )
        self.current_row_index += 1
        self.step_count += 1
        self.total_reward += reward

        if self.current_row_index >= len(self.dataset):
            self.done = True

        return self._make_observation(reward=reward)

    # --------------------------------------------------------------- actions

    def _apply_action(
        self,
        action_type: str,
        raw: Optional[float],
        override: Any,
        stats: Dict[str, float],
    ) -> Optional[float]:
        """
        Compute the cleaned value for one action (master plan section 2.2).

        With no history yet (the first step of an episode) every corrective
        action has nothing to correct against, so it degrades gracefully to the
        raw reading — or to 0.0 if even that is missing.
        """
        if override is not None and action_type != "skip":
            return float(override)

        has_raw = raw is not None and np.isfinite(float(raw))
        raw_f = float(raw) if has_raw else None
        has_hist = len(self.emitted) > 0

        if action_type == "skip":
            # a0: retain the reading exactly as received, dropout included.
            return raw_f

        if not has_hist:
            return raw_f if has_raw else 0.0

        if action_type == "remove_outlier":
            # a1: replace a high-amplitude transient with the rolling median.
            return stats["median"]

        if action_type == "fill_missing":
            # a2: impute a dropout from the rolling median. Applied to a
            # present reading it is a false correction, and scored as one.
            return stats["median"] if not has_raw else stats["median"]

        if action_type == "fix_type":
            # a3: recalibrate a drifting sensor halfway to the rolling baseline.
            if not has_raw:
                return stats["mean"]
            return 0.5 * raw_f + 0.5 * stats["mean"]

        if action_type == "remove_duplicate":
            # a4: discard a repeated packet and extrapolate the local trend.
            last = self.emitted[-1]
            trend = (
                self.emitted[-1] - self.emitted[-2] if len(self.emitted) >= 2 else 0.0
            )
            return last + trend

        if action_type == "fix_category":
            # a5: normalisation fallback — clamp the reading into the envelope
            # spanned by the rolling history.
            if not has_raw:
                return stats["median"]
            return float(min(max(raw_f, stats["min"]), stats["max"]))

        return raw_f

    # ---------------------------------------------------------- observation

    def _rolling_stats(self) -> Dict[str, float]:
        """Statistics over the last ``history_len`` emitted values."""
        hist = self.emitted[-self.history_len :]
        if not hist:
            return {
                "mean": 0.0,
                "std": 0.0,
                "median": 0.0,
                "min": 0.0,
                "max": 0.0,
            }
        arr = np.asarray(hist, dtype=float)
        return {
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "median": float(np.median(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
        }

    def _carry_value(self, fallback: float) -> float:
        """Most recently emitted value, or ``fallback`` at a cold start."""
        return self.emitted[-1] if self.emitted else float(fallback)

    def _make_observation(self, reward: float) -> Dict[str, Any]:
        """
        Build the agent-visible observation.

        Oracle annotations are removed from ``current_data`` here. Everything
        else is derived from the current reading and the agent's own emission
        history, so the observation is computable at deployment time from a
        single packet plus ``history_len`` retained values.
        """
        if self.done or self.current_row_index >= len(self.dataset):
            return {
                "current_row": self.current_row_index,
                "total_rows": len(self.dataset),
                "current_data": {},
                "rolling_history": [],
                "rolling_stats": {"mean": 0.0, "std": 0.0, "median": 0.0},
                "issues_detected": [],
                "legal_actions": [],
                "progress": 1.0,
                "reward": round(reward, 4),
                "done": self.done,
            }

        row = self.dataset[self.current_row_index]
        current_data = {k: v for k, v in row.items() if k not in HIDDEN_FIELDS}
        stats = self._rolling_stats()
        issues = self._detect_issues(current_data, stats)

        return {
            "current_row": self.current_row_index,
            "total_rows": len(self.dataset),
            "current_data": current_data,
            "rolling_history": list(self.emitted[-self.history_len :]),
            "rolling_stats": {
                "mean": stats["mean"],
                "std": stats["std"],
                "median": stats["median"],
            },
            "issues_detected": issues,
            "legal_actions": list(ACTION_SPACE),
            "progress": round(
                self.current_row_index / max(len(self.dataset), 1), 4
            ),
            "reward": round(reward, 4),
            "done": self.done,
        }

    def _detect_issues(
        self, row: Dict[str, Any], stats: Dict[str, float]
    ) -> List[str]:
        """
        Heuristic fault flags, computed only from observable quantities.

        These are *detections*, not the generator's labels: they are what a
        deployed device could compute from the packet plus its own history.
        """
        issues: List[str] = []
        val = row.get("value")

        if val is None or not np.isfinite(float(val)):
            issues.append("missing:sensor")
            return issues

        val = float(val)
        if not self.emitted:
            return issues

        deviation = abs(val - stats["mean"])
        if stats["std"] > 1e-4 and deviation > 3.0 * stats["std"]:
            issues.append("outlier:spike")
        if stats["std"] > 1e-4 and deviation > 1.5 * stats["std"]:
            issues.append("drift:offset")
        if abs(val - self.emitted[-1]) < 1e-9:
            issues.append("duplicate:transmission")

        return issues

    # --------------------------------------------------------------- summary

    def get_state(self) -> Dict[str, Any]:
        """Episode summary, including the graded score once finished."""
        score, msg = (0.0, "")
        if self.done and self.grader:
            score, msg = self.grader(self.cleaned_data)
        return {
            "episode_id": self.episode_id,
            "task_name": self.task_name,
            "step_count": self.step_count,
            "total_reward": round(self.total_reward, 4),
            "rows_cleaned": len(self.cleaned_data),
            "score": score,
            "message": msg,
        }

    def emitted_series(self) -> np.ndarray:
        """The episode's emitted stream, carry-forward filled."""
        return carry_forward([r.get("value") for r in self.cleaned_data])
