# Next steps

Written 2026-09-29, to pick this up after practicals and mid-semesters without
re-deriving context. The submission state is frozen and defensible as it
stands; everything here is improvement, not repair.

## Where things stand

The research pipeline is complete, tested and reproducible. `main`-ready on
`feat/iot-stream-denoising` (PR #28), CI green, 179 tests passing, notebook
executing top to bottom.

**The result, honestly stated.** RL-Cleanse beats rule-based filtering — mean
absolute MAE 0.2002 against 0.2170 (calibrated rule filter) and 0.4811
(textbook rule filter), and neither rule configuration beats doing nothing at
all. It does **not** beat inaction uniformly: it improves spike (+30.6%), mixed
(+8.4%) and drift (+5.2%), and damages dropout (−50.7%) and duplicate (−34.4%),
whose raw error was already near zero. Per window, 34% improve, 31% are
unchanged, 35% are damaged.

Full detail in `docs/PROFESSOR_BRIEFING.md`. Section 7 there records the six
defects found during the audit, the fifth and sixth of which were introduced by
the refactor itself and caught by consistency checks.

## The one change most likely to improve the result

**Add an action cost to the reward so the policy only acts when the expected
gain exceeds it.**

This is the direct remedy for the over-correction that costs dropout and
duplicate, and it is the reason the equal-weight relative aggregate (1.082)
comes out worse than inaction while absolute MAE (0.2002 vs 0.2170) comes out
better. The policy currently has no incentive to stay still on a stream that
needs nothing.

The change is small: in `backend/ml/reward_shaper.py`, subtract a constant
`ACTION_COST` from every non-skip reward. Then retrain — roughly 85 s per seed
on an RTX 4050, so about 7 minutes for five seeds:

```bash
python -m backend.ml.train_dqn --epochs 800 --seeds 1 2 3 4 5
python -m backend.ml.evaluate_benchmarks --num-windows 30
```

**Decide it on the validation split, not on test.** Sweep the cost over
something like {0.02, 0.05, 0.1, 0.2}, compare validation relative-MAE against
the current 0.9725 ± 0.0104, and adopt a value only if it wins there. If none
wins, that is a publishable ablation — record it and keep the current numbers.
Do not tune this on the test split; removing that exact mistake was most of the
repair work.

Expect the headline numbers to move if you adopt it. README,
`docs/PROFESSOR_BRIEFING.md`, `docs/RESEARCH_PIVOT_MASTER_PLAN.md` §6.2 and the
notebook all quote them, and all four must be updated together.

## Other work, in rough priority order

1. **Paired significance test** across seeds and windows, replacing comparison
   of means. With 35% of windows damaged, a mean difference of 0.017 needs a
   test before it can be called an effect. This is the cheapest credibility win
   available and needs no retraining.
2. **A Kalman-filter baseline.** The briefing already concedes this is a fair
   request and that its absence is a gap. It brackets the learned policy from
   the classical side.
3. **A spike-amplitude sweep.** The specified 2.5–4.0σ amplitude lands inside
   the channel's own innovation envelope (99th-percentile robust z of genuine
   innovations is 8.8, maximum 44), which caps what any causal method can do.
   Mapping where a threshold filter starts to earn its false-positive cost
   would turn a stated limitation into a measured curve.
4. **Compare against the acausal oracle.** Already instrumented: an
   oracle-greedy policy reaches 98.5% error reduction on spikes and 68% on
   drift. Reporting it quantifies what the online constraint actually costs,
   which is the project's central claim.
5. **A second sensor channel.** The encoder is scale-relative by construction
   and a unit test asserts the invariance, but cross-channel transfer is
   untested. `T` or `C6H6(GT)` carry only 3.9% sentinel values against CO(GT)'s
   18%, so either is a cleaner target.

## Hardware

Nothing has been run on physical hardware. `docs/HARDWARE_SETUP.md` §0 is a
per-component status table — keep it accurate as parts arrive, and do not let
"designed" drift into "verified" in the write-up.

One thing to plan for: the policy is trained on CO(GT) air-quality data, **not
MQ-135 output**, whose scale and noise characteristics differ. The
scale-relative encoder is the reason to expect some transfer, but it is
untested. `scripts/live_iot_inference.py --replay` exercises the whole bridge
without a board, so rehearse there before trusting a live demo.

## Traps worth remembering

- **Never tune on the test split.** The original results were invalid partly
  because checkpoints were selected by test-split MAE.
- **Check that a new number agrees with the old ones.** Both invalid-result
  episodes were caught by two figures disagreeing, not by reading code.
- **Watch for filesystem side effects in tests.** The test suite silently
  overwrote the published checkpoint for most of a day. Two regression tests now
  assert `train(save=False)` writes nothing; keep that property.
- **Scoring convention:** every method must emit a value at every timestep, and
  timesteps whose reference came from interpolating the `-200` sentinel are
  excluded. All of it lives in `backend/ml/metrics.py` — one implementation, so
  methods cannot be scored differently.
