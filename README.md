---
title: Data Cleaning Openenv
emoji: 🧹
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
tags:
  - openenv
---
# 🧹 Data Cleaning OpenEnv

An [OpenEnv](https://openenv.dev)-compatible reinforcement learning environment where an AI agent learns to clean messy, real-world tabular datasets — row by row, action by action.

---

## 🌍 Environment Description & Motivation

Data cleaning is one of the most time-consuming tasks in any data pipeline. Studies estimate that data scientists spend **60–80% of their time** just preparing and cleaning data. Yet most RL benchmarks focus on games or toy problems.

This environment simulates a **realistic data cleaning workflow**: the agent is presented with a dirty dataset containing missing values, type errors, duplicates, formatting inconsistencies, and outliers. It must decide — for each row — what corrective action to take. A programmatic grader then scores the final cleaned dataset.

This environment is directly useful for:
- Training agents to automate ETL pipelines
- Evaluating LLMs on structured data reasoning
- Benchmarking decision-making under partial observability

---

## 🔁 API

The environment implements the full OpenEnv spec:

| Endpoint | Method | Description |
|---|---|---|
| `/reset` | POST | Start a new episode with a chosen task |
| `/step` | POST | Take a cleaning action on the current row |
| `/state` | GET | Get current episode metadata |
| `/health` | GET | Health check |
| `/tasks` | GET | List all available tasks |

---

## 👁️ Observation Space

At each step, the agent receives a `DataCleaningObservation`:

| Field | Type | Description |
|---|---|---|
| `current_row` | int | Index of the row currently being processed |
| `total_rows` | int | Total number of rows in the dataset |
| `current_data` | dict | The actual data in the current row |
| `issues_detected` | list[str] | Problems found (e.g. `missing:age`, `wrong_type:score`) |
| `legal_actions` | list[str] | Valid action types for this row |
| `progress` | float | Episode progress from 0.0 to 1.0 |
| `reward` | float | Reward received for the last action |
| `done` | bool | Whether the episode has ended |

---

## ⚡ Action Space

Each action is a `DataCleaningAction` with the following fields:

| Field | Type | Description |
|---|---|---|
| `action_type` | str | One of 6 cleaning operations (see below) |
| `column` | str | The column to apply the action to |
| `value` | any (optional) | New value, if required by the action |

### Action Types

| Action | Description | Reward |
|---|---|---|
| `fill_missing` | Fill a `None` value with a sensible default | +0.3 |
| `fix_type` | Convert a value to the correct data type (e.g. `"85"` → `85`) | +0.2 |
| `remove_duplicate` | Mark a row as a duplicate for removal | +0.3 |
| `fix_category` | Standardize a category label (e.g. `"eng"` → `"Engineering"`) | +0.3 |
| `remove_outlier` | Replace a statistical outlier with the column median | +0.3 |
| `skip` | Do nothing for this row | -0.2 (penalty) |

---

## 📋 Tasks

### Task 1 — Easy: Fix Missing Values & Type Errors
**Objective:** Given a 10-row employee dataset with `age`, `salary`, and `score` columns, fill all `None` values and convert string scores to floats.

- Issues present: missing values, wrong data types
- Expected score: **≥ 0.85**
- Grader checks: all fields non-null, `score` is numeric

---

### Task 2 — Medium: Remove Duplicates & Fix Formatting
**Objective:** Given an 8-row contacts dataset, remove duplicate rows, fill missing names, and standardize email addresses to lowercase.

- Issues present: duplicates, missing values, formatting inconsistencies
- Expected score: **≥ 0.85**
- Grader checks: no duplicate emails, all names filled, all emails lowercase, all ages filled

---

### Task 3 — Hard: Full Data Cleaning
**Objective:** Given an 8-row HR dataset with salary, department, name, and age fields, fix all issues simultaneously: fill missing values, remove duplicates, standardize department labels, and replace outlier/negative salaries.

- Issues present: missing values, duplicates, inconsistent categories (`"eng"`, `"h.r."`, `"ENGINEERING"`), outlier salaries (`999999`, `-5000`)
- Valid departments: `Engineering`, `HR`, `Finance`
- Expected score: **≥ 0.80**
- Grader checks: no duplicate names, all fields filled, all depts standardized, all salaries in range `(0, 200000)`

---

## 🏆 Baseline Scores

Scores from the baseline inference script (`inference.py`) using rule-based actions:

| Task | Score |
|---|---|
| Easy | **0.88** |
| Medium | **0.88** |
| Hard | **0.83** |
| **Average** | **0.86** |

---

## 🚀 Setup & Usage

### Option 1: Run with Docker

```bash
git clone https://github.com/AnubhavKiroula/data-cleaning-openenv
cd data-cleaning-openenv

docker build -t data-cleaning-openenv .
docker run -p 7860:7860 data-cleaning-openenv
```

Server will be available at `http://localhost:7860`.

---

### Option 2: Run locally

```bash
pip install fastapi uvicorn pydantic openai requests

cd envs/data_cleaning_env/server
uvicorn app:app --host 0.0.0.0 --port 7860
```

---

### Run the baseline inference script

```bash
export OPENAI_API_KEY=your_key_here
export API_BASE_URL=http://localhost:7860   # or your HF Space URL
export MODEL_NAME=gpt-4o-mini

python inference.py
```

---

### Example: Manual API interaction

**Reset to easy task:**
```bash
curl.exe -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task_name": "easy"}'
```

**Take a step:**
```bash
curl.exe -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"action_type": "fill_missing", "column": "age", "value": 30}'
```

**Check state:**
```bash
curl.exe http://localhost:7860/state
```

---

## 📁 Project Structure

```
data-cleaning-openenv/
├── envs/
│   └── data_cleaning_env/
│       ├── server/
│       │   ├── app.py           # FastAPI server
│       │   ├── environment.py   # Core RL environment logic
│       │   └── models.py        # Typed Pydantic models
│       └── tasks/
│           └── graders.py       # Task definitions + graders
├── inference.py                 # Baseline OpenAI inference script
├── openenv.yaml                 # OpenEnv metadata
├── Dockerfile                   # Container definition
└── README.md
```

---

## ✅ OpenEnv Spec Compliance

- [x] Typed `Action`, `Observation`, `State` Pydantic models
- [x] `step()` → returns observation, reward, done, info
- [x] `reset()` → returns initial observation
- [x] `state()` → returns current episode metadata
- [x] `openenv.yaml` with environment metadata
- [x] 3 tasks with difficulty progression (easy → medium → hard)
- [x] Graders produce deterministic scores between 0.0 and 1.0
- [x] Meaningful reward function with partial progress signals
- [x] Baseline inference script using OpenAI client
- [x] Deployable via Docker on port 7860

---

## 🤗 HuggingFace Space

Live environment: https://01ammu-data-cleaning-openenv.hf.space

Health check: `GET /health` → `{"status": "ok"}`