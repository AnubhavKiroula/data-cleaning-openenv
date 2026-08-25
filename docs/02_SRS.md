# Software Requirements Specification (SRS) — data-cleaning-openenv

> **For AI coding tools:** This defines exact scope. Do not implement features not listed here without team approval. When generating code, validate against the edge cases in Section 4 — most bugs will come from unhandled edge cases, not core logic errors.

---

## 1. Functional Requirements

### 1.1 Dataset Management
| ID | Feature | Description |
|---|---|---|
| FR-1 | Upload CSV/Excel | Accept `.csv`, `.xlsx`, `.xls` files up to 100MB via `POST /api/datasets/upload` |
| FR-2 | File validation | Reject invalid formats, oversized files, and empty files before persisting |
| FR-3 | Quality scoring | Compute an initial data quality score (0.0–1.0) on upload based on missing and duplicate ratios |
| FR-4 | Dataset retrieval | Return metadata by ID via `GET /api/datasets/{id}` |
| FR-5 | Dataset metrics | Return before/after quality metrics via `GET /api/datasets/{id}/metrics` |
| FR-6 | Dataset listing | Return paginated list via `GET /api/datasets` with optional filters |

### 1.2 Cleaning Job Management
| ID | Feature | Description |
|---|---|---|
| FR-7 | Create batch job | Queue an async cleaning job via `POST /api/jobs/batch` with `dataset_id` and `cleaning_mode` |
| FR-8 | Job status polling | Return job status, progress, and current score via `GET /api/jobs/{id}` |
| FR-9 | Audit log access | Return full per-row action log via `GET /api/jobs/{id}/audit-log` |
| FR-10 | Result download | Return cleaned CSV file via `GET /api/results/{id}/download` |
| FR-11 | Direct inference | Accept a row observation and return an action via `POST /api/inference` (no job queue) |

### 1.3 Authentication (Phase 2 Completion Target)
| ID | Feature | Description |
|---|---|---|
| FR-12 | User login | `POST /api/auth/login` — validate credentials and return a signed JWT |
| FR-13 | Protected routes | Datasets and jobs endpoints require a valid Bearer token |
| FR-14 | Token refresh | `POST /api/auth/refresh` — issue a new token from a valid refresh token |

### 1.4 Observability
| ID | Feature | Description |
|---|---|---|
| FR-15 | Health check | `GET /api/health` returns service status, DB connectivity, and Redis status |
| FR-16 | Prometheus metrics | `GET /metrics` exposes job counts, durations, agent action tallies in Prometheus format |
| FR-17 | Structured logging | All log output is JSON-structured with level, timestamp, and correlation fields |

---

## 2. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-1 | API response time for all non-file endpoints must be < 200ms at p95 |
| NFR-2 | File upload must not block the event loop — use `UploadFile` (async) throughout |
| NFR-3 | All endpoints must have type hints on all parameters and return types |
| NFR-4 | All public functions and classes must have Google-style docstrings |
| NFR-5 | No hardcoded credentials, URLs, or thresholds — all values in `backend/config/__init__.py` from env |
| NFR-6 | Celery tasks must be idempotent — re-running a completed job must not corrupt data |
| NFR-7 | RL agent selection must be deterministic given the same observation + random seed |
| NFR-8 | All DB credentials must live in `.env` — never committed to Git |
| NFR-9 | SOLID principles enforced — see `05_DEVELOPMENT.md` Section 3 for the checklist |
| NFR-10 | Rate limiting applied on upload and job creation endpoints (configurable via env) |

---

## 3. User Flow Summary

**API Consumer flow:**  
`POST /api/auth/login` → `POST /api/datasets/upload` → `POST /api/jobs/batch` → poll `GET /api/jobs/{id}` → `GET /api/results/{id}/download`

**Frontend flow:**  
Upload page → Job monitor (with real-time progress) → Results page (audit log + download)

**Admin/Monitoring flow:**  
`GET /api/health` → `GET /metrics` → Prometheus/Grafana dashboard

---

## 4. Edge Cases — Must Be Explicitly Handled, Not Assumed Away

| # | Edge Case | Expected Behaviour |
|---|---|---|
| 1 | Upload file with all rows duplicated | Quality score reflects duplicate ratio; cleaning job removes duplicates and logs each removal |
| 2 | Upload file with zero non-null values in a column | Agent selects `skip` or `remove_column` — must not divide by zero or crash |
| 3 | Dataset file deleted from disk after upload but before job runs | Job fails with `FAILED` status and a clear error message — not a 500 server crash |
| 4 | Job created for a dataset that belongs to a different user (after auth is enabled) | `403 Forbidden` — not a 404 (which would reveal existence) |
| 5 | Celery worker crashes mid-job | Job remains in `PROCESSING` state — a recovery mechanism or operator note is needed |
| 6 | `cleaning_mode` value not in `["aggressive", "conservative"]` | Pydantic validation rejects with `422 Unprocessable Entity` before the handler is called |
| 7 | Audit log for a job with 100k rows | Pagination on `GET /api/jobs/{id}/audit-log` is required — returning all rows in a single response is not acceptable |
| 8 | Concurrent duplicate job submissions (same dataset, same user, within 1 second) | Only one job is created — idempotency key or DB constraint prevents duplicates |
| 9 | JWT token expired on a protected endpoint | `401 Unauthorized` with a clear `"Token expired"` detail message |
| 10 | Upload of a CSV with no headers (only data rows) | Return `400 Bad Request` with a specific message — not a 500 |
| 11 | Redis unavailable when trying to enqueue a job | Return `503 Service Unavailable` with a Retry-After header — do not create the job record |
| 12 | PostgreSQL unavailable at startup | Application must fail fast with a clear error log — not silently start and crash on first request |

---

## 5. API Contract Summary

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/login` | No | Login, returns access + refresh tokens |
| `POST` | `/api/auth/refresh` | No | Refresh token → new access token |
| `POST` | `/api/datasets/upload` | Yes | Upload CSV/Excel, returns dataset metadata |
| `GET` | `/api/datasets/{id}` | Yes | Get dataset metadata by ID |
| `GET` | `/api/datasets/{id}/metrics` | Yes | Get quality metrics for a dataset |
| `GET` | `/api/datasets` | Yes | List datasets (paginated) |
| `POST` | `/api/jobs/batch` | Yes | Create async cleaning job |
| `GET` | `/api/jobs/{id}` | Yes | Get job status and progress |
| `GET` | `/api/jobs/{id}/audit-log` | Yes | Get audit log (paginated) |
| `GET` | `/api/results/{id}/download` | Yes | Download cleaned CSV |
| `POST` | `/api/inference` | Yes | Direct row-level RL inference |
| `GET` | `/api/health` | No | Service health check |
| `GET` | `/metrics` | No | Prometheus metrics |

---

## 6. Out of Scope for Current Iteration

- Real-time collaborative dataset editing.
- Multi-tenant team/organization account model.
- Webhook notifications when a job completes.
- Mobile/responsive web client (web-first only).

---

**Any AI-generated code must be checked against Section 4 edge cases before being considered complete.**
