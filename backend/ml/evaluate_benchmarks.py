"""
Benchmark: do-nothing vs. rule-based streaming filter vs. RL-Cleanse DQN.

All three methods are scored on *identical* test windows, under the same online
constraint, through the single metric implementation in
:mod:`backend.ml.metrics`. Run with::

    python -m backend.ml.evaluate_benchmarks

Reporting choices worth knowing about before reading the table:

* **The do-nothing policy is a column, not an afterthought.** It is the stream
  passed through with carry-forward across dropouts. Both other methods have to
  beat it to be worth deploying, and on some fault families neither does.
* **Relative MAE, not just absolute.** The five fault families differ in error
  scale by two orders of magnitude (mixed ~0.5, duplicate ~0.03), so an
  unweighted mean of absolute MAE is dominated by one family. Each family's MAE
  is therefore also reported relative to its own do-nothing MAE, where 1.0
  means "no improvement" and the mean of those ratios is the headline number.
* **Error-reduction percentages on the benign families are near-meaningless**
  and are reported anyway, with a warning. When raw MAE is 0.03, a 0.01
  absolute change reads as -33%; the absolute columns are the honest ones there.
* **Multi-seed.** A single DQN run's validation relative-MAE spans roughly
  0.93-1.08 on this task, so the RL column aggregates across seeds when
  per-seed checkpoints are present, and the spread is reported.
"""

import argparse
import glob
import json
import os
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from backend.ml.dqn_model import DQNAgent
from backend.ml.metrics import evaluate_window
from backend.ml.rule_based_baseline import (
    CALIBRATED_HISTORY_LEN,
    CALIBRATED_WARMUP,
    CALIBRATED_Z_THRESHOLD,
    RuleBasedStreamFilter,
)
from envs.data_cleaning_env.server.environment import DataCleaningEnvironment
from envs.data_cleaning_env.tasks.graders import CORRUPTION_TYPES

DEFAULT_MODEL = "models/dqn_iot_stream_best.pt"
SEED_GLOB = "models/dqn_iot_stream_best_seed*.pt"

# Two rule-filter configurations are reported, because one number alone is
# misleading in opposite directions:
#
#   'calibrated' is the winner of the training-split grid search. Its gate is so
#   wide that it essentially never fires, so it scores identically to doing
#   nothing. That is the honest calibration outcome, but as a table column it is
#   degenerate and invites the reader to think the baseline was never run.
#
#   'textbook' is the conventional Hampel cut-off a practitioner would reach for
#   without calibrating on this channel. It shows what a reasonably-tuned
#   industrial filter actually does to this signal, which is the more
#   informative comparison.
BASELINE_CONFIGS = {
    "calibrated": {
        "z_threshold": CALIBRATED_Z_THRESHOLD,
        "history_len": CALIBRATED_HISTORY_LEN,
        "warmup": CALIBRATED_WARMUP,
    },
    "textbook": {"z_threshold": 4.0, "history_len": 24, "warmup": 6},
}


def _rl_predict(agent: DQNAgent, env: DataCleaningEnvironment, reset_kwargs) -> List[Any]:
    """Run the greedy policy over one window and return its emissions."""
    obs = env.reset(**reset_kwargs)
    agent.reset(obs)
    while not obs["done"]:
        action = agent.get_action(obs, obs["legal_actions"])
        obs = env.step(
            action_type=action["action_type"],
            column=action["column"],
            value=action["value"],
        )
    return [r.get("value") for r in env.cleaned_data]


def run_benchmark(
    model_path: str = DEFAULT_MODEL,
    seed_models: Optional[List[str]] = None,
    num_windows: int = 30,
    window_size: int = 24,
    seed_base: int = 2026,
    split: str = "test",
    device: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate every method on the same windows of ``split``.

    Returns a dict with the results dataframe, the per-family detail and the
    aggregate headline numbers.
    """
    import torch

    device = device or ("cuda" if torch.cuda.is_available() else "cpu")

    if seed_models is None:
        seed_models = sorted(glob.glob(SEED_GLOB))
    if not seed_models:
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"No trained checkpoint found at {model_path} and no per-seed "
                f"checkpoints matching {SEED_GLOB}. Train first with "
                "`python -m backend.ml.train_dqn --epochs 800 --seeds 1 2 3 4 5`."
            )
        seed_models = [model_path]

    agents = []
    for path in seed_models:
        agent = DQNAgent(device=device)
        agent.load_model(path)
        agents.append((os.path.basename(path), agent))

    env = DataCleaningEnvironment(history_len=5)
    rows = []
    detail: Dict[str, Any] = {}

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

        raw_maes, raw_rmses = [], []
        base: Dict[str, Dict[str, List[float]]] = {
            name: {"mae": [], "rmse": [], "score": []} for name in BASELINE_CONFIGS
        }
        # Per-seed means, so the RL column can report a spread.
        rl_per_seed: Dict[str, Dict[str, float]] = {}

        for kwargs in reset_kwargs_list:
            env.reset(**kwargs)
            dataset = [dict(r) for r in env.dataset]

            m_raw = evaluate_window(dataset, [r["raw_corrupted"] for r in dataset])
            raw_maes.append(m_raw["raw_mae"])
            raw_rmses.append(m_raw["raw_rmse"])

            for name, cfg in BASELINE_CONFIGS.items():
                m_base = evaluate_window(
                    dataset, RuleBasedStreamFilter(**cfg).predict_window(dataset)
                )
                base[name]["mae"].append(m_base["mae"])
                base[name]["rmse"].append(m_base["rmse"])
                base[name]["score"].append(m_base["score"])

        for name, agent in agents:
            maes, rmses, scores = [], [], []
            with agent.eval_mode():
                for kwargs in reset_kwargs_list:
                    preds = _rl_predict(agent, env, kwargs)
                    m = evaluate_window([dict(r) for r in env.dataset], preds)
                    maes.append(m["mae"])
                    rmses.append(m["rmse"])
                    scores.append(m["score"])
            rl_per_seed[name] = {
                "mae": float(np.mean(maes)),
                "rmse": float(np.mean(rmses)),
                "score": float(np.mean(scores)),
            }

        raw_mae = float(np.mean(raw_maes))
        base_mae_by_cfg = {
            name: float(np.mean(v["mae"])) for name, v in base.items()
        }
        base_mae = base_mae_by_cfg["calibrated"]
        rl_maes = [v["mae"] for v in rl_per_seed.values()]
        rl_mae = float(np.mean(rl_maes))
        rl_std = float(np.std(rl_maes))

        def reduction(mae: float) -> float:
            return (
                float((raw_mae - mae) / raw_mae * 100.0) if raw_mae > 1e-9 else 0.0
            )

        textbook_mae = base_mae_by_cfg["textbook"]
        rows.append(
            {
                "Corruption": ctype.capitalize(),
                "Raw MAE": round(raw_mae, 4),
                "Rule(cal) MAE": round(base_mae, 4),
                "Rule(txt) MAE": round(textbook_mae, 4),
                "RL MAE": round(rl_mae, 4),
                "RL std": round(rl_std, 4),
                "Rule(cal) rel": round(base_mae / max(raw_mae, 1e-9), 3),
                "Rule(txt) rel": round(textbook_mae / max(raw_mae, 1e-9), 3),
                "RL rel": round(rl_mae / max(raw_mae, 1e-9), 3),
                "RL red %": round(reduction(rl_mae), 1),
            }
        )
        detail[ctype] = {
            "raw_mae": raw_mae,
            "raw_rmse": float(np.mean(raw_rmses)),
            "baseline_mae_by_config": base_mae_by_cfg,
            "baseline_scores_by_config": {
                name: float(np.mean(v["score"])) for name, v in base.items()
            },
            "rl_per_seed": rl_per_seed,
        }

    df = pd.DataFrame(rows)
    aggregate = {
        "num_windows": num_windows,
        "window_size": window_size,
        "split": split,
        "seed_base": seed_base,
        "models": [n for n, _ in agents],
        "mean_raw_mae": float(df["Raw MAE"].mean()),
        "mean_baseline_calibrated_mae": float(df["Rule(cal) MAE"].mean()),
        "mean_baseline_textbook_mae": float(df["Rule(txt) MAE"].mean()),
        "mean_rl_mae": float(df["RL MAE"].mean()),
        # Two aggregates that disagree, both reported. See the printout.
        "baseline_calibrated_relative_mae": float(df["Rule(cal) rel"].mean()),
        "baseline_textbook_relative_mae": float(df["Rule(txt) rel"].mean()),
        "rl_relative_mae": float(df["RL rel"].mean()),
    }
    return {"df": df, "detail": detail, "aggregate": aggregate}


def plot_comparison(
    df: pd.DataFrame, save_path: str = "plots/baseline_vs_rl_comparison.png"
) -> str:
    """Bar chart of absolute MAE and of MAE relative to the do-nothing policy."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    x = np.arange(len(df))
    w = 0.27

    axes[0].bar(x - w, df["Raw MAE"], w, label="Do nothing", color="#9e9e9e")
    axes[0].bar(x, df["Rule(txt) MAE"], w, label="Rule filter (textbook z=4)",
                color="#ff7f0e")
    axes[0].bar(
        x + w,
        df["RL MAE"],
        w,
        yerr=df["RL std"],
        capsize=3,
        label="RL-Cleanse DQN",
        color="#1f77b4",
    )
    axes[0].set_title(
        "Absolute MAE by fault family (lower is better)", fontweight="bold"
    )
    axes[0].set_ylabel("MAE vs. measured ground truth")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(df["Corruption"])
    axes[0].legend()
    axes[0].grid(alpha=0.3, axis="y")

    # Log scale: the textbook filter reaches 11x on the duplicate family, which
    # on a linear axis flattens every RL bar onto the 1.0 reference line and
    # hides the comparison this panel exists to show.
    for bars in (
        axes[1].bar(x - w / 2, df["Rule(txt) rel"], w,
                    label="Rule filter (textbook z=4)", color="#ff7f0e"),
        axes[1].bar(x + w / 2, df["RL rel"], w,
                    label="RL-Cleanse DQN", color="#1f77b4"),
    ):
        for rect in bars:
            axes[1].annotate(
                f"{rect.get_height():.2f}",
                (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                textcoords="offset points", xytext=(0, 3),
                ha="center", fontsize=7.5,
            )
    axes[1].set_yscale("log")
    axes[1].axhline(1.0, color="#333", ls="--", lw=1.4, zorder=0,
                    label="Do nothing (= 1.0)")
    axes[1].set_ylim(0.5, 22)
    axes[1].set_yticks([0.5, 1, 2, 5, 10, 20])
    axes[1].get_yaxis().set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"{v:g}")
    )
    axes[1].set_title(
        "MAE relative to doing nothing (log scale; <1.0 is an improvement)",
        fontweight="bold",
    )
    axes[1].set_ylabel("method MAE / do-nothing MAE")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(df["Corruption"])
    axes[1].legend(loc="upper left", fontsize=8.5)
    axes[1].grid(alpha=0.3, axis="y", which="both")

    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
    return save_path


def plot_signal_example(
    save_path: str = "plots/denoising_before_after.png",
    model_path: str = DEFAULT_MODEL,
    seed: int = 2026,
    window_size: int = 24,
) -> str:
    """Ground truth vs. corrupted vs. rule-cleaned vs. RL-cleaned, one window."""
    import matplotlib
    import torch

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from backend.ml.metrics import carry_forward

    device = "cuda" if torch.cuda.is_available() else "cpu"
    agent = DQNAgent(device=device)
    agent.load_model(model_path)

    env = DataCleaningEnvironment(history_len=5)
    kwargs = {
        "task_name": "iot_stream",
        "window_size": window_size,
        "split": "test",
        "corruption_type": "mixed",
        "seed": seed,
    }
    env.reset(**kwargs)
    dataset = [dict(r) for r in env.dataset]
    gt = np.array([r["ground_truth"] for r in dataset])
    corrupted = carry_forward([r["raw_corrupted"] for r in dataset])
    rule = np.asarray(RuleBasedStreamFilter().predict_window(dataset), dtype=float)

    with agent.eval_mode():
        rl = carry_forward(_rl_predict(agent, env, kwargs))

    dropped = [i for i, r in enumerate(dataset) if r["raw_corrupted"] is None]

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig, ax = plt.subplots(figsize=(13, 5.5))
    t = np.arange(len(gt))
    ax.plot(t, gt, "k-", lw=2.4, label="Ground truth", zorder=5)
    ax.plot(t, corrupted, color="#d62728", lw=1.2, ls=":", marker="x", ms=5,
            label="Corrupted (carry-forward)")
    ax.plot(t, rule, color="#ff7f0e", lw=1.4, alpha=0.9, label="Rule filter")
    ax.plot(t, rl, color="#1f77b4", lw=1.8, label="RL-Cleanse DQN")
    if dropped:
        ax.scatter(dropped, gt[dropped], facecolors="none", edgecolors="#d62728",
                   s=140, lw=1.8, label="Transmission dropout", zorder=6)

    ax.set_title(
        f"Online denoising of a 24-hour CO(GT) window (mixed faults, test split, seed {seed})",
        fontweight="bold",
    )
    ax.set_xlabel("Hour within episode")
    ax.set_ylabel("CO concentration (mg/m$^3$)")
    ax.legend(loc="best", fontsize=9)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
    return save_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-windows", type=int, default=30)
    parser.add_argument("--window-size", type=int, default=24)
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("--split", type=str, default="test")
    parser.add_argument(
        "--out", type=str, default="reports/benchmark_results.json"
    )
    args = parser.parse_args()

    res = run_benchmark(
        model_path=args.model,
        num_windows=args.num_windows,
        window_size=args.window_size,
        split=args.split,
    )
    df, agg = res["df"], res["aggregate"]

    print("\n" + "=" * 100)
    print("BENCHMARK: DO-NOTHING vs. RULE-BASED STREAMING FILTER vs. RL-CLEANSE DQN")
    print(f"{args.num_windows} windows x {args.window_size} h, '{args.split}' split, "
          f"{len(agg['models'])} RL seed(s)")
    print("=" * 100)
    print(df.to_string(index=False))
    print("-" * 100)
    print("Rule(cal) = grid-searched on the training split.  "
          "Rule(txt) = conventional Hampel cut-off z=4.")
    print(
        f"\nMean ABSOLUTE MAE   do-nothing {agg['mean_raw_mae']:.4f} | "
        f"rule(cal) {agg['mean_baseline_calibrated_mae']:.4f} | "
        f"rule(txt) {agg['mean_baseline_textbook_mae']:.4f} | "
        f"RL {agg['mean_rl_mae']:.4f}"
    )
    print(
        f"Mean RELATIVE MAE   do-nothing 1.000 | "
        f"rule(cal) {agg['baseline_calibrated_relative_mae']:.3f} | "
        f"rule(txt) {agg['baseline_textbook_relative_mae']:.3f} | "
        f"RL {agg['rl_relative_mae']:.3f}"
    )
    print("=" * 100)
    print("READING THIS TABLE")
    print("  1. The two aggregates disagree, and both are reported. RL wins on mean")
    print("     absolute MAE because it removes a lot of error where there is a lot to")
    print("     remove. It loses on the equal-weight relative mean because it")
    print("     over-corrects the two families whose raw error is already near zero.")
    print("  2. Error-reduction percentages for dropout and duplicate have a near-zero")
    print("     denominator and are not informative; read their absolute MAE instead.")
    print("  3. Rule(cal) scores identically to doing nothing on every family: the")
    print("     calibrated gate essentially never fires. That is the measured outcome")
    print("     of the training-split grid search, not a missing run.")

    plot_path = plot_comparison(df)
    signal_path = plot_signal_example(model_path=args.model)
    print(f"\nPlots written: {plot_path}, {signal_path}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(
            {
                "aggregate": agg,
                "table": df.to_dict(orient="records"),
                "detail": res["detail"],
            },
            fh,
            indent=2,
        )
    print(f"Results written: {args.out}")


if __name__ == "__main__":
    main()
