"""
Live demonstration of the policy on one chosen window.

    python scripts/demo_window.py                      # a representative window
    python scripts/demo_window.py --pick               # search for candidates
    python scripts/demo_window.py --seed 2155 --corruption spike

Prints the agent's decision at every timestep beside the raw reading and the
reference value, then writes a before/after plot.

**Why a chosen window, and why that is not cherry-picking.** Per-window
variance is large: over 750 test episodes the policy improves 34%, leaves 31%
unchanged and *damages* 35%, so a window drawn at random is close to a coin
flip and tells an audience nothing about the method. This script therefore
defaults to a window that is *representative of the measured average* on a
family where the policy demonstrably works, and it prints the population
statistics alongside so the single window is never mistaken for the result.

The honest number is the aggregate in `docs/PROFESSOR_BRIEFING.md` section 4.
This is an illustration of mechanism, not evidence of performance. `--pick`
exists so you can see the whole candidate distribution rather than trusting
the default.
"""

import argparse
import os
import sys

import numpy as np

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from backend.ml.dqn_model import DQNAgent  # noqa: E402
from backend.ml.metrics import carry_forward, evaluate_window  # noqa: E402
from backend.ml.rule_based_baseline import RuleBasedStreamFilter  # noqa: E402
from envs.data_cleaning_env.server.environment import (  # noqa: E402
    DataCleaningEnvironment,
)

DEFAULT_MODEL = "models/dqn_iot_stream_best.pt"
# Chosen with --pick: the spike window whose error reduction (+14.4%) sits
# nearest the family median (+16.0%), so the demo shows typical behaviour
# rather than a best case. 17 of 30 spike windows improve, 5 are damaged.
DEFAULT_SEED = 3273
DEFAULT_CORRUPTION = "spike"


def run_window(agent, env, seed, corruption, window_size=24):
    """Roll the greedy policy over one window; return the per-step trace."""
    kwargs = {
        "task_name": "iot_stream",
        "window_size": window_size,
        "split": "test",
        "corruption_type": corruption,
        "seed": seed,
    }
    with agent.eval_mode():
        obs = env.reset(**kwargs)
        agent.reset(obs)
        trace = []
        while not obs["done"]:
            raw = obs["current_data"]["value"]
            flags = list(obs["issues_detected"])
            action = agent.get_action(obs, obs["legal_actions"])
            obs = env.step(action["action_type"], action["column"], action["value"])
            row = env.cleaned_data[-1]
            trace.append(
                {
                    "t": row["timestep"],
                    "raw": raw,
                    "action": action["action_type"],
                    "cleaned": row["value"],
                    "truth": row["ground_truth"],
                    "fault": row["fault_type"],
                    "flags": flags,
                }
            )
    dataset = [dict(r) for r in env.dataset]
    metrics = evaluate_window(dataset, [r.get("value") for r in env.cleaned_data])
    return trace, dataset, metrics


def pick(agent, env, corruption, n=30):
    """Print every candidate window so the default can be sanity-checked."""
    rows = []
    for i in range(n):
        seed = 2026 + i * 43
        _, _, m = run_window(agent, env, seed, corruption)
        rows.append((seed, m["raw_mae"], m["mae"], m["error_reduction_pct"]))

    reductions = np.array([r[3] for r in rows])
    median = float(np.median(reductions))
    print(f"{n} candidate '{corruption}' windows, sorted by error reduction:\n")
    print(f"{'seed':>6} {'raw MAE':>9} {'RL MAE':>9} {'reduction':>11}")
    for seed, raw, rl, red in sorted(rows, key=lambda r: -r[3]):
        mark = " <- nearest the median" if abs(red - median) < 1e-9 else ""
        print(f"{seed:>6} {raw:>9.4f} {rl:>9.4f} {red:>+10.1f}%{mark}")
    nearest = min(rows, key=lambda r: abs(r[3] - median))
    print(f"\nfamily median reduction {median:+.1f}%")
    print(f"most representative seed: {nearest[0]} ({nearest[3]:+.1f}%)")
    print(f"{int((reductions > 0).sum())}/{n} windows improved, "
          f"{int((reductions < 0).sum())}/{n} damaged")


def plot(trace, dataset, corruption, seed, out):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    gt = np.array([r["ground_truth"] for r in dataset])
    corrupted = carry_forward([r["raw_corrupted"] for r in dataset])
    rl = carry_forward([s["cleaned"] for s in trace])
    rule = np.asarray(
        RuleBasedStreamFilter(z_threshold=4.0, history_len=24, warmup=6)
        .predict_window(dataset),
        dtype=float,
    )
    t = np.arange(len(gt))
    acted = [s["t"] for s in trace if s["action"] != "skip"]

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    fig, ax = plt.subplots(figsize=(13, 5.5))
    ax.plot(t, gt, "k-", lw=2.6, label="Ground truth", zorder=5)
    ax.plot(t, corrupted, color="#d62728", lw=1.2, ls=":", marker="x", ms=6,
            label="Corrupted stream")
    ax.plot(t, rule, color="#ff7f0e", lw=1.5, alpha=0.9, label="Rule filter (z=4)")
    ax.plot(t, rl, color="#1f77b4", lw=2.1, label="RL-Cleanse DQN")
    if acted:
        ax.scatter(acted, rl[acted], facecolors="none", edgecolors="#1f77b4",
                   s=150, lw=1.8, label="Agent intervened", zorder=6)
    ax.set_title(
        f"RL-Cleanse on a 24-hour CO(GT) window "
        f"({corruption} faults, test split, seed {seed})",
        fontweight="bold",
    )
    ax.set_xlabel("Hour within episode")
    ax.set_ylabel("CO concentration (mg/m$^3$)")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--corruption", default=DEFAULT_CORRUPTION)
    p.add_argument("--window-size", type=int, default=24)
    p.add_argument("--pick", action="store_true",
                   help="List candidate windows instead of demonstrating one.")
    p.add_argument("--out", default="plots/demo_window.png")
    args = p.parse_args()

    agent = DQNAgent(device="cpu")
    agent.load_model(args.model)
    env = DataCleaningEnvironment(history_len=5)

    if args.pick:
        pick(agent, env, args.corruption)
        return

    trace, dataset, m = run_window(
        agent, env, args.seed, args.corruption, args.window_size
    )

    print("=" * 78)
    print(f"RL-Cleanse on one {args.window_size}-hour window "
          f"({args.corruption} faults, test split, seed {args.seed})")
    print("=" * 78)
    print(f"{'t':>3} {'raw':>9} {'action':>17} {'cleaned':>9} {'truth':>8} "
          f"{'err raw':>8} {'err out':>8}")
    print("-" * 78)
    for s in trace:
        raw_s = "DROPPED" if s["raw"] is None else f"{s['raw']:.3f}"
        err_raw = "   --" if s["raw"] is None else f"{abs(s['raw'] - s['truth']):.3f}"
        cleaned = s["cleaned"] if s["cleaned"] is not None else float("nan")
        err_out = abs(cleaned - s["truth"])
        mark = "  *" if s["action"] != "skip" else ""
        print(f"{s['t']:>3} {raw_s:>9} {s['action']:>17} {cleaned:>9.3f} "
              f"{s['truth']:>8.3f} {err_raw:>8} {err_out:>8.3f}{mark}")

    interventions = sum(1 for s in trace if s["action"] != "skip")
    print("-" * 78)
    print(f"interventions: {interventions}/{len(trace)} steps  (* marks an action)")
    print(f"window MAE   : raw {m['raw_mae']:.4f} -> RL {m['mae']:.4f} "
          f"({m['error_reduction_pct']:+.1f}%)")

    print("\nContext, so this window is not mistaken for the result:")
    print("  Over 750 test episodes (5 seeds) the policy improves 34%, leaves 31%")
    print("  unchanged and damages 35%. By family it improves 63% of spike and 65%")
    print("  of mixed windows, but damages 70% of dropout and 39% of duplicate.")
    print("  The aggregate in docs/PROFESSOR_BRIEFING.md section 4 is the result;")
    print("  this window illustrates the mechanism. Run with --pick to see the")
    print("  full candidate distribution.")

    out = plot(trace, dataset, args.corruption, args.seed, args.out)
    print(f"\nPlot written: {out}")


if __name__ == "__main__":
    main()
