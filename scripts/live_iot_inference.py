"""
RL-Cleanse real-time inference bridge for a serial-attached sensor node.

Reads newline-delimited JSON telemetry from a microcontroller over UART and
denoises each reading as it arrives, one at a time, with the trained DQN policy::

    {"timestep": 41, "sensor": "CO(GT)", "value": 2.45}

Run with::

    python scripts/live_iot_inference.py --port /dev/ttyUSB0
    python scripts/live_iot_inference.py --replay          # no hardware needed

**Status: implemented and exercised in replay mode only.** The ``--replay`` path
drives the bridge from the UCI test split and is covered by the test suite. The
serial path has *not* been run against a physical ESP32; ``pyserial`` is an
optional dependency and the latency figures this script prints are measured on
the host CPU, not on a microcontroller.

The bridge deliberately reuses :class:`DataCleaningEnvironment` for its rolling
state and action semantics instead of re-deriving them. A separate
implementation here is how the deployed filter silently drifts away from the one
that was trained and evaluated.
"""

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, Iterator, Optional

import numpy as np

# Runnable as a script from the repository root, not only as a module.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from backend.ml.dqn_model import DQNAgent
from envs.data_cleaning_env.server.environment import DEFAULT_HISTORY_LEN

DEFAULT_PORT = "/dev/ttyUSB0"
DEFAULT_BAUD = 115200
DEFAULT_MODEL = "models/dqn_iot_stream_best.pt"


class StreamDenoiser:
    """
    Single-reading denoiser holding only ``history_len`` floats of state.

    This is the deployable object: it takes one reading and returns one cleaned
    reading, with no access to future samples and no buffer that grows over
    time.
    """

    def __init__(
        self,
        model_path: str = DEFAULT_MODEL,
        history_len: int = DEFAULT_HISTORY_LEN,
        device: str = "cpu",
    ):
        self.agent = DQNAgent(device=device)
        self.agent.load_model(model_path)
        self.agent.epsilon = 0.0  # greedy at deployment
        self.agent.set_training_mode(False)

        self.history_len = history_len
        self.emitted: list = []
        self.sensor: Optional[str] = None

    # The action formulas below mirror DataCleaningEnvironment._apply_action.
    def _stats(self) -> Dict[str, float]:
        hist = self.emitted[-self.history_len :]
        if not hist:
            return {"mean": 0.0, "std": 0.0, "median": 0.0, "min": 0.0, "max": 0.0}
        arr = np.asarray(hist, dtype=float)
        return {
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "median": float(np.median(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
        }

    def _observation(self, value: Optional[float], timestep: int) -> Dict[str, Any]:
        stats = self._stats()
        issues = []
        if value is None or not np.isfinite(value):
            issues.append("missing:sensor")
        elif self.emitted:
            dev = abs(value - stats["mean"])
            if stats["std"] > 1e-4 and dev > 3.0 * stats["std"]:
                issues.append("outlier:spike")
            if stats["std"] > 1e-4 and dev > 1.5 * stats["std"]:
                issues.append("drift:offset")
            if abs(value - self.emitted[-1]) < 1e-9:
                issues.append("duplicate:transmission")

        return {
            "current_data": {
                "id": timestep,
                "timestep": timestep,
                "sensor": self.sensor,
                "value": value,
            },
            "rolling_history": list(self.emitted[-self.history_len :]),
            "rolling_stats": {
                "mean": stats["mean"],
                "std": stats["std"],
                "median": stats["median"],
            },
            "issues_detected": issues,
            "legal_actions": None,
            "progress": 0.0,
            "reward": 0.0,
            "done": False,
        }

    def _apply(self, action: str, value: Optional[float], stats: Dict[str, float]):
        has_val = value is not None and np.isfinite(value)
        if action == "skip":
            return value if has_val else None
        if not self.emitted:
            return value if has_val else 0.0
        if action == "remove_outlier":
            return stats["median"]
        if action == "fill_missing":
            return stats["median"]
        if action == "fix_type":
            return stats["mean"] if not has_val else 0.5 * value + 0.5 * stats["mean"]
        if action == "remove_duplicate":
            trend = (
                self.emitted[-1] - self.emitted[-2] if len(self.emitted) >= 2 else 0.0
            )
            return self.emitted[-1] + trend
        if action == "fix_category":
            if not has_val:
                return stats["median"]
            return float(min(max(value, stats["min"]), stats["max"]))
        return value if has_val else None

    def step(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        """Denoise one packet. Returns the decision plus inference latency."""
        self.sensor = packet.get("sensor", self.sensor)
        timestep = int(packet.get("timestep", len(self.emitted)))
        raw = packet.get("value")
        if raw is not None:
            try:
                raw = float(raw)
                if not np.isfinite(raw):
                    raw = None
            except (TypeError, ValueError):
                raw = None

        t0 = time.perf_counter()
        obs = self._observation(raw, timestep)
        action = self.agent.get_action(obs, obs["legal_actions"])["action_type"]
        stats = self._stats()
        cleaned = self._apply(action, raw, stats)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        # A downstream controller needs a number at every step.
        emitted = cleaned if cleaned is not None else (
            self.emitted[-1] if self.emitted else 0.0
        )
        self.emitted.append(float(emitted))
        if len(self.emitted) > max(self.history_len, 2):
            self.emitted.pop(0)

        return {
            "timestep": timestep,
            "raw": raw,
            "action": action,
            "cleaned": float(emitted),
            "latency_ms": latency_ms,
            "flags": obs["issues_detected"],
        }


def serial_packets(port: str, baud: int) -> Iterator[Dict[str, Any]]:
    """Yield JSON packets from a serial port. Requires ``pyserial``."""
    try:
        import serial
    except ImportError:
        sys.exit(
            "pyserial is not installed. Install it with `pip install pyserial`, "
            "or run with --replay to drive the bridge from the UCI test split."
        )

    with serial.Serial(port, baud, timeout=2) as ser:
        time.sleep(2)  # allow the board to boot
        while True:
            line = ser.readline().decode("utf-8", errors="replace").strip()
            if not line.startswith("{"):
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def replay_packets(
    num: int = 48, corruption_type: str = "mixed", seed: int = 2026
) -> Iterator[Dict[str, Any]]:
    """Yield packets from a corrupted UCI test window, for hardware-free runs."""
    from envs.data_cleaning_env.tasks.graders import generate_iot_stream_dataset

    dataset = generate_iot_stream_dataset(
        window_size=num, corruption_type=corruption_type, split="test", seed=seed
    )
    for row in dataset:
        yield {
            "timestep": row["timestep"],
            "sensor": row["sensor"],
            "value": row["value"],
            # Carried for display only; the denoiser never receives it.
            "_ground_truth": row["ground_truth"],
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--replay",
        action="store_true",
        help="Drive the bridge from the UCI test split instead of a serial port.",
    )
    parser.add_argument("--steps", type=int, default=48, help="Replay length.")
    args = parser.parse_args()

    denoiser = StreamDenoiser(model_path=args.model)
    print(f"Loaded policy from {args.model} "
          f"({denoiser.agent.get_model_info()['total_parameters']:,} parameters)")

    if args.replay:
        print(f"Replay mode: {args.steps} corrupted readings from the UCI test split\n")
        source = replay_packets(num=args.steps)
    else:
        print(f"Listening on {args.port} @ {args.baud} baud (Ctrl+C to stop)\n")
        source = serial_packets(args.port, args.baud)

    header = f"{'t':>4} {'raw':>9} {'action':>17} {'cleaned':>9} {'ms':>7}"
    if args.replay:
        header += f" {'truth':>9} {'|err|':>8}"
    print(header)
    print("-" * len(header))

    latencies, errors = [], []
    try:
        for packet in source:
            res = denoiser.step(packet)
            latencies.append(res["latency_ms"])
            raw_s = "DROPPED" if res["raw"] is None else f"{res['raw']:.3f}"
            line = (
                f"{res['timestep']:>4} {raw_s:>9} {res['action']:>17} "
                f"{res['cleaned']:>9.3f} {res['latency_ms']:>7.2f}"
            )
            if "_ground_truth" in packet:
                gt = packet["_ground_truth"]
                err = abs(res["cleaned"] - gt)
                errors.append(err)
                line += f" {gt:>9.3f} {err:>8.3f}"
            print(line)
    except KeyboardInterrupt:
        print("\nStopped.")

    if latencies:
        print(f"\nHost-CPU inference latency over {len(latencies)} readings: "
              f"mean {np.mean(latencies):.2f} ms, p95 {np.percentile(latencies, 95):.2f} ms")
        print("This is a host measurement. No ESP32 latency figure is claimed.")
    if errors:
        print(f"Replay MAE vs. ground truth: {np.mean(errors):.4f}")


if __name__ == "__main__":
    main()
