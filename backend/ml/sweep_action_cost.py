"""
Validation sweep over the reward's action cost.

    python -m backend.ml.sweep_action_cost --epochs 400 --seeds 1 2 3

The published reward (``action_cost = 0.0``) prices intervention at nothing, so
a policy pays only when a correction makes the error worse. Measured
consequence: it over-corrects streams that need nothing, damaging 70% of dropout
windows and 39% of duplicate windows, which is why the equal-weight relative
aggregate (1.082) is worse than inaction even though absolute MAE (0.2002 vs
0.2170) is better.

A positive cost makes acting a decision with a price. This sweep asks whether
any cost is worth paying.

**Decided on validation, never on test.** Selecting a hyperparameter by
held-out performance is the exact mistake that invalidated the first round of
results in this project. Test numbers are produced once, afterwards, for
whichever cost validation chose. If no cost beats 0.0 on validation, that is a
publishable ablation and the published reward stands.
"""

import argparse
import json
from typing import Any, Dict, List, Optional

import numpy as np

from backend.ml.train_dqn import DQNTrainer

DEFAULT_COSTS = [0.0, 0.05, 0.10, 0.20]


def evaluate_cost(
    action_cost: float,
    seeds: List[int],
    epochs: int,
    device: str,
    val_windows: int,
) -> Dict[str, Any]:
    """Train one agent per seed at this cost; return validation statistics."""
    runs = []
    for seed in seeds:
        trainer = DQNTrainer(
            {
                "epochs": epochs,
                "device": device,
                "seed": seed,
                "val_windows": val_windows,
                "eval_every": max(epochs // 8, 1),
                "action_cost": action_cost,
            }
        )
        # save=False: nothing is written to models/, so a sweep cannot clobber
        # the published checkpoints. The selected weights come back in memory.
        result = trainer.train(epochs=epochs, save=False)
        runs.append(
            {
                "seed": seed,
                "best_epoch": result["best_epoch"],
                "val_relative_mae": result["best_val_relative_mae"],
            }
        )

    vals = [r["val_relative_mae"] for r in runs]
    return {
        "action_cost": action_cost,
        "runs": runs,
        "mean": float(np.mean(vals)),
        "std": float(np.std(vals)),
        "min": float(np.min(vals)),
        "max": float(np.max(vals)),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--costs", type=float, nargs="+", default=DEFAULT_COSTS)
    p.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    p.add_argument("--epochs", type=int, default=400)
    p.add_argument("--device", default="auto")
    p.add_argument("--val-windows", type=int, default=30)
    p.add_argument("--out", default="reports/action_cost_sweep.json")
    args = p.parse_args()

    results = []
    for cost in args.costs:
        res = evaluate_cost(
            cost, args.seeds, args.epochs, args.device, args.val_windows
        )
        results.append(res)
        print(
            f"[sweep] action_cost={cost:<5} "
            f"val rel-MAE {res['mean']:.4f} +/- {res['std']:.4f} "
            f"(range {res['min']:.4f}-{res['max']:.4f})",
            flush=True,
        )

    baseline = next((r for r in results if r["action_cost"] == 0.0), None)
    best = min(results, key=lambda r: r["mean"])

    print("\n" + "=" * 72)
    print(f"ACTION COST SWEEP — {len(args.seeds)} seeds x {args.epochs} epochs, "
          "validation split")
    print("=" * 72)
    print(f"{'cost':>6} {'val rel-MAE':>14} {'std':>8} {'vs 0.0':>10}")
    for r in sorted(results, key=lambda r: r["action_cost"]):
        delta = (
            f"{r['mean'] - baseline['mean']:+.4f}"
            if baseline and r is not baseline
            else "--"
        )
        mark = "  <- best" if r is best else ""
        print(f"{r['action_cost']:>6} {r['mean']:>14.4f} {r['std']:>8.4f} "
              f"{delta:>10}{mark}")

    print("-" * 72)
    if baseline and best["action_cost"] != 0.0 and best["mean"] < baseline["mean"]:
        gap = baseline["mean"] - best["mean"]
        separated = gap > (best["std"] + baseline["std"])
        print(f"Best cost {best['action_cost']} improves validation relative-MAE "
              f"by {gap:.4f}.")
        print(
            "The gap "
            + ("exceeds" if separated else "does NOT exceed")
            + " the combined seed spread, so it is "
            + ("worth adopting" if separated else "within noise — treat as inconclusive")
            + "."
        )
        print("Next: retrain 5 seeds at this cost, then evaluate on test ONCE.")
    else:
        print("No action cost beat 0.0 on validation. The published reward stands;")
        print("report this as an ablation rather than adopting a worse policy.")
    print("=" * 72)

    import os

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(
            {
                "epochs": args.epochs,
                "seeds": args.seeds,
                "val_windows": args.val_windows,
                "results": results,
                "best_cost": best["action_cost"],
            },
            fh,
            indent=2,
        )
    print(f"Written: {args.out}")


if __name__ == "__main__":
    main()
