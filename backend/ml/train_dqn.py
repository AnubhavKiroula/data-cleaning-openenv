"""
DQN training pipeline for streaming IoT sensor-stream denoising.

Run with::

    python -m backend.ml.train_dqn --epochs 300

Hyperparameter defaults follow ``docs/RESEARCH_PIVOT_MASTER_PLAN.md`` section
6.1 (batch 64, lr 3e-4, gamma 0.99, epsilon 1.0 -> 0.02 at decay 0.95, target
network refreshed every 5 epochs, replay capacity 10,000). CUDA is used when
available and the pipeline falls back to CPU unchanged, so tests and CI need no
GPU.

Three correctness properties this pipeline is built to hold, each of which the
previous revision violated:

**Checkpoints are selected on validation data, never on test.** The old loop
called its evaluator with ``split="test"`` and kept the best-scoring weights,
which is model selection on the held-out set. The validation split is carved
from the end of the *training* region by the loader.

**Exploration survives evaluation.** Mid-training evaluation runs inside
``agent.eval_mode()``, which restores epsilon afterwards. Previously the
evaluator set epsilon to zero permanently at epoch 10 of 40.

**Training covers the whole training split and every fault family.** Window
position is drawn from an epoch-seeded RNG over the entire split, and the fault
family is cycled. The old loop passed ``seed=epoch * 17`` into
``start_idx = seed % max_start``, confining 40 epochs to the first 680 of 7,485
hours, and never passed a corruption type, so it only ever saw ``mixed``.
"""

import argparse
import copy
import json
import logging
import os
import random
import time
from typing import Any, Dict, List, Optional

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from backend.ml.dqn_model import ACTION_TO_INDEX, DQNAgent
from backend.ml.experience_replay import ReplayBuffer
from backend.ml.metrics import evaluate_window
from envs.data_cleaning_env.server.environment import DataCleaningEnvironment
from envs.data_cleaning_env.tasks.graders import CORRUPTION_TYPES

DEFAULT_CONFIG: Dict[str, Any] = {
    "epochs": 300,
    "window_size": 24,
    "batch_size": 64,
    "learning_rate": 3e-4,
    "gamma": 0.99,
    "epsilon": 1.0,
    "epsilon_min": 0.02,
    # The master plan specifies decay=0.95 per epoch. Applied literally that
    # reaches the 0.02 floor at epoch 76, so a 500-epoch run would spend 85% of
    # training with effectively no exploration. `epsilon_decay=None` instead
    # derives the rate so the schedule spans `epsilon_span` of the run, keeping
    # the plan's 1.0 -> 0.02 endpoints. Pass a float to force a fixed rate.
    "epsilon_decay": None,
    "epsilon_span": 0.7,
    "double_dqn": True,
    "updates_per_step": 1,
    "target_update_frequency": 5,
    "buffer_capacity": 10000,
    "history_len": 5,
    # Fixed penalty for any non-skip action. 0.0 is the published reward.
    "action_cost": 0.0,
    "grad_clip": 10.0,
    "seed": 42,
    "val_windows": 12,
    "eval_every": 10,
}


def set_global_seeds(seed: int) -> None:
    """Seed every RNG the pipeline touches, for reproducible runs."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class DQNTrainer:
    """Trains a :class:`DQNAgent` on the ``iot_stream`` environment."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.logger = self._setup_logging()

        requested = self.config.get("device", "auto")
        if requested == "auto":
            requested = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(requested)

        set_global_seeds(self.config["seed"])

        self.config["epsilon_decay"] = self._resolve_epsilon_decay()

        self.agent = DQNAgent(
            device=str(self.device),
            epsilon=self.config["epsilon"],
            epsilon_min=self.config["epsilon_min"],
            epsilon_decay=self.config["epsilon_decay"],
            gamma=self.config["gamma"],
            seed=self.config["seed"],
        )
        self.replay_buffer = ReplayBuffer(
            capacity=self.config["buffer_capacity"], seed=self.config["seed"]
        )
        self.optimizer = optim.Adam(
            self.agent.q_network.parameters(), lr=self.config["learning_rate"]
        )
        self.loss_fn = nn.SmoothL1Loss()
        self.batch_size = self.config["batch_size"]
        self.gamma = self.config["gamma"]

        self.env = DataCleaningEnvironment(
            history_len=self.config["history_len"],
            action_cost=self.config["action_cost"],
        )

        self.metrics: Dict[str, List[Any]] = {
            "episode_rewards": [],
            "episode_lengths": [],
            "losses": [],
            "epsilon_values": [],
            "corruption_types": [],
            "val_history": [],
        }

        self.logger.info(
            "DQNTrainer ready on %s | state_dim=%d action_dim=%d params=%d",
            self.device,
            self.agent.state_dim,
            self.agent.action_dim,
            self.agent.get_model_info()["total_parameters"],
        )

    def _resolve_epsilon_decay(self) -> float:
        """
        Return the per-epoch epsilon decay rate.

        When configured as ``None``, solve for the rate that carries epsilon
        from its initial value to ``epsilon_min`` over ``epsilon_span`` of the
        planned epochs, so the exploration schedule scales with run length
        instead of collapsing in the first 15% of it.
        """
        configured = self.config.get("epsilon_decay")
        if configured is not None:
            return float(configured)

        epochs = max(int(self.config["epochs"]), 1)
        span = max(1, int(epochs * float(self.config.get("epsilon_span", 0.7))))
        eps0 = float(self.config["epsilon"])
        eps_min = float(self.config["epsilon_min"])
        if eps0 <= eps_min:
            return 1.0
        return float((eps_min / eps0) ** (1.0 / span))

    def _setup_logging(self) -> logging.Logger:
        logger = logging.getLogger("DQNTrainer")
        if not logger.handlers:
            os.makedirs("logs", exist_ok=True)
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(message)s")
            )
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger

    # -------------------------------------------------------------- learning

    def train_step(self) -> Optional[float]:
        """One gradient step on a replay batch. Returns the loss, if it ran."""
        if self.replay_buffer.size() < self.batch_size:
            return None

        batch = self.replay_buffer.sample(self.batch_size)
        states = torch.as_tensor(
            np.asarray([t.state for t in batch]), dtype=torch.float32, device=self.device
        )
        actions = torch.as_tensor(
            [t.action for t in batch], dtype=torch.int64, device=self.device
        ).unsqueeze(1)
        rewards = torch.as_tensor(
            [t.reward for t in batch], dtype=torch.float32, device=self.device
        )
        next_states = torch.as_tensor(
            np.asarray([t.next_state for t in batch]),
            dtype=torch.float32,
            device=self.device,
        )
        dones = torch.as_tensor(
            [float(t.done) for t in batch], dtype=torch.float32, device=self.device
        )

        q_taken = self.agent.q_network(states).gather(1, actions).squeeze(1)
        with torch.no_grad():
            if self.config.get("double_dqn", True):
                # Double DQN: the online network chooses the bootstrap action
                # and the target network values it. Plain DQN takes the max over
                # the target network, so the same noise that inflates an
                # action's value also selects it, and the bias compounds. Here
                # that showed up behaviourally: the agent over-corrected clean
                # streams, degrading dropout and duplicate windows whose raw
                # error was already near zero.
                next_actions = (
                    self.agent.q_network(next_states).argmax(dim=1, keepdim=True)
                )
                next_q = (
                    self.agent.target_network(next_states)
                    .gather(1, next_actions)
                    .squeeze(1)
                )
            else:
                next_q = self.agent.target_network(next_states).max(dim=1).values
            target = rewards + self.gamma * next_q * (1.0 - dones)

        loss = self.loss_fn(q_taken, target)
        self.optimizer.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(
            self.agent.q_network.parameters(), self.config["grad_clip"]
        )
        self.optimizer.step()
        return float(loss.item())

    def run_episode(self, corruption_type: str, split: str, seed: int) -> Dict[str, Any]:
        """Roll out one training episode and push its transitions to replay."""
        obs = self.env.reset(
            task_name="iot_stream",
            window_size=self.config["window_size"],
            split=split,
            corruption_type=corruption_type,
            seed=seed,
        )
        self.agent.reset(obs)

        episode_reward = 0.0
        steps = 0
        losses = []

        while not obs["done"]:
            state = self.agent.encode_observation(obs)
            action = self.agent.get_action(obs, obs["legal_actions"])
            next_obs = self.env.step(
                action_type=action["action_type"],
                column=action["column"],
                value=action["value"],
            )
            next_state = self.agent.encode_observation(next_obs)

            self.replay_buffer.add(
                state,
                ACTION_TO_INDEX[action["action_type"]],
                next_obs["reward"],
                next_state,
                next_obs["done"],
            )
            self.agent.update_reward(next_obs["reward"])

            episode_reward += next_obs["reward"]
            steps += 1
            obs = next_obs

            for _ in range(int(self.config.get("updates_per_step", 1))):
                loss = self.train_step()
                if loss is not None:
                    losses.append(loss)

        return {
            "reward": episode_reward,
            "steps": steps,
            "mean_loss": float(np.mean(losses)) if losses else None,
        }

    # ------------------------------------------------------------ evaluation

    def evaluate(
        self,
        split: str = "val",
        num_windows: int = 12,
        seed_base: int = 7000,
        corruption_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate the greedy policy on a split, per fault family.

        Runs inside :meth:`DQNAgent.eval_mode` so that exploration state is
        restored on exit.
        """
        corruption_types = corruption_types or list(CORRUPTION_TYPES)
        env = DataCleaningEnvironment(
            history_len=self.config["history_len"],
            action_cost=self.config["action_cost"],
        )
        by_type: Dict[str, Dict[str, float]] = {}

        with self.agent.eval_mode():
            for ctype in corruption_types:
                maes, raw_maes, scores, reductions = [], [], [], []
                for i in range(num_windows):
                    seed = seed_base + i * 31
                    obs = env.reset(
                        task_name="iot_stream",
                        window_size=self.config["window_size"],
                        split=split,
                        corruption_type=ctype,
                        seed=seed,
                    )
                    self.agent.reset(obs)
                    while not obs["done"]:
                        action = self.agent.get_action(obs, obs["legal_actions"])
                        obs = env.step(
                            action_type=action["action_type"],
                            column=action["column"],
                            value=action["value"],
                        )
                    m = evaluate_window(
                        env.cleaned_data, [r.get("value") for r in env.cleaned_data]
                    )
                    maes.append(m["mae"])
                    raw_maes.append(m["raw_mae"])
                    scores.append(m["score"])
                    reductions.append(m["error_reduction_pct"])

                by_type[ctype] = {
                    "mae": float(np.mean(maes)),
                    "raw_mae": float(np.mean(raw_maes)),
                    "score": float(np.mean(scores)),
                    "error_reduction_pct": float(np.mean(reductions)),
                }

        # Selection criterion: the mean, over fault families, of each family's
        # MAE relative to its own do-nothing MAE. 1.0 means "no better than
        # doing nothing"; below 1.0 means a genuine improvement.
        #
        # Plain mean MAE is the wrong objective here because the families have
        # error scales two orders of magnitude apart (mixed ~0.53, duplicate
        # ~0.03). Averaging raw MAE lets `mixed` dominate selection entirely,
        # which favours aggressive policies and hides the fact that the same
        # policy is damaging the benign families.
        rel = [
            v["mae"] / v["raw_mae"] if v["raw_mae"] > 1e-9 else (1.0 + v["mae"])
            for v in by_type.values()
        ]

        return {
            "by_corruption": by_type,
            "mean_mae": float(np.mean([v["mae"] for v in by_type.values()])),
            "mean_raw_mae": float(np.mean([v["raw_mae"] for v in by_type.values()])),
            "mean_score": float(np.mean([v["score"] for v in by_type.values()])),
            "mean_relative_mae": float(np.mean(rel)),
        }

    # -------------------------------------------------------------- training

    def train(self, epochs: Optional[int] = None, save: bool = True) -> Dict[str, Any]:
        """Train for ``epochs`` episodes, selecting the best model on validation."""
        epochs = epochs or self.config["epochs"]
        os.makedirs("models", exist_ok=True)
        suffix = self.config.get("checkpoint_suffix", "")
        best_path = os.path.join("models", f"dqn_iot_stream_best{suffix}.pt")
        final_path = os.path.join("models", f"dqn_iot_stream_final{suffix}.pt")

        # Draw window seeds from a dedicated RNG so that window position is
        # independent of the epoch index.
        window_rng = np.random.RandomState(self.config["seed"] + 1)

        best_val_rel = float("inf")
        best_val_mae = float("inf")
        best_epoch = -1
        best_state = None
        start = time.time()
        self.agent.set_training_mode(True)

        self.logger.info("Training %d epochs on %s", epochs, self.device)

        for epoch in range(1, epochs + 1):
            # Cycle fault families so every epoch trains on a different one.
            ctype = CORRUPTION_TYPES[(epoch - 1) % len(CORRUPTION_TYPES)]
            seed = int(window_rng.randint(0, 2**31 - 1))

            res = self.run_episode(ctype, split="train", seed=seed)

            self.metrics["episode_rewards"].append(res["reward"])
            self.metrics["episode_lengths"].append(res["steps"])
            self.metrics["corruption_types"].append(ctype)
            if res["mean_loss"] is not None:
                self.metrics["losses"].append(res["mean_loss"])

            if epoch % self.config["target_update_frequency"] == 0:
                self.agent.update_target_network()

            self.agent.decay_epsilon()
            self.metrics["epsilon_values"].append(self.agent.epsilon)

            if epoch % self.config["eval_every"] == 0 or epoch == epochs:
                val = self.evaluate(
                    split="val", num_windows=self.config["val_windows"]
                )
                self.metrics["val_history"].append(
                    {
                        "epoch": epoch,
                        "mean_mae": val["mean_mae"],
                        "mean_raw_mae": val["mean_raw_mae"],
                        "mean_score": val["mean_score"],
                        "mean_relative_mae": val["mean_relative_mae"],
                    }
                )
                recent = float(np.mean(self.metrics["episode_rewards"][-10:]))
                self.logger.info(
                    "epoch %3d/%d | reward(10) %+.2f | val rel-MAE %.4f "
                    "| val MAE %.4f (raw %.4f) | eps %.3f",
                    epoch,
                    epochs,
                    recent,
                    val["mean_relative_mae"],
                    val["mean_mae"],
                    val["mean_raw_mae"],
                    self.agent.epsilon,
                )
                if val["mean_relative_mae"] < best_val_rel:
                    best_val_rel = val["mean_relative_mae"]
                    best_val_mae = val["mean_mae"]
                    best_epoch = epoch
                    # Held in memory, not written yet. Writing here -- outside
                    # the `save` guard -- meant every test that called
                    # train(save=False) with the default empty checkpoint
                    # suffix silently overwrote models/dqn_iot_stream_best.pt
                    # with a 12-epoch CPU model. That is exactly how the
                    # published headline checkpoint came to be a test artifact
                    # scoring worse than doing nothing.
                    best_state = {
                        "q": copy.deepcopy(self.agent.q_network.state_dict()),
                        "target": copy.deepcopy(
                            self.agent.target_network.state_dict()
                        ),
                        "epsilon": self.agent.epsilon,
                    }
                    self.logger.info(
                        "  new best on validation (rel-MAE %.4f) at epoch %d",
                        best_val_rel,
                        epoch,
                    )

        training_time = time.time() - start

        if save:
            if best_state is not None:
                # Persist the validation-selected weights, then restore them
                # into the live agent so the returned trainer holds the model
                # the checkpoint describes.
                current = {
                    "q": copy.deepcopy(self.agent.q_network.state_dict()),
                    "target": copy.deepcopy(self.agent.target_network.state_dict()),
                    "epsilon": self.agent.epsilon,
                }
                self.agent.q_network.load_state_dict(best_state["q"])
                self.agent.target_network.load_state_dict(best_state["target"])
                self.agent.epsilon = best_state["epsilon"]
                self.agent.save_model(best_path)
                self.logger.info(
                    "best checkpoint (epoch %d, val rel-MAE %.4f) -> %s",
                    best_epoch,
                    best_val_rel,
                    best_path,
                )
                # Restore the final-epoch weights for final_path below.
                self.agent.q_network.load_state_dict(current["q"])
                self.agent.target_network.load_state_dict(current["target"])
                self.agent.epsilon = current["epsilon"]
            self.agent.save_model(final_path)
            summary = {
                "config": {k: v for k, v in self.config.items()},
                "device": str(self.device),
                "epochs": epochs,
                "training_time_sec": training_time,
                "best_val_relative_mae": best_val_rel,
                "best_val_mae": best_val_mae,
                "best_epoch": best_epoch,
                "state_dim": self.agent.state_dim,
                "action_dim": self.agent.action_dim,
                "episode_rewards": self.metrics["episode_rewards"],
                "epsilon_values": self.metrics["epsilon_values"],
                "losses": self.metrics["losses"],
                "corruption_types": self.metrics["corruption_types"],
                "val_history": self.metrics["val_history"],
            }
            metrics_path = os.path.join(
                "models", f"dqn_iot_stream_metrics{suffix}.json"
            )
            with open(metrics_path, "w") as fh:
                json.dump(summary, fh, indent=2)

        self.plot_training_curves(
            save_path=f"plots/dqn_iot_training_curves{suffix or ''}.png"
        )

        return {
            "training_time": training_time,
            "best_val_relative_mae": best_val_rel,
            "best_val_mae": best_val_mae,
            "best_epoch": best_epoch,
            # None when save=False: nothing was written, so there is no path to
            # hand back and no caller can be misled into loading a stale file.
            "best_model_path": best_path if (save and best_state) else None,
            "final_model_path": final_path if save else None,
            "best_state": best_state,
            "metrics": self.metrics,
        }

    # ----------------------------------------------------------------- plots

    def plot_training_curves(
        self, save_path: str = "plots/dqn_iot_training_curves.png"
    ) -> str:
        """Plot episode return, exploration schedule, TD loss and validation MAE."""
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        rewards = self.metrics["episode_rewards"]
        fig, axes = plt.subplots(2, 2, figsize=(13, 8))

        axes[0][0].plot(rewards, alpha=0.3, color="#1f77b4", label="episode")
        if len(rewards) >= 10:
            kernel = np.ones(10) / 10.0
            smooth = np.convolve(rewards, kernel, mode="valid")
            axes[0][0].plot(
                range(9, len(rewards)), smooth, color="#1f77b4", lw=2, label="10-ep mean"
            )
        axes[0][0].set_title("Episode return", fontweight="bold")
        axes[0][0].set_xlabel("epoch")
        axes[0][0].legend()
        axes[0][0].grid(alpha=0.3)

        axes[0][1].plot(self.metrics["epsilon_values"], color="#d62728")
        axes[0][1].set_title("Exploration schedule (epsilon)", fontweight="bold")
        axes[0][1].set_xlabel("epoch")
        axes[0][1].grid(alpha=0.3)

        if self.metrics["losses"]:
            axes[1][0].plot(self.metrics["losses"], color="#7f7f7f", alpha=0.8)
            axes[1][0].set_yscale("log")
        axes[1][0].set_title("TD loss (Huber)", fontweight="bold")
        axes[1][0].set_xlabel("epoch")
        axes[1][0].grid(alpha=0.3)

        vh = self.metrics["val_history"]
        if vh:
            ep = [v["epoch"] for v in vh]
            axes[1][1].plot(ep, [v["mean_mae"] for v in vh], "o-", label="RL agent")
            axes[1][1].plot(
                ep,
                [v["mean_raw_mae"] for v in vh],
                "--",
                color="#888",
                label="do-nothing",
            )
            axes[1][1].legend()
        axes[1][1].set_title("Validation MAE", fontweight="bold")
        axes[1][1].set_xlabel("epoch")
        axes[1][1].grid(alpha=0.3)

        plt.tight_layout()
        plt.savefig(save_path, dpi=150)
        plt.close()
        return save_path


def train_seeds(
    seeds: List[int],
    epochs: int,
    device: str = "auto",
    val_windows: int = 30,
    eval_every: int = 25,
    action_cost: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Train one agent per seed, each selected on validation.

    Reported results are aggregated across seeds. A single DQN run on this task
    has a validation relative-MAE spread of roughly 0.93 to 1.08, so a
    single-seed number would say more about the seed than about the method.
    """
    runs = []
    for seed in seeds:
        trainer = DQNTrainer(
            {
                "epochs": epochs,
                "device": device,
                "seed": seed,
                "val_windows": val_windows,
                "eval_every": eval_every,
                "checkpoint_suffix": f"_seed{seed}",
                **({"action_cost": action_cost} if action_cost is not None else {}),
            }
        )
        result = trainer.train(epochs=epochs, save=True)
        trainer.agent.load_model(result["best_model_path"])
        test = trainer.evaluate(split="test", num_windows=30, seed_base=2026)
        runs.append(
            {
                "seed": seed,
                "best_epoch": result["best_epoch"],
                "val_relative_mae": result["best_val_relative_mae"],
                "checkpoint": result["best_model_path"],
                "test": test,
            }
        )
        trainer.logger.info(
            "seed %d done: val rel-MAE %.4f, test rel-MAE %.4f",
            seed,
            result["best_val_relative_mae"],
            test["mean_relative_mae"],
        )

    # The headline checkpoint is the one with the best VALIDATION score.
    best = min(runs, key=lambda r: r["val_relative_mae"])
    import shutil

    shutil.copyfile(best["checkpoint"], "models/dqn_iot_stream_best.pt")
    shutil.copyfile(
        best["checkpoint"].replace("_best_", "_final_")
        if "_best_" in best["checkpoint"]
        else best["checkpoint"],
        "models/dqn_iot_stream_final.pt",
    )
    shutil.copyfile(
        f"models/dqn_iot_stream_metrics_seed{best['seed']}.json",
        "models/dqn_iot_stream_metrics.json",
    )
    shutil.copyfile(
        f"plots/dqn_iot_training_curves_seed{best['seed']}.png",
        "plots/dqn_iot_training_curves.png",
    )

    summary = {
        "seeds": seeds,
        "epochs": epochs,
        "selected_seed": best["seed"],
        "runs": runs,
        "val_relative_mae": {
            "mean": float(np.mean([r["val_relative_mae"] for r in runs])),
            "std": float(np.std([r["val_relative_mae"] for r in runs])),
            "min": float(np.min([r["val_relative_mae"] for r in runs])),
            "max": float(np.max([r["val_relative_mae"] for r in runs])),
        },
    }
    with open("models/dqn_iot_stream_seed_summary.json", "w") as fh:
        json.dump(summary, fh, indent=2)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=DEFAULT_CONFIG["epochs"])
    parser.add_argument("--batch-size", type=int, default=DEFAULT_CONFIG["batch_size"])
    parser.add_argument(
        "--learning-rate", type=float, default=DEFAULT_CONFIG["learning_rate"]
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_CONFIG["seed"])
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=None,
        help="Train one agent per seed and aggregate (recommended).",
    )
    parser.add_argument("--device", type=str, default="auto", help="cpu | cuda | auto")
    parser.add_argument("--no-save", action="store_true")
    args = parser.parse_args()

    if args.seeds:
        summary = train_seeds(args.seeds, epochs=args.epochs, device=args.device)
        print("\n" + "=" * 72)
        print(f"MULTI-SEED TRAINING COMPLETE ({len(args.seeds)} seeds)")
        print("=" * 72)
        v = summary["val_relative_mae"]
        print(
            f"Validation relative-MAE: {v['mean']:.4f} +/- {v['std']:.4f} "
            f"(range {v['min']:.4f} - {v['max']:.4f})"
        )
        print(f"Selected seed (best on validation): {summary['selected_seed']}")
        print("\nPer-seed held-out TEST relative-MAE:")
        for r in summary["runs"]:
            print(
                f"  seed {r['seed']:<5} val {r['val_relative_mae']:.4f} "
                f"-> test {r['test']['mean_relative_mae']:.4f} "
                f"(best epoch {r['best_epoch']})"
            )
        print("=" * 72)
        return

    trainer = DQNTrainer(
        {
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "seed": args.seed,
            "device": args.device,
        }
    )
    result = trainer.train(epochs=args.epochs, save=not args.no_save)

    print("\n" + "=" * 72)
    print("IOT STREAM DQN TRAINING COMPLETE")
    print("=" * 72)
    print(f"Device            : {trainer.device}")
    print(f"Epochs            : {args.epochs}")
    print(f"Training time     : {result['training_time']:.1f}s")
    print(f"Best val rel-MAE  : {result['best_val_relative_mae']:.4f} (epoch {result['best_epoch']})")
    print(f"  its val MAE     : {result['best_val_mae']:.4f}")

    print("\nHeld-out TEST evaluation of the best checkpoint:")
    trainer.agent.load_model(result["best_model_path"])
    test = trainer.evaluate(split="test", num_windows=30, seed_base=2026)
    for ctype, d in test["by_corruption"].items():
        print(
            f"  {ctype:<10} raw MAE {d['raw_mae']:.4f} -> RL MAE {d['mae']:.4f} "
            f"({d['error_reduction_pct']:+.1f}%, score {d['score']:.3f})"
        )
    print(f"  {'MEAN':<10} raw MAE {test['mean_raw_mae']:.4f} -> RL MAE {test['mean_mae']:.4f}")
    print("=" * 72)


if __name__ == "__main__":
    main()
