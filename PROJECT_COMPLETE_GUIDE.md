# 📘 Data Cleaning OpenEnv — Complete Project Guide

> **Everything you need to understand, run, teach, and extend this project.**
> Written for the Meta OpenEnv Hackathon, April 2026.

---

## 📌 Table of Contents

1. [What is this project?](#1-what-is-this-project)
2. [What is Reinforcement Learning?](#2-what-is-reinforcement-learning)
3. [What is OpenEnv?](#3-what-is-openenv)
4. [Project File Structure](#4-project-file-structure)
5. [What Each File Does](#5-what-each-file-does)
6. [System Flowchart — How Everything Works Together](#6-system-flowchart--how-everything-works-together)
7. [The RL Loop in This Project](#7-the-rl-loop-in-this-project)
8. [Reward System Explained](#8-reward-system-explained)
9. [The 3 Tasks Explained](#9-the-3-tasks-explained)
10. [All Commands to Run the Project](#10-all-commands-to-run-the-project)
11. [How to Deploy to HuggingFace](#11-how-to-deploy-to-huggingface)
12. [Live URLs](#12-live-urls)
13. [Baseline Scores](#13-baseline-scores)
14. [Tech Stack](#14-tech-stack)
15. [Quick Glossary](#15-quick-glossary)

---

## 1. What is this project?

This project is a **Reinforcement Learning (RL) environment** where an AI agent learns to **clean messy datasets**.

In the real world, data scientists spend 60–80% of their time cleaning data — fixing missing values, removing duplicates, correcting wrong data types, standardizing categories, and handling outliers.

We built an environment where an AI agent can **practice and learn** this skill automatically, row by row, getting rewarded for good cleaning decisions and penalized for bad ones.

**Think of it like this:**
- The environment is a "gym" for the AI
- The dataset is the "obstacle course"
- Each dirty row is a challenge
- The agent picks an action (fill, fix, skip, etc.)
- It gets a reward or penalty based on the quality of its decision
- Over thousands of episodes, it learns to clean data like an expert

---

## 2. What is Reinforcement Learning?

Reinforcement Learning (RL) is a type of machine learning where an agent learns by **trial and error** — interacting with an environment and learning from rewards.

**The RL Loop:**
```
┌─────────────────────────────────────────────────┐
│                                                 │
│   ENVIRONMENT  ──observation──▶  AGENT          │
│                                                 │
│   ENVIRONMENT  ◀──action──────  AGENT          │
│                                                 │
│   ENVIRONMENT  ──reward───────▶  AGENT          │
│                                                 │
│   (repeat until episode ends)                   │
│                                                 │
└─────────────────────────────────────────────────┘
```

**In plain English:**
1. Environment shows agent the current situation (observation)
2. Agent decides what to do (action)
3. Environment evaluates the action and gives feedback (reward)
4. Agent learns from the reward and improves over time

**In our project:**
1. Environment shows agent a dirty data row
2. Agent picks a cleaning action (fill_missing, fix_type, etc.)
3. Environment gives +0.3 for good action, -0.2 for bad
4. Agent learns which actions to take for which types of issues

---

## 3. What is OpenEnv?

OpenEnv is a framework by Meta that standardizes how RL environments are built and deployed.

**Key idea:** RL environments should work like REST APIs — type-safe, containerized, and deployable anywhere.

**Why OpenEnv over traditional Gym?**

| Feature | Traditional (OpenAI Gym) | OpenEnv |
|---|---|---|
| Type Safety | ❌ Raw arrays/dicts | ✅ Typed Pydantic models |
| Isolation | ❌ Same process | ✅ Docker containers |
| Deployment | ❌ "Works on my machine" | ✅ Same everywhere |
| Language | ❌ Python only | ✅ Any language (HTTP API) |
| Scaling | ❌ Hard | ✅ Kubernetes-ready |

**The 3 mandatory endpoints:**
```
POST /reset  → Start a new episode
POST /step   → Take an action
GET  /state  → Get episode metadata
```

---

## 4. Project File Structure

```
data-cleaning-openenv/
│
├── Dockerfile                  ← Containerizes the whole app
├── inference.py                ← Baseline agent using OpenAI API
├── test_env.py                 ← Local testing script
├── README.md                   ← HuggingFace/GitHub readme
├── pyproject.toml              ← Makes env pip-installable
├── PROJECT_COMPLETE_GUIDE.md   ← This file!
│
└── envs/
    └── data_cleaning_env/
        │
        ├── models.py           ← Typed contracts (Action, Observation, State)
        ├── client.py           ← HTTP client for agents to use
        ├── openenv.yaml        ← OpenEnv metadata/spec file
        ├── __init__.py
        │
        ├── server/
        │   ├── app.py          ← FastAPI server (all endpoints)
        │   ├── environment.py  ← Core RL logic
        │   └── __init__.py
        │
        └── tasks/
            ├── graders.py      ← Task definitions + scoring logic
            └── __init__.py
```

---

## 5. What Each File Does

### `models.py` — The Language
Defines the **typed data structures** that the agent and environment use to communicate.

```python
# What the agent SENDS to the environment
class DataCleaningAction:
    action_type: str    # "fill_missing", "fix_type", "skip", etc.
    column: str         # Which column to act on ("age", "salary", etc.)
    value: Any          # New value if needed (e.g., 30 for age)

# What the agent RECEIVES from the environment
class DataCleaningObservation:
    current_row: int          # Which row we're on (0, 1, 2...)
    total_rows: int           # Total rows in dataset
    current_data: dict        # The actual dirty data {'age': None, 'score': '85'}
    issues_detected: list     # ['missing:age', 'wrong_type:score']
    legal_actions: list       # ['fill_missing', 'fix_type', 'skip']
    progress: float           # 0.0 to 1.0
    reward: float             # Last reward received
    done: bool                # Is episode over?

# Episode metadata
class DataCleaningState:
    episode_id: str
    task_name: str
    step_count: int
    total_reward: float
    rows_cleaned: int
    score: float              # Final grader score (0.0 to 1.0)
```

---

### `environment.py` — The Brain
The **core RL logic**. This is where the environment lives.

**Key methods:**

`reset(task_name)` → Starts a new episode
- Loads a dirty dataset for the chosen task
- Resets all counters
- Returns the first observation

`step(action_type, column, value)` → Processes one action
- Applies the cleaning action to the current row
- Calculates reward (+/- based on action quality)
- Moves to next row
- Returns new observation

`_detect_issues(row)` → Finds problems in a row
- Checks for None values → "missing:age"
- Checks for wrong types → "wrong_type:score"
- Checks for formatting → "formatting:email"

`_get_legal_actions(row, issues)` → What can agent do right now?
- If missing values exist → add "fill_missing"
- If wrong types exist → add "fix_type"
- Always includes "skip", "remove_duplicate", etc.

---

### `graders.py` — The Judge
Defines the **3 tasks** and **scores** the cleaned dataset after an episode.

**Task generation:**
- `generate_easy_dataset()` → 10 rows with missing values + wrong types
- `generate_medium_dataset()` → 8 rows with duplicates + formatting issues
- `generate_hard_dataset()` → 8 rows with all issues combined

**Grading:**
- `grade_easy(cleaned_data)` → Checks all values filled + score is numeric
- `grade_medium(cleaned_data)` → Checks no duplicates + emails lowercase
- `grade_hard(cleaned_data)` → Checks depts standardized + salaries in range

All graders return `(score, message)` where score is 0.0–1.0.

---

### `app.py` — The Server
Exposes the environment over **HTTP and WebSocket** so any agent can interact with it.

**HTTP Endpoints:**
```
POST /reset     → env.reset(task_name)
POST /step      → env.step(action_type, column, value)
GET  /state     → env.get_state()
GET  /health    → {"status": "ok"}
GET  /tasks     → list all tasks
GET  /docs      → Swagger API documentation
```

**WebSocket Endpoint:**
```
WS /ws          → Persistent connection for efficient RL training
                  Each connection gets its own environment instance
                  Much faster than HTTP for thousands of steps
```

---

### `client.py` — The Agent's Interface
How your **training code** talks to the environment. Wraps all HTTP calls into clean Python methods.

```python
# Usage example
env = DataCleaningEnv(base_url="https://01ammu-data-cleaning-openenv.hf.space")

result = env.reset(task_name="easy")
# Returns StepResult(observation=..., reward=0.0, done=False, info={...})

result = env.step(action_type="fill_missing", column="age", value=30)
# Returns StepResult(observation=..., reward=0.3, done=False, info={...})

state = env.state()
# Returns episode metadata dict
```

---

### `inference.py` — The Baseline Agent
Uses the **OpenAI API** to run a language model against the environment. Produces reproducible baseline scores to show in the README.

---

### `Dockerfile` — The Container
Packages everything so it runs **identically everywhere**.

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install fastapi uvicorn requests openai pydantic
COPY envs/data_cleaning_env/server/ ./server/
COPY envs/data_cleaning_env/tasks/ ./tasks/
EXPOSE 7860
CMD ["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
```

---

### `openenv.yaml` — The Spec File
Tells the OpenEnv framework everything about your environment — name, version, tasks, action space, observation space, endpoints.

---

### `pyproject.toml` — pip Installable
Makes your environment installable directly from HuggingFace:
```bash
pip install git+https://huggingface.co/spaces/01ammu/data-cleaning-openenv
```

---

## 6. System Flowchart — How Everything Works Together

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AGENT (Your Code)                           │
│                                                                     │
│   from client import DataCleaningEnv                                │
│   env = DataCleaningEnv(base_url="https://...hf.space")             │
│   result = env.reset(task_name="easy")                              │
│   result = env.step("fill_missing", "age", 30)                      │
└────────────────────────┬────────────────────────────────────────────┘
                         │ HTTP POST /reset
                         │ HTTP POST /step
                         │ (or WebSocket /ws)
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DOCKER CONTAINER (HF Space)                      │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    app.py (FastAPI Server)                  │    │
│  │                                                             │    │
│  │   POST /reset ──────────────────────────────────────────┐   │    │
│  │   POST /step  ──────────────────────────────────────┐   │   │    │
│  │   GET  /state ──────────────────────┐               │   │   │    │
│  │   WS   /ws    ──────────────────┐   │               │   │   │    │
│  └─────────────────────────────────┼───┼───────────────┼───┘   │    │
│                                    │   │               │       │    │
│  ┌─────────────────────────────────▼───▼───────────────▼───┐   │   │
│  │                environment.py (Core RL Logic)           │  │   │
│  │                                                         │  │   │
│  │   reset() ──▶ loads dataset ──▶ returns observation    │  │   │
│  │   step()  ──▶ applies action ──▶ calculates reward     │  │   │
│  │               ──▶ moves to next row ──▶ returns obs    │  │   │
│  │   get_state() ──▶ returns episode metadata             │   │   │
│  └──────────────────────────┬──────────────────────────────┘  │   │
│                             │                                 │   │
│  ┌──────────────────────────▼───────────────────────────────┐ │   │
│  │                   graders.py (Tasks + Scoring)           │ │   │
│  │                                                          │ │   │
│  │   generate_easy_dataset()   → 10 rows, missing+types     │ │   │
│  │   generate_medium_dataset() → 8 rows, +duplicates        │ │   │
│  │   generate_hard_dataset()   → 8 rows, +outliers          │ │   │
│  │                                                          │ │   │
│  │   grade_easy(data)   → score 0.0–1.0                     │ │   │
│  │   grade_medium(data) → score 0.0–1.0                     │ │   │
│  │   grade_hard(data)   → score 0.0–1.0                     │ │   │
│  └──────────────────────────────────────────────────────────┘ │   │
│                                                               │   │
└───────────────────────────────────────────────────────────────────┘
                         │
                         ▼
              Observation + Reward returned to Agent
```

---

## 7. The RL Loop in This Project

Here is exactly what happens during one full episode:

```
START: Agent calls reset(task_name="easy")
│
├── Environment loads dirty dataset (10 rows)
├── Returns first row: {'age': None, 'salary': 50000, 'score': '85'}
│   Issues: ['missing:age', 'wrong_type:score']
│   Legal actions: ['fill_missing', 'fix_type', 'skip', ...]
│
├── Agent sees the row and issues
├── Agent picks action: fill_missing on column 'age', value=30
│
├── Environment applies: row['age'] = 30
├── Reward: +0.3 (correct action for a missing value)
├── Returns next row
│
├── Agent picks action: fix_type on column 'score'
├── Environment applies: row['score'] = float('85') = 85.0
├── Reward: +0.2
│
├── ... (repeat for all 10 rows) ...
│
END: All rows processed → done = True
│
└── Grader scores final cleaned dataset → 0.88
    "Passed 31/35 checks"
```

---

## 8. Reward System Explained

| Action | When to use | Reward |
|---|---|---|
| `fill_missing` | Column value is None | **+0.3** |
| `fix_type` | Value is wrong type (e.g. "85" instead of 85) | **+0.2** |
| `remove_duplicate` | Row is a duplicate of previous row | **+0.4** |
| `fix_category` | Category is inconsistent (e.g. "eng" → "Engineering") | **+0.3** |
| `remove_outlier` | Value is out of normal range (e.g. salary = 999999) | **+0.4** |
| `fix_formatting` | Text needs formatting (e.g. "ALICE@GMAIL.COM" → lowercase) | **+0.2** |
| `skip` | Do nothing | **-0.2** (penalty) |
| Wrong action | e.g. fill_missing when value already exists | **-0.1** |
| Unknown action | Not in the action space | **-0.3** |

**Why penalties matter:**
The agent can't just always pick "fill_missing" and get rewards. If the value already exists and you try to fill it, you get -0.1. This forces the agent to actually read the observation and pick the right action.

---

## 9. The 3 Tasks Explained

### Task 1 — Easy: Fix Missing Values & Type Errors
**Dataset:** 10-row employee dataset with age, salary, score
**Issues:**
- `age` or `salary` is None → needs `fill_missing`
- `score` is "85" (string) instead of 85.0 (float) → needs `fix_type`

**Grader checks:**
- All age, salary, score fields are non-null
- score is numeric (float)

**Baseline score: 0.88**

---

### Task 2 — Medium: Remove Duplicates & Fix Formatting
**Dataset:** 8-row contacts dataset with name, email, age
**Issues:**
- Rows 2 and 4 are exact duplicates (Bob, bob@gmail.com, 30)
- Rows 3 and 7 are exact duplicates (charlie)
- `email` is uppercase ("ALICE@GMAIL.COM") → needs `fix_formatting`
- `name` or `age` is None → needs `fill_missing`

**Grader checks:**
- No duplicate emails
- All names filled
- All emails lowercase
- All ages filled

**Baseline score: 0.88**

---

### Task 3 — Hard: Full Data Cleaning
**Dataset:** 8-row HR dataset with name, dept, salary, age
**Issues:**
- Inconsistent departments: "eng", "h.r.", "ENGINEERING", "Finance" all need standardizing to "Engineering", "HR", "Finance"
- Outlier salary: 999999 (way too high) → replace with median
- Negative salary: -5000 → invalid
- Missing name, age, salary
- Duplicate rows (alice appears twice)

**Grader checks:**
- No duplicate names
- All fields filled
- All depts in {"Engineering", "HR", "Finance"}
- All salaries between 0 and 200,000

**Baseline score: 0.83**

---

## 10. All Commands to Run the Project

### Prerequisites
```bash
# Make sure you have Python 3.10+ and Git installed
python --version
git --version
```

---

### Clone the project
```bash
git clone https://github.com/AnubhavKiroula/data-cleaning-openenv
cd data-cleaning-openenv
```

---

### Install dependencies
```bash
pip install fastapi uvicorn pydantic requests openai
```

---

### Run the server locally
```bash
# From the project root: D:\META-HACKATHON\data-cleaning-openenv\
cd D:\META-HACKATHON\data-cleaning-openenv

python -m uvicorn server.app:app --host 0.0.0.0 --port 7860
```

Server will be live at: http://localhost:7860

---

### Test all 3 tasks locally
```bash
# From project root
cd D:\META-HACKATHON\data-cleaning-openenv

python test_env.py
```

Expected output:
```
easy   : 0.88
medium : 0.88
hard   : 0.83
average: 0.86
```

---

### Run with Docker locally
```bash
# From project root
cd D:\META-HACKATHON\data-cleaning-openenv

# Build the Docker image
docker build -t data-cleaning-openenv .

# Run the container
docker run -p 7860:7860 data-cleaning-openenv
```

---

### Run the baseline inference script
```bash
# Set environment variables first
$env:OPENAI_API_KEY = "your_openai_key_here"
$env:API_BASE_URL = "http://localhost:7860"
$env:MODEL_NAME = "gpt-4o-mini"

# Run inference
python inference.py
```

---

### Test the API manually (curl)
```bash
# Health check
curl.exe http://localhost:7860/health

# Reset to easy task
curl.exe -X POST http://localhost:7860/reset -H "Content-Type: application/json" -d '{\"task_name\": \"easy\"}'

# Take a step
curl.exe -X POST http://localhost:7860/step -H "Content-Type: application/json" -d '{\"action_type\": \"fill_missing\", \"column\": \"age\", \"value\": 30}'

# Check state
curl.exe http://localhost:7860/state

# List tasks
curl.exe http://localhost:7860/tasks
```

---

### Push changes to GitHub
```bash
cd D:\META-HACKATHON\data-cleaning-openenv

git add .
git commit -m "your commit message here"
git push origin main
```

---

### Push changes to HuggingFace Space
```bash
cd D:\META-HACKATHON\data-cleaning-openenv

git push hf main
```

If hf remote doesn't exist yet:
```bash
git remote add hf https://huggingface.co/spaces/01ammu/data-cleaning-openenv
git push hf main --force
```

---

### Use the client in your own code
```python
from envs.data_cleaning_env.client import DataCleaningEnv

# Connect to local server
env = DataCleaningEnv(base_url="http://localhost:7860")

# Or connect to live HF Space
env = DataCleaningEnv(base_url="https://01ammu-data-cleaning-openenv.hf.space")

# Run an episode
result = env.reset(task_name="easy")
print(result.observation)

while not result.done:
    result = env.step(
        action_type="fill_missing",
        column="age",
        value=30
    )
    print(f"Reward: {result.reward}, Done: {result.done}")

state = env.state()
print(f"Final score: {state['score']}")
```

---

## 11. How to Deploy to HuggingFace

### One-time setup (already done)
```bash
# Add HF as a git remote
git remote add hf https://huggingface.co/spaces/01ammu/data-cleaning-openenv
```

### Every time you want to redeploy
```bash
cd D:\META-HACKATHON\data-cleaning-openenv
git add .
git commit -m "update: describe what you changed"
git push hf main
git push origin main    # also keep GitHub in sync
```

### Check deployment
- Go to: https://huggingface.co/spaces/01ammu/data-cleaning-openenv
- Click App tab → watch Container logs
- Look for: "Application startup complete" and green Running dot

---

## 12. Live URLs

| What | URL |
|---|---|
| HF Space | https://01ammu-data-cleaning-openenv.hf.space |
| Health Check | https://01ammu-data-cleaning-openenv.hf.space/health |
| API Docs (Swagger) | https://01ammu-data-cleaning-openenv.hf.space/docs |
| List Tasks | https://01ammu-data-cleaning-openenv.hf.space/tasks |
| GitHub Repo | https://github.com/AnubhavKiroula/data-cleaning-openenv |

---

## 13. Baseline Scores

These scores were produced by running `inference.py` with a rule-based agent:

| Task | Score | What was tested |
|---|---|---|
| Easy | **1.00** | 31/35 checks passed |
| Medium | **0.88** | Duplicates removed, formatting fixed |
| Hard | **0.85** | All issues including outliers + categories |
| **Average** | **0.91** | Across all 3 tasks |

---

## 14. Tech Stack

| Technology | Role |
|---|---|
| **Python 3.11** | Core language |
| **FastAPI** | HTTP server framework |
| **Uvicorn** | ASGI server to run FastAPI |
| **Pydantic** | Typed data models (Action, Observation, State) |
| **Docker** | Containerization for deployment |
| **HuggingFace Spaces** | Cloud hosting platform |
| **OpenAI API** | Baseline inference agent |
| **Git** | Version control |
| **OpenEnv** | RL environment framework by Meta |

---

## 15. Quick Glossary

| Term | Meaning |
|---|---|
| **Agent** | The AI that makes decisions (what to do with each row) |
| **Environment** | The system the agent interacts with (our data cleaning env) |
| **Observation** | What the agent sees (current row, issues, legal actions) |
| **Action** | What the agent does (fill_missing, fix_type, skip, etc.) |
| **Reward** | Feedback the agent gets (+0.3, -0.2, etc.) |
| **Episode** | One full run through a dataset (all rows processed) |
| **Grader** | Function that scores the cleaned dataset (0.0–1.0) |
| **OpenEnv** | Meta's framework for standardizing RL environments |
| **HF Space** | HuggingFace hosting — where our environment runs live |
| **Docker** | Container technology — packages app + dependencies together |
| **FastAPI** | Python web framework — handles HTTP requests |
| **WebSocket** | Persistent connection — faster than HTTP for many RL steps |
| **Pydantic** | Python library for typed, validated data models |
| **Baseline** | A simple agent's score used as a reference point |
| **GRPO** | Group Relative Policy Optimization — an RL training algorithm |

---

*Built for the Meta OpenEnv Hackathon, April 2026.*
*Team: AnubhavKiroula*
*HF Space: https://01ammu-data-cleaning-openenv.hf.space*
*GitHub: https://github.com/AnubhavKiroula/data-cleaning-openenv*