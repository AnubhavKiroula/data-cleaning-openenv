import uuid
from typing import Any, Dict, List, Optional
from copy import deepcopy


class DataCleaningEnvironment:
    """
    Data Cleaning RL Environment.
    Agent receives a messy dataset row by row and must clean it.
    """

    def __init__(self):
        self.episode_id = None
        self.task_name = None
        self.dataset = []
        self.cleaned_data = []
        self.current_row_index = 0
        self.step_count = 0
        self.total_reward = 0.0
        self.done = False
        self.grader = None

    def reset(self, task_name: str = "easy") -> Dict[str, Any]:
        """Start a new episode with the given task."""
        from tasks.graders import TASKS

        if task_name not in TASKS:
            raise ValueError(f"Unknown task: {task_name}. Choose from {list(TASKS.keys())}")

        task = TASKS[task_name]
        self.episode_id = str(uuid.uuid4())[:8]
        self.task_name = task_name
        self.dataset = task["generate"]()
        self.cleaned_data = []
        self.current_row_index = 0
        self.step_count = 0
        self.total_reward = 0.0
        self.done = False
        self.grader = task["grade"]

        return self._make_observation(reward=0.0)

    def step(self, action_type: str, column: str, value: Any = None) -> Dict[str, Any]:
        """Apply a cleaning action to the current row."""
        if self.done:
            raise ValueError("Episode done. Call reset() first.")

        current_row = deepcopy(self.dataset[self.current_row_index])
        reward = 0.0
        issues = self._detect_issues(current_row)

        if action_type == "fill_missing":
            if current_row.get(column) is None:
                current_row[column] = value
                reward += 0.3
            else:
                reward -= 0.1  # Penalize unnecessary action

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
                self.current_row_index += 1
                reward += 0.4
                self.step_count += 1
                self.total_reward += reward
                if self.current_row_index >= len(self.dataset):
                    self.done = True
                return self._make_observation(reward=reward)
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
                current_row[column] = 70000  # Replace with median
                reward += 0.4
            else:
                reward -= 0.1

        elif action_type == "fix_formatting":
            val = current_row.get(column)
            if isinstance(val, str):
                current_row[column] = val.lower().strip()
                reward += 0.2
            else:
                reward -= 0.1

        elif action_type == "skip":
            reward -= 0.2  # Penalize skipping

        else:
            reward -= 0.3  # Unknown action

        self.cleaned_data.append(current_row)
        self.current_row_index += 1
        self.step_count += 1
        self.total_reward += reward

        if self.current_row_index >= len(self.dataset):
            self.done = True

        return self._make_observation(reward=reward)

    def get_state(self) -> Dict[str, Any]:
        score = 0.0
        if self.done and self.grader:
            score, _ = self.grader(self.cleaned_data)
        return {
            "episode_id": self.episode_id,
            "task_name": self.task_name,
            "step_count": self.step_count,
            "total_reward": round(self.total_reward, 3),
            "rows_cleaned": len(self.cleaned_data),
            "score": score,
        }

    def _detect_issues(self, row: Dict[str, Any]) -> List[str]:
        issues = []
        for col, val in row.items():
            if val is None:
                issues.append(f"missing:{col}")
            if isinstance(val, str):
                try:
                    float(val)
                    issues.append(f"wrong_type:{col}")
                except ValueError:
                    pass
                if val != val.lower():
                    issues.append(f"formatting:{col}")
        return issues

    def _make_observation(self, reward: float) -> Dict[str, Any]:
        if self.done or self.current_row_index >= len(self.dataset):
            current_data = {}
            issues = []
            legal_actions = []
        else:
            current_data = self.dataset[self.current_row_index]
            issues = self._detect_issues(current_data)
            legal_actions = self._get_legal_actions(current_data, issues)

        return {
            "current_row": self.current_row_index,
            "total_rows": len(self.dataset),
            "current_data": current_data,
            "issues_detected": issues,
            "legal_actions": legal_actions,
            "progress": round(self.current_row_index / max(len(self.dataset), 1), 2),
            "reward": round(reward, 3),
            "done": self.done,
        }

    def _get_legal_actions(self, row: Dict[str, Any], issues: List[str]) -> List[str]:
        actions = ["skip"]
        issue_types = [i.split(":")[0] for i in issues]
        if "missing" in issue_types:
            actions.append("fill_missing")
        if "wrong_type" in issue_types:
            actions.append("fix_type")
        if "formatting" in issue_types:
            actions.append("fix_formatting")
        actions.extend(["remove_duplicate", "fix_category", "remove_outlier"])
        return list(set(actions))