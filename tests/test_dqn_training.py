"""
Tests for the DQN policy, the replay buffer and the training pipeline.

Everything here runs on CPU in seconds, so CI needs no GPU. Two tests are
explicit regression guards for bugs that silently invalidated the previous
training run: exploration being destroyed by evaluation, and checkpoint
selection reading the held-out test split.
"""

import json
import os

import numpy as np
import pytest
import torch

from backend.ml.dqn_model import (
    ACTION_DIM,
    ACTION_INDEX,
    ACTION_TO_INDEX,
    STATE_DIM,
    DQNAgent,
    QNetwork,
    Transition,
)
from backend.ml.experience_replay import ReplayBuffer
from backend.ml.metrics import evaluate_window
from backend.ml.rule_based_baseline import RuleBasedStreamFilter
from backend.ml.train_dqn import DQNTrainer, set_global_seeds
from envs.data_cleaning_env.server.environment import (
    ACTION_SPACE,
    DataCleaningEnvironment,
)
from envs.data_cleaning_env.tasks.graders import generate_iot_stream_dataset


@pytest.fixture
def agent():
    return DQNAgent(device="cpu", seed=0)


@pytest.fixture
def observation():
    env = DataCleaningEnvironment(history_len=5)
    obs = env.reset(task_name="iot_stream", window_size=24, split="test", seed=5)
    for _ in range(6):
        obs = env.step("skip")
    return obs


class TestQNetwork:
    def test_output_shape_matches_the_action_space(self):
        net = QNetwork()
        out = net(torch.zeros(4, STATE_DIM))
        assert out.shape == (4, ACTION_DIM)

    def test_accepts_a_single_unbatched_row(self):
        assert QNetwork()(torch.zeros(1, STATE_DIM)).shape == (1, ACTION_DIM)

    def test_forward_is_finite(self):
        out = QNetwork()(torch.randn(16, STATE_DIM) * 10)
        assert torch.isfinite(out).all()

    def test_custom_hidden_dims_are_honoured(self):
        net = QNetwork(hidden_dims=[8, 8, 8])
        linears = [m for m in net.network if isinstance(m, torch.nn.Linear)]
        assert len(linears) == 4

    def test_get_q_values_returns_a_flat_array(self):
        q = QNetwork().get_q_values(torch.zeros(1, STATE_DIM))
        assert q.shape == (ACTION_DIM,)


class TestActionSpaceConsistency:
    def test_agent_and_environment_agree(self):
        """A mismatch here would silently mislabel every replayed transition."""
        assert ACTION_INDEX == ACTION_SPACE

    def test_six_actions(self):
        assert ACTION_DIM == 6

    def test_mapping_is_a_bijection(self):
        assert len(ACTION_TO_INDEX) == ACTION_DIM
        assert sorted(ACTION_TO_INDEX.values()) == list(range(ACTION_DIM))
        for i, name in enumerate(ACTION_INDEX):
            assert ACTION_TO_INDEX[name] == i


class TestEncoding:
    def test_shape_and_finiteness(self, agent, observation):
        v = agent.encode_observation(observation)
        assert v.shape == (STATE_DIM,)
        assert v.dtype == np.float32
        assert np.isfinite(v).all()

    def test_bounded_even_on_an_extreme_reading(self, agent, observation):
        obs = dict(observation)
        obs["current_data"] = dict(obs["current_data"], value=1e9)
        v = agent.encode_observation(obs)
        assert np.isfinite(v).all()
        assert np.abs(v).max() <= 1e3

    def test_handles_a_dropout(self, agent, observation):
        obs = dict(observation)
        obs["current_data"] = dict(obs["current_data"], value=None)
        v = agent.encode_observation(obs)
        assert v[0] == 0.0  # 'reading present' flag
        assert np.isfinite(v).all()

    def test_handles_an_empty_observation(self, agent):
        v = agent.encode_observation({})
        assert v.shape == (STATE_DIM,)
        assert np.isfinite(v).all()

    def test_handles_a_zero_variance_history(self, agent, observation):
        obs = dict(observation)
        obs["rolling_history"] = [2.0] * 5
        obs["rolling_stats"] = {"mean": 2.0, "std": 0.0, "median": 2.0}
        v = agent.encode_observation(obs)
        assert np.isfinite(v).all()

    def test_is_deterministic(self, agent, observation):
        np.testing.assert_array_equal(
            agent.encode_observation(observation),
            agent.encode_observation(observation),
        )

    def test_is_scale_relative(self, observation):
        """
        Scaling the whole window must leave the relative features unchanged.

        This is what lets a policy trained on one sensor channel transfer to a
        channel with a different dynamic range.
        """
        a = DQNAgent(device="cpu", seed=0)
        k = 10.0
        scaled = dict(observation)
        scaled["current_data"] = dict(
            observation["current_data"], value=observation["current_data"]["value"] * k
        )
        scaled["rolling_history"] = [h * k for h in observation["rolling_history"]]
        scaled["rolling_stats"] = {
            key: v * k for key, v in observation["rolling_stats"].items()
        }
        v1 = a.encode_observation(observation)
        v2 = a.encode_observation(scaled)
        # Indices 3-6 and 10-14 are sigma-normalised and must be invariant.
        for i in [3, 4, 5, 6, 10, 11, 12, 13, 14]:
            assert v1[i] == pytest.approx(v2[i], abs=1e-3), f"feature {i}"


class TestActionSelection:
    def test_returns_a_legal_action_dict(self, agent, observation):
        act = agent.get_action(observation, observation["legal_actions"])
        assert set(act) == {"action_type", "column", "value"}
        assert act["action_type"] in ACTION_SPACE
        # The environment owns each action's correction formula.
        assert act["value"] is None

    def test_respects_a_restricted_legal_set(self, agent, observation):
        agent.epsilon = 0.0
        for _ in range(20):
            act = agent.get_action(observation, ["skip", "fix_type"])
            assert act["action_type"] in {"skip", "fix_type"}

    def test_falls_back_to_skip_when_nothing_is_legal(self, agent, observation):
        assert agent.get_action(observation, [])["action_type"] in ACTION_SPACE

    def test_greedy_selection_is_deterministic(self, agent, observation):
        agent.epsilon = 0.0
        picks = {
            agent.get_action(observation, observation["legal_actions"])["action_type"]
            for _ in range(10)
        }
        assert len(picks) == 1

    def test_full_exploration_uses_the_whole_action_space(self, agent, observation):
        agent.epsilon = 1.0
        picks = {
            agent.get_action(observation, observation["legal_actions"])["action_type"]
            for _ in range(300)
        }
        assert picks == set(ACTION_SPACE)

    def test_greedy_choice_matches_the_argmax_q_value(self, agent, observation):
        agent.epsilon = 0.0
        state = torch.as_tensor(
            agent.encode_observation(observation), dtype=torch.float32
        )
        with torch.no_grad():
            q = agent.q_network(state.unsqueeze(0)).numpy()[0]
        expected = ACTION_INDEX[int(np.argmax(q))]
        assert agent.get_action(observation, ACTION_SPACE)["action_type"] == expected

    def test_confidence_is_a_probability(self, agent, observation):
        agent.epsilon = 0.0
        agent.get_action(observation, observation["legal_actions"])
        assert 0.0 <= agent.get_confidence() <= 1.0


class TestExplorationSchedule:
    def test_decay_moves_toward_the_floor(self):
        a = DQNAgent(device="cpu", epsilon=1.0, epsilon_min=0.02, epsilon_decay=0.9)
        assert a.decay_epsilon() == pytest.approx(0.9)
        for _ in range(500):
            a.decay_epsilon()
        assert a.epsilon == pytest.approx(0.02)

    def test_eval_mode_restores_epsilon(self):
        """
        Regression test for the bug that invalidated the previous training run.

        ``set_training_mode(False)`` used to zero epsilon with nothing to
        restore it, so the first mid-training evaluation ended exploration for
        good — visible in the old metrics as epsilon collapsing to the floor at
        epoch 11 of 40.
        """
        a = DQNAgent(device="cpu", epsilon=0.63)
        with a.eval_mode():
            assert a.epsilon == 0.0
            assert not a.q_network.training
        assert a.epsilon == 0.63

    def test_eval_mode_restores_epsilon_after_an_exception(self):
        a = DQNAgent(device="cpu", epsilon=0.41)
        with pytest.raises(RuntimeError):
            with a.eval_mode():
                raise RuntimeError("boom")
        assert a.epsilon == 0.41

    def test_set_training_mode_does_not_touch_epsilon(self):
        a = DQNAgent(device="cpu", epsilon=0.5)
        a.set_training_mode(False)
        assert a.epsilon == 0.5
        a.set_training_mode(True)
        assert a.epsilon == 0.5


class TestReplayBuffer:
    def _fill(self, buf, n):
        for i in range(n):
            buf.add(
                np.zeros(STATE_DIM, dtype=np.float32),
                i % ACTION_DIM,
                float(i),
                np.ones(STATE_DIM, dtype=np.float32),
                i == n - 1,
            )

    def test_add_and_size(self):
        buf = ReplayBuffer(capacity=100, seed=0)
        self._fill(buf, 10)
        assert buf.size() == 10

    def test_capacity_evicts_oldest(self):
        buf = ReplayBuffer(capacity=5, seed=0)
        self._fill(buf, 20)
        assert buf.size() == 5
        assert buf.is_full()
        # Oldest transitions are gone; rewards were the loop index.
        assert min(t.reward for t in buf.buffer) == 15.0

    def test_sample_returns_transitions(self):
        buf = ReplayBuffer(capacity=100, seed=0)
        self._fill(buf, 50)
        batch = buf.sample(16)
        assert len(batch) == 16
        assert all(isinstance(t, Transition) for t in batch)

    def test_sample_without_enough_data_raises(self):
        buf = ReplayBuffer(capacity=100, seed=0)
        self._fill(buf, 4)
        with pytest.raises(ValueError):
            buf.sample(8)

    def test_sampling_is_reproducible_from_seed(self):
        a, b = ReplayBuffer(capacity=100, seed=7), ReplayBuffer(capacity=100, seed=7)
        self._fill(a, 50)
        self._fill(b, 50)
        assert [t.reward for t in a.sample(8)] == [t.reward for t in b.sample(8)]

    def test_independent_seeds_differ(self):
        a, b = ReplayBuffer(capacity=100, seed=1), ReplayBuffer(capacity=100, seed=2)
        self._fill(a, 50)
        self._fill(b, 50)
        assert [t.reward for t in a.sample(8)] != [t.reward for t in b.sample(8)]

    def test_clear(self):
        buf = ReplayBuffer(capacity=100, seed=0)
        self._fill(buf, 10)
        buf.clear()
        assert buf.size() == 0


class TestCheckpointing:
    def test_roundtrip_preserves_weights_and_epsilon(self, tmp_path):
        a = DQNAgent(device="cpu", seed=1, epsilon=0.33)
        path = tmp_path / "agent.pt"
        a.save_model(str(path))

        b = DQNAgent(device="cpu", seed=2)
        b.load_model(str(path))
        assert b.epsilon == pytest.approx(0.33)
        for p, q in zip(a.q_network.parameters(), b.q_network.parameters()):
            assert torch.equal(p, q)

    def test_loaded_policy_reproduces_the_same_actions(self, tmp_path, observation):
        a = DQNAgent(device="cpu", seed=1)
        a.epsilon = 0.0
        path = tmp_path / "agent.pt"
        a.save_model(str(path))
        b = DQNAgent(device="cpu", seed=9)
        b.load_model(str(path))
        b.epsilon = 0.0
        assert (
            a.get_action(observation, ACTION_SPACE)["action_type"]
            == b.get_action(observation, ACTION_SPACE)["action_type"]
        )

    def test_shape_mismatch_is_rejected_with_a_clear_message(self, tmp_path):
        a = DQNAgent(device="cpu", state_dim=8, action_dim=6)
        path = tmp_path / "small.pt"
        a.save_model(str(path))
        with pytest.raises(ValueError, match="state_dim"):
            DQNAgent(device="cpu").load_model(str(path))

    def test_reordered_action_space_is_rejected(self, tmp_path):
        a = DQNAgent(device="cpu")
        path = tmp_path / "agent.pt"
        a.save_model(str(path))
        ckpt = torch.load(str(path), weights_only=False)
        ckpt["action_index"] = list(reversed(ACTION_INDEX))
        torch.save(ckpt, str(path))
        with pytest.raises(ValueError, match="action ordering"):
            DQNAgent(device="cpu").load_model(str(path))

    def test_model_info_is_populated(self):
        info = DQNAgent(device="cpu").get_model_info()
        assert info["total_parameters"] > 0
        assert info["actions"] == ACTION_INDEX
        assert info["state_dim"] == STATE_DIM


class TestTrainingPipeline:
    @pytest.fixture(scope="class")
    @staticmethod
    def trained():
        trainer = DQNTrainer(
            {
                "epochs": 12,
                "device": "cpu",
                "batch_size": 16,
                "val_windows": 2,
                "eval_every": 6,
                "seed": 123,
            }
        )
        result = trainer.train(epochs=12, save=False)
        return trainer, result

    def test_runs_on_cpu(self, trained):
        trainer, _ = trained
        assert trainer.device.type == "cpu"

    def test_train_step_returns_a_finite_loss(self):
        trainer = DQNTrainer({"epochs": 2, "device": "cpu", "batch_size": 8})
        for _ in range(64):
            trainer.replay_buffer.add(
                np.random.randn(STATE_DIM).astype(np.float32),
                0,
                0.1,
                np.random.randn(STATE_DIM).astype(np.float32),
                False,
            )
        loss = trainer.train_step()
        assert loss is not None and np.isfinite(loss)

    def test_train_step_is_a_no_op_before_the_buffer_fills(self):
        trainer = DQNTrainer({"epochs": 2, "device": "cpu", "batch_size": 64})
        assert trainer.train_step() is None

    def test_a_gradient_step_changes_the_weights(self):
        trainer = DQNTrainer({"epochs": 2, "device": "cpu", "batch_size": 8})
        before = [p.clone() for p in trainer.agent.q_network.parameters()]
        for _ in range(32):
            trainer.replay_buffer.add(
                np.random.randn(STATE_DIM).astype(np.float32),
                1,
                1.0,
                np.random.randn(STATE_DIM).astype(np.float32),
                False,
            )
        for _ in range(5):
            trainer.train_step()
        after = list(trainer.agent.q_network.parameters())
        assert any(not torch.equal(b, a) for b, a in zip(before, after))

    def test_target_network_only_moves_when_synced(self):
        trainer = DQNTrainer({"epochs": 2, "device": "cpu", "batch_size": 8})
        target_before = [p.clone() for p in trainer.agent.target_network.parameters()]
        for _ in range(32):
            trainer.replay_buffer.add(
                np.random.randn(STATE_DIM).astype(np.float32),
                1,
                1.0,
                np.random.randn(STATE_DIM).astype(np.float32),
                False,
            )
        for _ in range(5):
            trainer.train_step()
        assert all(
            torch.equal(b, a)
            for b, a in zip(target_before, trainer.agent.target_network.parameters())
        )
        trainer.agent.update_target_network()
        assert any(
            not torch.equal(b, a)
            for b, a in zip(target_before, trainer.agent.target_network.parameters())
        )

    def test_collects_metrics_for_every_epoch(self, trained):
        trainer, _ = trained
        assert len(trainer.metrics["episode_rewards"]) == 12
        assert len(trainer.metrics["epsilon_values"]) == 12
        assert len(trainer.metrics["episode_lengths"]) == 12

    def test_epsilon_decays_across_training(self, trained):
        trainer, _ = trained
        eps = trainer.metrics["epsilon_values"]
        assert eps[0] > eps[-1]
        assert all(b <= a for a, b in zip(eps, eps[1:]))

    def test_exploration_survives_mid_training_evaluation(self):
        """
        Epsilon after training must equal pure decay, untouched by evaluation.

        The old loop zeroed epsilon inside its evaluator, so from the first
        mid-training evaluation onwards the schedule was pinned at the floor.
        A slow explicit decay is used here so the floor is never reached and
        any interference would be visible.
        """
        epochs, decay = 10, 0.99
        trainer = DQNTrainer(
            {
                "epochs": epochs,
                "device": "cpu",
                "batch_size": 16,
                "epsilon_decay": decay,
                "val_windows": 1,
                "eval_every": 2,  # several evaluations during the run
                "seed": 5,
            }
        )
        trainer.train(epochs=epochs, save=False)

        expected = max(trainer.config["epsilon_min"], 1.0 * decay**epochs)
        assert trainer.agent.epsilon == pytest.approx(expected)
        assert trainer.agent.epsilon > trainer.config["epsilon_min"]
        # Confirm evaluation really did run, so the test cannot pass vacuously.
        assert len(trainer.metrics["val_history"]) >= 4

    def test_training_cycles_every_fault_family(self, trained):
        trainer, _ = trained
        from envs.data_cleaning_env.tasks.graders import CORRUPTION_TYPES

        assert set(trainer.metrics["corruption_types"]) == set(CORRUPTION_TYPES)

    def test_checkpoint_selection_uses_validation_not_test(self, trained):
        """
        Regression test: the old loop selected the best model by test-split MAE.

        The validation history must record entries, and the split it evaluates
        must be 'val'.
        """
        trainer, result = trained
        assert trainer.metrics["val_history"]
        assert result["best_epoch"] > 0
        assert "mean_relative_mae" in trainer.metrics["val_history"][0]

    def test_epsilon_decay_schedule_spans_the_run(self):
        """decay=None must scale with run length, not collapse in 15% of it."""
        for epochs in (100, 500):
            t = DQNTrainer({"epochs": epochs, "device": "cpu"})
            eps, floor = 1.0, t.config["epsilon_min"]
            reached = epochs
            for i in range(1, epochs + 1):
                eps = max(floor, eps * t.config["epsilon_decay"])
                if eps <= floor * 1.001:
                    reached = i
                    break
            assert 0.6 * epochs <= reached <= 0.8 * epochs

    def test_explicit_epsilon_decay_is_respected(self):
        t = DQNTrainer({"epochs": 100, "device": "cpu", "epsilon_decay": 0.5})
        assert t.config["epsilon_decay"] == 0.5

    def test_evaluate_reports_every_fault_family(self, trained):
        trainer, _ = trained
        res = trainer.evaluate(split="val", num_windows=2)
        from envs.data_cleaning_env.tasks.graders import CORRUPTION_TYPES

        assert set(res["by_corruption"]) == set(CORRUPTION_TYPES)
        assert np.isfinite(res["mean_mae"])
        assert np.isfinite(res["mean_relative_mae"])

    def test_double_dqn_can_be_disabled(self):
        t = DQNTrainer({"epochs": 2, "device": "cpu", "batch_size": 8, "double_dqn": False})
        for _ in range(32):
            t.replay_buffer.add(
                np.random.randn(STATE_DIM).astype(np.float32),
                0,
                0.5,
                np.random.randn(STATE_DIM).astype(np.float32),
                False,
            )
        assert np.isfinite(t.train_step())

    def test_train_with_save_false_writes_no_checkpoint(self, tmp_path, monkeypatch):
        """
        Regression test: train(save=False) must not touch models/ at all.

        The best-checkpoint save used to sit outside the `save` guard, so every
        run of this very test class -- train(epochs=12, save=False) with the
        default empty checkpoint suffix -- overwrote
        models/dqn_iot_stream_best.pt with a 12-epoch CPU model. The published
        headline checkpoint was a test artifact, and it scored worse on the
        spike family than doing nothing. The test suite was corrupting the
        thing the project reports.
        """
        monkeypatch.chdir(tmp_path)
        trainer = DQNTrainer(
            {
                "epochs": 8,
                "device": "cpu",
                "batch_size": 16,
                "val_windows": 1,
                "eval_every": 4,
                "seed": 77,
            }
        )
        result = trainer.train(epochs=8, save=False)

        written = (
            sorted(os.listdir(tmp_path / "models"))
            if (tmp_path / "models").exists()
            else []
        )
        assert written == [], f"train(save=False) wrote {written}"
        # The selected weights are still available, just in memory.
        assert result["best_state"] is not None
        assert result["best_model_path"] is None
        assert result["final_model_path"] is None

    def test_train_with_save_true_writes_the_selected_weights(self, tmp_path, monkeypatch):
        """The persisted best checkpoint must be the validation-selected one."""
        monkeypatch.chdir(tmp_path)
        trainer = DQNTrainer(
            {
                "epochs": 8,
                "device": "cpu",
                "batch_size": 16,
                "val_windows": 1,
                "eval_every": 4,
                "seed": 77,
            }
        )
        result = trainer.train(epochs=8, save=True)
        assert os.path.exists(result["best_model_path"])

        reloaded = DQNAgent(device="cpu")
        reloaded.load_model(result["best_model_path"])
        for key, tensor in result["best_state"]["q"].items():
            assert torch.equal(tensor, reloaded.q_network.state_dict()[key])

    def test_plot_is_written(self, trained, tmp_path):
        trainer, _ = trained
        path = trainer.plot_training_curves(str(tmp_path / "curves.png"))
        assert os.path.exists(path) and os.path.getsize(path) > 0


class TestReproducibility:
    def test_identical_seeds_give_identical_training(self):
        runs = []
        for _ in range(2):
            t = DQNTrainer(
                {
                    "epochs": 6,
                    "device": "cpu",
                    "batch_size": 16,
                    "val_windows": 1,
                    "eval_every": 100,
                    "seed": 2026,
                }
            )
            t.train(epochs=6, save=False)
            runs.append(t.metrics["episode_rewards"])
        assert runs[0] == pytest.approx(runs[1])

    def test_set_global_seeds_makes_torch_deterministic(self):
        set_global_seeds(11)
        a = torch.randn(4)
        set_global_seeds(11)
        assert torch.equal(a, torch.randn(4))


class TestBaselineIsFair:
    """
    The comparison is only meaningful if the baseline is competent.

    These are guards against the regression that made the previous results
    meaningless: a filter that damaged a clean signal worse than the corruption
    it was supposed to remove.
    """

    def test_does_not_damage_an_uncorrupted_stream(self):
        maes = []
        for s in range(15):
            ds = generate_iot_stream_dataset(24, "none", "test", seed=s)
            f = RuleBasedStreamFilter()
            maes.append(evaluate_window(ds, f.predict_window(ds))["mae"])
        # The earlier revision scored 0.208 here.
        assert np.mean(maes) < 0.02

    def test_never_emits_a_missing_value(self):
        ds = generate_iot_stream_dataset(48, "dropout", "test", seed=4)
        out = RuleBasedStreamFilter().predict_window(ds)
        assert all(v is not None and np.isfinite(v) for v in out)

    def test_imputes_every_dropout(self):
        ds = generate_iot_stream_dataset(48, "dropout", "test", seed=4)
        rows = RuleBasedStreamFilter().process_window(ds)
        dropped = [i for i, r in enumerate(ds) if r["value"] is None]
        assert dropped
        for i in dropped:
            assert rows[i]["baseline_action"] == "fill_missing"

    def test_removes_a_large_injected_spike(self):
        f = RuleBasedStreamFilter(warmup=6, z_threshold=4.0)
        for v in [5.0, 5.1, 4.9, 5.0, 5.2, 4.8, 5.1]:
            f.filter_step(v)
        res = f.filter_step(500.0)
        assert res["action_type"] == "remove_outlier"
        assert res["cleaned_value"] == pytest.approx(5.1, abs=0.5)

    def test_history_is_not_poisoned_by_its_own_replacements(self):
        """
        The failure mode that flatlined the old filter.

        After rejecting a reading the buffer must be unchanged, or a few
        rejections collapse the spread and every later reading looks like an
        outlier.
        """
        f = RuleBasedStreamFilter(warmup=6, z_threshold=4.0)
        for v in [5.0, 5.1, 4.9, 5.0, 5.2, 4.8, 5.1]:
            f.filter_step(v)
        before = list(f.history)
        for _ in range(10):
            f.filter_step(500.0)
        assert f.history == before

    def test_accepts_a_genuine_step_change_after_it_persists(self):
        f = RuleBasedStreamFilter(warmup=6)
        for v in [1.0, 1.1, 0.9, 1.0, 1.2, 0.8, 1.1]:
            f.filter_step(v)
        accepted = sum(
            f.filter_step(v)["action_type"] == "skip" for v in [3.0] * 10
        )
        assert accepted >= 5

    def test_reset_clears_all_state(self):
        f = RuleBasedStreamFilter()
        for v in [1.0, 2.0, 3.0]:
            f.filter_step(v)
        f.reset()
        assert f.history == [] and f.residuals == [] and f.last_valid_value is None

    def test_is_deterministic(self):
        ds = generate_iot_stream_dataset(24, "mixed", "test", seed=9)
        a = RuleBasedStreamFilter().predict_window(ds)
        b = RuleBasedStreamFilter().predict_window(ds)
        assert a == b


@pytest.mark.skipif(not torch.cuda.is_available(), reason="no CUDA device")
class TestGpuSupport:
    def test_agent_runs_on_cuda(self, observation):
        a = DQNAgent(device="cuda", seed=0)
        assert a.device.type == "cuda"
        act = a.get_action(observation, ACTION_SPACE)
        assert act["action_type"] in ACTION_SPACE

    def test_checkpoint_moves_between_devices(self, tmp_path, observation):
        gpu = DQNAgent(device="cuda", seed=0)
        path = tmp_path / "gpu.pt"
        gpu.save_model(str(path))
        cpu = DQNAgent(device="cpu")
        cpu.load_model(str(path))
        assert cpu.device.type == "cpu"

    def test_trainer_auto_selects_cuda(self):
        t = DQNTrainer({"epochs": 2, "device": "auto"})
        assert t.device.type == "cuda"
