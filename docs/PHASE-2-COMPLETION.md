# Phase 2 Completion — Implementation Plan

> **For AI coding tools:** This is the authoritative task list for completing Phase 2. Implement tasks in the priority order listed (P0 first). Each task includes the exact files to create or modify, the acceptance criteria, and links to the relevant SRS requirements.

---

## Overview

Phase 2 is **85% complete**. The following work remains to reach 100%:

| Priority | Task | Complexity |
|---|---|---|
| **P0** | JWT authentication (login endpoint + middleware) | High |
| **P0** | `GET /api/results/{id}/download` endpoint | Medium |
| **P0** | API endpoint tests (`tests/test_api.py`) | Medium |
| **P1** | Dataset list endpoint with pagination | Low |
| **P1** | Audit log pagination | Low |
| **P1** | Rate limiting on upload + job creation | Low |
| **P2** | Celery error retry + dead-letter policy | Medium |

---

## P0 — JWT Authentication

**SRS Reference:** FR-12, FR-13, FR-14 | **Architecture Reference:** `03_ARCHITECTURE.md` Section 4

### Files to Create

#### `backend/models/user.py` (NEW)
```python
"""User ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class User(Base):
    """Represents an authenticated user."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
```

#### `backend/auth/__init__.py` (NEW)
Empty — marks the `auth` package.

#### `backend/auth/jwt_handler.py` (NEW)
Responsibilities:
- `create_access_token(user_id: str) -> str` — signs a JWT with 15min expiry.
- `create_refresh_token(user_id: str) -> str` — signs a JWT with 7d expiry.
- `decode_token(token: str) -> dict[str, Any]` — validates and decodes; raises `HTTPException(401)` on expiry or invalid signature.
- `hash_password(plain: str) -> str` — bcrypt hash.
- `verify_password(plain: str, hashed: str) -> bool` — bcrypt verify.

Libraries: `python-jose[cryptography]` for JWT, `passlib[bcrypt]` for passwords (add to `requirements.txt`).

#### `backend/auth/dependencies.py` (NEW)
Responsibilities:
- `get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User` — FastAPI dependency that validates the Bearer token and returns the user.
- Raises `HTTPException(401, "Token expired")` or `HTTPException(401, "Invalid token")` as appropriate.

#### `backend/auth/router.py` (NEW)
Endpoints:
- `POST /api/auth/login` — validates username/password, returns `{ access_token, refresh_token, token_type: "bearer" }`.
- `POST /api/auth/refresh` — validates refresh token, returns new `{ access_token }`.

Response models:
```python
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshResponse(BaseModel):
    access_token: str
```

### Files to Modify

#### `backend/app.py` — register auth router
```python
from backend.auth.router import router as auth_router
app.include_router(auth_router)
```

#### `backend/routes/datasets.py` — protect upload + list endpoints
```python
from backend.auth.dependencies import get_current_user

@router.post("/upload", ...)
async def upload_dataset(
    ...,
    current_user: User = Depends(get_current_user),  # add this
) -> DatasetResponse:
```

#### `backend/routes/jobs.py` — protect all job endpoints
Same pattern as datasets.

### Alembic Migration Required
```bash
cd backend
alembic revision --autogenerate -m "add users table"
alembic upgrade head
```

### Acceptance Criteria
- `POST /api/auth/login` returns 200 + tokens for valid credentials.
- `POST /api/auth/login` returns 401 for wrong password.
- `GET /api/datasets/{id}` without token returns 401.
- `GET /api/datasets/{id}` with expired token returns 401 with `"Token expired"`.
- `GET /api/datasets/{id}` with valid token returns 200.
- `POST /api/auth/refresh` with valid refresh token returns new access token.
- Tests in `tests/test_auth.py` cover all cases above.

---

## P0 — Result Download Endpoint

**SRS Reference:** FR-10

### File to Modify: `backend/routes/jobs.py`

Add:
```python
from fastapi.responses import FileResponse

@router.get("/{job_id}/download")
async def download_result(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Download the cleaned CSV for a completed job.

    Args:
        job_id: The UUID of the completed cleaning job.
        db: Database session (injected).
        current_user: Authenticated user (injected).

    Returns:
        The cleaned CSV as a file download.

    Raises:
        HTTPException 404: If the job does not exist.
        HTTPException 400: If the job is not yet complete.
        HTTPException 404: If the output file is not found on disk.
    """
```

Implementation notes:
- The cleaned file path should be stored in `job.job_metadata["output_path"]` — update `cleaning_service.py` to write the cleaned DataFrame to disk and save the path.
- Use `FileResponse(path, media_type="text/csv", filename="cleaned_{original_name}.csv")`.
- If the job status is not `DONE`, return `400 Bad Request` with `"Job not yet complete"`.
- If the file path doesn't exist on disk, return `404 Not Found` with `"Output file not found"`.

### Acceptance Criteria
- `GET /api/results/{job_id}/download` returns a CSV file for a `DONE` job.
- Returns 400 for a `QUEUED` or `PROCESSING` job.
- Returns 404 for a job that does not exist.
- The downloaded file contains the cleaned data (verify at least one modified row in tests).

---

## P0 — API Endpoint Tests

**File to Create:** `tests/test_api.py`

Use FastAPI's `TestClient` with a SQLite in-memory database (same pattern as existing tests).

Required test cases:

```python
# Authentication
test_login_success()
test_login_wrong_password()
test_login_user_not_found()
test_refresh_token_success()
test_refresh_token_invalid()

# Dataset endpoints (with auth token)
test_upload_csv_success()
test_upload_invalid_format()
test_upload_oversized_file()
test_get_dataset_success()
test_get_dataset_not_found()
test_get_dataset_unauthorized()

# Job endpoints
test_create_batch_job_success()
test_create_batch_job_dataset_not_found()
test_get_job_status_success()
test_get_job_status_not_found()
test_get_audit_log_empty()
test_download_result_job_not_done()
test_download_result_success()

# Health
test_health_check()
```

---

## P1 — Dataset List Endpoint with Pagination

**SRS Reference:** FR-6 | **File to Modify:** `backend/routes/datasets.py`

Add:
```python
@router.get("", response_model=PaginatedResponse[DatasetResponse])
async def list_datasets(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedResponse[DatasetResponse]:
```

`PaginatedResponse` generic model (add to `backend/schemas/pagination.py`):
```python
class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
```

---

## P1 — Audit Log Pagination

**SRS Reference:** Edge case #7 | **File to Modify:** `backend/routes/jobs.py`

Current `GET /api/jobs/{id}/audit-log` returns all rows — this is unacceptable for large jobs.

Add `page` and `page_size` query parameters using the same `PaginatedResponse` pattern. Implement using SQLAlchemy `.offset()` and `.limit()`.

---

## P1 — Rate Limiting

**File to Modify:** `backend/app.py`  
**Library:** `slowapi` (add to `requirements.txt`)

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Apply to upload endpoint:
@router.post("/upload")
@limiter.limit("10/minute")  # configurable via env
async def upload_dataset(request: Request, ...):
```

Rate limit defaults (configurable via env):
- Upload: 10 requests/minute per IP.
- Job creation: 30 requests/minute per IP.
- All other endpoints: 100 requests/minute per IP.

---

## P2 — Celery Error Retry + Dead-Letter Policy

**File to Modify:** `backend/tasks/cleaning_tasks.py`

```python
@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # seconds
    acks_late=True,           # re-queue on worker crash
)
def clean_dataset(self, job_id: str) -> None:
    try:
        ...
    except Exception as exc:
        # Update job status to FAILED before retrying
        # On final retry exhaustion, mark permanently FAILED
        raise self.retry(exc=exc)
```

Add `CELERY_TASK_REJECT_ON_WORKER_LOST = True` to `backend/config/celery_config.py` for crash safety.

---

## Implementation Order

```
1. backend/models/user.py                  ← prerequisite for auth
2. Alembic migration for users table
3. backend/auth/__init__.py
4. backend/auth/jwt_handler.py
5. backend/auth/dependencies.py
6. backend/auth/router.py
7. backend/app.py                          ← register auth router
8. backend/routes/datasets.py              ← add auth dependency + list endpoint
9. backend/routes/jobs.py                  ← add auth dependency + download endpoint
10. backend/services/cleaning_service.py   ← save output file path in metadata
11. backend/schemas/pagination.py          ← PaginatedResponse generic model
12. tests/test_api.py                      ← all endpoint tests
13. backend/app.py                         ← rate limiting
14. backend/tasks/cleaning_tasks.py        ← retry policy
```

---

## Definition of Done for Phase 2

- [ ] All endpoints in `02_SRS.md` Section 5 respond correctly with auth.
- [ ] `tests/test_api.py` covers all routes listed in P0 above.
- [ ] `pytest -q tests/` — 0 failures.
- [ ] `tsc --noEmit` — 0 errors.
- [ ] `GET /api/results/{id}/download` returns a valid cleaned CSV.
- [ ] Audit log endpoint supports pagination (no more unbounded responses).
- [ ] Rate limiting active on upload + job creation endpoints.
- [ ] CI pipeline passes on `develop` branch.
- [ ] No secrets hardcoded anywhere.
