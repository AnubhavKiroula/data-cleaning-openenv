"""
Generate the README banner from real data.

The trace drawn in `assets/banner.svg` is not decorative line art. It is the
same window `scripts/demo_window.py` defaults to -- the spike-family test
window whose error reduction sits nearest the family median -- rolled through
the published checkpoint, with the corrupted input, the policy's output and the
reference signal plotted from the actual arrays. If the checkpoint changes, the
banner changes with it.

That costs nothing and keeps one property the rest of this repository has:
every published figure is regenerable from committed code, including the
decorative one.

Run::

    python scripts/make_banner.py

Writes ``assets/banner.svg``.
"""

import argparse
import os
import sys
from typing import List, Sequence

import numpy as np

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from backend.ml.dqn_model import DQNAgent  # noqa: E402
from envs.data_cleaning_env.server.environment import (  # noqa: E402
    DataCleaningEnvironment,
)

# Matches scripts/demo_window.py, deliberately: the banner and the demo should
# show the same window, so an audience seeing both is not shown two stories.
DEFAULT_MODEL = "models/dqn_iot_stream_best.pt"
DEFAULT_SEED = 3273
DEFAULT_CORRUPTION = "spike"
WINDOW = 24

W, H = 1200, 320
# The plot panel occupies the right of the banner; the title block sits left.
PX0, PX1 = 660, 1152
PY0, PY1 = 74, 250

BG_TOP, BG_BOTTOM = "#0B1F33", "#13314F"
CORRUPT = "#F4A259"
CLEAN = "#2A9D8F"
REFERENCE = "#8FA6BC"
TITLE = "#FFFFFF"
SUB = "#2EC4B6"
MUTED = "#9FB3C8"


def roll(model: str, seed: int, corruption: str):
    """Return (reference, corrupted, cleaned) for one window."""
    agent = DQNAgent(device="cpu")
    agent.load_model(model)
    env = DataCleaningEnvironment(history_len=5)

    with agent.eval_mode():
        obs = env.reset(
            task_name="iot_stream",
            window_size=WINDOW,
            split="test",
            corruption_type=corruption,
            seed=seed,
        )
        agent.reset(obs)
        while not obs["done"]:
            action = agent.get_action(obs, obs["legal_actions"])
            obs = env.step(
                action_type=action["action_type"],
                column=action["column"],
                value=action["value"],
            )

    rows = [dict(r) for r in env.dataset]
    reference = [float(r["ground_truth"]) for r in rows]
    corrupted = [float(r["raw_corrupted"]) for r in rows]
    cleaned = [
        float(r["value"]) if r.get("value") is not None else float("nan")
        for r in env.cleaned_data
    ]
    return reference, corrupted, cleaned


def to_points(series: Sequence[float], lo: float, hi: float) -> str:
    """Map a series onto the panel rectangle and format as SVG points."""
    n = len(series)
    span = max(hi - lo, 1e-9)
    pts: List[str] = []
    for i, v in enumerate(series):
        if not np.isfinite(v):
            continue
        x = PX0 + (PX1 - PX0) * i / max(n - 1, 1)
        y = PY1 - (PY1 - PY0) * (v - lo) / span
        pts.append(f"{x:.1f},{y:.1f}")
    return " ".join(pts)


def build_svg(reference, corrupted, cleaned) -> str:
    finite = [v for v in list(reference) + list(corrupted) + list(cleaned)
              if np.isfinite(v)]
    lo, hi = min(finite), max(finite)
    pad = 0.08 * (hi - lo)
    lo, hi = lo - pad, hi + pad

    # Mark the samples the corruption actually moved, so the eye lands on the
    # spikes the policy is there to pull back.
    hits = [
        i for i, (r, c) in enumerate(zip(reference, corrupted))
        if abs(r - c) > 1e-9
    ]
    span = max(hi - lo, 1e-9)
    marks = []
    for i in hits:
        x = PX0 + (PX1 - PX0) * i / max(len(reference) - 1, 1)
        y = PY1 - (PY1 - PY0) * (corrupted[i] - lo) / span
        marks.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.4" '
                     f'fill="{CORRUPT}" fill-opacity="0.95"/>')

    gridlines = []
    for k in range(1, 4):
        y = PY0 + (PY1 - PY0) * k / 4
        gridlines.append(
            f'<line x1="{PX0}" y1="{y:.1f}" x2="{PX1}" y2="{y:.1f}" '
            f'stroke="#FFFFFF" stroke-opacity="0.07" stroke-width="1"/>'
        )

    alt = (
        "RL-Cleanse banner: a corrupted IoT sensor window, the reference "
        "signal, and the learned policy's output over the same 24 hours"
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{alt}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{BG_TOP}"/>
      <stop offset="1" stop-color="{BG_BOTTOM}"/>
    </linearGradient>
    <linearGradient id="fade" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{BG_TOP}" stop-opacity="1"/>
      <stop offset="1" stop-color="{BG_TOP}" stop-opacity="0"/>
    </linearGradient>
  </defs>

  <rect width="{W}" height="{H}" fill="url(#bg)"/>

  <!-- panel -->
  <g>
    {chr(10).join('    ' + g for g in gridlines)}
    <!-- reference signal -->
    <polyline points="{to_points(reference, lo, hi)}" fill="none"
              stroke="{REFERENCE}" stroke-width="2" stroke-opacity="0.55"
              stroke-dasharray="5 4"/>
    <!-- corrupted input -->
    <polyline points="{to_points(corrupted, lo, hi)}" fill="none"
              stroke="{CORRUPT}" stroke-width="2.2" stroke-opacity="0.9"/>
    {chr(10).join('    ' + m for m in marks)}
    <!-- policy output -->
    <polyline points="{to_points(cleaned, lo, hi)}" fill="none"
              stroke="{CLEAN}" stroke-width="3" stroke-linejoin="round"/>
  </g>

  <!-- legend -->
  <g font-family="'Segoe UI', Helvetica, Arial, sans-serif" font-size="13">
    <line x1="{PX0}" y1="272" x2="{PX0 + 22}" y2="272" stroke="{CORRUPT}" stroke-width="2.2"/>
    <text x="{PX0 + 30}" y="276" fill="{MUTED}">corrupted input</text>
    <line x1="{PX0 + 158}" y1="272" x2="{PX0 + 180}" y2="272" stroke="{REFERENCE}" stroke-width="2" stroke-dasharray="5 4" stroke-opacity="0.7"/>
    <text x="{PX0 + 188}" y="276" fill="{MUTED}">reference</text>
    <line x1="{PX0 + 278}" y1="272" x2="{PX0 + 300}" y2="272" stroke="{CLEAN}" stroke-width="3"/>
    <text x="{PX0 + 308}" y="276" fill="{MUTED}">RL-Cleanse output</text>
  </g>

  <!-- left fade, so the trace never crowds the wordmark -->
  <rect x="{PX0 - 64}" y="0" width="92" height="252" fill="url(#fade)"/>

  <!-- title -->
  <g font-family="'Segoe UI', Helvetica, Arial, sans-serif">
    <text x="60" y="132" fill="{TITLE}" font-size="52" font-weight="700">RL-Cleanse</text>
    <text x="62" y="172" fill="{SUB}" font-size="20" font-weight="500">Learned sequential correction of noisy IoT sensor streams</text>
    <text x="62" y="202" fill="{MUTED}" font-size="14.5">Double DQN &#183; strictly causal, O(1) memory &#183; 11,206 parameters &#183; UCI Air Quality</text>
    <text x="62" y="226" fill="{MUTED}" font-size="14.5" fill-opacity="0.8">Real test window, drawn from the published checkpoint</text>
  </g>
</svg>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--corruption", default=DEFAULT_CORRUPTION)
    parser.add_argument("--output", default="assets/banner.svg")
    args = parser.parse_args()

    reference, corrupted, cleaned = roll(args.model, args.seed, args.corruption)

    raw_err = float(np.mean([abs(r - c) for r, c in zip(reference, corrupted)]))
    rl_err = float(np.mean([
        abs(r - c) for r, c in zip(reference, cleaned) if np.isfinite(c)
    ]))
    print(f"window seed {args.seed} ({args.corruption}, {WINDOW} h)")
    print(f"  raw MAE {raw_err:.4f} -> RL MAE {rl_err:.4f}")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write(build_svg(reference, corrupted, cleaned))
    print(f"Written {args.output}")


if __name__ == "__main__":
    main()
