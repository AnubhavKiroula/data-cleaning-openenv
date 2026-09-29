"""
IoT Air Quality Data Loader & Synthetic Corruption Generator.

Loads the UCI Air Quality dataset (9,357 hourly instances) and provides
chronological train/validation/test splitting plus realistic IoT sensor
corruption injection (spikes, drift, dropouts, duplicate transmissions).

Methodological notes
--------------------
* Hardware faults in the raw dataset are encoded as the sentinel ``-200``.
  These are linearly interpolated to build a continuous reference signal, but
  the interpolated positions are tracked in an ``<col>__imputed`` mask column
  so that evaluation can exclude them. Scoring an agent against interpolated
  values would measure agreement with ``numpy.interp``, not with reality.
* Splits are strictly chronological. The validation split is carved from the
  *end of the training region*, never from the test region, so that model
  selection never observes held-out data.
* The parsed dataframe is cached at module level: the environment re-parses
  nothing when ``reset()`` is called thousands of times during training.
"""

import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

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

# Parsed-dataframe cache, keyed by absolute CSV path.
_FRAME_CACHE: Dict[str, pd.DataFrame] = {}


def imputed_mask_col(col: str) -> str:
    """Name of the boolean column flagging interpolated reference values."""
    return f"{col}__imputed"


def clear_cache() -> None:
    """Drop the parsed-dataframe cache (used by tests)."""
    _FRAME_CACHE.clear()


class UCIAirQualityLoader:
    """
    Loader for the UCI Air Quality Dataset.

    Enforces strictly chronological train/validation/test splits so that
    streaming claims remain valid: no shuffling, no k-fold, no future leakage.
    """

    def __init__(self, csv_path: str = DEFAULT_CSV_PATH, target_col: str = "CO(GT)"):
        self.csv_path = os.path.abspath(csv_path)
        self.target_col = target_col
        self.df_clean: Optional[pd.DataFrame] = None
        self.train_df: Optional[pd.DataFrame] = None
        self.val_df: Optional[pd.DataFrame] = None
        self.test_df: Optional[pd.DataFrame] = None
        self.load_data()

    def load_data(self) -> pd.DataFrame:
        """Parse the semicolon-delimited, comma-decimal CSV and resolve sentinels."""
        if self.csv_path in _FRAME_CACHE:
            self.df_clean = _FRAME_CACHE[self.csv_path]
            return self.df_clean

        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(
                f"UCI Air Quality CSV not found at: {self.csv_path}"
            )

        # Semicolon separators, comma as the decimal mark, trailing empty columns.
        df = pd.read_csv(self.csv_path, sep=";", decimal=",").dropna(how="all", axis=1)
        df = df.dropna(how="all")

        clean_df = pd.DataFrame()
        clean_df["Date"] = df["Date"].values
        clean_df["Time"] = df["Time"].values

        for col in KEY_SENSOR_COLUMNS:
            if col not in df.columns:
                continue
            series = pd.to_numeric(df[col], errors="coerce")
            # -200 is the dataset's hardware-fault sentinel, not a reading.
            series_nan = series.replace(SENTINEL_MISSING, np.nan)
            # Record where the reference signal is synthetic before filling it.
            clean_df[imputed_mask_col(col)] = series_nan.isna().values
            clean_df[col] = (
                series_nan.interpolate(method="linear", limit_direction="both")
                .bfill()
                .ffill()
                .values
            )

        clean_df = clean_df.reset_index(drop=True)
        _FRAME_CACHE[self.csv_path] = clean_df
        self.df_clean = clean_df
        return self.df_clean

    def get_chronological_split(
        self, train_ratio: float = 0.8, val_ratio: float = 0.1
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Split the dataset chronologically and return ``(train, test)``.

        ``train_ratio`` marks the train/test boundary over the full record
        (0.8 of 9,357 = 7,485 training hours, 1,872 test hours, matching the
        published protocol). ``val_ratio`` is the fraction *of the training
        region* reserved at its end for model selection; the returned train
        frame excludes it. Pass ``val_ratio=0.0`` for the full training region.
        """
        if self.df_clean is None:
            self.load_data()

        n = len(self.df_clean)
        split_idx = int(n * train_ratio)
        val_len = int(split_idx * val_ratio)
        fit_end = split_idx - val_len

        self.train_df = self.df_clean.iloc[:fit_end].copy().reset_index(drop=True)
        self.val_df = (
            self.df_clean.iloc[fit_end:split_idx].copy().reset_index(drop=True)
        )
        self.test_df = self.df_clean.iloc[split_idx:].copy().reset_index(drop=True)
        return self.train_df, self.test_df

    def get_split(self, split: str, train_ratio: float = 0.8, val_ratio: float = 0.1):
        """Return one of the ``train`` / ``val`` / ``test`` frames by name."""
        self.get_chronological_split(train_ratio=train_ratio, val_ratio=val_ratio)
        frames = {"train": self.train_df, "val": self.val_df, "test": self.test_df}
        if split not in frames:
            raise ValueError(f"Unknown split '{split}'. Choose from {list(frames)}.")
        return frames[split]


class SyntheticCorruptionInjector:
    """
    Injects synthetic IoT telemetry faults into sensor time-series:

    1. Spikes: high-amplitude electrical / electromagnetic transient noise.
    2. Drift: cumulative calibration ramp from chemical or thermal degradation.
    3. Dropout: contiguous transmission gaps (lost wireless packets).
    4. Duplicate: an immediately repeated packet from a network retry glitch.
    """

    def __init__(self, seed: Optional[int] = 42):
        self.rng = np.random.RandomState(seed)

    def set_seed(self, seed: int):
        self.rng = np.random.RandomState(seed)

    def inject_spikes(
        self, series: np.ndarray, prob: float = 0.08, magnitude_scale: float = 4.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Add electrical noise spikes. Returns ``(corrupted, spike_mask)``."""
        corrupted = series.copy().astype(float)
        n = len(series)
        finite = corrupted[np.isfinite(corrupted)]
        std_val = max(float(np.std(finite)) if finite.size else 0.0, 1e-3)
        mask = self.rng.rand(n) < prob

        signs = self.rng.choice([-1.0, 1.0], size=n)
        magnitudes = self.rng.uniform(2.5, magnitude_scale, size=n) * std_val * signs
        corrupted[mask] = corrupted[mask] + magnitudes[mask]
        return corrupted, mask

    def inject_drift(
        self,
        series: np.ndarray,
        slope_range: Tuple[float, float] = (0.05, 0.15),
        window_len: int = 12,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Inject a linear calibration ramp. Returns ``(corrupted, drift_mask)``."""
        corrupted = series.copy().astype(float)
        n = len(series)
        mask = np.zeros(n, dtype=bool)

        if n <= 4:
            return corrupted, mask

        drift_len = min(window_len, max(2, n // 2))
        start_idx = self.rng.randint(0, max(1, n - drift_len))
        end_idx = start_idx + drift_len

        finite = corrupted[np.isfinite(corrupted)]
        std_val = max(float(np.std(finite)) if finite.size else 0.0, 1e-3)
        slope = self.rng.uniform(*slope_range) * std_val * self.rng.choice([-1.0, 1.0])
        ramp = np.arange(drift_len) * slope

        corrupted[start_idx:end_idx] = corrupted[start_idx:end_idx] + ramp
        mask[start_idx:end_idx] = True
        return corrupted, mask

    def inject_dropouts(
        self, series: np.ndarray, prob: float = 0.05, max_gap: int = 4
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Replace contiguous runs with NaN. Returns ``(corrupted, dropout_mask)``."""
        corrupted = series.copy().astype(float)
        n = len(series)
        mask = np.zeros(n, dtype=bool)

        # Never drop the first sample: a stream with no history at all is a
        # cold-start problem, not a denoising problem, and both the baseline and
        # the agent would be scored on an unanswerable step.
        i = 1
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
        self, series: np.ndarray, prob: float = 0.06
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Repeat the previous reading. Returns ``(corrupted, duplicate_mask)``."""
        corrupted = series.copy().astype(float)
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
        Apply one fault family, or a mixture, to a window.

        Supported: ``spike``, ``drift``, ``dropout``, ``duplicate``, ``mixed``,
        ``none``. Masks are recorded before later stages overwrite values, so a
        sample hidden by a dropout still carries the flag of the fault that hit
        it first.
        """
        ground_truth = np.asarray(ground_truth, dtype=float)
        corrupted = ground_truth.copy()
        masks = {
            "spike": np.zeros(len(ground_truth), dtype=bool),
            "drift": np.zeros(len(ground_truth), dtype=bool),
            "dropout": np.zeros(len(ground_truth), dtype=bool),
            "duplicate": np.zeros(len(ground_truth), dtype=bool),
        }

        if corruption_type == "none":
            pass
        elif corruption_type == "spike":
            corrupted, masks["spike"] = self.inject_spikes(corrupted)
        elif corruption_type == "drift":
            corrupted, masks["drift"] = self.inject_drift(corrupted)
        elif corruption_type == "dropout":
            corrupted, masks["dropout"] = self.inject_dropouts(corrupted)
        elif corruption_type == "duplicate":
            corrupted, masks["duplicate"] = self.inject_duplicates(corrupted)
        elif corruption_type == "mixed":
            corrupted, masks["spike"] = self.inject_spikes(corrupted, prob=0.05)
            corrupted, masks["drift"] = self.inject_drift(corrupted)
            corrupted, masks["dropout"] = self.inject_dropouts(corrupted, prob=0.04)
            corrupted, masks["duplicate"] = self.inject_duplicates(corrupted, prob=0.04)
        else:
            raise ValueError(f"Unknown corruption_type: {corruption_type}")

        return {
            "ground_truth": ground_truth,
            "corrupted": corrupted,
            "masks": masks,
            "corruption_type": corruption_type,
        }


def sample_window(
    df: pd.DataFrame,
    column: str,
    window_size: int,
    rng: np.random.RandomState,
    min_real_fraction: float = 0.75,
    max_attempts: int = 50,
) -> Tuple[int, np.ndarray, np.ndarray]:
    """
    Draw a contiguous window whose reference signal is mostly real readings.

    Returns ``(start_index, ground_truth, imputed_mask)``. Windows where more
    than ``1 - min_real_fraction`` of the reference came from interpolating over
    the ``-200`` sentinel are rejected and redrawn, because those positions
    carry no measured truth to score against. The criterion is a data-quality
    filter applied identically to every method under comparison — it is not
    conditioned on any method's output.
    """
    series = df[column].to_numpy(dtype=float)
    mask_col = imputed_mask_col(column)
    imputed = (
        df[mask_col].to_numpy(dtype=bool)
        if mask_col in df.columns
        else np.zeros(len(series), dtype=bool)
    )

    if len(series) < window_size:
        raise ValueError(
            f"Split has {len(series)} rows, too few for window_size={window_size}."
        )

    max_start = len(series) - window_size
    best = None
    for _ in range(max_attempts):
        start = int(rng.randint(0, max_start + 1))
        win_imputed = imputed[start : start + window_size]
        real_fraction = 1.0 - float(win_imputed.mean())
        if best is None or real_fraction > best[0]:
            best = (real_fraction, start)
        if real_fraction >= min_real_fraction:
            return start, series[start : start + window_size], win_imputed

    # Fall back to the cleanest window seen rather than looping forever.
    start = best[1]
    return start, series[start : start + window_size], imputed[start : start + window_size]
