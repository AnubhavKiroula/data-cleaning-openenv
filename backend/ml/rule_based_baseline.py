"""
Rule-Based Streaming Baseline Filter for IoT Sensor Streams.

Under the same online/sequential real-time constraint (seeing one reading at a time):
1. Forward-fill for missing values (dropouts).
2. Rolling Z-Score (|z| > 3) clipping with rolling median for outliers (spikes).
3. Consecutive equality check for duplicate transmissions.
4. No correction for drift (standard heuristic filters typically cannot detect slow calibration drift).
"""

import numpy as np
from typing import Dict, Any, List, Optional


class RuleBasedStreamFilter:
    """
    Online rule-based filter operating step-by-step on streaming sensor readings.
    """

    def __init__(self, history_len: int = 5, z_threshold: float = 3.0):
        self.history_len = history_len
        self.z_threshold = z_threshold
        self.history: List[float] = []
        self.last_valid_value: Optional[float] = None

    def reset(self):
        """Reset state for a new stream/episode."""
        self.history = []
        self.last_valid_value = None

    def filter_step(self, raw_value: Optional[float]) -> Dict[str, Any]:
        """
        Process a single incoming reading under online constraints.
        Returns:
            {
                "action_type": str,
                "cleaned_value": float,
                "reason": str
            }
        """
        # 1. Missing Value / Dropout Handling: Forward Fill
        if raw_value is None or (isinstance(raw_value, float) and np.isnan(raw_value)):
            cleaned = self.last_valid_value if self.last_valid_value is not None else 0.0
            return {
                "action_type": "fill_missing",
                "cleaned_value": float(cleaned),
                "reason": "forward_fill_dropout",
            }

        val = float(raw_value)

        # 2. Duplicate Transmission Check
        if self.last_valid_value is not None and abs(val - self.last_valid_value) < 1e-7:
            # Check if this could be an artificial duplicate packet
            # In a rule baseline, we might pass or interpolate
            action = "remove_duplicate" if len(self.history) >= 2 else "skip"
            cleaned = val
            # Update history
            self._update_history(cleaned)
            return {
                "action_type": action,
                "cleaned_value": cleaned,
                "reason": "duplicate_detected_or_passed",
            }

        # 3. Statistical Outlier Detection via Rolling Z-Score
        if len(self.history) >= 3:
            hist_mean = float(np.mean(self.history))
            hist_std = float(np.std(self.history))
            hist_median = float(np.median(self.history))

            if hist_std > 1e-4:
                z_score = abs(val - hist_mean) / hist_std
                if z_score > self.z_threshold:
                    # Outlier detected: replace with rolling median
                    cleaned = hist_median
                    self._update_history(cleaned)
                    return {
                        "action_type": "remove_outlier",
                        "cleaned_value": float(cleaned),
                        "reason": f"z_score_spike_detected (z={z_score:.2f})",
                    }

        # 4. Drift is typically undetected by static z-score/forward-fill heuristics
        cleaned = val
        self._update_history(cleaned)
        return {
            "action_type": "skip",
            "cleaned_value": cleaned,
            "reason": "pass_through",
        }

    def _update_history(self, val: float):
        self.history.append(val)
        self.last_valid_value = val
        if len(self.history) > self.history_len:
            self.history.pop(0)

    def process_window(self, dataset: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process an entire window/episode of readings sequentially."""
        self.reset()
        cleaned_records = []

        for row in dataset:
            res = self.filter_step(row.get("value"))
            rec = row.copy()
            rec["raw_corrupted"] = row.get("value")
            rec["value"] = res["cleaned_value"]
            rec["baseline_action"] = res["action_type"]
            rec["baseline_reason"] = res["reason"]
            cleaned_records.append(rec)

        return cleaned_records
