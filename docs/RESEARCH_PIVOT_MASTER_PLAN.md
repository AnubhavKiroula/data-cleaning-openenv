# RL-Cleanse: Research Pivot, Repository Refactoring, & CI/CD Master Blueprint

> ## Status: this is the original design blueprint, not a results document
>
> This file records the *plan* as written before implementation. It is kept for
> provenance. Two kinds of content in it are now superseded:
>
> * **The benchmark table in section 6.2 was never produced by a valid
>   experiment.** It is preserved below, struck through, with the measured
>   numbers beside it. `docs/PROFESSOR_BRIEFING.md` section 4 is the
>   authoritative results document, and `python -m backend.ml.evaluate_benchmarks`
>   regenerates it from scratch.
> * **Several specifications were mis-calibrated and were changed deliberately.**
>   Each change is listed in "Implementation deviations" at the end of this file,
>   with the reason. Nothing was changed silently.

**Project Name:** RL-Cleanse  
**Competition Track:** technIEEEks'26 — Embedded Systems & IoT Track  
**Submission Deadline:** October 5, 2026  
**Primary Target Artifacts:**
1. Standalone Executable Notebook: `RL-Cleanse_demo.ipynb`
2. Trained Model Weights: `models/dqn_iot_stream_best.pt`
3. Research Briefing Paper: `docs/PROFESSOR_BRIEFING.md`
4. Hardware & Simulation Spec: `docs/HARDWARE_SETUP.md`
5. Green, Passing CI/CD Pipeline: `.github/workflows/ci.yml`

---

## 1. Executive Summary & Research Pivot

### 1.1 The Pivot Context
- **Previous Architecture (Legacy):** A full-stack web application for static tabular CSV data cleaning (cleaning employee/HR records), including React 18, FastAPI, PostgreSQL, Redis, Celery, Alembic migrations, Docker containers, and Render/HuggingFace deployment scripts.
- **New Purpose (Research Paper):** An academic, real-time reinforcement learning system investigating sequential, online IoT sensor-stream telemetry denoising under strict single-step real-time constraints.

### 1.2 Core Research Question
> **"Does a learned RL cleaning/filtering policy outperform static rule-based filtering when correcting noisy sensor readings under an online/sequential (real-time) constraint, where the agent sees one reading at a time and cannot access the full batch upfront?"**

### 1.3 Academic Novelty Claim
1. **Online/Streaming Constraint:** Offline ML approaches (matrix completion, autoencoders, batch KNN) require buffering future data ($t+1 \dots T$). RL-Cleanse operates with $O(1)$ streaming latency at step $t$ using rolling historical buffers ($N=5$).
2. **Magnitude-Aware Reward Function:** Unlike tabular data cleaning agents that receive flat rewards per action, RL-Cleanse scales rewards dynamically based on instantaneous error reduction ($|y_{\text{corrupt}} - y^*| - |y_{\text{clean}} - y^*|$), preventing signal attenuation and penalizing false positives.
3. ~~**Robustness to Sensor Drift:** ... the RL agent successfully learns drift trajectory dynamics ...~~
   **NOT SUPPORTED.** Measurement gives the agent a 5.2% drift-family error
   reduction — real but modest, and far from "learns drift trajectory dynamics".
   The half of the claim about classical filters does hold: a median/MAD test
   cannot detect a ramp, because the reading and its own neighbourhood move
   together. The supported novelty claim is different and is stated in
   `docs/PROFESSOR_BRIEFING.md` section 1: a *soft* correction beats a hard
   threshold on transients, because under a causal constraint a spike and a step
   change are not distinguishable at time $t$ at all.

---

## 2. Mathematical Formulation (MDP)

The sequential denoising problem is formulated as a discrete-time Markov Decision Process:
$$\mathcal{M} = \langle \mathcal{S}, \mathcal{A}, \mathcal{P}, \mathcal{R}, \gamma \rangle$$

### 2.1 State Space $\mathcal{S} \subset \mathbb{R}^{50}$
At timestep $t$, the state vector $\mathbf{s}_t$ captures instantaneous readings and rolling temporal context:
- **Instantaneous Signal:** Current reading $y_t$, missingness indicator $m_t \in \{0, 1\}$.
- **Rolling Statistics (over window $N=5$):** Mean $\mu_t$, Standard Deviation $\sigma_t$, Median $\tilde{y}_t$.
- **Relative Dynamics:** Deviation $\delta_t = y_t - \mu_t$, Z-score $z_t = \frac{|y_t - \mu_t|}{\sigma_t + \epsilon}$, Rate of Change $\Delta y_t = y_t - y_{t-1}$.
- **Temporal Context:** Normalized episode timestep $\tau_t = \frac{t \pmod{24}}{24}$, Rolling buffer $[y_{t-1}, y_{t-2}, y_{t-3}, y_{t-4}, y_{t-5}]$.
- **Fault Detection Flags:** Binary indicators for detected spikes, drift, dropouts, and duplicates.

### 2.2 Action Space $\mathcal{A}$
The discrete action space preserves the original OpenEnv interface:
- $a_0 = \text{skip}$: Retain current reading ($y_t^{\text{clean}} = y_t$).
- $a_1 = \text{remove\_outlier}$: Replace high-amplitude spike with rolling median ($\tilde{y}_t$).
- $a_2 = \text{fill\_missing}$: Impute dropout using rolling median/mean.
- $a_3 = \text{fix\_type}$: Recalibrate sensor drift ($0.5 y_t + 0.5 \mu_t$).
- $a_4 = \text{remove\_duplicate}$: Drop repeated packet transmission and extrapolate trend ($y_{t-1} + \Delta y_{t-1}$).
- $a_5 = \text{fix\_category}$: Normalization fallback.

### 2.3 Magnitude-Aware Reward Shaping $\mathcal{R}$
$$R_t = \begin{cases}
R_{\text{base}} + \min(0.45, 0.2 \cdot (|y_t - y_t^*| - |y_t^{\text{clean}} - y_t^*|)) & \text{if error is reduced} \\
-0.15 - \min(0.35, 0.2 \cdot (|y_t^{\text{clean}} - y_t^*| - |y_t - y_t^*|)) & \text{if error is increased (false correction)} \\
+0.15 & \text{if action is skip and } |y_t - y_t^*| < 0.2
\end{cases}$$

---

## 3. Dataset Engineering & Scaling Pipeline

### 3.1 Primary Dataset: UCI Air Quality (9,357 Hourly Instances)
- **Origin:** Real chemical multisensor array deployed on-field in an Italian city (March 2004 – April 2005).
- **Target Channels:** `CO(GT)`, `PT08.S1(CO)`, `NMHC(GT)`, `C6H6(GT)`, `PT08.S2(NMHC)`, `NOx(GT)`, `PT08.S3(NOx)`, `NO2(GT)`, `PT08.S4(NO2)`, `PT08.S5(O3)`, Temperature (`T`), Relative Humidity (`RH`), Absolute Humidity (`AH`).
- **Sentinel Handling:** Hardware faults encoded as `-200` are replaced with linear spline interpolation for the nominal ground-truth reference baseline.

### 3.2 Chronological Splitting Protocol
- **Training Set (80%):** First 7,485 contiguous hours.
- **Testing Set (20%):** Final 1,872 contiguous hours held-out.
- **Strict Rule:** No random shuffling or standard k-fold cross-validation. Only chronological splits (or Purged Group TimeSeriesSplit) are valid for streaming time-series claims.

### 3.3 Synthetic IoT Fault Injection Engine
Implemented in `data/iot_data_loader.py`:
1. **Spikes:** Random amplitude bursts ($2.5\sigma$ to $4.0\sigma$) simulating electrical / electromagnetic transient noise.
2. **Drift:** Cumulative linear/random-walk ramp over a window of length 12 simulating chemical sensor degradation and thermal calibration loss.
3. **Dropouts:** Contiguous missing sequences (1 to 4 steps) simulating wireless packet drops.
4. **Duplicate Transmissions:** Direct repeats of previous timestep values simulating network retry glitching.

---

## 4. Repository Cleanup Plan: Removing Legacy Bloat

The base repository currently contains significant full-stack scaffolding that is completely unnecessary for your ML research submission and causes CI failures.

### 4.1 What to Remove / Deprecate

> **Completed.** The removal was carried out across commits a118829..bd8a71a,
> taking the repository from 312 tracked files to 50. Generated artifacts and
> local data (`graphify-out/`, `data/uploads/`, pre-pivot checkpoints, reports
> and plots, the SQLite database) were untracked with `git rm --cached` rather
> than deleted from disk. One item turned out to matter more than bloat: the
> root-level `server/` and `tasks/` directories shadowed
> `envs/data_cleaning_env/` on `sys.path` and had already broken an import.
```
[DELETE / REMOVE]
├── frontend/                     # React 18 UI, Vite, Tailwind, node_modules (Not evaluated)
├── redis/                        # Redis configuration & Dockerfiles
├── infra/                        # Old cloud deployment terraform / scripts
├── backend/
│   ├── alembic/                  # Database migration files
│   ├── alembic.ini
│   ├── celery_app.py             # Celery distributed worker tasks
│   ├── database.py               # SQLAlchemy SQLite/Postgres connection logic
│   ├── models.py                 # SQL tabular models (User, Dataset, Row)
│   ├── api/                      # REST endpoints for web upload/download
│   └── monitoring.py             # Prometheus metrics endpoints
├── Dockerfile                    # Legacy web server container
├── docker-compose*.yml           # Multi-container orchestration
├── render.yaml                   # Cloud PaaS deployment configuration
├── data_cleaning.db              # SQLite binary database
└── package.json / package-lock   # Root NPM lockfiles
```

### 4.2 Target Streamlined Research Directory Structure
```
data-cleaning-openenv/
├── backend/
│   └── ml/
│       ├── __init__.py
│       ├── dqn_model.py          # PyTorch QNetwork & DQNAgent with rolling context
│       ├── experience_replay.py  # Circular ReplayBuffer for RL transitions
│       ├── reward_shaper.py      # Magnitude-aware reward calculation
│       ├── rule_based_baseline.py# Z-score and carry-forward streaming filter
│       ├── train_dqn.py          # GPU-accelerated training pipeline
│       └── evaluate_benchmarks.py# Comparison table & plot generator
├── data/
│   ├── air_quality/
│   │   └── AirQualityUCI.csv     # 9,357 instances raw benchmark data
│   └── iot_data_loader.py        # Semicolon loader, split & fault injection
├── envs/
│   └── data_cleaning_env/
│       ├── client.py
│       ├── server/
│       │   └── environment.py    # Streaming episode window (k=24) + history (N=5)
│       └── tasks/
│           └── graders.py        # iot_stream task definition & MAE/RMSE grader
├── models/
│   ├── dqn_iot_stream_best.pt    # Best checkpoint evaluated on test split
│   ├── dqn_iot_stream_final.pt   # Final epoch checkpoint
│   └── dqn_iot_stream_metrics.json
├── plots/
│   ├── baseline_vs_rl_comparison.png
│   ├── denoising_before_after.png
│   └── dqn_iot_training_curves.png
├── docs/
│   ├── PROFESSOR_BRIEFING.md     # Academic briefing for faculty/reviewers
│   ├── HARDWARE_SETUP.md         # ESP32 requisition, schematics, and simulation
│   └── RESEARCH_PIVOT_MASTER_PLAN.md # This blueprint
├── tests/
│   ├── test_data_loader.py       # Data loader & corruption unit tests
│   ├── test_iot_env.py           # Streaming environment & grader tests
│   └── test_dqn_training.py      # Model forward pass & training loop tests
├── .github/
│   └── workflows/
│       └── ci.yml                # Clean, single-job Python 3.11 test workflow
├── RL-Cleanse_demo.ipynb         # Master graded notebook (100% self-contained)
├── pyproject.toml                # UV / Pip build configuration
└── .gitignore
```

---

## 5. Fixing the Failing CI/CD Pipeline

### 5.1 Why CI is Currently Failing
The current `.github/workflows/ci.yml` attempts to:
1. Run `pip install -r backend/requirements.txt` (which depends on legacy database/web packages).
2. Run `alembic upgrade --sql head` (which expects database migration schemas).
3. Run `npm run type-check` and `npm run test` inside `frontend/` (which fails on Node/NPM dependencies).
4. Run legacy `tests/test_api.py`, `tests/test_celery.py`, `tests/test_database.py` (which fail without Redis and Postgres).

### 5.2 The Clean Research CI Pipeline (`.github/workflows/ci.yml`)
Replace `.github/workflows/ci.yml` with a dedicated, lightweight ML testing workflow:

```yaml
name: Research ML CI

on:
  push:
    branches: [main, feat/*, "Phase-*"]
  pull_request:
    branches: [main]

jobs:
  test-ml-pipeline:
    name: Test ML Core & Streaming Environment (Python 3.11)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install torch --index-url https://download.pytorch.org/whl/cpu
          pip install pandas numpy matplotlib scipy tqdm requests tabulate jupyter nbconvert

      - name: Run ML Unit Tests
        env:
          PYTHONPATH: ${{ github.workspace }}
        run: |
          pytest -v tests/test_data_loader.py tests/test_iot_env.py tests/test_dqn_training.py

      - name: Validate Demo Notebook Headless Execution
        run: |
          jupyter nbconvert --to notebook --execute --inplace RL-Cleanse_demo.ipynb
```

---

## 6. Model Training & Validation Protocol

### 6.1 Hyperparameter Specifications
| Hyperparameter | Value | Rationale |
|:---|:---:|:---|
| **Epochs (Sweet Spot)** | **200 – 500** | 7,485 training hours = ~311 daily windows. Gives full exploration decay without Q-value overestimation. |
| **Batch Size** | **64** | Balances stochastic gradient noise with vectorized tensor throughput on RTX 4050. |
| **Learning Rate** | **3e-4** | Standard Adam learning rate for DQN stability. |
| **Discount Factor ($\gamma$)** | **0.99** | Values future temporal continuity across the 24-hour episode window. |
| **Epsilon Schedule** | **$1.0 \to 0.02$** | Smooth decay over epochs ($\text{decay} = 0.95$). |
| **Target Update Frequency** | Every 5 epochs | Stabilizes Bellman temporal difference targets. |
| **Replay Buffer Capacity** | 10,000 | Stores transitions across multiple diverse window permutations. |

### 6.2 Benchmark results

> **The table originally in this section was invalid and has been replaced.**
> It reported +19.9% error reduction on spikes, "100% imputation" on dropouts,
> and baseline MAE of 0.55–0.69. Audit found that the evaluated agent selected
> an unimplemented action on 110 of 120 steps and therefore never modified the
> signal; that un-imputed dropouts were filtered out of the MAE average, so
> emitting nothing scored a perfect 0.0000; and that the baseline fed its own
> replacements back into its history buffer, scoring 0.208 MAE on *perfectly
> clean* input. `docs/PROFESSOR_BRIEFING.md` section 7 documents all five root
> causes and the regression tests that now guard them.

**Measured results.** 30 held-out test windows of 24 hours per fault family,
identical window seeds for every method, 5 independently trained seeds.
Regenerate with `python -m backend.ml.evaluate_benchmarks --num-windows 30`.

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

**Headline.** RL-Cleanse beats both rule configurations on mean absolute MAE
(0.2002 vs 0.2170 and 0.4811), and neither rule configuration improves on doing
nothing at all. It does **not** beat inaction uniformly: it over-corrects the two
families whose raw error was already near zero, so the equal-weight relative
aggregate is 1.082. Both aggregates are reported everywhere.

**Three negative findings that the original plan did not anticipate**, detailed
in the briefing section 4.3:

1. No finite rejection threshold beats pass-through on this channel. The
   training-split sweep is monotone to z → ∞.
2. Validation did not predict test: 0.9725 ± 0.0104 on validation, ~1.01 on
   test.
3. The specified 2.5–4.0σ spike amplitude lands inside the channel's own
   innovation envelope (99th-percentile robust z of genuine innovations = 8.8),
   so the faults are inherently hard to separate from the signal. The specified
   amplitudes were kept rather than raised.

---

## 7. Graded Notebook Specification (`RL-Cleanse_demo.ipynb`)

The notebook is the primary graded deliverable. It must execute cleanly top-to-bottom and follow this 9-part academic structure:

1. **Title & Problem Statement:** Explains the real-world edge IoT anomaly problem and states the research question.
2. **Dataset Preprocessing:** Loads `AirQualityUCI.csv`, details the `-200` sentinel handling, performs the 80/20 chronological split, and plots synthetic corruption examples.
3. **Environment Setup:** Imports `DataCleaningEnvironment`, instantiates `iot_stream`, and demonstrates observation buffers ($N=5$).
4. **Baseline Rule Filter:** Implements the forward-fill and rolling Z-score filter, benchmarks it on 30 test windows, and displays baseline metrics.
5. **DQN Training Loop:** Instantiates `DQNAgent`, runs/loads checkpoints on GPU, and plots the training reward curve and epsilon decay schedule inline.
6. **Agent Test Split Evaluation:** Evaluates the RL agent on the identical 30 test windows across all 5 fault conditions.
7. **Comparative Results:** Displays the Pandas markdown table and side-by-side bar chart (`plots/baseline_vs_rl_comparison.png`).
8. **Signal Visualization:** Plots Ground Truth vs. Corrupted vs. Rule Cleaned vs. RL Cleaned signals for a 24-hour test window.
9. **Academic Conclusion:** 4-5 concise sentences summarizing the empirical findings, drift robustness, and microcontroller edge feasibility.

---

## 8. Physical Hardware Demo Scope

Full specification is maintained in `docs/HARDWARE_SETUP.md`:
- **Hardware Requisition:** ESP32 NodeMCU, MQ-135 Gas Sensor, DHT22 Temperature/Humidity Sensor, Breadboard, Jumper Wires, Micro-USB cable.
- **Simulation:** *Planned.* No Wokwi or Tinkercad run is recorded in this repository, so no simulation result is claimed. See `docs/HARDWARE_SETUP.md` section 0 for the per-component status table.
- **Firmware:** ESP32 C++ sketch streaming formatted JSON telemetry (`{"timestep": t, "sensor": "CO(GT)", "value": 2.45}`) over UART Serial at 115200 baud.
- **Laptop Real-Time Bridge:** `scripts/live_iot_inference.py` — **implemented, replay-tested only.** Runs end to end from the UCI test split via `--replay`; its serial path has never been connected to a board. Host-CPU inference measures 0.25 ms mean / 0.36 ms p95. No ESP32 latency figure is claimed.

---

## 9. Implementation deviations from this blueprint

Every change from the specification above, with its reason. Nothing here was
changed to improve a metric.

| # | Specified | Implemented | Why |
|---|---|---|---|
| 1 | Epsilon decay 0.95 per epoch | Decay derived from run length to span 70% of training, preserving the 1.0 → 0.02 endpoints | 0.95 per epoch reaches the floor at epoch 76, so an 800-epoch run would explore for its first 10% only. The literal value is still available as an explicit override. |
| 2 | State space $\mathbb{R}^{50}$ | $\mathbb{R}^{19}$ | The original encoder produced 38 features zero-padded to 50. The new layout is explicit, fully documented, and every dimension carries signal. A 21-dimensional variant adding absolute-magnitude features was tested and **rejected on validation** (0.997 vs 0.932). |
| 3 | Action dim 7 | 6 | There are six actions. The seventh output head was unreachable. |
| 4 | Train/test split only | Train / validation / test | The original loop selected checkpoints by test-split MAE, which is model selection on held-out data. Validation is carved from the end of the training region; the train/test boundary is unchanged at hour 7,485. |
| 5 | Plain DQN | Double DQN | Diagnosed, not preferred a priori: plain DQN's overestimation bias showed up behaviourally as the policy over-correcting clean streams. |
| 6 | Reward gated on `row["fault_type"]` | Reward is a function of error reduction only | Gating on the generator's annotation rewards matching a label rather than improving the signal, and produces a policy that cannot transfer. The reward formula of §2.3 is unchanged; what changed is that it is now the *live* reward — previously `RewardShaper` implemented it correctly but the environment used a different ad-hoc function and the shaper was dead code. |
| 7 | Rule baseline: rolling z-score on the reading | Robust gating of the one-step forecast **innovation**, hyperparameters grid-searched on the training split | A median/MAD test on the raw level assumes a locally stationary mean; this channel's diurnal cycle breaks that, and genuine rush-hour peaks were being clipped. Measured at 0.240 MAE on uncorrupted input before the fix, 0.208 for the revision before that. |
| 8 | MAE over available values | MAE over all timesteps, with un-emitted values carry-forward filled and counted | Filtering out un-imputed dropouts let a policy that emitted nothing score 0.0000. Interpolated-reference timesteps are excluded instead, which is the exclusion that is actually justified. |
| 9 | Window index from the epoch seed | Window drawn from a dedicated RNG over the whole split | `start_idx = (epoch * 17) % max_start` confined 40 epochs to the first 680 of 7,485 training hours. |
| 10 | Legacy tabular tasks (`easy`/`medium`/`hard`) retained | Removed | They belonged to the pre-pivot static tabular cleaning application. |
| 11 | Single training run | Five seeds, aggregated | Single-run validation relative-MAE spans 0.93–1.08 on this task, so a single-seed number describes the seed rather than the method. |

### Specifications kept deliberately, despite being unfavourable

* **Spike amplitude 2.5–4.0σ of the window standard deviation.** Measurement
  shows this lands inside the channel's own innovation envelope, which caps what
  any causal method can achieve. Raising it would have improved every headline
  number. It was not raised; the limitation is reported instead.
* **Reward skip tolerance of 0.2 absolute signal units.** This leaves the agent
  no incentive to improve errors already below 0.2, which caps achievable
  reduction on the low-amplitude fault families — an oracle-greedy policy under
  this reward reaches only +9.1% on dropout. The specified constant was kept and
  the consequence documented.
* **Episode window k = 24 and history N = 5.** Unchanged.
* **Batch 64, lr 3e-4, gamma 0.99, target update every 5 epochs, replay 10,000.**
  Unchanged.
