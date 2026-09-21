"""
Benchmark Evaluation: Rule-Based Online Baseline vs. Learned RL-Cleanse DQN Agent.

Runs both filters on identical chronological test windows across all corruption types
(Spikes, Drift, Dropouts, Duplicates, and Mixed) under real-time streaming constraints.
Generates comparative summary tables and visual plots.
"""

import os
import torch
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Any, List

from envs.data_cleaning_env.server.environment import DataCleaningEnvironment
from backend.ml.rule_based_baseline import RuleBasedStreamFilter
from backend.ml.dqn_model import DQNAgent


def run_benchmark_comparison(
    model_path: str = "models/dqn_iot_stream_best.pt",
    num_windows: int = 30,
    window_size: int = 24,
    seed_base: int = 2026,
    save_plot_path: str = "plots/baseline_vs_rl_comparison.png",
) -> Dict[str, Any]:
    """
    Run identical test streams through Baseline and RL Agent and compute metrics.
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    agent = DQNAgent(state_dim=50, action_dim=7, device=device)
    if os.path.exists(model_path):
        agent.load_model(model_path)
    agent.set_training_mode(False)

    baseline_filter = RuleBasedStreamFilter(history_len=5, z_threshold=2.8)
    env = DataCleaningEnvironment(history_len=5)

    corruption_types = ["spike", "drift", "dropout", "duplicate", "mixed"]

    results = []

    for ctype in corruption_types:
        raw_maes, raw_rmses = [], []
        base_maes, base_rmses, base_scores = [], [], []
        rl_maes, rl_rmses, rl_scores = [], [], []

        for w_idx in range(num_windows):
            seed = seed_base + w_idx * 43

            # 1. Reset environment for this test window
            obs = env.reset(
                task_name="iot_stream",
                window_size=window_size,
                split="test",
                corruption_type=ctype,
                seed=seed,
            )
            raw_dataset = env.dataset

            # 2. Evaluate Baseline Filter
            baseline_cleaned = baseline_filter.process_window(raw_dataset)
            base_score, _ = env.grader(baseline_cleaned)

            b_errs = [
                abs(r["value"] - r["ground_truth"])
                for r in baseline_cleaned
                if r.get("ground_truth") is not None and r.get("value") is not None
            ]
            raw_errs = [
                abs(r["raw_corrupted"] - r["ground_truth"])
                for r in raw_dataset
                if r.get("ground_truth") is not None and r.get("raw_corrupted") is not None
            ]

            raw_maes.append(float(np.mean(raw_errs)))
            raw_rmses.append(float(np.sqrt(np.mean([e**2 for e in raw_errs]))))

            base_maes.append(float(np.mean(b_errs)))
            base_rmses.append(float(np.sqrt(np.mean([e**2 for e in b_errs]))))
            base_scores.append(base_score)

            # 3. Evaluate RL Agent on identical window
            # Reset env with identical seed
            obs = env.reset(
                task_name="iot_stream",
                window_size=window_size,
                split="test",
                corruption_type=ctype,
                seed=seed,
            )
            agent.reset(obs)
            done = False

            while not done:
                legal_actions = obs.get("legal_actions", ["skip"])
                action_dict = agent.get_action(obs, legal_actions)
                obs = env.step(
                    action_type=action_dict["action_type"],
                    column=action_dict.get("column", "value"),
                    value=action_dict.get("value"),
                )
                done = obs["done"]

            rl_cleaned = env.cleaned_data
            rl_score, _ = env.grader(rl_cleaned)
            rl_errs = [
                abs(r["value"] - r["ground_truth"])
                for r in rl_cleaned
                if r.get("ground_truth") is not None and r.get("value") is not None
            ]

            rl_maes.append(float(np.mean(rl_errs)))
            rl_rmses.append(float(np.sqrt(np.mean([e**2 for e in rl_errs]))))
            rl_scores.append(rl_score)

        # Average over test windows
        mean_raw_mae = float(np.mean(raw_maes))
        mean_base_mae = float(np.mean(base_maes))
        mean_rl_mae = float(np.mean(rl_maes))

        mean_base_rmse = float(np.mean(base_rmses))
        mean_rl_rmse = float(np.mean(rl_rmses))

        mean_base_score = float(np.mean(base_scores))
        mean_rl_score = float(np.mean(rl_scores))

        base_improv = (
            (1.0 - mean_base_mae / max(mean_raw_mae, 1e-6)) * 100.0
            if mean_raw_mae > 1e-6
            else 0.0
        )
        rl_improv = (
            (1.0 - mean_rl_mae / max(mean_raw_mae, 1e-6)) * 100.0
            if mean_raw_mae > 1e-6
            else 0.0
        )

        results.append(
            {
                "Corruption": ctype.capitalize(),
                "Raw MAE": round(mean_raw_mae, 4),
                "Baseline MAE": round(mean_base_mae, 4),
                "RL Agent MAE": round(mean_rl_mae, 4),
                "Baseline RMSE": round(mean_base_rmse, 4),
                "RL Agent RMSE": round(mean_rl_rmse, 4),
                "Baseline Score": round(mean_base_score, 3),
                "RL Agent Score": round(mean_rl_score, 3),
                "Baseline Improv (%)": round(base_improv, 1),
                "RL Improv (%)": round(rl_improv, 1),
            }
        )

    df_results = pd.DataFrame(results)

    # Plot comparison bar chart
    os.makedirs(os.path.dirname(save_plot_path), exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    x = np.arange(len(df_results))
    width = 0.35

    # Plot 1: MAE Comparison
    axes[0].bar(x - width / 2, df_results["Baseline MAE"], width, label="Rule Baseline", color="#ff7f0e", alpha=0.85)
    axes[0].bar(x + width / 2, df_results["RL Agent MAE"], width, label="RL-Cleanse DQN", color="#1f77b4", alpha=0.85)
    axes[0].set_title("Mean Absolute Error (MAE) by Corruption Type\n(Lower is Better)", fontsize=11, fontweight="bold")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(df_results["Corruption"], fontsize=10)
    axes[0].set_ylabel("MAE vs Ground Truth")
    axes[0].legend()
    axes[0].grid(True, linestyle="--", alpha=0.5, axis="y")

    # Plot 2: Task Score (Denoising Quality)
    axes[1].bar(x - width / 2, df_results["Baseline Score"], width, label="Rule Baseline", color="#ff7f0e", alpha=0.85)
    axes[1].bar(x + width / 2, df_results["RL Agent Score"], width, label="RL-Cleanse DQN", color="#2ca02c", alpha=0.85)
    axes[1].set_title("Task Quality Score (0.0 to 1.0)\n(Higher is Better)", fontsize=11, fontweight="bold")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(df_results["Corruption"], fontsize=10)
    axes[1].set_ylabel("Task Score")
    axes[1].legend()
    axes[1].grid(True, linestyle="--", alpha=0.5, axis="y")

    plt.tight_layout()
    plt.savefig(save_plot_path, dpi=300)
    plt.close()

    return {
        "df": df_results,
        "plot_path": save_plot_path,
    }


if __name__ == "__main__":
    res = run_benchmark_comparison()
    print("\n" + "=" * 80)
    print("BENCHMARK COMPARISON TABLE: RULE-BASED BASELINE VS. RL-CLEANSE DQN")
    print("=" * 80)
    print(res["df"].to_markdown(index=False))
    print("=" * 80)
    print(f"Plot saved to: {res['plot_path']}")
