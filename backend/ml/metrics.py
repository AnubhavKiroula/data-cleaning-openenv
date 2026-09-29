"""
Shared evaluation metrics for streaming sensor denoising.

Every method under comparison (do-nothing, rule baseline, RL agent) is scored by
the *same* function here. Earlier revisions computed MAE separately inside the
trainer, the benchmark script and the grader, which let the three disagree — in
particular by silently dropping un-imputed dropout samples from the average and
so reporting a perfect score for a method that had emitted nothing at all.

Two conventions make the numbers comparable:

1. **Output is mandatory.** A streaming filter feeds a downstream controller, so
   it must emit a number at every timestep. If a method emits ``None``/NaN the
   harness carries the last emitted value forward and counts the event in
   ``nan_emitted``. The do-nothing reference policy is therefore "pass the raw
   stream through, carrying forward across dropouts" — a real, non-trivial
   baseline rather than an undefined one.
2. **Only measured truth is scored.** Timesteps whose reference value came from
   interpolating over the dataset's ``-200`` sentinel are excluded, because
   scoring against them measures agreement with an interpolator, not with a
   sensor.
"""

from typing import Any, Dict, List, Optional, Sequence

import numpy as np


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(np.isnan(float(value)))
    except (TypeError, ValueError):
        return True


def carry_forward(values: Sequence[Any], initial: Optional[float] = None) -> np.ndarray:
    """
    Fill missing entries with the most recent present value.

    A leading run of missing values takes ``initial`` when supplied, otherwise
    the first present value in the series (a documented cold-start convention),
    otherwise 0.0 for an all-missing series.
    """
    out = np.empty(len(values), dtype=float)
    last = initial
    if last is None:
        present = [float(v) for v in values if not _is_missing(v)]
        last = present[0] if present else 0.0

    for i, v in enumerate(values):
        if not _is_missing(v):
            last = float(v)
        out[i] = last
    return out


def stream_metrics(
    ground_truth: Sequence[float],
    predicted: Sequence[Any],
    reference_imputed: Optional[Sequence[bool]] = None,
) -> Dict[str, float]:
    """
    Score one denoised stream against its reference.

    Returns MAE, RMSE, max absolute error, the number of NaN/None emissions that
    had to be carried forward, and the number of timesteps actually scored.
    """
    gt = np.asarray(ground_truth, dtype=float)
    predicted = list(predicted)
    nan_emitted = int(sum(1 for v in predicted if _is_missing(v)))
    filled = carry_forward(predicted)

    if reference_imputed is None:
        scored = np.ones(len(gt), dtype=bool)
    else:
        scored = ~np.asarray(reference_imputed, dtype=bool)

    # Never return an empty average: if the whole window is interpolated
    # reference, score all of it and let `n_scored` disclose the situation.
    if not scored.any():
        scored = np.ones(len(gt), dtype=bool)

    err = np.abs(filled[scored] - gt[scored])
    return {
        "mae": float(np.mean(err)),
        "rmse": float(np.sqrt(np.mean(err**2))),
        "max_err": float(np.max(err)) if err.size else 0.0,
        "nan_emitted": nan_emitted,
        "n_scored": int(scored.sum()),
    }


def error_reduction_pct(raw_mae: float, method_mae: float) -> float:
    """
    Percentage of the do-nothing error that a method removed.

    Positive means the method helped; negative means it damaged the signal.
    Returns 0.0 when the raw stream was already exact, since there was no error
    available to reduce.
    """
    if raw_mae <= 1e-9:
        return 0.0
    return float((raw_mae - method_mae) / raw_mae * 100.0)


def quality_score(raw_mae: float, method_mae: float) -> float:
    """
    Map error reduction onto ``[0, 1]`` with 0.5 meaning "no better than raw".

    1.0 is a perfect reconstruction, 0.5 is a pass-through, and below 0.5 means
    the filter actively degraded the stream.
    """
    if raw_mae <= 1e-9:
        return float(max(0.0, min(1.0, 1.0 - method_mae)))
    improvement = (raw_mae - method_mae) / raw_mae
    return float(round(max(0.0, min(1.0, 0.5 + 0.5 * improvement)), 4))


def evaluate_window(
    dataset: List[Dict[str, Any]],
    predicted: Sequence[Any],
) -> Dict[str, float]:
    """
    Score a method's output for one episode window against its dataset rows.

    ``dataset`` rows carry ``ground_truth``, ``raw_corrupted`` and
    ``reference_imputed`` as produced by the ``iot_stream`` task generator. The
    do-nothing reference is derived from the same rows so that raw and method
    metrics always come from one code path.
    """
    gt = [row["ground_truth"] for row in dataset]
    raw = [row.get("raw_corrupted") for row in dataset]
    ref_imputed = [bool(row.get("reference_imputed", False)) for row in dataset]

    raw_m = stream_metrics(gt, raw, ref_imputed)
    method_m = stream_metrics(gt, predicted, ref_imputed)

    return {
        "raw_mae": raw_m["mae"],
        "raw_rmse": raw_m["rmse"],
        "mae": method_m["mae"],
        "rmse": method_m["rmse"],
        "max_err": method_m["max_err"],
        "nan_emitted": method_m["nan_emitted"],
        "n_scored": method_m["n_scored"],
        "error_reduction_pct": error_reduction_pct(raw_m["mae"], method_m["mae"]),
        "score": quality_score(raw_m["mae"], method_m["mae"]),
    }
