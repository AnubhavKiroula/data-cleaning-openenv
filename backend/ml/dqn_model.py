"""
Deep Q-Network for streaming IoT sensor-stream denoising.

The agent chooses one of the six actions in
:data:`envs.data_cleaning_env.server.environment.ACTION_SPACE` from an
observation containing the current reading, a rolling buffer of the last ``N``
values it emitted, and heuristic fault flags. Action *semantics* live in the
environment, so this module is only a policy: it picks an index and never
computes a replacement value.

Design notes
------------
**Canonical action mapping.** Index ↔ action is a fixed module-level table.
An earlier revision rebuilt the mapping from whatever order ``legal_actions``
arrived in on each call, which made replay-buffer action indices and saved
checkpoints depend on list ordering.

**Epsilon is a property of the training loop, not of eval mode.**
``set_training_mode(False)`` used to assign ``self.epsilon = 0.0`` and nothing
restored it, so the first mid-training evaluation permanently ended
exploration — visible in the old metrics file as epsilon dropping from 0.95 to
the floor at epoch 11 of 40. Exploration is now suspended with
:meth:`eval_mode`, a context manager that restores the previous value.

**Scale-invariant features.** Observations are encoded relative to the rolling
window (deviations divided by rolling sigma) plus two log-compressed absolute
magnitude cues. A policy trained on one sensor channel therefore transfers to
channels with a different dynamic range, which matters for the edge-deployment
claim, and gradients stay well conditioned without a dataset-wide normaliser
that a streaming device could not compute.
"""

import contextlib
import logging
from collections import namedtuple
from typing import Any, Dict, List, Optional

import numpy as np
import torch
import torch.nn as nn

from .base_agent import Agent

Transition = namedtuple("Transition", ["state", "action", "reward", "next_state", "done"])

#: Canonical index -> action name. Must match the environment's ACTION_SPACE.
ACTION_INDEX = [
    "skip",
    "remove_outlier",
    "fill_missing",
    "fix_type",
    "remove_duplicate",
    "fix_category",
]
ACTION_TO_INDEX = {name: i for i, name in enumerate(ACTION_INDEX)}
ACTION_DIM = len(ACTION_INDEX)

#: Fault flags the encoder reads, in fixed order.
ISSUE_FLAGS = [
    "missing:sensor",
    "outlier:spike",
    "drift:offset",
    "duplicate:transmission",
]

HISTORY_LEN = 5
EPS = 1e-4
Z_CLIP = 10.0

#: Feature layout (see :meth:`DQNAgent.encode_observation`):
#:   10 instantaneous/relative + 5 history deviations + 4 fault flags = 19
STATE_DIM = 10 + HISTORY_LEN + len(ISSUE_FLAGS)


class QNetwork(nn.Module):
    """MLP approximating Q(s, a) for the six-action space."""

    def __init__(
        self,
        state_dim: int = STATE_DIM,
        action_dim: int = ACTION_DIM,
        hidden_dims: Optional[List[int]] = None,
    ):
        super().__init__()
        hidden_dims = hidden_dims or [128, 64]

        layers: List[nn.Module] = []
        in_dim = state_dim
        for h in hidden_dims:
            layers += [nn.Linear(in_dim, h), nn.ReLU()]
            in_dim = h
        layers.append(nn.Linear(in_dim, action_dim))

        self.network = nn.Sequential(*layers)
        self.state_dim = state_dim
        self.action_dim = action_dim
        self._initialize_weights()

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                nn.init.constant_(m.bias, 0)

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        return self.network(state)

    def get_q_values(self, state: torch.Tensor) -> np.ndarray:
        with torch.no_grad():
            return self.forward(state).cpu().numpy().flatten()


class DQNAgent(Agent):
    """Epsilon-greedy DQN policy over the six denoising actions."""

    def __init__(
        self,
        state_dim: int = STATE_DIM,
        action_dim: int = ACTION_DIM,
        device: str = "cpu",
        epsilon: float = 1.0,
        epsilon_min: float = 0.02,
        epsilon_decay: float = 0.95,
        gamma: float = 0.99,
        hidden_dims: Optional[List[int]] = None,
        seed: Optional[int] = None,
    ):
        super().__init__("DQNAgent")
        self.logger = logging.getLogger("DQNAgent")

        self.device = torch.device(device)
        self.state_dim = state_dim
        self.action_dim = action_dim

        if seed is not None:
            torch.manual_seed(seed)

        self.q_network = QNetwork(state_dim, action_dim, hidden_dims).to(self.device)
        self.target_network = QNetwork(state_dim, action_dim, hidden_dims).to(self.device)
        self.target_network.load_state_dict(self.q_network.state_dict())
        self.target_network.eval()

        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.gamma = gamma

        self.rng = np.random.RandomState(seed)
        self.action_mapping = dict(enumerate(ACTION_INDEX))
        self.reverse_action_mapping = dict(ACTION_TO_INDEX)

    # ------------------------------------------------------------- interface

    def reset(self, observation: Dict[str, Any]) -> None:
        """Reset per-episode state. The action mapping is fixed, so nothing else."""
        self._confidence = 0.0

    def get_action(
        self, observation: Dict[str, Any], legal_actions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Select an action epsilon-greedily over the legal subset.

        Returns ``{"action_type", "column", "value"}`` with ``value=None``: the
        environment owns each action's correction formula.
        """
        legal = list(legal_actions) if legal_actions else list(ACTION_INDEX)
        legal_idx = [ACTION_TO_INDEX[a] for a in legal if a in ACTION_TO_INDEX]
        if not legal_idx:
            legal_idx = [ACTION_TO_INDEX["skip"]]

        if self.rng.random_sample() < self.epsilon:
            action_idx = int(self.rng.choice(legal_idx))
            self._confidence = 0.0
        else:
            state = self.encode_observation(observation)
            state_t = torch.as_tensor(state, dtype=torch.float32, device=self.device)
            with torch.no_grad():
                q = self.q_network(state_t.unsqueeze(0)).cpu().numpy()[0]
            masked = np.full(self.action_dim, -np.inf, dtype=np.float64)
            masked[legal_idx] = q[legal_idx]
            action_idx = int(np.argmax(masked))
            self._confidence = float(self._softmax_confidence(q[legal_idx]))

        return {
            "action_type": ACTION_INDEX[action_idx],
            "column": "value",
            "value": None,
        }

    @staticmethod
    def _softmax_confidence(q_legal: np.ndarray) -> float:
        """Probability mass the greedy policy puts on its chosen action."""
        if q_legal.size == 0:
            return 0.0
        z = q_legal - np.max(q_legal)
        p = np.exp(z)
        return float(np.max(p) / np.sum(p))

    def get_confidence(self) -> float:
        return self._confidence

    def update_reward(self, reward: float) -> None:
        self._last_reward = reward

    # -------------------------------------------------------------- encoding

    def encode_observation(self, observation: Dict[str, Any]) -> np.ndarray:
        """
        Encode one streaming observation into a fixed-length feature vector.

        Layout (19 dims):
          0  reading present (1.0) or dropped (0.0)
          1  log1p(|y_t|) * sign(y_t)          absolute magnitude cue
          2  log1p(sigma_t)                    rolling amplitude cue
          3  (y_t - mu_t) / (sigma_t + eps)    deviation in sigmas, clipped
          4  (y_t - median_t) / (sigma_t + eps)
          5  (y_t - y_{t-1}) / (sigma_t + eps) rate of change
          6  (mu_t - median_t) / (sigma_t + eps)  local skew, hints at drift
          7  history fill level, in [0, 1]
          8  tau_t = (t mod 24) / 24           time-of-day phase
          9  episode progress, in [0, 1]
          10-14 (y_{t-k} - mu_t) / (sigma_t + eps) for k = 1..5, zero-padded
          15-18 heuristic fault flags: missing, spike, drift, duplicate

        Ablation (decided on the validation split, 800 epochs, seed 42): adding
        two un-normalised absolute-magnitude features — ``log1p|y - median|``
        and ``log1p|y - y_prev|`` — made the policy *worse*, 0.997 vs 0.932
        validation relative-MAE. The motivation had been that the reward's skip
        tolerance is an absolute threshold, so the network must recover
        deviation in signal units from the sigma-relative features; in practice
        the unbounded extra inputs cost more in conditioning than they returned
        in expressiveness. The purely scale-relative encoding is kept.
        """
        current = observation.get("current_data", {}) or {}
        stats = observation.get("rolling_stats", {}) or {}
        hist = [h for h in (observation.get("rolling_history") or []) if h is not None]

        raw = current.get("value")
        present = raw is not None and np.isfinite(float(raw))
        y = float(raw) if present else 0.0

        mu = float(stats.get("mean", 0.0))
        sigma = float(stats.get("std", 0.0))
        med = float(stats.get("median", 0.0))
        scale = sigma + EPS

        def clip(x: float) -> float:
            return float(np.clip(x, -Z_CLIP, Z_CLIP))

        prev = float(hist[-1]) if hist else mu
        timestep = float(current.get("timestep", 0))

        features = [
            1.0 if present else 0.0,
            float(np.sign(y) * np.log1p(abs(y))),
            float(np.log1p(max(sigma, 0.0))),
            clip((y - mu) / scale) if present else 0.0,
            clip((y - med) / scale) if present else 0.0,
            clip((y - prev) / scale) if present else 0.0,
            clip((mu - med) / scale),
            len(hist) / float(HISTORY_LEN),
            (timestep % 24.0) / 24.0,
            float(observation.get("progress", 0.0)),
        ]

        buf = hist[-HISTORY_LEN:]
        padded = [None] * (HISTORY_LEN - len(buf)) + list(buf)
        features += [
            0.0 if v is None else clip((float(v) - mu) / scale) for v in padded
        ]

        issues = set(observation.get("issues_detected") or [])
        features += [1.0 if flag in issues else 0.0 for flag in ISSUE_FLAGS]

        vec = np.asarray(features, dtype=np.float32)
        if vec.shape[0] != self.state_dim:
            # Only reachable if state_dim was overridden; pad/truncate so an
            # explicitly sized network still runs.
            out = np.zeros(self.state_dim, dtype=np.float32)
            n = min(self.state_dim, vec.shape[0])
            out[:n] = vec[:n]
            return out
        return vec

    # Backwards-compatible alias used by older call sites.
    _encode_observation = encode_observation

    # ------------------------------------------------------------- training

    def decay_epsilon(self) -> float:
        """Multiplicatively decay exploration toward ``epsilon_min``."""
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        return self.epsilon

    def update_target_network(self) -> None:
        self.target_network.load_state_dict(self.q_network.state_dict())

    def set_training_mode(self, training: bool = True) -> None:
        """Switch module train/eval mode. Does **not** touch epsilon."""
        self.q_network.train(training)
        self.target_network.train(False)

    @contextlib.contextmanager
    def eval_mode(self):
        """
        Temporarily act greedily, then restore the exploration schedule.

        Used for mid-training validation so that evaluating the policy cannot
        silently terminate exploration.
        """
        prev_epsilon = self.epsilon
        prev_training = self.q_network.training
        self.epsilon = 0.0
        self.q_network.train(False)
        try:
            yield self
        finally:
            self.epsilon = prev_epsilon
            self.q_network.train(prev_training)

    # ----------------------------------------------------------- checkpoints

    def save_model(self, filepath: str) -> None:
        torch.save(
            {
                "q_network_state_dict": self.q_network.state_dict(),
                "target_network_state_dict": self.target_network.state_dict(),
                "epsilon": self.epsilon,
                "state_dim": self.state_dim,
                "action_dim": self.action_dim,
                "action_index": ACTION_INDEX,
            },
            filepath,
        )
        self.logger.info("Model saved to %s", filepath)

    def load_model(self, filepath: str) -> None:
        ckpt = torch.load(filepath, map_location=self.device, weights_only=False)

        if ckpt.get("state_dim") != self.state_dim or ckpt.get("action_dim") != self.action_dim:
            raise ValueError(
                f"Checkpoint shape mismatch: file has state_dim="
                f"{ckpt.get('state_dim')}, action_dim={ckpt.get('action_dim')}; "
                f"agent expects {self.state_dim}/{self.action_dim}. "
                "Checkpoints from before the streaming-encoder rewrite are not "
                "loadable; retrain with backend/ml/train_dqn.py."
            )

        saved_actions = ckpt.get("action_index")
        if saved_actions is not None and list(saved_actions) != ACTION_INDEX:
            raise ValueError(
                f"Checkpoint action ordering {list(saved_actions)} does not match "
                f"the current ACTION_INDEX {ACTION_INDEX}."
            )

        self.q_network.load_state_dict(ckpt["q_network_state_dict"])
        self.target_network.load_state_dict(ckpt["target_network_state_dict"])
        self.epsilon = float(ckpt.get("epsilon", 0.0))
        self.logger.info("Model loaded from %s", filepath)

    def get_model_info(self) -> Dict[str, Any]:
        total = sum(p.numel() for p in self.q_network.parameters())
        return {
            "state_dim": self.state_dim,
            "action_dim": self.action_dim,
            "actions": list(ACTION_INDEX),
            "total_parameters": total,
            "device": str(self.device),
            "epsilon": self.epsilon,
        }
