import uuid
import sys
import os
import numpy as np
from typing import Any, Dict, List, Optional
from copy import deepcopy

# Fix path so 'tasks' module can be found
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tasks.graders import TASKS


class DataCleaningEnvironment:
    """
    Data Cleaning & Streaming Denoising RL Environment.
    Supports both legacy tabular records and sequential IoT sensor telemetry streams.
    """

    def __init__(self, history_len: int = 5):
        self.episode_id = None
        self.task_name = None
        self.dataset = []
        self.cleaned_data = []
        self.current_row_index = 0
        self.step_count = 0
        self.total_reward = 0.0
        self.done = False
        self.grader = None
        self.history_len = history_len

    def reset(self, task_name: str = "iot_stream", **kwargs) -> Dict[str, Any]:
        """Start a new episode with the given task."""
        if task_name not in TASKS:
            raise ValueError(f"Unknown task: {task_name}. Choose from {list(TASKS.keys())}")

        task = TASKS[task_name]
        self.episode_id = str(uuid.uuid4())[:8]
        self.task_name = task_name

        if task_name == "iot_stream":
            self.dataset = task["generate"](**kwargs)
        else:
            self.dataset = task["generate"]()

        self.cleaned_data = []
        self.current_row_index = 0
        self.step_count = 0
        self.total_reward = 0.0
        self.done = False
        self.grader = task["grade"]

        return self._make_observation(reward=0.0)

    def step(self, action_type: str, column: str = "value", value: Any = None) -> Dict[str, Any]:
        """Apply an action to the current reading/row."""
        if self.done:
            raise ValueError("Episode done. Call reset() first.")

        current_row = deepcopy(self.dataset[self.current_row_index])
        reward = 0.0

        if self.task_name == "iot_stream":
            reward = self._step_iot_stream(current_row, action_type, column, value)
        else:
            reward = self._step_tabular(current_row, action_type, column, value)

        self.cleaned_data.append(current_row)
        self.current_row_index += 1
        self.step_count += 1
        self.total_reward += reward

        if self.current_row_index >= len(self.dataset):
            self.done = True

        return self._make_observation(reward=reward)

    def _step_iot_stream(
        self, current_row: Dict[str, Any], action_type: str, column: str, value: Any
    ) -> float:
        """
        Step logic tailored to streaming IoT telemetry denoising with magnitude-aware rewards.
        """
        gt = current_row.get("ground_truth", 0.0)
        raw_val = current_row.get("value")
        raw_err = abs(float(raw_val) - gt) if raw_val is not None else 5.0
        rolling_hist = [
            r.get("value")
            for r in self.cleaned_data[-self.history_len :]
            if r.get("value") is not None
        ]
        rolling_mean = float(np.mean(rolling_hist)) if rolling_hist else gt
        rolling_med = float(np.median(rolling_hist)) if rolling_hist else gt

        reward = 0.0

        if action_type == "fill_missing":
            if raw_val is None:
                # Agent fills dropout
                fill_val = value if value is not None else rolling_mean
                current_row["value"] = float(fill_val)
                new_err = abs(current_row["value"] - gt)
                # Magnitude-aware reward
                reward = 0.3 + max(-0.2, (raw_err - new_err) * 0.2)
            else:
                # Value was not missing; unnecessary imputation penalty
                reward = -0.15

        elif action_type == "remove_outlier":
            if raw_val is not None and (raw_err > 2.0 or current_row.get("fault_type") == "spike"):
                # Agent removes spike
                clean_val = value if value is not None else rolling_med
                current_row["value"] = float(clean_val)
                new_err = abs(current_row["value"] - gt)
                reward = 0.4 + max(-0.2, (raw_err - new_err) * 0.25)
            else:
                # False positive outlier removal penalty
                reward = -0.15

        elif action_type == "fix_type":
            # Recalibrate drift offset
            if current_row.get("fault_type") == "drift" or raw_err > 0.5:
                # Offset correction towards rolling baseline
                recalibrated = value if value is not None else (0.5 * float(raw_val) + 0.5 * rolling_mean)
                current_row["value"] = float(recalibrated)
                new_err = abs(current_row["value"] - gt)
                reward = 0.3 + max(-0.2, (raw_err - new_err) * 0.2)
            else:
                reward = -0.1

        elif action_type == "remove_duplicate":
            # Duplicate transmission filter
            if current_row.get("fault_type") == "duplicate" and len(self.cleaned_data) > 0:
                prev_val = self.cleaned_data[-1].get("value", rolling_mean)
                # Linear trend extrapolation
                trend = (
                    (self.cleaned_data[-1].get("value", 0) - self.cleaned_data[-2].get("value", 0))
                    if len(self.cleaned_data) >= 2
                    else 0.0
                )
                current_row["value"] = float(value) if value is not None else float(prev_val + trend)
                new_err = abs(current_row["value"] - gt)
                reward = 0.35 + max(-0.2, (raw_err - new_err) * 0.2)
            else:
                reward = -0.1

        elif action_type == "skip":
            if raw_val is not None and raw_err < 0.3:
                # Properly preserved pristine reading
                reward = 0.15
            else:
                # Missed an anomaly
                reward = -0.2 - min(0.5, raw_err * 0.1)

        else:
            reward = -0.2

        return round(float(reward), 3)

    def _step_tabular(
        self, current_row: Dict[str, Any], action_type: str, column: str, value: Any
    ) -> float:
        """Legacy tabular step logic for backward compatibility."""
        reward = 0.0
        if action_type == "fill_missing":
            if current_row.get(column) is None:
                current_row[column] = value
                reward += 0.3
            else:
                reward -= 0.1

        elif action_type == "fix_type":
            try:
                current_row[column] = float(current_row[column])
                reward += 0.2
            except (ValueError, TypeError):
                reward -= 0.1

        elif action_type == "remove_duplicate":
            is_dup = any(
                r.get("email") == current_row.get("email")
                and r.get("name") == current_row.get("name")
                for r in self.cleaned_data
            )
            if is_dup:
                reward += 0.4
            else:
                reward -= 0.2

        elif action_type == "fix_category":
            category_map = {
                "eng": "Engineering", "engineering": "Engineering",
                "ENGINEERING": "Engineering",
                "hr": "HR", "h.r.": "HR", "H.R.": "HR",
                "finance": "Finance", "FINANCE": "Finance",
            }
            raw = str(current_row.get(column, ""))
            if raw in category_map:
                current_row[column] = category_map[raw]
                reward += 0.3
            else:
                reward -= 0.1

        elif action_type == "remove_outlier":
            val = current_row.get(column)
            if val is not None and (val > 200000 or val < 0):
                current_row[column] = 70000
                reward += 0.4
            else:
                reward -= 0.1

        elif action_type == "skip":
            reward -= 0.1

        return reward

    def get_state(self) -> Dict[str, Any]:
        score = 0.0
        msg = ""
        if self.done and self.grader:
            score, msg = self.grader(self.cleaned_data)
        return {
            "episode_id": self.episode_id,
            "task_name": self.task_name,
            "step_count": self.step_count,
            "total_reward": round(self.total_reward, 3),
            "rows_cleaned": len(self.cleaned_data),
            "score": score,
            "message": msg,
        }

    def _detect_issues(self, row: Dict[str, Any]) -> List[str]:
        issues = []
        if self.task_name == "iot_stream":
            val = row.get("value")
            if val is None:
                issues.append("missing:sensor")
            else:
                rolling_hist = [
                    r.get("value")
                    for r in self.cleaned_data[-self.history_len :]
                    if r.get("value") is not None
                ]
                if rolling_hist:
                    hist_mean = float(np.mean(rolling_hist))
                    hist_std = float(np.std(rolling_hist))
                    if hist_std > 1e-4 and abs(val - hist_mean) > 3.0 * hist_std:
                        issues.append("outlier:spike")
                    if abs(val - hist_mean) > 1.5:
                        issues.append("drift:offset")
                if len(self.cleaned_data) > 0:
                    prev_val = self.cleaned_data[-1].get("value")
                    if prev_val is not None and abs(val - prev_val) < 1e-6:
                        issues.append("duplicate:transmission")
        else:
            for col, val in row.items():
                if val is None:
                    issues.append(f"missing:{col}")
                if isinstance(val, str):
                    try:
                        float(val)
                        issues.append(f"wrong_type:{col}")
                    except ValueError:
                        pass
        return issues

    def _make_observation(self, reward: float) -> Dict[str, Any]:
        if self.done or self.current_row_index >= len(self.dataset):
            current_data = {}
            issues = []
            legal_actions = []
            rolling_history = []
            rolling_stats = {"mean": 0.0, "std": 0.0, "median": 0.0}
        else:
            current_data = self.dataset[self.current_row_index]
            issues = self._detect_issues(current_data)
            legal_actions = self._get_legal_actions(current_data, issues)

            # Extract rolling history of past readings
            rolling_history = [
                r.get("value")
                for r in self.cleaned_data[-self.history_len :]
                if r.get("value") is not None
            ]
            if rolling_history:
                rolling_stats = {
                    "mean": float(np.mean(rolling_history)),
                    "std": float(np.std(rolling_history)),
                    "median": float(np.median(rolling_history)),
                }
            else:
                rolling_stats = {"mean": 0.0, "std": 0.0, "median": 0.0}

        return {
            "current_row": self.current_row_index,
            "total_rows": len(self.dataset),
            "current_data": current_data,
            "rolling_history": rolling_history,
            "rolling_stats": rolling_stats,
            "issues_detected": issues,
            "legal_actions": legal_actions,
            "progress": round(self.current_row_index / max(len(self.dataset), 1), 2),
            "reward": round(reward, 3),
            "done": self.done,
        }

    def _get_legal_actions(self, row: Dict[str, Any], issues: List[str]) -> List[str]:
        # Always allow skip and general cleaning actions
        return [
            "skip",
            "fill_missing",
            "remove_outlier",
            "fix_type",
            "remove_duplicate",
            "fix_category",
        ]