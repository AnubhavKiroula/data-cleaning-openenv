# Technical Architecture — data-cleaning-openenv

> **For AI coding tools:** Before generating cross-module code, read Section 5 (Module Boundaries) carefully. Never call ML code directly from a route handler — go through the service layer. Never import from `backend.routes` inside `backend.services` or `backend.ml`. Communication between layers flows strictly downward.

---

## 1. Technology Stack

| Component | Technology | Reason |
|---|---|---|
| **Language (Backend)** | Python 3.11 | Async support, rich ML ecosystem, type hints |
| **Web Framework** | FastAPI | Native async/await, Pydantic validation, auto-generated OpenAPI docs |
| **ORM** | SQLAlchemy 2.0 (declarative) | Type-safe queries, Alembic migration support |
| **Migrations** | Alembic | Version-controlled schema evolution |
| **Task Queue** | Celery 5.x | Distributed background task execution |
| **Message Broker** | Redis 7 | Celery broker + result backend |
| **Database** | PostgreSQL 16 | ACID guarantees, JSON column support for metadata |
| **Settings** | pydantic-settings | Env-driven config, no hardcoded values |
| **ML / RL** | PyTorch 2.x | DQN policy network, GPU-compatible if available |
| **Data Processing** | Pandas, NumPy | DataFrame manipulation in cleaning service |
| **Monitoring** | Prometheus (prometheus-client) | Counters, histograms exposed at `/metrics` |
| **Language (Frontend)** | TypeScript 6 (strict) | Compile-time safety, no `any` types allowed |
| **Frontend Framework** | React 18 + Vite 8 | SPA, hot module replacement for development |
| **UI Components** | Material UI 9 | Consistent design system |
| **HTTP Client** | Axios | Typed API calls with interceptors |
| **Containerization** | Docker + Docker Compose | Reproducible environments, multi-stage builds |
| **CI/CD** | GitHub Actions | Automated test, build, publish pipeline |
| **Image Registry** | GitHub Container Registry (GHCR) | First-party GitHub integration |
| **Linting** | Ruff (Python), ESLint (TypeScript) | Fast, opinionated linting |

> [!IMPORTANT]
> **Dependency rule:** Any new package must be added to `backend/requirements.txt` (Python) or `frontend/package.json` (Node). No `pip install` or `npm install` directly into a container — all dependencies must be committed and version-pinned.

---

## 2. API Layer

### 2.1 REST Endpoints

All endpoints are prefixed under `/api`. FastAPI auto-generates OpenAPI docs at `/docs` (Swagger UI) and `/redoc`.

**Authentication (Phase 2 completion target):**
```
POST /api/auth/login       → { access_token, refresh_token, token_type }
POST /api/auth/refresh     → { access_token }
```

**Datasets:**
```
POST   /api/datasets/upload       → DatasetResponse (201)
GET    /api/datasets/{id}         → DatasetResponse (200)
GET    /api/datasets/{id}/metrics → MetricsResponse (200)
GET    /api/datasets              → PaginatedResponse[DatasetResponse] (200)
```

**Jobs:**
```
POST   /api/jobs/batch              → BatchJobResponse (201)
GET    /api/jobs/{id}               → JobStatusResponse (200)
GET    /api/jobs/{id}/audit-log     → PaginatedResponse[AuditLogEntry] (200)
GET    /api/results/{id}/download   → FileResponse (CSV) (200)
```

**Inference:**
```
POST   /api/inference → InferenceResponse (200)
```

**Observability:**
```
GET    /api/health    → HealthResponse (200)
GET    /metrics       → text/plain Prometheus format (200)
```

### 2.2 Pydantic Response Models

Every endpoint must define an explicit Pydantic response model. No endpoint may return a raw `dict` as its declared return type — use typed Pydantic models with `model_config = {"from_attributes": True}` where ORM objects are mapped.

---

## 3. Database

**PostgreSQL 16** with SQLAlchemy 2.0 declarative models and Alembic migrations.

### 3.1 Schema

| Table | Purpose |
|---|---|
| `datasets` | Uploaded file metadata + quality score |
| `cleaning_jobs` | Job lifecycle (status FSM, progress counters) |
| `audit_logs` | Per-row action records (agent, action type, old/new values, reward) |

Full ER diagram is in [`00_PROJECT-OVERVIEW-AND-DIAGRAMS.md`](./00_PROJECT-OVERVIEW-AND-DIAGRAMS.md) Section 6.

### 3.2 Migration Rules

- **All schema changes** must go through an Alembic migration — never use `Base.metadata.create_all()` in production code paths.
- Migration files live in `backend/alembic/versions/`.
- Run `alembic upgrade head` on app startup (handled by `backend/entrypoint.sh`).
- Never modify a committed migration file — generate a new one instead.

### 3.3 Connection

```python
# backend/database.py — single source of truth for DB session
engine = create_engine(settings.database_url, pool_pre_ping=True)

def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
```

`get_db` is the only way to obtain a DB session in route handlers. Never instantiate `SessionLocal` directly in routes or services.

---

## 4. Authentication Architecture (Phase 2 Target)

**Chosen approach: JWT (stateless, no DB session storage)**

**Decision rationale:** The platform is single-tenant for now. JWT avoids a `sessions` table and allows horizontal Celery scaling without shared session state.

```
POST /api/auth/login
  body: { username, password }
  → validates against users table (bcrypt hash comparison)
  → returns: { access_token (15min TTL), refresh_token (7d TTL) }

GET /api/datasets (protected)
  header: Authorization: Bearer <access_token>
  → FastAPI dependency extracts + validates JWT
  → injects current_user into handler
```

**Implementation components:**
- `backend/auth/` — new module (to be created in Phase 2 completion):
  - `jwt_handler.py` — `encode_token()`, `decode_token()`, `verify_password()`
  - `dependencies.py` — `get_current_user` FastAPI dependency
  - `router.py` — `/api/auth/login` and `/api/auth/refresh` handlers
- `backend/models/user.py` — User ORM model (id, username, hashed_password)
- Alembic migration for `users` table

**Security rules:**
- JWT secret is `settings.jwt_secret` — must be a long random string in production, set via `JWT_SECRET` env var.
- Passwords stored as bcrypt hashes — `passlib[bcrypt]` is the library.
- Access tokens expire in 15 minutes; refresh tokens in 7 days.
- Never log tokens or passwords.

---

## 5. Module Boundaries (strict — no exceptions)

```
┌─────────────────────────────────────────────────────────┐
│                    Routes Layer                         │
│  (backend/routes/*.py)                                  │
│  • Validates input via Pydantic                         │
│  • Calls service layer ONLY                             │
│  • Never imports from backend.ml directly               │
└──────────────────────────────┬──────────────────────────┘
                               │ calls
┌──────────────────────────────▼──────────────────────────┐
│                   Service Layer                         │
│  (backend/services/*.py)                                │
│  • All business logic lives here                        │
│  • Calls backend.ml for RL decisions                    │
│  • Writes to DB via SQLAlchemy session                  │
│  • Emits Prometheus metrics                             │
└──────────────────────────────┬──────────────────────────┘
                               │ calls
┌──────────────────────────────▼──────────────────────────┐
│                      ML Layer                           │
│  (backend/ml/*.py)                                      │
│  • Pure RL logic — no FastAPI, no DB, no HTTP           │
│  • AgentCoordinator is the only public interface        │
│  • Takes observation dict, returns action dict          │
│  • No side effects (no DB writes, no file I/O)          │
└─────────────────────────────────────────────────────────┘
```

**Rule for AI tools:** If you find yourself importing `from backend.routes` inside `backend.services`, or importing `from backend.ml` inside `backend.routes`, stop and restructure.

---

## 6. Celery Task Architecture

```
Route handler
  → creates CleaningJob (DB, status=QUEUED)
  → clean_dataset.delay(job_id)   ← enqueue, return immediately

Celery Worker (backend/worker.py)
  → dequeues job_id
  → fetches CleaningJob from DB
  → instantiates CleaningService(db)
  → calls cleaning_service.clean_existing_job(job, mode)
    → loads dataset file
    → loops rows → AgentCoordinator.get_best_action()
    → inserts AuditLog per row
    → updates job.rows_processed per row
  → updates job.status = DONE / FAILED
```

**Task rules:**
- Tasks in `backend/tasks/` are **thin wrappers** only — all logic is in `backend/services/`.
- Tasks must handle their own exceptions and update job status to `FAILED` on error — never let an exception propagate silently.
- Tasks must be idempotent: re-running a `DONE` job should be a no-op or create a new job, not overwrite the existing one.

---

## 7. Configuration Management

All configuration is in `backend/config/__init__.py` via `pydantic-settings`:

```python
class Settings(BaseSettings):
    database_url: str        # DATABASE_URL env var
    redis_url: str           # REDIS_URL env var
    jwt_secret: str          # JWT_SECRET env var
    max_upload_size: int     # MAX_UPLOAD_SIZE env var (default 100MB)
    log_level: str           # LOG_LEVEL env var
    environment: str         # ENVIRONMENT env var (dev / staging / production)
    api_port: int            # API_PORT env var
```

**Rules:**
- Never add `if environment == "dev"` branching in application code — use config values instead.
- New settings go here — never inline `os.environ.get()` in route or service files.
- Default values are safe for local development only. Production values must be set via environment variables.

---

## 8. Error Handling Standards

All errors must be explicit HTTPExceptions. Never let unhandled exceptions propagate to the client:

```python
# ✅ Correct
try:
    ...
except ValueError as exc:
    raise HTTPException(status_code=404, detail=str(exc)) from exc
except Exception as exc:
    logger.exception("Unexpected error in upload_dataset")
    raise HTTPException(status_code=500, detail="Server error.") from exc

# ❌ Wrong — leaks internal stack trace to client
except Exception as exc:
    return {"error": str(exc)}
```

HTTP status codes must match semantics:
- `200` — success (GET)
- `201` — resource created (POST)
- `400` — client sent invalid data
- `401` — not authenticated
- `403` — authenticated but not authorized
- `404` — resource not found
- `413` — payload too large
- `422` — validation failed (Pydantic handles this automatically)
- `500` — unexpected server error
- `503` — dependency unavailable (Redis, DB)

---

## 9. Docker Architecture

### 9.1 Backend Multi-Stage Dockerfile (`backend/Dockerfile`)

```
Stage 1: builder (python:3.11-slim)
  → Install build tools (gcc, libpq-dev)
  → pip install into /opt/venv

Stage 2: runtime (python:3.11-slim)
  → Copy /opt/venv from builder (no build tools in production image)
  → Install only runtime deps (postgresql-client, curl)
  → Create non-root 'app' user
  → ENTRYPOINT: entrypoint.sh (waits for postgres, runs alembic, starts uvicorn)
```

### 9.2 Frontend Multi-Stage Dockerfile (`frontend/Dockerfile`)

```
Stage 1: builder (node:20-alpine)
  → npm ci
  → npm run build → /app/dist

Stage 2: nginx (nginx:alpine)
  → Copy dist/ from builder
  → Serve via nginx with SPA routing config
```

### 9.3 Compose Files

| File | Purpose |
|---|---|
| `docker-compose.new.yml` | **Development** — builds images from source, mounts uploads volume |
| `docker-compose.prod.yml` | **Production** — pulls pre-built GHCR images, no source mounts |

---

## 10. For AI Coding Tools Specifically

- Always check `02_SRS.md` Section 4 edge cases before considering a function complete.
- Respect module boundaries in Section 5 — never suggest cross-layer imports.
- Never introduce new external libraries without checking Section 1's tech stack.
- Prefer `raise HTTPException(...)` over returning error dicts.
- New config values go in `backend/config/__init__.py`, not inline `os.environ.get()`.
- All new DB schema changes need a new Alembic migration file.
