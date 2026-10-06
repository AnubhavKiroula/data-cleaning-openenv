# RL-Cleanse — project context

Living state of the project. Read this first; it links out to the detailed
documents rather than repeating them.

| | |
|---|---|
| **Last updated** | 2026-10-06 |
| **Competition** | technIEEEks'26, Embedded Systems & IoT track |
| **Status** | Submission artifacts complete and frozen. Active work is an improvement experiment, not repair. |
| **Branches** | `main` (PR #28 merged 2026-09-29) · `feat/action-cost-reward` (in progress) |
| **CI** | Green. One workflow, `.github/workflows/ci.yml`. |
| **Tests** | 184 passing, CPU-only, ~8 s |

---

## 1. What this project is

A research system asking one question:

> Does a learned RL filtering policy outperform static rule-based filtering when
> correcting noisy sensor readings under an online, sequential constraint, where
> the agent sees one reading at a time and cannot access the full batch upfront?

### The use case

A field-deployed gas sensor node streams one reading per interval to an edge
controller. That stream is dirty: electromagnetic transients cause spikes,
chemical and thermal ageing causes calibration drift, wireless links drop
packets, and retry logic duplicates them. A controller acting on the stream
needs a corrected value **now**, from the reading in front of it plus whatever
little history fits in RAM.

That "now" is the whole difficulty. The strong classical denoisers — matrix
completion, autoencoders, batch KNN imputation, Kalman smoothing — all buffer
future samples before deciding about the present one. An edge node cannot.

### Why it is not a toy

The constraint turns out to be an **information barrier**, not an
inconvenience. At time *t* a single-sample spike and a genuine step change
produce the same innovation; they only separate at *t+1*, when one reverts and
the other persists. We measured the consequence: on this channel, **no finite
rejection threshold beats doing nothing** — a training-split sweep is monotone
out to z → ∞.

That is the gap a learned policy exploits. Its action space includes a *soft*
correction (`fix_type`, which moves a reading halfway to the rolling baseline),
so it can trade a little error on genuine readings for a lot on spikes **without
ever having to decide which is which**. A threshold filter has only
accept-or-reject available.

### History

The repository began as a full-stack web application for static tabular CSV
cleaning (React, FastAPI, PostgreSQL, Redis, Celery, Docker). It was pivoted to
this research project in September 2026, and the legacy stack was removed —
312 tracked files down to 50. See `docs/RESEARCH_PIVOT_MASTER_PLAN.md` §4 and §9.

---

## 2. What has been done

### Method

- **Dataset.** UCI Air Quality (De Vito et al., 2008): 9,357 real hourly
  readings from a chemical multisensor array on an Italian road. Target channel
  `CO(GT)`. Committed locally; **no network access at runtime, and nothing from
  HuggingFace.**
- **Sentinel handling.** Hardware faults are coded `-200` — 18.0% of `CO(GT)`.
  Resolved by interpolation to give a continuous reference, but the interpolated
  positions are **flagged and excluded from every metric**. Scoring there would
  measure agreement with `numpy.interp`, not with a sensor.
- **Splits.** Strictly chronological, no shuffling or k-fold: train 6,737 h,
  validation 748 h (model selection only), test 1,872 h (held out). The
  train/test boundary is at hour 7,485 as specified.
- **Faults injected.** Spikes, calibration drift, dropouts, duplicate packets,
  and a mixture.
- **MDP.** State ∈ ℝ¹⁹ from one packet plus five retained floats, every
  deviation divided by the rolling σ so the policy is **scale-relative**. Six
  discrete actions, semantics owned by the environment. Magnitude-aware bounded
  reward (master plan §2.3), a function of outcome only — never of the
  generator's fault label.
- **Algorithm.** Double DQN, 19→128→64→6 (11,206 params), Adam 3e-4, batch 64,
  γ 0.99, 800 epochs, 5 seeds. 83 s per seed on an RTX 4050; CPU fallback works.
- **Baseline.** Robust innovation gating with carry-forward imputation,
  hyperparameters grid-searched on the **training split** — the same tuning
  budget the agent gets. This is what stops it being a strawman.

### Result (held out, 30 windows × 24 h per family, 5 seeds)

| Method | Mean absolute MAE | Mean relative MAE |
|---|---:|---:|
| Do nothing (carry-forward) | 0.2170 | 1.000 |
| Rule filter, calibrated on train | 0.2170 | 1.000 |
| Rule filter, textbook z=4 | 0.4811 | 4.277 |
| **RL-Cleanse DQN** | **0.2002** | 1.082 |

**Answer: yes against rule-based filtering, qualified against inaction.**
RL-Cleanse beats both rule configurations, and neither rule configuration beats
doing nothing at all. Spike error reduction is **+30.6%** with a cross-seed std
of 0.0037.

The qualification: it **damages** the two families whose raw error was already
near zero — dropout (rel 1.507) and duplicate (rel 1.344) — so the equal-weight
relative aggregate is worse than inaction. Per window, 34% improve, 31% are
unchanged, **35% are damaged**.

Three negative findings are reported rather than smoothed over: no finite
threshold beats pass-through; validation did not predict test (0.9725 ± 0.0104
vs ~1.01); and the specified spike amplitude lands inside the channel's own
innovation envelope. Full detail in `docs/PROFESSOR_BRIEFING.md` §4.

### Engineering

- One shared metric implementation (`backend/ml/metrics.py`) that raw, baseline
  and RL all score through, so they cannot diverge.
- Two invariants enforced in code and asserted in the notebook: **no future
  access** and **no oracle leakage** (the generator's `ground_truth`,
  `fault_type`, `reference_imputed` and `is_corrupted` are stripped from the
  observation; the agent sees `{id, timestep, sensor, value}`).
- 184 tests, each regression guard asserting a specific past failure.
- `RL-Cleanse_demo.ipynb` executes top to bottom in CI with no GPU.

---

## 3. How to run it

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu   # or CUDA
pip install -e ".[dev]"

pytest tests/                                                  # 184 tests

python -m backend.ml.calibrate_baseline --num-windows 120      # tune baseline on train
python -m backend.ml.train_dqn --epochs 800 --seeds 1 2 3 4 5  # ~7 min on RTX 4050
python -m backend.ml.evaluate_benchmarks --num-windows 30      # the results table
python scripts/demo_window.py                                  # live demo, chosen window
python scripts/live_iot_inference.py --replay --steps 48       # streaming bridge
jupyter nbconvert --to notebook --execute --inplace RL-Cleanse_demo.ipynb
```

**For a demo, never use a random window.** With 35% of windows damaged a random
draw is close to a coin flip. `scripts/demo_window.py` defaults to the spike
window nearest the family median and prints the population statistics beside it;
`--pick` lists every candidate.

### Layout

```
backend/ml/     metrics, reward_shaper, dqn_model, experience_replay,
                rule_based_baseline, calibrate_baseline, sweep_action_cost,
                train_dqn, evaluate_benchmarks
data/           iot_data_loader.py + air_quality/AirQualityUCI.csv
envs/data_cleaning_env/   server/environment.py (action semantics live here),
                          tasks/graders.py, OpenEnv HTTP surface
scripts/        live_iot_inference.py, demo_window.py
tools/          build_notebook.py (the notebook is generated, not hand-edited)
```

---

## 4. In progress

**Action cost in the reward** (branch `feat/action-cost-reward`).

The published reward prices intervention at nothing — a policy pays only when a
correction makes things worse. That is why it over-corrects streams needing
nothing. `RewardShaper(action_cost=…)` charges a fixed penalty for any non-skip
action; the default 0.0 reproduces §2.3 exactly.

`backend/ml/sweep_action_cost.py` searches the cost **on validation**.

**Result (3 seeds × 400 epochs, validation only):**

| cost | 0.0 | 0.05 | 0.1 | 0.2 | **0.3** | 0.5 | 0.8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| val rel-MAE | 1.0155 | 0.9925 | 0.9511 | 0.9188 | **0.9156** | 0.9225 | 0.9446 |
| std | 0.0227 | 0.0481 | 0.0218 | 0.0051 | 0.0175 | 0.0078 | 0.0169 |

The curve **turns** — the minimum at 0.3 is an interior point, not a grid
boundary, so it is a real operating point rather than the degenerate "never act"
solution that a large enough cost would produce. The gap against the published
reward (+0.0999) is more than double the combined seed spread (0.0402).

This is a genuine improvement and it crosses below 1.0, meaning a priced policy
beats inaction on validation where the published one does not.

**Not yet adopted.** Remaining steps, in order:

1. Retrain 5 seeds at cost 0.3 for the full 800 epochs (~7 min on the RTX 4050).
2. Evaluate on test **once**, and report whatever it gives — including if the
   validation gain fails to transfer, which happened before (0.9725 validation
   vs ~1.01 test for the published policy).
3. If it holds, regenerate every artifact and update README, the briefing,
   master plan §6.2 and the notebook **together** — all four quote the numbers.

---

## 5. Known issues and limitations

- **Does not beat inaction uniformly.** The headline qualification above.
- **Validation generalises poorly to test.** Selecting the best of ~32
  validation evaluations is itself a selection bias.
- **High seed variance** — validation relative-MAE spans 0.93–1.08.
- **18% of the `CO(GT)` reference is interpolated.** Excluded from metrics, but
  the remainder is not pristine.
- **Reward skip tolerance is absolute (0.2 signal units)**, so the agent has no
  incentive to improve errors already below it. Even an oracle-greedy policy
  reaches only +9.1% on dropout for this reason.
- **Single dataset, single channel, single algorithm, five seeds.**
- **No hardware tested.** `docs/HARDWARE_SETUP.md` §0 is a per-component status
  table. The policy is trained on `CO(GT)`, **not MQ-135 output** — transfer is
  untested.
- **No Kalman-filter baseline.** A fair request; conceded in the briefing.

---

## 6. Decisions worth knowing

| Decision | Why |
|---|---|
| Validation split carved from the end of train | The original loop selected checkpoints by test-split MAE — model selection on held-out data. |
| Reward depends on outcome, never on the fault label | Gating on `fault_type` rewards matching an annotation, not improving the signal, and will not transfer. |
| Action semantics live in the environment | One definition each, unit-testable without an agent. |
| Epsilon decay derived from run length | The plan's literal 0.95/epoch hits the floor at epoch 76, so an 800-epoch run would explore for its first 10%. |
| Double DQN | Diagnosed, not preferred a priori: overestimation showed up as over-correction of clean streams. |
| Two baseline configurations reported | Calibrated alone looks like a missing run (it ties pass-through); textbook alone overstates the filter. |
| Both aggregates reported | Absolute and relative MAE disagree, and which matters depends on the deployment. |
| Scale-relative encoder | A 21-dim variant with absolute-magnitude features was tested and **rejected on validation** (0.997 vs 0.932). |

Deviations from the original blueprint are enumerated in
`docs/RESEARCH_PIVOT_MASTER_PLAN.md` §9, including four specifications kept
deliberately **despite being unfavourable to the results**.

---

## 7. Research-integrity record

Two rounds of invalid results occurred, and **neither was caught by reading
code** — both surfaced because two figures that should have agreed did not.

1. The original published table came from an agent that selected an
   unimplemented action on 110 of 120 steps and so never modified the signal.
   Its "RL MAE" equalled raw MAE on three of five families, which gave it away.
   Root cause: exploration was destroyed at epoch 10 of 40 by an evaluator that
   zeroed epsilon with nothing to restore it.
2. A later headline checkpoint was a 12-epoch **test artifact** scoring worse
   than inaction. The test suite called `train(save=False)`, but the
   best-checkpoint write sat outside the `save` guard, so every test run
   overwrote the published model. Caught when the demo script's per-window
   statistic contradicted the 5-seed analysis.

Six defects total, each with a named regression test asserting the specific
failure. `docs/PROFESSOR_BRIEFING.md` §7 has the full account.

**Working rules that follow from this**, and they are not optional here:

- Never tune or select on the test split.
- Compute at least one quantity two independent ways and assert they agree.
- Treat any two of your own numbers disagreeing as a defect to run down.
- Check whether tests write to paths the project reports.
- Never hand-type a result into a document that code can generate.

---

## 8. Documents

| File | Contents |
|---|---|
| `docs/PROFESSOR_BRIEFING.md` | The authoritative write-up: method, results, negative findings, limitations, integrity record, anticipated questions. |
| `docs/RESEARCH_PIVOT_MASTER_PLAN.md` | Original design blueprint, kept for provenance, with all implementation deviations recorded in §9. |
| `docs/HARDWARE_SETUP.md` | ESP32/MQ-135/DHT22 requisition, wiring, firmware, serial bridge. §0 states per-component status. |
| `docs/NEXT_STEPS.md` | Prioritised future work and the traps this project already fell into. |
| `README.md` | Short entry point: question, results table, quick start. |
| `RL-Cleanse_demo.ipynb` | Primary graded artifact. Every number computed at run time. |
