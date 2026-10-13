"""
Paired significance testing for the RL-Cleanse benchmark.

The headline table reports means. A mean difference of 0.017 MAE, drawn from a
population where 35% of individual windows are *damaged*, is not evidence until
it survives a test. This script supplies the test.

Design:

* **Pairing unit is the window.** Every method is evaluated on the identical
  window (same split, same seed, same injected faults), so the per-window MAEs
  are paired observations and a paired test is the correct one. An unpaired
  test here would throw away the variance reduction that identical windows buy
  and understate the effect.
* **The RL column is the across-seed mean per window.** Five checkpoints are
  five samples of one training procedure, not five methods, so the procedure's
  per-window estimate is their mean. Per-seed tests are reported alongside so a
  reader can see the conclusion does not rest on one lucky seed.
* **Wilcoxon signed-rank, not a t-test.** The per-window differences are
  heavily zero-inflated (on the duplicate family 61% of windows are unchanged)
  and right-skewed by a minority of large transients. Normality is not on offer.
  Zeros are dropped (Wilcoxon's own convention) and the count is reported,
  because dropping them changes what the test is about.
* **A bootstrap CI on the mean difference is reported next to it**, because the
  signed-rank test is about the median of the differences while the benchmark
  headline is a mean. The two answer different questions and both belong.
* **Holm-Bonferroni across the five families**, since each comparison is run
  five times and an uncorrected 0.05 over five tests is not a 0.05.

Run::

    python scripts/significance_test.py --num-windows 30

Writes ``reports/significance.json``.
"""

import argparse
import glob
import json
import os
import sys
from typing import Any, Dict, List

import numpy as np
from scipy.stats import wilcoxon

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.ml.dqn_model import DQNAgent  # noqa: E402
from backend.ml.evaluate_benchmarks import (  # noqa: E402
    BASELINE_CONFIGS,
    SEED_GLOB,
    _rl_predict,
)
from backend.ml.metrics import evaluate_window  # noqa: E402
from backend.ml.rule_based_baseline import RuleBasedStreamFilter  # noqa: E402
from envs.data_cleaning_env.server.environment import DataCleaningEnvironment  # noqa: E402
from envs.data_cleaning_env.tasks.graders import CORRUPTION_TYPES  # noqa: E402

ZERO_TOL = 1e-9


def collect_per_window(
    num_windows: int = 30,
    window_size: int = 24,
    seed_base: int = 2026,
    split: str = "test",
    device: str = "cpu",
) -> Dict[str, Dict[str, Any]]:
    """Per-window MAE for every method on identical windows."""
    seed_models = sorted(glob.glob(SEED_GLOB))
    if not seed_models:
        raise FileNotFoundError(
            f"No per-seed checkpoints matching {SEED_GLOB}. Train first."
        )

    agents = []
    for path in seed_models:
        agent = DQNAgent(device=device)
        agent.load_model(path)
        agents.append((os.path.basename(path), agent))

    env = DataCleaningEnvironment(history_len=5)
    out: Dict[str, Dict[str, Any]] = {}

    for ctype in CORRUPTION_TYPES:
        reset_kwargs_list = [
            {
                "task_name": "iot_stream",
                "window_size": window_size,
                "split": split,
                "corruption_type": ctype,
                "seed": seed_base + i * 43,
            }
            for i in range(num_windows)
        ]

        raw: List[float] = []
        base: Dict[str, List[float]] = {name: [] for name in BASELINE_CONFIGS}
        for kwargs in reset_kwargs_list:
            env.reset(**kwargs)
            dataset = [dict(r) for r in env.dataset]
            raw.append(
                evaluate_window(dataset, [r["raw_corrupted"] for r in dataset])["raw_mae"]
            )
            for name, cfg in BASELINE_CONFIGS.items():
                base[name].append(
                    evaluate_window(
                        dataset, RuleBasedStreamFilter(**cfg).predict_window(dataset)
                    )["mae"]
                )

        rl_by_seed: Dict[str, List[float]] = {}
        for name, agent in agents:
            maes = []
            with agent.eval_mode():
                for kwargs in reset_kwargs_list:
                    preds = _rl_predict(agent, env, kwargs)
                    maes.append(
                        evaluate_window([dict(r) for r in env.dataset], preds)["mae"]
                    )
            rl_by_seed[name] = maes

        out[ctype] = {
            "raw": raw,
            "rule_calibrated": base["calibrated"],
            "rule_textbook": base["textbook"],
            "rl_by_seed": rl_by_seed,
            "rl_seed_mean": np.mean(
                np.array(list(rl_by_seed.values())), axis=0
            ).tolist(),
        }
        print(f"  collected {ctype}: {num_windows} windows x {len(agents)} seeds")

    return out


def bootstrap_ci(
    diff: np.ndarray, n_boot: int = 10000, alpha: float = 0.05, seed: int = 0
) -> List[float]:
    """Percentile bootstrap CI for the mean paired difference."""
    rng = np.random.RandomState(seed)
    n = len(diff)
    means = diff[rng.randint(0, n, size=(n_boot, n))].mean(axis=1)
    lo, hi = np.percentile(means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return [float(lo), float(hi)]


def paired_test(method: np.ndarray, reference: np.ndarray) -> Dict[str, Any]:
    """
    Wilcoxon signed-rank plus a bootstrap CI on the mean difference.

    ``diff = method - reference``, so a negative mean difference means the
    method reduced error against the reference.
    """
    diff = np.asarray(method, dtype=float) - np.asarray(reference, dtype=float)
    nonzero = diff[np.abs(diff) > ZERO_TOL]

    result: Dict[str, Any] = {
        "n_windows": int(len(diff)),
        "n_zero_differences": int(len(diff) - len(nonzero)),
        "mean_difference": float(diff.mean()),
        "median_difference": float(np.median(diff)),
        "mean_difference_ci95": bootstrap_ci(diff),
        "improved": int((diff < -ZERO_TOL).sum()),
        "damaged": int((diff > ZERO_TOL).sum()),
    }

    if len(nonzero) == 0:
        # The calibrated rule filter's gate never fires, so it is bit-identical
        # to pass-through. Reporting p = 1.0 here would imply a test was run.
        result.update(
            {
                "wilcoxon_statistic": None,
                "p_value": None,
                "rank_biserial": None,
                "note": "all paired differences are zero; the two methods are identical",
            }
        )
        return result

    stat, p = wilcoxon(nonzero, alternative="two-sided")
    n = len(nonzero)
    total_rank = n * (n + 1) / 2.0
    # Rank-biserial: +1 means every nonzero window favours the method.
    result.update(
        {
            "wilcoxon_statistic": float(stat),
            "p_value": float(p),
            "rank_biserial": float(2.0 * stat / total_rank - 1.0),
        }
    )
    return result


def holm(p_by_key: Dict[str, float]) -> Dict[str, float]:
    """Holm-Bonferroni adjusted p-values, order preserved."""
    items = [(k, v) for k, v in p_by_key.items() if v is not None]
    m = len(items)
    items.sort(key=lambda kv: kv[1])
    adjusted: Dict[str, float] = {}
    running = 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        adjusted[k] = running
    return {k: adjusted.get(k) for k in p_by_key}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-windows", type=int, default=30)
    parser.add_argument("--window-size", type=int, default=24)
    parser.add_argument("--seed-base", type=int, default=2026)
    parser.add_argument("--split", type=str, default="test")
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument("--output", type=str, default="reports/significance.json")
    args = parser.parse_args()

    print(
        f"Collecting per-window MAE on {args.num_windows} {args.split} windows "
        f"of {args.window_size} h ..."
    )
    per_window = collect_per_window(
        num_windows=args.num_windows,
        window_size=args.window_size,
        seed_base=args.seed_base,
        split=args.split,
        device=args.device,
    )

    comparisons = {
        "rl_vs_do_nothing": "raw",
        "rl_vs_rule_calibrated": "rule_calibrated",
        "rl_vs_rule_textbook": "rule_textbook",
    }

    results: Dict[str, Any] = {"by_comparison": {}, "per_seed": {}, "pooled": {}}

    for label, ref_key in comparisons.items():
        by_family = {}
        for ctype, d in per_window.items():
            by_family[ctype] = paired_test(
                np.array(d["rl_seed_mean"]), np.array(d[ref_key])
            )
        adj = holm({c: r["p_value"] for c, r in by_family.items()})
        for c, r in by_family.items():
            r["p_value_holm"] = adj[c]

        pooled_method = np.concatenate(
            [np.array(d["rl_seed_mean"]) for d in per_window.values()]
        )
        pooled_ref = np.concatenate([np.array(d[ref_key]) for d in per_window.values()])
        results["by_comparison"][label] = {
            "by_family": by_family,
            "pooled_all_families": paired_test(pooled_method, pooled_ref),
        }

    # Per-seed robustness: is the pooled conclusion carried by one seed?
    seed_names = list(next(iter(per_window.values()))["rl_by_seed"].keys())
    for sname in seed_names:
        pooled_method = np.concatenate(
            [np.array(d["rl_by_seed"][sname]) for d in per_window.values()]
        )
        pooled_ref = np.concatenate([np.array(d["raw"]) for d in per_window.values()])
        results["per_seed"][sname] = paired_test(pooled_method, pooled_ref)

    results["config"] = {
        "num_windows": args.num_windows,
        "window_size": args.window_size,
        "split": args.split,
        "seed_base": args.seed_base,
        "seeds": seed_names,
        "test": "Wilcoxon signed-rank, two-sided, zeros dropped",
        "correction": "Holm-Bonferroni across the five fault families",
        "ci": "percentile bootstrap, 10000 resamples, 95%",
    }
    results["per_window_mae"] = per_window

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as fh:
        json.dump(results, fh, indent=2)

    # Printout
    for label in comparisons:
        print(f"\n{label}   (negative mean difference favours RL)")
        print(
            f"{'Family':<12}{'mean diff':>11}{'95% CI':>22}"
            f"{'median':>10}{'zeros':>7}{'p':>10}{'p(Holm)':>10}"
        )
        block = results["by_comparison"][label]
        for ctype, r in block["by_family"].items():
            ci = r["mean_difference_ci95"]
            p = "identical" if r["p_value"] is None else f"{r['p_value']:.4g}"
            ph = "-" if r["p_value_holm"] is None else f"{r['p_value_holm']:.4g}"
            print(
                f"{ctype:<12}{r['mean_difference']:>+11.4f}"
                f"{f'[{ci[0]:+.4f}, {ci[1]:+.4f}]':>22}"
                f"{r['median_difference']:>+10.4f}{r['n_zero_differences']:>7}"
                f"{p:>10}{ph:>10}"
            )
        r = block["pooled_all_families"]
        ci = r["mean_difference_ci95"]
        p = "identical" if r["p_value"] is None else f"{r['p_value']:.4g}"
        print(
            f"{'POOLED':<12}{r['mean_difference']:>+11.4f}"
            f"{f'[{ci[0]:+.4f}, {ci[1]:+.4f}]':>22}"
            f"{r['median_difference']:>+10.4f}{r['n_zero_differences']:>7}{p:>10}"
        )

    print("\nPer-seed, pooled across families, vs do-nothing:")
    for sname, r in results["per_seed"].items():
        p = "identical" if r["p_value"] is None else f"{r['p_value']:.4g}"
        print(
            f"  {sname:<34}{r['mean_difference']:>+10.4f}  p={p:<10}"
            f"improved {r['improved']:>3} / damaged {r['damaged']:>3}"
        )

    print(f"\nWritten to {args.output}")


if __name__ == "__main__":
    main()
