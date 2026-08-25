# Development Guide — data-cleaning-openenv

> **For AI coding tools:** Follow the phase order below and the SOLID checklist in Section 3. Do not generate code for a phase until its prerequisites are marked done. Never restructure an existing class without flagging it first — prefer adding via interface extension.

---

## 1. Development Principles (non-negotiable)

### SOLID

| Principle | Application in This Project |
|---|---|
| **S** — Single Responsibility | Each class does one thing. `CleaningService` orchestrates; it does not also parse CSV or emit metrics directly. |
| **O** — Open/Closed | Extend agent behaviour by adding a new subclass of `Agent` — never modify `base_agent.py` or `agent_coordinator.py` to accommodate a new agent type. |
| **L** — Liskov Substitution | Any `Agent` subclass must honour the base class contract — `get_available_actions()` and `evaluate_observation()` must always return the same types. |
| **I** — Interface Segregation | Pydantic response models are narrow and focused. Do not add fields to `DatasetResponse` just because they exist in the ORM model. |
| **D** — Dependency Inversion | Route handlers depend on `get_db` (abstraction) — not on `SessionLocal` directly. `CleaningService` depends on `AgentCoordinator` (interface), not on specific agent implementations. |

### DRY

- **No duplicated validation logic** — define once in Pydantic models, not repeated in route handlers and services.
- **No repeated SQL queries** — common DB lookups go in helper functions or a repository layer.
- **No copy-pasted Celery boilerplate** — all task scaffolding is in `backend/tasks/cleaning_tasks.py`.

### Fail Loud, Not Silent

- Every invalid state raises an `HTTPException` with a meaningful `detail` message.
- Celery tasks catch all exceptions, set `job.status = FAILED`, and log the traceback — they never swallow errors silently.
- Agents return a structured action dict — they never return `None` or `-1` for "no action".

### Test as You Build

- Write a test for any new endpoint before considering it done.
- Write a test for any new agent method that contains logic (not just `pass`).
- Tests go in `tests/` — `test_agents.py` for ML layer, `test_dqn.py` for DQN model, `test_api.py` for API endpoints (to be created in Phase 2 completion).

---

## 2. Phase Roadmap

### Phase 1 — Multi-Agent RL Engine ✅ COMPLETE

**Deliverables (all done):**
- Abstract `Agent` base class with `AgentFactory` registry.
- 5 specialist agents: `DataQualityAgent`, `DeduplicationAgent`, `NormalizationAgent`, `OutlierDetectionAgent`, `TypeInferenceAgent`.
- `AgentCoordinator` with scoring and best-action selection.
- `QNetwork` + `DQNAgent` (PyTorch).
- Standard + Prioritized `ExperienceReplayBuffer`.
- `RewardShaper` with configurable reward functions.
- Full training loop (`train_dqn.py`) with checkpointing.
- `ModelRegistry` for save/load with metadata.
- 96/96 tests passing.

**Definition of Done:** ✅ Met — agents tested, DQN trains without error, models save/load correctly.

---

### Phase 2 — Backend REST API 🟡 85% → Target: 100%

**Completed:**
- FastAPI app with async handlers.
- PostgreSQL ORM models + Alembic migrations.
- `POST /api/datasets/upload`, `GET /api/datasets/{id}`, `GET /api/datasets/{id}/metrics`.
- `POST /api/jobs/batch`, `GET /api/jobs/{id}`, `GET /api/jobs/{id}/audit-log`.
- `POST /api/inference`.
- Celery + Redis integration.
- Prometheus metrics middleware.

**Still needed (Phase 2 completion sprint):**

| Task | File(s) to Create/Modify | Priority |
|---|---|---|
| JWT auth middleware + login endpoint | `backend/auth/` (new module) | P0 |
| `GET /api/results/{id}/download` | `backend/routes/jobs.py` | P0 |
| `GET /api/datasets` list with pagination | `backend/routes/datasets.py` | P1 |
| Audit log pagination | `backend/routes/jobs.py` | P1 |
| Rate limiting on upload + job create | `backend/app.py` (slowapi) | P1 |
| Celery error retry + dead-letter policy | `backend/tasks/cleaning_tasks.py` | P2 |
| `test_api.py` endpoint tests | `tests/test_api.py` | P0 |

**Exit criteria:** All endpoints from `02_SRS.md` Section 5 respond correctly. `test_api.py` covers all routes. CI passes.

---

### Phase 3 — React Frontend 🟡 80% → Target: 100%

**Completed:**
- Dashboard, Upload, Results, JobMonitor pages.
- Axios API client (`services/api.ts`).
- TypeScript strict mode, 0 errors.
- MUI component library.

**Still needed (Phase 3 completion sprint):**

| Task | File(s) | Priority |
|---|---|---|
| Login page + auth flow | `src/pages/Login.tsx`, `src/hooks/useAuth.ts` | P0 (blocked by Phase 2 auth) |
| Auth interceptor (attach Bearer token) | `src/services/api.ts` | P0 |
| SSE-based real-time job progress | `src/hooks/useJobProgress.ts` | P1 |
| Audit log pagination in Results page | `src/components/results/AuditLogTable.tsx` | P1 |
| `useDatasets` hook + Dataset list page | `src/hooks/useDatasets.ts` | P2 |

**Exit criteria:** Full flow works end-to-end with auth. Job monitor shows live progress without polling. All pages match `04_UIUX.md` specifications.

---

### Phase 4 — DevOps & Deployment ⚠️ 65% → Target: 100%

**Completed:**
- Multi-stage Dockerfiles (backend + frontend).
- `docker-compose.new.yml` (dev) + `docker-compose.prod.yml` (prod).
- GitHub Actions: `ci.yml`, `build-and-publish.yml`, `lint.yml`, `integration.yml`, `sync-to-hf.yml`.

**Still needed:**

| Task | File(s) | Priority |
|---|---|---|
| Fix CI failures in 3 copilot PRs | `.github/workflows/build-and-publish.yml` | P0 |
| Add `develop` branch to CI trigger | `.github/workflows/ci.yml` | P0 (already done) |
| Staging environment env vars | `.env.staging.example` (new) | P1 |
| Render deploy script / secrets docs | `docs/PHASE-2-COMPLETION.md` | P1 |
| Post-deploy smoke test in CI | `.github/workflows/build-and-publish.yml` | P2 |

**Exit criteria:** All GitHub Actions pass on `develop`. Docker images publish to GHCR on merge. Staging deploy works.

---

## 3. SOLID Checklist (run before every PR)

Before opening a PR, answer these for every file changed:

```
[ ] S — Does this class/function have a single, clearly statable responsibility?
        If you need "and" to describe it, split it.

[ ] O — Did you extend via a new class or function, or did you modify an existing one?
        If modified: was there truly no way to extend instead?

[ ] L — If you added a subclass, does it honour the parent's contract in ALL cases?
        Run the parent's tests against the subclass to verify.

[ ] I — Are Pydantic models / function signatures focused?
        No function takes a "god object" parameter just to read 1 field from it.

[ ] D — Are dependencies injected (via FastAPI Depends, constructor args)?
        No `from backend.services.cleaning_service import CleaningService` inside a route handler directly.
```

---

## 4. Coding Standards

### Python

```python
# ✅ Required for every public function and class
def calculate_quality_score(frame: pd.DataFrame) -> float:
    """Calculate a data quality score for a DataFrame.

    Args:
        frame: The input DataFrame to evaluate.

    Returns:
        A float between 0.0 and 1.0 where 1.0 is perfect quality.

    Raises:
        ValueError: If the DataFrame is empty.
    """
    if frame.empty:
        raise ValueError("Cannot compute quality score for empty DataFrame.")
    ...
```

- **Type hints** on every function parameter and return type — no exceptions.
- **Google-style docstrings** on all public functions and classes.
- **`from __future__ import annotations`** at the top of every file (enables PEP 563 postponed evaluation).
- **No wildcard imports** (`from x import *`).
- **No `print()` statements** in production code — use `logger = logging.getLogger(__name__)`.
- **No `time.sleep()` in route handlers** — never block the event loop.
- **Max line length: 100 characters** (configured in `pyproject.toml`).

### TypeScript / React

```tsx
// ✅ Required — explicit Props interface
interface StatusBadgeProps {
  status: "QUEUED" | "PROCESSING" | "DONE" | "FAILED";
  size?: "small" | "medium";
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = "medium" }) => {
  ...
};
```

- **No `any`** — use `unknown` + type narrowing or define a proper interface.
- **`React.FC<Props>`** type annotation on every component.
- **No inline `style={{}}` for layout** — use MUI `sx` prop.
- **No `console.log`** in committed code — use a logger or remove before committing.
- **All API calls in `services/api.ts`** — no `axios.get()` directly in a component or hook.

---

## 5. Definition of Done (per feature)

A feature is **done**, not just **written**, when:

1. It has passing unit/integration tests covering the happy path and the relevant edge cases from `02_SRS.md` Section 4.
2. It compiles/runs with zero errors (Python) or zero TypeScript errors (`tsc --noEmit`).
3. It follows SOLID principles — verified via the checklist in Section 3.
4. It has Google-style docstrings (Python) or JSDoc comments (TypeScript) on public interfaces.
5. No secrets or credentials are hardcoded or logged.
6. The PR passes all CI checks (`ci.yml`, `lint.yml`).

---

## 6. Local Development Setup

### Prerequisites
- Docker Desktop running
- Python 3.11 (via `.venv` or `uv`)
- Node.js 20

### Backend
```bash
# 1. Start postgres + redis
docker compose -f docker-compose.new.yml up -d postgres redis

# 2. Activate venv
python -m venv .venv && .venv\Scripts\activate   # Windows
source .venv/bin/activate                          # Linux/macOS

# 3. Install deps
pip install -r backend/requirements.txt

# 4. Set env
cp .env.example .env  # then edit with your local values

# 5. Run migrations
cd backend && alembic upgrade head && cd ..

# 6. Start API
uvicorn backend.app:app --reload --port 8000

# 7. Start Celery worker (separate terminal)
celery -A backend.worker.celery_app worker --loglevel=info
```

### Frontend
```bash
cd frontend
npm install
npm run dev    # starts at http://localhost:5173
```

### Run Tests
```bash
# Backend
pytest -q tests/

# Frontend type check
cd frontend && npm run type-check
```

---

## 7. For AI Coding Tools Specifically

- Always check `02_SRS.md` Section 4 (edge cases) before marking a function complete.
- Always check `03_ARCHITECTURE.md` Section 5 (module boundaries) before suggesting cross-layer imports.
- Run the SOLID checklist (Section 3 of this doc) on generated code before presenting it.
- Never introduce a new external library without checking `03_ARCHITECTURE.md` Section 1 (tech stack).
- Never suggest `print()` — always `logger.info() / logger.error()`.
- When generating a new endpoint, also generate the corresponding Pydantic response model and at least one test.
- New config values belong in `backend/config/__init__.py`, not `os.environ.get()` inline.
