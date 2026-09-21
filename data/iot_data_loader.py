"""
IoT Air Quality Data Loader & Synthetic Corruption Generator.

Loads the UCI Air Quality dataset (9,357 hourly instances) and provides
chronological train/test splitting and realistic IoT sensor corruption injection
(spikes, drift, dropouts, duplicate transmissions).
"""

import os
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any, List, Optional


SENTINEL_MISSING = -200.0

KEY_SENSOR_COLUMNS = [
    "CO(GT)",
    "PT08.S1(CO)",
    "NMHC(GT)",
    "C6H6(GT)",
    "PT08.S2(NMHC)",
    "NOx(GT)",
    "PT08.S3(NOx)",
    "NO2(GT)",
    "PT08.S4(NO2)",
    "PT08.S5(O3)",
    "T",
    "RH",
    "AH",
]

DEFAULT_CSV_PATH = os.path.join(
    os.path.dirname(__file__), "air_quality", "AirQualityUCI.csv"
)


class UCIAirQualityLoader:
    """
    Loader for the UCI Air Quality Dataset.
    Enforces strictly chronological train/test splits for online/streaming validity.
    """

    def __init__(self, csv_path: str = DEFAULT_CSV_PATH, target_col: str = "CO(GT)"):
        self.csv_path = csv_path
        self.target_col = target_col
        self.df_raw: Optional[pd.DataFrame] = None
        self.df_clean: Optional[pd.DataFrame] = None
        self.train_df: Optional[pd.DataFrame] = None
        self.test_df: Optional[pd.DataFrame] = None
        self.load_data()

    def load_data(self) -> pd.DataFrame:
        """Parse semicolon delimited, comma-decimal CSV and clean missing sentinels."""
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"UCI Air Quality CSV not found at: {self.csv_path}")

        # The CSV has semicolon separators and comma as decimal separator
        df = pd.read_csv(self.csv_path, sep=";", decimal=",").dropna(how="all", axis=1)
        df = df.dropna(how="all")

        # Keep valid rows
        self.df_raw = df.copy()

        # Clean numerical columns
        clean_df = pd.DataFrame()
        clean_df["Date"] = df["Date"]
        clean_df["Time"] = df["Time"]

        for col in KEY_SENSOR_COLUMNS:
            if col in df.columns:
                series = pd.to_numeric(df[col], errors="coerce")
                # Replace -200 sentinel with NaN for ground truth baseline interpolation
                series_nan = series.replace(SENTINEL_MISSING, np.nan)
                # Forward-fill / backward-fill ground truth so we have an exact benchmark target
                clean_df[col] = series_nan.interpolate(method="linear").bfill().ffill()

        self.df_clean = clean_df
        return self.df_clean

    def get_chronological_split(
        self, train_ratio: float = 0.8
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Split dataset strictly chronologically (first train_ratio for training,
        remaining for testing) to prevent temporal data leakage in online streaming.
        """
        if self.df_clean is None:
            self.load_data()

        split_idx = int(len(self.df_clean) * train_ratio)
        self.train_df = self.df_clean.iloc[:split_idx].copy().reset_index(drop=True)
        self.test_df = self.df_clean.iloc[split_idx:].copy().reset_index(drop=True)
        return self.train_df, self.test_df


class SyntheticCorruptionInjector:
    """
    Injects synthetic IoT telemetry faults into sensor time-series:
    1. Spikes: high-amplitude electrical/EM noise.
    2. Drift: slow cumulative linear/random-walk offset from calibration loss.
    3. Dropout: contiguous transmission gaps / lost packets.
    4. Duplicate: duplicate packet transmission immediately repeated.
    """

    def __init__(self, seed: Optional[int] = 42):
        self.rng = np.random.RandomState(seed)

    def set_seed(self, seed: int):
        self.rng = np.random.RandomState(seed)

    def inject_spikes(
        self, series: np.ndarray, prob: float = 0.04, magnitude_scale: float = 3.5
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Add electrical noise spikes to series.
        Returns (corrupted_series, spike_mask).
        """
        corrupted = series.copy()
        n = len(series)
        std_val = max(float(np.std(series)), 1.0)
        mask = self.rng.rand(n) < prob

        # Spikes can be positive or negative bursts
        signs = self.rng.choice([-1.0, 1.0], size=n)
        magnitudes = self.rng.uniform(2.5, magnitude_scale, size=n) * std_val * signs
        corrupted[mask] = series[mask] + magnitudes[mask]
        return corrupted, mask

    def inject_drift(
        self, series: np.ndarray, slope_range: Tuple[float, float] = (0.02, 0.06), window_len: int = 12
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Inject slow calibration drift over a window.
        Returns (corrupted_series, drift_mask).
        """
        corrupted = series.copy()
        n = len(series)
        mask = np.zeros(n, dtype=bool)

        if n <= 4:
            return corrupted, mask

        # Pick random start point for drift window
        drift_len = min(window_len, n // 2)
        start_idx = self.rng.randint(0, max(1, n - drift_len))
        end_idx = start_idx + drift_len

        std_val = max(float(np.std(series)), 1.0)
        slope = self.rng.uniform(*slope_range) * std_val * self.rng.choice([-1.0, 1.0])
        ramp = np.arange(drift_len) * slope

        corrupted[start_idx:end_idx] = series[start_idx:end_idx] + ramp
        mask[start_idx:end_idx] = True
        return corrupted, mask

    def inject_dropouts(
        self, series: np.ndarray, prob: float = 0.04, max_gap: int = 3
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Simulate transmission dropout by replacing readings with NaN / None.
        Returns (corrupted_series, dropout_mask).
        """
        corrupted = series.copy().astype(float)
        n = len(series)
        mask = np.zeros(n, dtype=bool)

        i = 0
        while i < n:
            if self.rng.rand() < prob:
                gap = self.rng.randint(1, max_gap + 1)
                end = min(n, i + gap)
                corrupted[i:end] = np.nan
                mask[i:end] = True
                i = end
            else:
                i += 1
        return corrupted, mask

    def inject_duplicates(
        self, series: np.ndarray, prob: float = 0.03
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Simulate transmission retry glitch by repeating previous reading.
        Returns (corrupted_series, duplicate_mask).
        """
        corrupted = series.copy()
        n = len(series)
        mask = np.zeros(n, dtype=bool)

        for i in range(1, n):
            if self.rng.rand() < prob:
                corrupted[i] = corrupted[i - 1]
                mask[i] = True

        return corrupted, mask

    def corrupt_window(
        self,
        ground_truth: np.ndarray,
        corruption_type: str = "mixed",
    ) -> Dict[str, Any]:
        """
        Apply specified corruption type or mixed corruptions to a window.
        Supported types: 'spike', 'drift', 'dropout', 'duplicate', 'mixed'.
        """
        corrupted = ground_truth.copy().astype(float)
        masks = {
            "spike": np.zeros(len(ground_truth), dtype=bool),
            "drift": np.zeros(len(ground_truth), dtype=bool),
            "dropout": np.zeros(len(ground_truth), dtype=bool),
            "duplicate": np.zeros(len(ground_truth), dtype=bool),
        }

        if corruption_type == "spike":
            corrupted, masks["spike"] = self.inject_spikes(corrupted)
        elif corruption_type == "drift":
            corrupted, masks["drift"] = self.inject_drift(corrupted)
        elif corruption_type == "dropout":
            corrupted, masks["dropout"] = self.inject_dropouts(corrupted)
        elif corruption_type == "duplicate":
            corrupted, masks["duplicate"] = self.inject_duplicates(corrupted)
        elif corruption_type == "mixed":
            # Apply a combination of realistic faults
            corrupted, masks["spike"] = self.inject_spikes(corrupted, prob=0.03)
            corrupted, masks["drift"] = self.inject_drift(corrupted)
            corrupted, masks["dropout"] = self.inject_dropouts(corrupted, prob=0.03)
            corrupted, masks["duplicate"] = self.inject_duplicates(corrupted, prob=0.02)
        else:
            raise ValueError(f"Unknown corruption_type: {corruption_type}")

        return {
            "ground_truth": ground_truth,
            "corrupted": corrupted,
            "masks": masks,
            "corruption_type": corruption_type,
        }
