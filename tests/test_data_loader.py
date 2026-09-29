"""
Tests for the UCI Air Quality loader and the synthetic fault injector.

Coverage targets the properties the research claim rests on: the split is
chronological and the published sizes, the ``-200`` sentinel is resolved and
*flagged*, window sampling covers the split and is reproducible, and each fault
family does what its name says.
"""

import numpy as np
import pandas as pd
import pytest

from data.iot_data_loader import (
    KEY_SENSOR_COLUMNS,
    SENTINEL_MISSING,
    SyntheticCorruptionInjector,
    UCIAirQualityLoader,
)


class TestLoading:
    def test_loads_published_row_count(self, loader):
        assert len(loader.df_clean) == 9357

    def test_all_key_sensor_columns_present(self, loader):
        for col in KEY_SENSOR_COLUMNS:
            assert col in loader.df_clean.columns

    def test_sentinel_values_are_resolved(self, loader):
        for col in KEY_SENSOR_COLUMNS:
            series = loader.df_clean[col]
            assert not series.isna().any(), f"{col} still has NaN"
            assert not (series == SENTINEL_MISSING).any(), f"{col} still has -200"

    def test_sentinel_positions_are_flagged_not_hidden(self, loader):
        """
        The interpolated positions must remain identifiable.

        Scoring a denoiser against an interpolated reference measures agreement
        with numpy.interp rather than with a sensor, so evaluation needs to be
        able to exclude these timesteps.
        """
        mask = loader.df_clean["CO(GT)__imputed"]
        assert mask.dtype == bool
        # CO(GT) carries 1,683 sentinel readings in the published dataset.
        assert mask.sum() == 1683

    def test_frame_is_cached_across_instances(self):
        from data.iot_data_loader import _FRAME_CACHE, clear_cache

        clear_cache()
        first = UCIAirQualityLoader()
        second = UCIAirQualityLoader()
        # Same object, not merely equal: reset() must not re-parse the CSV.
        assert first.df_clean is second.df_clean
        assert len(_FRAME_CACHE) == 1

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            UCIAirQualityLoader(csv_path="does/not/exist.csv")


class TestChronologicalSplit:
    def test_published_split_sizes(self, loader):
        train, test = loader.get_chronological_split(train_ratio=0.8, val_ratio=0.0)
        assert len(train) == 7485
        assert len(test) == 1872
        assert len(train) + len(test) == 9357

    def test_validation_is_carved_from_training_region(self, loader):
        train, test = loader.get_chronological_split(train_ratio=0.8, val_ratio=0.1)
        # The test split must be untouched by reserving validation data.
        assert len(test) == 1872
        assert len(train) + len(loader.val_df) == 7485

    def test_splits_are_contiguous_and_ordered(self, loader):
        loader.get_chronological_split(train_ratio=0.8, val_ratio=0.1)
        full = loader.df_clean["CO(GT)"].to_numpy()
        joined = np.concatenate(
            [
                loader.train_df["CO(GT)"].to_numpy(),
                loader.val_df["CO(GT)"].to_numpy(),
                loader.test_df["CO(GT)"].to_numpy(),
            ]
        )
        # Reassembling the splits in order must reproduce the original series:
        # this fails if anything shuffles or overlaps.
        np.testing.assert_allclose(joined, full)

    def test_no_shared_timestamps_between_splits(self, loader):
        loader.get_chronological_split(train_ratio=0.8, val_ratio=0.1)
        keys = [
            set(zip(df["Date"], df["Time"]))
            for df in (loader.train_df, loader.val_df, loader.test_df)
        ]
        assert not keys[0] & keys[2]
        assert not keys[0] & keys[1]
        assert not keys[1] & keys[2]

    def test_get_split_rejects_unknown_name(self, loader):
        with pytest.raises(ValueError):
            loader.get_split("holdout")


class TestFaultInjection:
    @pytest.fixture
    def signal(self):
        # A smooth ramp with curvature: no fault family should be confusable
        # with the underlying trend.
        t = np.arange(48, dtype=float)
        return 10.0 + 2.0 * np.sin(t / 6.0) + 0.05 * t

    def test_spikes_shift_only_flagged_positions(self, signal):
        inj = SyntheticCorruptionInjector(seed=3)
        out, mask = inj.inject_spikes(signal, prob=0.2)
        np.testing.assert_allclose(out[~mask], signal[~mask])
        assert mask.sum() > 0
        assert np.all(np.abs(out[mask] - signal[mask]) > 0)

    def test_spike_amplitude_respects_configured_scale(self, signal):
        inj = SyntheticCorruptionInjector(seed=3)
        out, mask = inj.inject_spikes(signal, prob=0.5, magnitude_scale=4.0)
        sigma = np.std(signal)
        amp = np.abs(out[mask] - signal[mask]) / sigma
        assert amp.min() >= 2.5 - 1e-6
        assert amp.max() <= 4.0 + 1e-6

    def test_drift_is_a_contiguous_monotone_ramp(self, signal):
        inj = SyntheticCorruptionInjector(seed=5)
        out, mask = inj.inject_drift(signal, window_len=12)
        idx = np.flatnonzero(mask)
        assert idx.size > 0
        # Contiguous.
        assert np.array_equal(idx, np.arange(idx[0], idx[-1] + 1))
        offset = out[mask] - signal[mask]
        # A calibration ramp grows monotonically from zero.
        assert abs(offset[0]) < 1e-9
        assert np.all(np.diff(offset) > 0) or np.all(np.diff(offset) < 0)

    def test_dropouts_are_nan_runs_and_never_hit_the_first_sample(self, signal):
        inj = SyntheticCorruptionInjector(seed=7)
        out, mask = inj.inject_dropouts(signal, prob=0.3, max_gap=4)
        assert mask.sum() > 0
        assert np.array_equal(np.isnan(out), mask)
        # A stream whose very first sample is absent is a cold-start problem,
        # not a denoising problem.
        assert not mask[0]

    def test_duplicates_repeat_the_previous_reading(self, signal):
        inj = SyntheticCorruptionInjector(seed=11)
        out, mask = inj.inject_duplicates(signal, prob=0.3)
        assert mask.sum() > 0
        for i in np.flatnonzero(mask):
            assert out[i] == out[i - 1]

    def test_mixed_applies_several_families(self, signal):
        inj = SyntheticCorruptionInjector(seed=13)
        res = inj.corrupt_window(signal, corruption_type="mixed")
        active = [k for k, m in res["masks"].items() if m.any()]
        assert len(active) >= 3

    def test_none_is_a_true_passthrough(self, signal):
        inj = SyntheticCorruptionInjector(seed=13)
        res = inj.corrupt_window(signal, corruption_type="none")
        np.testing.assert_allclose(res["corrupted"], signal)
        assert not any(m.any() for m in res["masks"].values())

    def test_unknown_corruption_type_raises(self, signal):
        inj = SyntheticCorruptionInjector(seed=1)
        with pytest.raises(ValueError):
            inj.corrupt_window(signal, corruption_type="cosmic_rays")

    def test_ground_truth_is_never_mutated(self, signal):
        original = signal.copy()
        inj = SyntheticCorruptionInjector(seed=17)
        res = inj.corrupt_window(signal, corruption_type="mixed")
        np.testing.assert_allclose(signal, original)
        np.testing.assert_allclose(res["ground_truth"], original)

    @pytest.mark.parametrize(
        "ctype", ["spike", "drift", "dropout", "duplicate", "mixed"]
    )
    def test_same_seed_reproduces_identical_corruption(self, signal, ctype):
        a = SyntheticCorruptionInjector(seed=99).corrupt_window(signal, ctype)
        b = SyntheticCorruptionInjector(seed=99).corrupt_window(signal, ctype)
        np.testing.assert_allclose(a["corrupted"], b["corrupted"], equal_nan=True)

    def test_different_seeds_differ(self, signal):
        a = SyntheticCorruptionInjector(seed=1).corrupt_window(signal, "mixed")
        b = SyntheticCorruptionInjector(seed=2).corrupt_window(signal, "mixed")
        assert not np.allclose(
            np.nan_to_num(a["corrupted"]), np.nan_to_num(b["corrupted"])
        )

    def test_short_window_degrades_gracefully(self):
        inj = SyntheticCorruptionInjector(seed=1)
        tiny = np.array([1.0, 2.0])
        out, mask = inj.inject_drift(tiny)
        np.testing.assert_allclose(out, tiny)
        assert not mask.any()


class TestWindowSampling:
    def test_returns_requested_length(self, loader):
        from data.iot_data_loader import sample_window

        train, _ = loader.get_chronological_split()
        _, gt, imp = sample_window(
            train, "CO(GT)", 24, np.random.RandomState(0)
        )
        assert gt.shape == (24,)
        assert imp.shape == (24,)

    def test_covers_the_whole_split(self, loader):
        """
        Regression test for window starvation.

        A previous revision computed the start index as ``seed % max_start``
        with ``seed = epoch * 17``, so a 40-epoch run only ever saw the first
        680 hours of a 7,485-hour split.
        """
        from data.iot_data_loader import sample_window

        train, _ = loader.get_chronological_split()
        starts = [
            sample_window(train, "CO(GT)", 24, np.random.RandomState(s))[0]
            for s in range(300)
        ]
        assert len(set(starts)) > 200
        assert max(starts) > 0.8 * (len(train) - 24)

    def test_is_reproducible_from_seed(self, loader):
        from data.iot_data_loader import sample_window

        train, _ = loader.get_chronological_split()
        a = sample_window(train, "CO(GT)", 24, np.random.RandomState(42))
        b = sample_window(train, "CO(GT)", 24, np.random.RandomState(42))
        assert a[0] == b[0]
        np.testing.assert_allclose(a[1], b[1])

    def test_prefers_windows_backed_by_real_measurements(self, loader):
        from data.iot_data_loader import sample_window

        train, _ = loader.get_chronological_split()
        fractions = [
            1.0 - sample_window(train, "CO(GT)", 24, np.random.RandomState(s))[2].mean()
            for s in range(60)
        ]
        # The sampler rejects windows that are mostly interpolated reference.
        assert np.mean(fractions) > 0.9

    def test_window_longer_than_split_raises(self, loader):
        from data.iot_data_loader import sample_window

        tiny = loader.df_clean.iloc[:10]
        with pytest.raises(ValueError):
            sample_window(tiny, "CO(GT)", 24, np.random.RandomState(0))
