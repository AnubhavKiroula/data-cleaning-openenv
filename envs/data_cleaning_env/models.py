from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class DataCleaningAction(BaseModel):
    """What the agent does to a cell."""
    action_type: str
    # Options:
    # "fill_missing"   → fill a missing value
    # "fix_type"       → convert to correct data type
    # "remove_duplicate" → mark row as duplicate
    # "fix_category"   → standardize category label
    # "remove_outlier" → replace outlier with median
    # "skip"           → do nothing (penalized)

    column: str                        # Which column to act on
    value: Optional[Any] = None        # New value (if needed)


class DataCleaningObservation(BaseModel):
    """What the agent sees at each step."""
    current_row: int                   # Which row we're on
    total_rows: int                    # Total rows in dataset
    current_data: Dict[str, Any]       # Current row's data
    issues_detected: List[str]         # Problems found in this row
    legal_actions: List[str]           # Valid action_types right now
    progress: float                    # 0.0 to 1.0
    reward: float                      # Last step reward
    done: bool                         # Episode over?


class DataCleaningState(BaseModel):
    """Episode metadata."""
    episode_id: str
    task_name: str
    step_count: int
    total_reward: float
    rows_cleaned: int
    score: float                       # 0.0 to 1.0 grader score