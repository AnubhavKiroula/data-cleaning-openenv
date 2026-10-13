"""
Per-window change in MAE, as a distribution rather than a mean.

The benchmark table reports one number per fault family. This plot reports the
30 windows behind each of those numbers, because the distributions are the
finding: on spike and mixed the mass sits below zero, on dropout and duplicate
it sits above, and pooled across families the mean and the median fall on
opposite sides of zero.

Reads ``reports/significance.json`` (written by ``scripts/significance_test.py``)
and writes ``plots/per_window_delta.png``.
"""

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

IN_PATH = "reports/significance.json"
OUT_PATH = "plots/per_window_delta.png"

LABELS = {
    "spike": "Electrical\nspike",
    "drift": "Calibration\ndrift",
    "dropout": "Transmission\ndropout",
    "duplicate": "Duplicate\npacket",
    "mixed": "Mixed\nreal-world",
}


def main() -> None:
    with open(IN_PATH) as fh:
        res = json.load(fh)

    per_window = res["per_window_mae"]
    families = list(LABELS)
    tests = res["by_comparison"]["rl_vs_do_nothing"]["by_family"]

    deltas = [
        np.array(per_window[f]["rl_seed_mean"]) - np.array(per_window[f]["raw"])
        for f in families
    ]

    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    rng = np.random.RandomState(0)

    bp = ax.boxplot(
        deltas,
        positions=range(len(families)),
        widths=0.55,
        showfliers=False,
        medianprops={"color": "#111111", "linewidth": 1.6},
        boxprops={"color": "#555555"},
        whiskerprops={"color": "#555555"},
        capprops={"color": "#555555"},
    )
    del bp

    for i, d in enumerate(deltas):
        jitter = rng.uniform(-0.17, 0.17, size=len(d))
        colours = np.where(d < 0, "#1f6f4a", "#9c2b2b")
        ax.scatter(
            i + jitter, d, s=14, c=colours, alpha=0.65, linewidths=0, zorder=3
        )
        ax.scatter(
            [i], [d.mean()], marker="D", s=38, c="#1a4f8a", zorder=4,
            label="mean" if i == 0 else None,
        )

    ax.axhline(0.0, color="#333333", linewidth=1.0, linestyle="--")

    for i, f in enumerate(families):
        p = tests[f]["p_value"]
        stars = "n.s." if p is None or p >= 0.05 else ("***" if p < 1e-3 else "*")
        ax.annotate(
            stars,
            (i, max(deltas[i].max(), 0) + 0.012),
            ha="center",
            fontsize=9,
            color="#333333",
        )

    ax.set_xticks(range(len(families)))
    ax.set_xticklabels([LABELS[f] for f in families], fontsize=9)
    ax.set_ylabel("Change in window MAE  (negative = agent reduced error)")
    ax.set_title(
        "Per-window outcome of the learned policy, 30 held-out windows per family\n"
        "(5-seed mean per window; Wilcoxon signed-rank, Holm-corrected)",
        fontsize=10,
    )
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    fig.savefig(OUT_PATH, dpi=200)
    print(f"Written {OUT_PATH}")


if __name__ == "__main__":
    main()
