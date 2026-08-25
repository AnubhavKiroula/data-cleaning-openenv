# data-cleaning-openenv — Project Overview & Architecture Diagrams

> **Quick navigation for any AI tool or new contributor:** This is the entry point. Read this document first to understand the system as a whole before touching any code. Every other document in `docs/` is linked from here.

**Repository:** https://github.com/AnubhavKiroula/data-cleaning-openenv  
**Last updated:** August 2026  
**Overall Phase Status:**

| Phase | Name | Status |
|---|---|---|
| **Phase 1** | Multi-Agent RL Engine | ✅ 100% Complete |
| **Phase 2** | FastAPI Backend & Job Queue | 🟡 85% Complete |
| **Phase 3** | React + TypeScript UI | 🟡 80% Complete |
| **Phase 4** | Docker, CI/CD & Deployment | ⚠️ 65% Complete |

---

## 1. What This Project Is

**data-cleaning-openenv** is a production-grade, AI-powered data cleaning platform. Instead of writing one-off cleaning scripts, users upload dirty CSV/Excel datasets and a coordinated ensemble of RL agents autonomously detects and fixes data quality issues — missing values, duplicates, outliers, type mismatches, and normalization problems.

**The core value proposition:**
- A **DQN-based multi-agent system** selects the most effective cleaning action per row, per column, and updates its strategy from feedback (reward shaping).
- A **FastAPI REST backend** exposes the RL engine as an async job queue (Celery + Redis), making it usable by any frontend or API client.
- A **React SPA** provides a polished upload → monitor → export experience.
- **CI/CD via GitHub Actions** builds, tests, and publishes Docker images to GHCR on every merge to `main`.

---

## 2. High-Level System Architecture

```mermaid
graph TD
    subgraph "User Interface"
        FE["React SPA\n(Vite + TypeScript + MUI)\nPort :3000"]
    end

    subgraph "API Layer"
        API["FastAPI App\n(backend/app.py)\nPort :8000"]
    end

    subgraph "Job Queue"
        CELERY["Celery Worker\n(backend/worker.py)"]
        REDIS["Redis Broker\nPort :6379"]
    end

    subgraph "RL Engine - Phase 1"
        COORD["AgentCoordinator"]
        DQN["DQN Policy Network"]
        AGENTS["5 Specialist Agents"]
        REPLAY["Experience Replay Buffer"]
        REWARD["Reward Shaper"]
    end

    subgraph "Persistence"
        PG["PostgreSQL\nPort :5432"]
        UPLOADS["File Storage /data/uploads"]
    end

    FE -->|HTTP/JSON| API
    API --> REDIS
    REDIS --> CELERY
    CELERY --> COORD
    COORD --> DQN
    COORD --> AGENTS
    DQN --> REPLAY
    AGENTS --> REWARD
    API --> PG
    CELERY --> PG
    CELERY --> UPLOADS
    API --> UPLOADS
```

---

## 3. Module Map

```
data-cleaning-openenv/
├── backend/
│   ├── app.py                  ← FastAPI app factory, routers, CORS, middleware
│   ├── database.py             ← SQLAlchemy engine, session factory, get_db dependency
│   ├── worker.py               ← Celery app entry point
│   ├── config/
│   │   ├── __init__.py         ← Settings (pydantic-settings, env-driven, no hardcoded values)
│   │   └── celery_config.py    ← Celery broker/backend URL config
│   ├── models/                 ← SQLAlchemy ORM models (one file per domain entity)
│   │   ├── dataset.py          ← Dataset (id, filename, rows, columns, quality_score)
│   │   ├── cleaning_job.py     ← CleaningJob (status FSM: QUEUED → PROCESSING → DONE/FAILED)
│   │   └── audit_log.py        ← Per-action record: agent, action, reward, old/new value
│   ├── routes/                 ← FastAPI routers (no business logic here)
│   │   ├── datasets.py         ← POST /upload, GET /{id}, GET /{id}/metrics
│   │   ├── jobs.py             ← POST /batch, GET /{id}, GET /{id}/audit-log
│   │   └── inference.py        ← POST /inference (direct RL without job queue)
│   ├── services/               ← Business logic (used by routes AND celery tasks)
│   │   └── cleaning_service.py ← Dataset load → agent loop → DB writes → metrics
│   ├── tasks/
│   │   └── cleaning_tasks.py   ← clean_dataset.delay(job_id) Celery task
│   ├── ml/                     ← RL Engine (Phase 1 — fully complete)
│   │   ├── base_agent.py       ← Abstract Agent base class + AgentFactory
│   │   ├── specialist_agents.py← 5 agents: DataQuality, Dedup, Normalize, Outlier, TypeInfer
│   │   ├── agent_coordinator.py← Scores agents, selects best action
│   │   ├── dqn_model.py        ← QNetwork (PyTorch), DQNAgent
│   │   ├── experience_replay.py← Standard + Prioritized Replay Buffers
│   │   ├── reward_shaper.py    ← Configurable reward functions per action type
│   │   ├── train_dqn.py        ← Full training loop with checkpointing
│   │   ├── model_registry.py   ← Save/load trained models with metadata
│   │   └── benchmark.py        ← Agent comparison utilities
│   └── monitoring/
│       ├── metrics.py          ← Prometheus counters/histograms
│       └── middleware.py       ← FastAPI request duration middleware
│
├── frontend/src/
│   ├── pages/                  ← Dashboard, Upload, Results, JobMonitor
│   ├── components/             ← Reusable UI components
│   └── services/api.ts         ← Axios client with typed API methods
│
├── tests/                      ← 96 tests, all passing on main
│   ├── test_agents.py          ← Agent + coordinator unit tests
│   └── test_dqn.py             ← DQN model + replay buffer tests
│
├── .github/workflows/
│   ├── ci.yml                  ← Tests + type-check on every PR
│   ├── build-and-publish.yml   ← Build & push Docker images to GHCR
│   ├── integration.yml         ← Docker Compose smoke tests
│   ├── lint.yml                ← Ruff linter
│   └── sync-to-hf.yml          ← Sync to Hugging Face Spaces on main push
│
├── docker-compose.new.yml      ← Dev compose: postgres + redis + backend + celery + frontend
├── docker-compose.prod.yml     ← Prod compose: uses pre-built GHCR images
└── docs/                       ← All project documentation (you are here)
```

---

## 4. Data Flow: A Cleaning Job End-to-End

```mermaid
sequenceDiagram
    participant User
    participant FE as React Frontend
    participant API as FastAPI
    participant DB as PostgreSQL
    participant Redis
    participant Worker as Celery Worker
    participant RL as Agent Coordinator

    User->>FE: Upload CSV file
    FE->>API: POST /api/datasets/upload
    API->>DB: INSERT dataset (metadata, quality_score)
    API-->>FE: dataset_id + quality_score

    User->>FE: Start Cleaning
    FE->>API: POST /api/jobs/batch { dataset_id, cleaning_mode }
    API->>DB: INSERT cleaning_job (status=QUEUED)
    API->>Redis: enqueue clean_dataset.delay(job_id)
    API-->>FE: job_id

    loop Poll Every 2s
        FE->>API: GET /api/jobs/{job_id}
        API-->>FE: status + progress
    end

    Redis->>Worker: dequeue job
    Worker->>DB: UPDATE job status=PROCESSING
    loop For Each Row
        Worker->>RL: get_best_action(observation, legal_actions)
        RL-->>Worker: action_type + agent_used + confidence
        Worker->>DB: INSERT audit_log entry
        Worker->>DB: UPDATE rows_processed
    end
    Worker->>DB: UPDATE job status=DONE

    FE->>API: GET /api/results/{job_id}/download
    API-->>FE: cleaned CSV
```

---

## 5. RL Engine Architecture (Phase 1 Detail)

```mermaid
graph LR
    subgraph "Input"
        OBS["Observation Vector\n• missing_ratio\n• duplicate_flag\n• type_mismatch\n• outlier_score\n• column_stats"]
    end

    subgraph "5 Specialist Agents"
        A1["DataQualityAgent\n→ fill_missing"]
        A2["DeduplicationAgent\n→ remove_duplicate"]
        A3["NormalizationAgent\n→ standardize"]
        A4["OutlierDetectionAgent\n→ cap/remove_outlier"]
        A5["TypeInferenceAgent\n→ fix_type / skip"]
    end

    subgraph "DQN Policy"
        DQN["QNetwork\n3-layer MLP\nargmax Q(s,a)"]
        REPLAY["Replay Buffer"]
        TARGET["Target Network\nsoft update τ=0.005"]
    end

    subgraph "Reward Signal"
        REWARD["RewardShaper:\n+1.0 fill_missing resolved\n+0.8 remove_duplicate\n+0.6 standardize\n-0.5 wrong action\n-0.1 skip"]
    end

    OBS --> A1 & A2 & A3 & A4 & A5
    OBS --> DQN
    DQN --> REPLAY
    REPLAY --> TARGET
    A1 & A2 & A3 & A4 & A5 --> REWARD
    REWARD --> REPLAY
```

---

## 6. Database ER Diagram

```mermaid
erDiagram
    DATASET {
        uuid id PK
        string filename
        string file_path
        int rows
        json columns
        float data_quality_score
        enum status
        timestamp created_at
    }

    CLEANING_JOB {
        uuid id PK
        uuid dataset_id FK
        enum status
        int total_rows
        int rows_processed
        float result_score
        json job_metadata
        timestamp created_at
        timestamp started_at
        timestamp completed_at
    }

    AUDIT_LOG {
        uuid id PK
        uuid job_id FK
        string action_type
        int row_index
        string column
        string old_value
        string new_value
        float reward
        string agent_used
        float confidence
        timestamp timestamp
    }

    DATASET ||--o{ CLEANING_JOB : "has many"
    CLEANING_JOB ||--o{ AUDIT_LOG : "generates"
```

---

## 7. CI/CD Pipeline Overview

```mermaid
graph LR
    PR["PR opened to develop or main"]
    CI["ci.yml\n96 pytest tests\ntsc type-check\nvite build"]
    LINT["lint.yml\nruff check"]
    INT["integration.yml\ndocker compose up\n/api/health smoke test"]
    MERGE["Merge to main"]
    BUILD["build-and-publish.yml\nBackend Docker image\nFrontend Docker image\nPush to GHCR\nTrivy security scan"]
    HF["sync-to-hf.yml\nHugging Face Spaces sync"]

    PR --> CI & LINT & INT
    CI & LINT & INT --> MERGE
    MERGE --> BUILD & HF
```

---

## 8. What's Done vs. What's Left

| Area | Done ✅ | Still Needed ⏳ |
|---|---|---|
| RL Engine | 5 agents, DQN, replay, reward shaping, 96 tests | — |
| Backend API | Upload, jobs CRUD, audit-log, health, metrics | Rate limiting, pagination, result download endpoint |
| Auth | JWT_SECRET in config | JWT middleware, login endpoint, protected routes |
| Celery | Task enqueue + execute + audit log | Error retry policy, dead-letter queue |
| Frontend | 4 pages, API client, TypeScript strict mode | Real-time updates (SSE/WS), auth login page |
| Docker | Multi-stage Dockerfiles, dev + prod compose | — |
| CI/CD | Tests, lint, Docker build, sync-to-hf | Fix CI failures in 3 copilot PR branches |
| Deployment | Render YAML drafted | Staging env vars, secrets, post-deploy smoke test |

---

## 9. Document Index

| File | Purpose |
|---|---|
| [`00_PROJECT-OVERVIEW-AND-DIAGRAMS.md`](./00_PROJECT-OVERVIEW-AND-DIAGRAMS.md) | **This file** — system architecture, diagrams, module map |
| [`01_PRD.md`](./01_PRD.md) | Product Requirements — *what* and *why* |
| [`02_SRS.md`](./02_SRS.md) | Software Requirements — functional requirements, edge cases |
| [`03_ARCHITECTURE.md`](./03_ARCHITECTURE.md) | Technical architecture — stack, module boundaries, API contracts |
| [`04_UIUX.md`](./04_UIUX.md) | UI/UX — page flows, component map |
| [`05_DEVELOPMENT.md`](./05_DEVELOPMENT.md) | Development guide — SOLID, coding standards, phase roadmap |
| [`06_VERSION-CONTROL.md`](./06_VERSION-CONTROL.md) | Git workflow — branching, commit format, PR template |
| [`DB-SETUP.md`](./DB-SETUP.md) | Local database setup with Docker Compose |
| [`PHASE-2-COMPLETION.md`](./PHASE-2-COMPLETION.md) | Phase 2 implementation plan |
