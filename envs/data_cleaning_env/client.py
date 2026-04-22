import requests
from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class StepResult:
    """Result returned from reset() and step() calls."""
    observation: dict
    reward: float
    done: bool
    info: dict


class DataCleaningEnv:
    """
    HTTP client for the Data Cleaning OpenEnv environment.
    Implements the OpenEnv HTTPEnvClient pattern.

    Usage:
        env = DataCleaningEnv(base_url="https://01ammu-data-cleaning-openenv.hf.space")
        obs = env.reset(task_name="easy")
        result = env.step(action_type="fill_missing", column="age", value=30)
    """

    def __init__(self, base_url: str = "http://localhost:7860"):
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()

    # ------------------------------------------------------------------ #
    #  Core OpenEnv interface                                              #
    # ------------------------------------------------------------------ #

    def reset(self, task_name: str = "easy") -> StepResult:
        """Start a new episode. Returns initial observation."""
        payload = self._reset_payload(task_name)
        response = self._session.post(f"{self.base_url}/reset", json=payload)
        response.raise_for_status()
        return self._parse_result(response.json())

    def step(self, action_type: str, column: str, value: Any = None) -> StepResult:
        """Apply a cleaning action to the current row."""
        payload = self._step_payload(action_type, column, value)
        response = self._session.post(f"{self.base_url}/step", json=payload)
        response.raise_for_status()
        return self._parse_result(response.json())

    def state(self) -> dict:
        """Get current episode metadata."""
        response = self._session.get(f"{self.base_url}/state")
        response.raise_for_status()
        return self._parse_state(response.json())

    # ------------------------------------------------------------------ #
    #  Payload builders (convert typed args → JSON)                        #
    # ------------------------------------------------------------------ #

    def _reset_payload(self, task_name: str) -> dict:
        return {"task_name": task_name}

    def _step_payload(self, action_type: str, column: str, value: Any) -> dict:
        return {
            "action_type": action_type,
            "column": column,
            "value": value,
        }

    # ------------------------------------------------------------------ #
    #  Response parsers (JSON → typed objects)                             #
    # ------------------------------------------------------------------ #

    def _parse_result(self, payload: dict) -> StepResult:
        return StepResult(
            observation=payload,
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
            info={
                "current_row": payload.get("current_row"),
                "total_rows": payload.get("total_rows"),
                "issues_detected": payload.get("issues_detected", []),
                "legal_actions": payload.get("legal_actions", []),
                "progress": payload.get("progress", 0.0),
            },
        )

    def _parse_state(self, payload: dict) -> dict:
        return {
            "episode_id": payload.get("episode_id"),
            "task_name": payload.get("task_name"),
            "step_count": payload.get("step_count"),
            "total_reward": payload.get("total_reward"),
            "rows_cleaned": payload.get("rows_cleaned"),
            "score": payload.get("score"),
        }

    # ------------------------------------------------------------------ #
    #  Utility endpoints                                                   #
    # ------------------------------------------------------------------ #

    def health(self) -> dict:
        """Check if the environment server is running."""
        response = self._session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    def tasks(self) -> dict:
        """List all available tasks."""
        response = self._session.get(f"{self.base_url}/tasks")
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------ #
    #  Context manager support                                             #
    # ------------------------------------------------------------------ #

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._session.close()