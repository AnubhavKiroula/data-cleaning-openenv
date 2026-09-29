"""
Training-split grid search for the rule-based baseline's hyperparameters.

Run with ``python -m backend.ml.calibrate_baseline``. The winning configuration
is recorded as the ``CALIBRATED_*`` constants in
:mod:`backend.ml.rule_based_baseline`.

The search touches the training split only. Giving the baseline a real tuning
budget on data it is allowed to see is what makes the headline comparison a
comparison rather than a demonstration: the alternative — hand-picking a
threshold and reporting whatever it does — is how a strawman gets built.
"""

import argparse
import itertools
import json
from typing import Any, Dict, List

import numpy as np

from backend.ml.metrics import evaluate_window
from backend.ml.rule_based_baseline import RuleBasedStreamFilter
from envs.data_cleaning_env.tasks.graders import (
    CORRUPTION_TYPES,
    generate_iot_stream_dataset,
)

Z_GRID = [4.0, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0, 25.0, 30.0, 40.0, 60.0]
HISTORY_GRID = [12, 24, 48]
WARMUP_GRID = [6, 12]


def calibrate(
    num_windows: int = 40,
    window_size: int = 24,
    seed_base: int = 500,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Grid-search the filter on training windows; return the ranked results."""
    families = list(CORRUPTION_TYPES) + ["none"]
    windows = {
        ct: [
            generate_iot_stream_dataset(
                window_size=window_size,
                corruption_type=ct,
                split="train",
                seed=seed_base + i * 13,
            )
            for i in range(num_windows)
        ]
        for ct in families
    }

    results: List[Dict[str, Any]] = []
    for z, hist, warm in itertools.product(Z_GRID, HISTORY_GRID, WARMUP_GRID):
        per_family = {}
        for ct, datasets in windows.items():
            maes = []
            for ds in datasets:
                f = RuleBasedStreamFilter(
                    history_len=hist, z_threshold=z, warmup=warm
                )
                maes.append(evaluate_window(ds, f.predict_window(ds))["mae"])
            per_family[ct] = float(np.mean(maes))

        results.append(
            {
                "z_threshold": z,
                "history_len": hist,
                "warmup": warm,
                # Objective: mean MAE over the five fault families. 'none' is
                # reported but excluded, so the filter is not rewarded merely
                # for refusing to act on uncorrupted input.
                "objective": float(np.mean([per_family[c] for c in CORRUPTION_TYPES])),
                "per_family_mae": per_family,
            }
        )

    results.sort(key=lambda r: r["objective"])
    best = results[0]

    if verbose:
        header = f"{'obj':>7} {'z':>5} {'hist':>5} {'warm':>5} | " + " ".join(
            f"{c[:6]:>7}" for c in families
        )
        print(header)
        print("-" * len(header))
        for r in results[:10]:
            print(
                f"{r['objective']:7.4f} {r['z_threshold']:5.1f} "
                f"{r['history_len']:5d} {r['warmup']:5d} | "
                + " ".join(f"{r['per_family_mae'][c]:7.4f}" for c in families)
            )
        print(
            f"\nBest: z_threshold={best['z_threshold']}, "
            f"history_len={best['history_len']}, warmup={best['warmup']}"
        )

    return {"best": best, "ranked": results}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-windows", type=int, default=40)
    parser.add_argument("--window-size", type=int, default=24)
    parser.add_argument("--out", type=str, default=None, help="Write JSON results here")
    args = parser.parse_args()

    res = calibrate(num_windows=args.num_windows, window_size=args.window_size)
    if args.out:
        with open(args.out, "w") as fh:
            json.dump(res, fh, indent=2)
        print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
