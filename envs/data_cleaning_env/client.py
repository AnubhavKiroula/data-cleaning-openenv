import requests
from typing import Any, Optional


class DataCleaningEnv:
    """HTTP client for the Data Cleaning environment."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    def reset(self, task_name: str = "easy") -> dict:
        r = requests.post(f"{self.base_url}/reset", json={"task_name": task_name})
        r.raise_for_status()
        return r.json()

    def step(self, action_type: str, column: str, value: Any = None) -> dict:
        r = requests.post(f"{self.base_url}/step", json={
            "action_type": action_type,
            "column": column,
            "value": value
        })
        r.raise_for_status()
        return r.json()

    def state(self) -> dict:
        r = requests.get(f"{self.base_url}/state")
        r.raise_for_status()
        return r.json()

    def health(self) -> dict:
        r = requests.get(f"{self.base_url}/health")
        return r.json()

    def tasks(self) -> dict:
        r = requests.get(f"{self.base_url}/tasks")
        return r.json()