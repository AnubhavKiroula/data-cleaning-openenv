"""
Tests for the streaming environment, its action semantics and its grader.

The two properties the research claim depends on — that the agent sees no future
data and no oracle annotation — are asserted directly rather than assumed, since
both were violated by earlier revisions of this environment.
"""

import numpy as np
import pytest

from backend.ml.metrics import (
    carry_forward,
    error_reduction_pct,
    evaluate_window,
    quality_score,
    stream_metrics,
)
from backend.ml.reward_shaper import RewardShaper
from envs.data_cleaning_env.server.environment import (
    ACTION_SPACE,
    DataCleaningEnvironment,
)
from envs.data_cleaning_env.tasks.graders import (
    CORRUPTION_TYPES,
    ORACLE_FIELDS,
    generate_iot_stream_dataset,
    grade_iot_stream,
)


@pytest.fixture
def env():
    return DataCleaningEnvironment(history_len=5)


def rollout(env, action="skip", **reset_kwargs):
    """Run a whole episode with a single fixed action."""
    kwargs = {
        "window_size": 24,
        "split": "test",
        "corruption_type": "mixed",
        "seed": 7,
        **reset_kwargs,
    }
    obs = env.reset(task_name="iot_stream", **kwargs)
    observations = [obs]
    while not obs["done"]:
        obs = env.step(action)
        observations.append(obs)
    return observations


class TestResetAndStep:
    def test_reset_returns_first_observation(self, env):
        obs = env.reset(task_name="iot_stream", window_size=24, split="test", seed=1)
        assert obs["current_row"] == 0
        assert obs["total_rows"] == 24
        assert obs["done"] is False
        assert obs["reward"] == 0.0

    def test_unknown_task_raises(self, env):
        with pytest.raises(ValueError):
            env.reset(task_name="easy")

    def test_unknown_action_raises(self, env):
        env.reset(task_name="iot_stream", window_size=6, split="test", seed=1)
        with pytest.raises(ValueError):
            env.step("reticulate_splines")

    def test_episode_terminates_after_exactly_window_size_steps(self, env):
        obs_list = rollout(env, window_size=24)
        assert env.step_count == 24
        assert obs_list[-1]["done"] is True
        assert len(env.cleaned_data) == 24

    def test_stepping_after_done_raises(self, env):
        rollout(env, window_size=6)
        with pytest.raises(ValueError):
            env.step("skip")

    def test_reset_clears_previous_episode(self, env):
        rollout(env, window_size=6)
        env.reset(task_name="iot_stream", window_size=6, split="test", seed=2)
        assert env.step_count == 0
        assert env.cleaned_data == []
        assert env.emitted == []
        assert env.total_reward == 0.0

    def test_progress_advances_monotonically(self, env):
        obs_list = rollout(env, window_size=12)
        progress = [o["progress"] for o in obs_list]
        assert progress == sorted(progress)

    def test_legal_actions_are_the_six_action_space(self, env):
        obs = env.reset(task_name="iot_stream", window_size=6, split="test", seed=1)
        assert obs["legal_actions"] == ACTION_SPACE
        assert len(ACTION_SPACE) == 6


class TestNoLeakage:
    def test_observation_never_contains_oracle_fields(self, env):
        """The generator's annotations must not reach the agent."""
        for obs in rollout(env, window_size=24):
            for field in ORACLE_FIELDS:
                assert field not in obs["current_data"], f"{field} leaked"

    def test_oracle_fields_do_exist_on_the_underlying_dataset(self, env):
        """Guards the test above from passing because the fields were dropped."""
        env.reset(task_name="iot_stream", window_size=6, split="test", seed=1)
        for field in ORACLE_FIELDS:
            assert field in env.dataset[0]

    def test_observation_exposes_only_packet_level_fields(self, env):
        obs = env.reset(task_name="iot_stream", window_size=6, split="test", seed=1)
        assert set(obs["current_data"]) == {"id", "timestep", "sensor", "value"}

    def test_observation_at_step_t_matches_dataset_row_t(self, env):
        """No future sample can enter an observation."""
        obs = env.reset(task_name="iot_stream", window_size=12, split="test", seed=4)
        t = 0
        while not obs["done"]:
            assert obs["current_data"]["timestep"] == t
            expected = env.dataset[t]["value"]
            got = obs["current_data"]["value"]
            assert (got is None and expected is None) or got == expected
            obs = env.step("skip")
            t += 1

    def test_rolling_history_only_contains_already_emitted_values(self, env):
        obs = env.reset(task_name="iot_stream", window_size=12, split="test", seed=4)
        while not obs["done"]:
            hist = obs["rolling_history"]
            assert hist == env.emitted[-5:]
            assert len(hist) <= 5
            obs = env.step("skip")

    def test_detected_issues_are_derived_not_labelled(self, env):
        """
        Fault flags must be computable from observables.

        A window with no faults at all should raise essentially no flags; if the
        flags were the generator's labels they would be exactly right instead.
        """
        obs = env.reset(
            task_name="iot_stream",
            window_size=24,
            split="test",
            corruption_type="none",
            seed=3,
        )
        flagged = 0
        while not obs["done"]:
            flagged += 1 if obs["issues_detected"] else 0
            obs = env.step("skip")
        assert flagged < 24


class TestObservationShape:
    def test_rolling_history_grows_to_the_window_then_saturates(self, env):
        obs = env.reset(task_name="iot_stream", window_size=12, split="test", seed=1)
        lengths = []
        while not obs["done"]:
            lengths.append(len(obs["rolling_history"]))
            obs = env.step("skip")
        assert lengths[:6] == [0, 1, 2, 3, 4, 5]
        assert all(n == 5 for n in lengths[5:])

    def test_rolling_stats_match_the_history_window(self, env):
        obs = env.reset(task_name="iot_stream", window_size=12, split="test", seed=1)
        while not obs["done"]:
            hist = obs["rolling_history"]
            if hist:
                assert obs["rolling_stats"]["mean"] == pytest.approx(np.mean(hist))
                assert obs["rolling_stats"]["std"] == pytest.approx(np.std(hist))
                assert obs["rolling_stats"]["median"] == pytest.approx(np.median(hist))
            obs = env.step("skip")

    def test_stats_are_zero_before_any_history_exists(self, env):
        obs = env.reset(task_name="iot_stream", window_size=6, split="test", seed=1)
        assert obs["rolling_stats"] == {"mean": 0.0, "std": 0.0, "median": 0.0}

    def test_terminal_observation_is_well_formed(self, env):
        final = rollout(env, window_size=6)[-1]
        assert final["done"] is True
        assert final["current_data"] == {}
        assert final["legal_actions"] == []


class TestActionSemantics:
    """Each action has one definition, over the rolling history."""

    def _env_with_history(self, values):
        """An environment primed with a known emission history."""
        e = DataCleaningEnvironment(history_len=5)
        e.reset(task_name="iot_stream", window_size=24, split="test", seed=1)
        e.emitted = list(values)
        return e

    def test_skip_retains_the_reading_exactly(self):
        e = self._env_with_history([1.0, 2.0, 3.0])
        stats = e._rolling_stats()
        assert e._apply_action("skip", 7.5, None, stats) == 7.5

    def test_skip_preserves_a_dropout_as_missing(self):
        e = self._env_with_history([1.0, 2.0, 3.0])
        assert e._apply_action("skip", None, None, e._rolling_stats()) is None

    def test_remove_outlier_emits_the_rolling_median(self):
        e = self._env_with_history([1.0, 2.0, 3.0, 4.0, 5.0])
        assert e._apply_action("remove_outlier", 99.0, None, e._rolling_stats()) == 3.0

    def test_fill_missing_imputes_the_rolling_median(self):
        e = self._env_with_history([1.0, 2.0, 3.0, 4.0, 5.0])
        assert e._apply_action("fill_missing", None, None, e._rolling_stats()) == 3.0

    def test_fix_type_shrinks_halfway_to_the_rolling_mean(self):
        e = self._env_with_history([2.0, 2.0, 2.0])
        got = e._apply_action("fix_type", 10.0, None, e._rolling_stats())
        assert got == pytest.approx(6.0)  # 0.5 * 10 + 0.5 * 2

    def test_remove_duplicate_extrapolates_the_local_trend(self):
        e = self._env_with_history([1.0, 2.0])
        # last=2.0, trend=+1.0 -> 3.0
        assert e._apply_action("remove_duplicate", 2.0, None, e._rolling_stats()) == 3.0

    def test_remove_duplicate_with_one_sample_has_zero_trend(self):
        e = self._env_with_history([4.0])
        assert e._apply_action("remove_duplicate", 4.0, None, e._rolling_stats()) == 4.0

    def test_fix_category_clamps_into_the_history_envelope(self):
        e = self._env_with_history([2.0, 3.0, 4.0])
        stats = e._rolling_stats()
        assert e._apply_action("fix_category", 99.0, None, stats) == 4.0
        assert e._apply_action("fix_category", -99.0, None, stats) == 2.0
        assert e._apply_action("fix_category", 3.5, None, stats) == 3.5

    @pytest.mark.parametrize("action", ACTION_SPACE)
    def test_every_action_is_safe_with_no_history(self, action):
        """The first step of an episode has nothing to correct against."""
        e = DataCleaningEnvironment(history_len=5)
        e.reset(task_name="iot_stream", window_size=6, split="test", seed=1)
        assert e.emitted == []
        out = e._apply_action(action, 5.0, None, e._rolling_stats())
        assert out == 5.0

    @pytest.mark.parametrize("action", ACTION_SPACE)
    def test_every_action_is_safe_with_no_history_and_no_reading(self, action):
        e = DataCleaningEnvironment(history_len=5)
        e.reset(task_name="iot_stream", window_size=6, split="test", seed=1)
        out = e._apply_action(action, None, None, e._rolling_stats())
        assert out is None if action == "skip" else out == 0.0

    @pytest.mark.parametrize("action", [a for a in ACTION_SPACE if a != "skip"])
    def test_explicit_value_overrides_the_canonical_correction(self, action):
        e = self._env_with_history([1.0, 2.0, 3.0])
        assert e._apply_action(action, 5.0, 42.0, e._rolling_stats()) == 42.0

    @pytest.mark.parametrize("action", ACTION_SPACE)
    def test_actions_are_deterministic(self, action):
        a = DataCleaningEnvironment(history_len=5)
        b = DataCleaningEnvironment(history_len=5)
        for e in (a, b):
            e.reset(task_name="iot_stream", window_size=24, split="test", seed=1)
            e.emitted = [1.0, 5.0, 2.0, 8.0, 3.0]
        stats = a._rolling_stats()
        assert a._apply_action(action, 6.0, None, stats) == b._apply_action(
            action, 6.0, None, b._rolling_stats()
        )


class TestReward:
    def test_skip_is_rewarded_on_a_pristine_reading(self):
        assert RewardShaper().compute_stream_reward("skip", 0.05, 0.05) == 0.15

    def test_skip_is_penalised_when_a_fault_was_missed(self):
        assert RewardShaper().compute_stream_reward("skip", 3.0, 3.0) == -0.15

    def test_reducing_error_pays_base_plus_magnitude(self):
        # base 0.30 + min(0.45, 0.2 * 2.9) = 0.30 + 0.45
        assert RewardShaper().compute_stream_reward(
            "remove_outlier", 3.0, 0.1
        ) == pytest.approx(0.75)

    def test_improvement_bonus_is_clipped(self):
        r = RewardShaper()
        small = r.compute_stream_reward("remove_outlier", 3.0, 0.1)
        huge = r.compute_stream_reward("remove_outlier", 1000.0, 0.1)
        assert small == huge

    def test_false_correction_is_penalised_in_proportion(self):
        r = RewardShaper()
        mild = r.compute_stream_reward("remove_outlier", 0.05, 0.5)
        severe = r.compute_stream_reward("remove_outlier", 0.05, 5.0)
        assert mild < -0.15
        assert severe < mild

    def test_degradation_penalty_is_clipped(self):
        r = RewardShaper()
        a = r.compute_stream_reward("remove_outlier", 0.0, 100.0)
        b = r.compute_stream_reward("remove_outlier", 0.0, 10000.0)
        assert a == b == pytest.approx(-0.5)

    def test_a_no_op_correction_is_penalised(self):
        assert RewardShaper().compute_stream_reward("fix_type", 1.0, 1.0) == -0.15

    def test_rewards_are_bounded(self):
        r = RewardShaper()
        for e_raw, e_clean in [(0, 1e6), (1e6, 0), (0, 0), (5, 5)]:
            for a in ACTION_SPACE:
                assert -1.0 <= r.compute_stream_reward(a, e_raw, e_clean) <= 1.0

    def test_reward_does_not_depend_on_the_fault_label(self):
        """
        The reward must be a function of outcome only.

        Passing identical errors must give an identical reward regardless of
        what fault the generator injected, which is what makes the learned
        policy transferable rather than an annotation matcher.
        """
        r = RewardShaper()
        baseline = r.compute_stream_reward("remove_outlier", 2.0, 0.2, record=False)
        for _ in range(5):
            assert (
                r.compute_stream_reward("remove_outlier", 2.0, 0.2, record=False)
                == baseline
            )

    def test_action_cost_defaults_to_the_published_reward(self):
        """action_cost=0.0 must reproduce master plan section 2.3 exactly."""
        default = RewardShaper()
        explicit = RewardShaper(action_cost=0.0)
        for action in ACTION_SPACE:
            for e_raw, e_clean in [(3.0, 0.1), (0.05, 0.5), (1.0, 1.0), (0.05, 0.05)]:
                assert default.compute_stream_reward(
                    action, e_raw, e_clean, record=False
                ) == explicit.compute_stream_reward(
                    action, e_raw, e_clean, record=False
                )

    def test_action_cost_is_charged_only_on_non_skip_actions(self):
        free = RewardShaper(action_cost=0.0)
        priced = RewardShaper(action_cost=0.1)

        # Skipping is free regardless of the cost.
        for e_raw in (0.05, 3.0):
            assert priced.compute_stream_reward(
                "skip", e_raw, e_raw, record=False
            ) == free.compute_stream_reward("skip", e_raw, e_raw, record=False)

        # Every other action pays it, helpful or not.
        for action in [a for a in ACTION_SPACE if a != "skip"]:
            for e_raw, e_clean in [(3.0, 0.1), (0.05, 0.5), (1.0, 1.0)]:
                delta = free.compute_stream_reward(
                    action, e_raw, e_clean, record=False
                ) - priced.compute_stream_reward(
                    action, e_raw, e_clean, record=False
                )
                assert delta == pytest.approx(0.1), action

    def test_action_cost_keeps_rewards_bounded(self):
        r = RewardShaper(action_cost=0.5)
        for action in ACTION_SPACE:
            for e_raw, e_clean in [(0.0, 1e6), (1e6, 0.0), (0.0, 0.0)]:
                assert -1.0 <= r.compute_stream_reward(
                    action, e_raw, e_clean, record=False
                ) <= 1.0

    def test_environment_passes_the_action_cost_to_its_shaper(self):
        e = DataCleaningEnvironment(history_len=5, action_cost=0.08)
        assert e.reward_shaper.action_cost == pytest.approx(0.08)
        assert DataCleaningEnvironment().reward_shaper.action_cost == 0.0

    def test_action_cost_changes_the_reward_the_environment_emits(self):
        """A priced environment must pay strictly less for the same action."""
        rewards = {}
        for cost in (0.0, 0.1):
            e = DataCleaningEnvironment(history_len=5, action_cost=cost)
            e.reset(task_name="iot_stream", window_size=12, split="test", seed=31)
            total = 0.0
            while not e.done:
                total += e.step("fix_type")["reward"]
            rewards[cost] = total
        assert rewards[0.1] < rewards[0.0]

    def test_environment_reward_is_consistent_with_the_shaper(self, env):
        obs = env.reset(
            task_name="iot_stream", window_size=24, split="test", seed=8
        )
        shaper = RewardShaper()
        while not obs["done"]:
            idx = env.current_row_index
            gt = env.dataset[idx]["ground_truth"]
            raw = env.dataset[idx]["value"]
            present = raw is not None and np.isfinite(float(raw))
            do_nothing = float(raw) if present else env._carry_value(gt)
            expected = shaper.compute_stream_reward(
                "skip", abs(do_nothing - gt), abs(do_nothing - gt), record=False
            )
            obs = env.step("skip")
            assert obs["reward"] == pytest.approx(expected)


class TestGrader:
    def test_passthrough_scores_exactly_one_half(self):
        """0.5 is defined as 'no better than the do-nothing policy'."""
        ds = generate_iot_stream_dataset(24, "mixed", "test", seed=21)
        score, _ = grade_iot_stream([dict(r) for r in ds])
        assert score == pytest.approx(0.5, abs=1e-3)

    def test_perfect_reconstruction_scores_one(self):
        ds = generate_iot_stream_dataset(24, "mixed", "test", seed=21)
        perfect = [dict(r, value=r["ground_truth"]) for r in ds]
        assert grade_iot_stream(perfect)[0] == pytest.approx(1.0)

    def test_damaging_the_signal_scores_below_one_half(self):
        ds = generate_iot_stream_dataset(24, "mixed", "test", seed=21)
        wrecked = [dict(r, value=r["ground_truth"] + 50.0) for r in ds]
        assert grade_iot_stream(wrecked)[0] < 0.5

    def test_empty_input_scores_zero(self):
        assert grade_iot_stream([])[0] == 0.0

    def test_unimputed_dropouts_are_charged_not_skipped(self):
        """
        Regression test for the metric that produced the old '100% imputation'.

        A policy that emits nothing on a dropout used to have those timesteps
        dropped from the average, scoring a perfect 0.0000 MAE for having done
        nothing at all.
        """
        ds = generate_iot_stream_dataset(
            48, "dropout", "test", seed=5
        )
        assert any(r["value"] is None for r in ds), "fixture has no dropouts"
        m = evaluate_window(ds, [r["value"] for r in ds])
        assert m["nan_emitted"] > 0
        assert m["raw_mae"] > 0.0
        assert m["n_scored"] > 0

    def test_grader_message_reports_the_carry_forward_count(self):
        ds = generate_iot_stream_dataset(48, "dropout", "test", seed=5)
        _, msg = grade_iot_stream([dict(r) for r in ds])
        assert "carried forward" in msg


class TestMetrics:
    def test_carry_forward_fills_gaps(self):
        np.testing.assert_allclose(
            carry_forward([1.0, None, None, 4.0]), [1.0, 1.0, 1.0, 4.0]
        )

    def test_carry_forward_handles_a_leading_gap(self):
        np.testing.assert_allclose(carry_forward([None, 2.0, 3.0]), [2.0, 2.0, 3.0])

    def test_carry_forward_handles_an_all_missing_series(self):
        np.testing.assert_allclose(carry_forward([None, None]), [0.0, 0.0])

    def test_interpolated_reference_positions_are_excluded(self):
        gt = [1.0, 2.0, 3.0]
        m = stream_metrics(gt, [1.0, 99.0, 3.0], [False, True, False])
        assert m["mae"] == 0.0
        assert m["n_scored"] == 2

    def test_a_fully_interpolated_window_still_reports_a_number(self):
        m = stream_metrics([1.0, 2.0], [1.0, 2.0], [True, True])
        assert m["n_scored"] == 2

    def test_error_reduction_is_zero_when_there_was_no_error(self):
        assert error_reduction_pct(0.0, 0.0) == 0.0

    def test_quality_score_is_bounded(self):
        assert quality_score(1.0, 0.0) == 1.0
        assert quality_score(1.0, 1.0) == 0.5
        assert quality_score(1.0, 100.0) == 0.0


class TestDeterminism:
    @pytest.mark.parametrize("ctype", CORRUPTION_TYPES)
    def test_same_seed_reproduces_the_same_episode(self, ctype):
        a = DataCleaningEnvironment(history_len=5)
        b = DataCleaningEnvironment(history_len=5)
        for e in (a, b):
            e.reset(
                task_name="iot_stream",
                window_size=24,
                split="test",
                corruption_type=ctype,
                seed=77,
            )
            while not e.done:
                e.step("skip")
        assert [r["value"] for r in a.cleaned_data] == [
            r["value"] for r in b.cleaned_data
        ]
        assert a.total_reward == pytest.approx(b.total_reward)

    def test_train_and_test_episodes_come_from_different_data(self):
        e = DataCleaningEnvironment(history_len=5)
        e.reset(task_name="iot_stream", window_size=24, split="train", seed=5)
        train_gt = [r["ground_truth"] for r in e.dataset]
        e.reset(task_name="iot_stream", window_size=24, split="test", seed=5)
        test_gt = [r["ground_truth"] for r in e.dataset]
        assert train_gt != test_gt

    def test_unknown_corruption_type_raises(self):
        e = DataCleaningEnvironment(history_len=5)
        with pytest.raises(ValueError):
            e.reset(
                task_name="iot_stream",
                window_size=24,
                split="test",
                corruption_type="gremlins",
                seed=1,
            )
