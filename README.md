# RL-Cleanse

**Reinforcement learning for online denoising of noisy IoT sensor streams.**

A research project for technIEEEks'26 (Embedded Systems & IoT). The question:

> Does a learned RL filtering policy outperform static rule-based filtering when
> correcting noisy sensor readings under an online, sequential constraint, where
> the agent sees one reading at a time and cannot access the full batch upfront?

A DQN agent steps through a real sensor stream one reading at a time, choosing
one of six corrective actions from the current packet plus five retained values.
It never sees a future sample and never sees the reference signal.

- **Dataset:** UCI Air Quality — 9,357 real hourly readings from a chemical
  multisensor array deployed at road level in an Italian city (De Vito et al.,
  2008). Target channel `CO(GT)`.
- **Faults:** electrical spikes, calibration drift, transmission dropouts,
  duplicate packets, and a mixture.
- **Baseline:** a robust streaming filter under the identical constraint, with
  its hyperparameters grid-searched on the training split — the same tuning
  budget the agent gets.

---

## Results

30 held-out test windows of 24 hours per fault family, identical window seeds
for every method, aggregated over 5 independently trained seeds.

| Fault family | Do-nothing MAE | Rule(cal) MAE | Rule(txt) MAE | RL MAE | RL std | RL rel | RL reduction |
|---|---:|---:|---:|---:|---:|---:|---:|
| Electrical spike | 0.2317 | 0.2317 | 0.4795 | **0.1608** | 0.0037 | **0.694** | **+30.6%** |
| Calibration drift | 0.2743 | 0.2743 | 0.5351 | **0.2600** | 0.0015 | **0.948** | +5.2% |
| Transmission dropout | **0.0627** | 0.0627 | 0.2861 | 0.0946 | 0.0018 | 1.507 | −50.7% |
| Duplicate packet | **0.0299** | 0.0299 | 0.3351 | 0.0401 | 0.0036 | 1.344 | −34.4% |
| Mixed real-world | 0.4863 | 0.4863 | 0.7697 | **0.4457** | 0.0126 | **0.916** | +8.4% |
| **Mean** | **0.2170** | 0.2170 | 0.4811 | **0.2002** | — | 1.082 | — |

`Rule(cal)` is grid-searched on the training split; `Rule(txt)` is the
conventional Hampel cut-off z=4. `rel` is method MAE divided by that family's
own do-nothing MAE, so 1.000 means no improvement.

**Answer: yes against rule-based filtering, with one qualification.** RL-Cleanse
reduces mean absolute error below every rule configuration (0.2002 vs 0.2170 and
0.4811), and **neither rule configuration improves on doing nothing at all**. It
removes 30.6% of the spike-family error with a cross-seed standard deviation of
0.0037. The qualification: it over-corrects the two families whose raw error was
already near zero, so an equal-weight relative aggregate comes out at 1.082 —
slightly worse than inaction.

Three findings worth reading before the headline:

1. **No finite rejection threshold beats pass-through on this channel.** The
   training-split sweep is monotone out to z → ∞. At time *t* a single-sample
   spike and a genuine step change produce the same innovation; they separate
   only at *t+1*, which a causal filter does not have. The learned policy wins by
   never making that decision — it uses a *soft* correction instead.
2. **Validation did not predict test.** 0.9725 ± 0.0104 on validation, ~1.01 on
   held-out test. Selecting the best of ~32 validation evaluations is itself a
   selection bias.
3. **The specified spike amplitude is marginal for this channel.** Injected
   spikes land inside the signal's own innovation envelope. The amplitudes were
   kept as specified rather than raised.

Full discussion, including three negative results and every limitation:
**[`docs/PROFESSOR_BRIEFING.md`](docs/PROFESSOR_BRIEFING.md)**.

---

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu   # or a CUDA build
pip install -e ".[dev]"

# Tests (CPU, a few seconds)
pytest tests/test_data_loader.py tests/test_iot_env.py tests/test_dqn_training.py

# The primary artifact — executes top to bottom, no GPU needed
jupyter nbconvert --to notebook --execute --inplace RL-Cleanse_demo.ipynb
```

### Reproducing the results

```bash
python -m backend.ml.calibrate_baseline --num-windows 120        # tune the baseline on train
python -m backend.ml.train_dqn --epochs 800 --seeds 1 2 3 4 5    # ~7 min on an RTX 4050
python -m backend.ml.evaluate_benchmarks --num-windows 30        # the table above
python scripts/live_iot_inference.py --replay --steps 48          # streaming bridge, no hardware
```

CUDA is auto-detected with an unchanged CPU fallback. Tests, CI and the notebook
are all CPU-only.

---

## Layout

```
backend/ml/
  dqn_model.py             DQN policy: Q-network, epsilon-greedy, state encoder
  experience_replay.py     Seeded circular replay buffer
  reward_shaper.py         Magnitude-aware reward (master plan §2.3)
  rule_based_baseline.py   Rule filter under the same online constraint
  calibrate_baseline.py    Training-split grid search for the baseline
  metrics.py               The single metric implementation every method uses
  train_dqn.py             Training pipeline, validation-based selection
  evaluate_benchmarks.py   Benchmark table and plots

data/
  iot_data_loader.py       UCI loader, chronological splits, fault injection
  air_quality/             The dataset

envs/data_cleaning_env/
  server/environment.py    Streaming environment; owns the action semantics
  tasks/graders.py         The iot_stream task and its grader
  client.py, server/app.py OpenEnv HTTP surface (optional, needs `.[serve]`)

tests/                     test_data_loader.py, test_iot_env.py, test_dqn_training.py
docs/                      PROFESSOR_BRIEFING.md, HARDWARE_SETUP.md, RESEARCH_PIVOT_MASTER_PLAN.md
scripts/live_iot_inference.py   Serial/replay inference bridge
tools/build_notebook.py    Regenerates the demo notebook
RL-Cleanse_demo.ipynb      Primary graded artifact
```

---

## Design notes

Three properties are enforced in code rather than by convention, because each
was violated by an earlier revision of this repository:

- **No future access.** The observation at step *t* is built from `dataset[t]`
  and from values the agent has already emitted. Asserted over full episodes.
- **No oracle leakage.** The task generator's `ground_truth`, `fault_type`,
  `reference_imputed` and `is_corrupted` annotations are stripped before the
  observation is returned. The agent sees `{id, timestep, sensor, value}`.
- **One metric implementation.** Raw, baseline and RL all score through
  `backend/ml/metrics.py`. An un-imputed dropout is charged for, not filtered out
  of the average.

`docs/PROFESSOR_BRIEFING.md` section 7 documents the five defects that
invalidated the first set of results, and the regression tests that now guard
each one.

**No physical hardware has been tested.** `docs/HARDWARE_SETUP.md` section 0 is a
per-component table of what is implemented, designed, simulated or planned.

---

## Status

The repository still contains the legacy full-stack application it was pivoted
from (`frontend/`, `redis/`, `infra/`, the FastAPI/Celery/Alembic backend, Docker
and Render configuration, and the legacy `tests/test_api.py`,
`test_celery.py`, `test_database.py`, `test_monitoring.py`, `test_agents.py`,
`test_dqn.py`). None of it is imported by the research pipeline, and CI does not
run it. Removal is pending.

## License

MIT
