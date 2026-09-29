"""
Task definitions and graders for the streaming IoT sensor-denoising environment.

The single task, ``iot_stream``, draws a contiguous window of hourly readings
from a chronological split of the UCI Air Quality dataset, injects a chosen
family of telemetry faults, and grades a denoised stream with the shared
metrics in :mod:`backend.ml.metrics` so that the environment, the trainer and
the benchmark script can never disagree on how error is measured.

The legacy synthetic HR-record tasks (``easy`` / ``medium`` / ``hard``) that
this environment carried before the research pivot have been removed; they
belonged to the static tabular cleaning application, not to sequential stream
denoising.
"""

import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Allow import both as a package (`envs.data_cleaning_env.tasks.graders`) and
# from the environment server, which inserts its parent directory on sys.path.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from backend.ml.metrics import evaluate_window  # noqa: E402
from data.iot_data_loader import (  # noqa: E402
    SyntheticCorruptionInjector,
    UCIAirQualityLoader,
    imputed_mask_col,
    sample_window,
)

DEFAULT_SENSOR_COLUMN = "CO(GT)"
CORRUPTION_TYPES = ["spike", "drift", "dropout", "duplicate", "mixed"]

# Oracle fields that describe the fault the generator injected. They are needed
# by the training reward and by offline analysis, but must never reach the
# agent's observation, so they are listed here and stripped by the environment.
ORACLE_FIELDS = ("ground_truth", "reference_imputed", "fault_type", "is_corrupted")

# Bookkeeping fields that are not oracle information but are also not something
# a deployed device would receive in a packet. They are stripped from the
# observation too, so that the observation stays exactly what an ESP32 could
# assemble from one reading plus its own retained history.
NON_OBSERVABLE_FIELDS = ("raw_corrupted", "window_start", "split")

_LOADER_CACHE: Dict[str, UCIAirQualityLoader] = {}


def _get_loader(sensor_column: str) -> UCIAirQualityLoader:
    """Return a cached loader so ``reset()`` never re-parses the CSV."""
    if sensor_column not in _LOADER_CACHE:
        _LOADER_CACHE[sensor_column] = UCIAirQualityLoader(target_col=sensor_column)
    return _LOADER_CACHE[sensor_column]


def generate_iot_stream_dataset(
    window_size: int = 24,
    corruption_type: str = "mixed",
    split: str = "train",
    seed: Optional[int] = None,
    sensor_column: str = DEFAULT_SENSOR_COLUMN,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
) -> List[Dict[str, Any]]:
    """
    Build one streaming episode: a contiguous window with injected faults.

    ``seed`` fully determines both the window position and the fault pattern,
    but through two independent draws — an earlier revision used the seed
    directly as ``seed % max_start``, which tied the window index to the epoch
    number and so confined 40 epochs of training to the first 680 hours of a
    7,485-hour split.
    """
    if corruption_type not in CORRUPTION_TYPES + ["none"]:
        raise ValueError(
            f"Unknown corruption_type '{corruption_type}'. "
            f"Choose from {CORRUPTION_TYPES + ['none']}."
        )

    loader = _get_loader(sensor_column)
    df = loader.get_split(split, train_ratio=train_ratio, val_ratio=val_ratio)

    rng = np.random.RandomState(seed if seed is not None else np.random.randint(0, 2**31 - 1))
    start_idx, gt_window, ref_imputed = sample_window(
        df, sensor_column, window_size, rng
    )

    # Draw the injector seed from the same stream: reproducible from `seed`, but
    # independent of where the window landed.
    injector = SyntheticCorruptionInjector(seed=int(rng.randint(0, 2**31 - 1)))
    result = injector.corrupt_window(gt_window, corruption_type=corruption_type)
    corrupted = result["corrupted"]
    masks = result["masks"]

    dataset = []
    for t in range(len(gt_window)):
        fault = "clean"
        for ftype in ("dropout", "spike", "duplicate", "drift"):
            if masks[ftype][t]:
                fault = ftype
                break

        val = corrupted[t]
        sensor_val = None if not np.isfinite(val) else float(val)

        dataset.append(
            {
                "id": t,
                "timestep": t,
                "sensor": sensor_column,
                "value": sensor_val,
                "raw_corrupted": sensor_val,
                "ground_truth": float(gt_window[t]),
                "reference_imputed": bool(ref_imputed[t]),
                "fault_type": fault,
                "is_corrupted": fault != "clean",
                "window_start": int(start_idx),
                "split": split,
            }
        )

    return dataset


def grade_iot_stream(cleaned_data: List[Dict[str, Any]]) -> Tuple[float, str]:
    """
    Grade a denoised stream in ``[0, 1]``, where 0.5 means "no better than raw".

    Scoring delegates to :func:`backend.ml.metrics.evaluate_window`, so a method
    that emits nothing on a dropout is charged for it (the harness carries the
    last value forward) instead of having those timesteps quietly dropped from
    the average.
    """
    if not cleaned_data:
        return 0.0, "No cleaned data returned"

    predicted = [row.get("value") for row in cleaned_data]
    m = evaluate_window(cleaned_data, predicted)

    msg = (
        f"MAE: {m['mae']:.4f} (raw {m['raw_mae']:.4f}), "
        f"RMSE: {m['rmse']:.4f}, "
        f"error reduction: {m['error_reduction_pct']:+.1f}%, "
        f"scored {m['n_scored']} steps"
    )
    if m["nan_emitted"]:
        msg += f", {m['nan_emitted']} un-imputed step(s) carried forward"
    return float(m["score"]), msg


TASKS = {
    "iot_stream": {
        "name": "IoT Sensor-Stream Denoising",
        "description": (
            "Denoise a sequential UCI Air Quality sensor stream online "
            "(spikes, calibration drift, dropouts, duplicate packets)."
        ),
        "difficulty": "streaming",
        "generate": generate_iot_stream_dataset,
        "grade": grade_iot_stream,
    },
}
