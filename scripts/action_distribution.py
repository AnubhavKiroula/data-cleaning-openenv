"""
What the learned policy actually does, counted over the held-out windows.

The benchmark table says the policy helps on two fault families and hurts on
two others. It does not say *how*, and the mechanism is not guessable from the
action space's design: an earlier revision of the briefing asserted that the
policy "leans on fix_type", the halfway-to-baseline correction, and the
measurement does not support it -- on the spike family the clamp action leads.

So this counts. For each fault family it runs every seed checkpoint greedily
over the same 30 held-out windows the benchmark uses and tallies which of the
six actions was selected at each of the 3,600 resulting decision steps.

The headline the counts produce is that the policy abstains on 85-97% of
samples, and that its intervention rate varies by family with how much there is
to win. That is the behaviour the causal constraint of section III rewards: the
policy is not solving the spike-versus-step-change classification, it is
declining to make it.

Run::

    python scripts/action_distribution.py

Writes ``reports/action_distribution.json``.
"""

import argparse
import collections
import glob
import json
import os
import sys
from typing import Any, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.ml.dqn_model import DQNAgent  # noqa: E402
from backend.ml.evaluate_benchmarks import SEED_GLOB  # noqa: E402
from envs.data_cleaning_env.server.environment import DataCleaningEnvironment  # noqa: E402
from envs.data_cleaning_env.tasks.graders import CORRUPTION_TYPES  # noqa: E402


def action_distribution(
    num_windows: int = 30,
    window_size: int = 24,
    seed_base: int = 2026,
    split: str = "test",
    device: str = "cpu",
) -> Dict[str, Any]:
    """Percentage of decision steps spent on each action, by fault family."""
    seed_models = sorted(glob.glob(SEED_GLOB))
    if not seed_models:
        raise FileNotFoundError(
            f"No per-seed checkpoints matching {SEED_GLOB}. Train first with "
            "`python -m backend.ml.train_dqn --epochs 800 --seeds 1 2 3 4 5`."
        )

    agents = []
    for path in seed_models:
        agent = DQNAgent(device=device)
        agent.load_model(path)
        agents.append(agent)

    env = DataCleaningEnvironment(history_len=5)
    out: Dict[str, Any] = {}

    for ctype in CORRUPTION_TYPES:
        counts: collections.Counter = collections.Counter()
        for agent in agents:
            with agent.eval_mode():
                for i in range(num_windows):
                    obs = env.reset(
                        task_name="iot_stream",
                        window_size=window_size,
                        split=split,
                        corruption_type=ctype,
                        seed=seed_base + i * 43,
                    )
                    agent.reset(obs)
                    while not obs["done"]:
                        action = agent.get_action(obs, obs["legal_actions"])
                        counts[action["action_type"]] += 1
                        obs = env.step(
                            action_type=action["action_type"],
                            column=action["column"],
                            value=action["value"],
                        )

        total = sum(counts.values())
        pct = {k: round(100.0 * v / total, 1) for k, v in counts.most_common()}
        out[ctype] = {
            "steps": total,
            "pct_by_action": pct,
            # The single number worth quoting: how often it does anything at all.
            "intervention_rate_pct": round(100.0 - pct.get("skip", 0.0), 1),
        }

    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-windows", type=int, default=30)
    parser.add_argument("--window-size", type=int, default=24)
    parser.add_argument("--seed-base", type=int, default=2026)
    parser.add_argument("--split", type=str, default="test")
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument("--output", type=str, default="reports/action_distribution.json")
    args = parser.parse_args()

    result = action_distribution(
        num_windows=args.num_windows,
        window_size=args.window_size,
        seed_base=args.seed_base,
        split=args.split,
        device=args.device,
    )

    actions = ["skip", "fix_type", "fix_category", "fill_missing",
               "remove_duplicate", "remove_outlier"]
    print(f"{'Family':<12}" + "".join(f"{a:>17}" for a in actions) + f"{'acts':>8}")
    for ctype, d in result.items():
        row = "".join(f"{d['pct_by_action'].get(a, 0.0):>17.1f}" for a in actions)
        print(f"{ctype:<12}{row}{d['intervention_rate_pct']:>8.1f}")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as fh:
        json.dump(result, fh, indent=2)
    print(f"\nWritten to {args.output}")


if __name__ == "__main__":
    main()
