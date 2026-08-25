# Local Database Setup — data-cleaning-openenv

This guide explains how to spin up PostgreSQL and Redis locally using Docker Compose, configure `.env`, run Alembic migrations, and verify your setup is working.

---

## 1. Prerequisites

- **Docker Desktop** installed and running.
- **Python 3.11** with dependencies installed (`pip install -r backend/requirements.txt`).
- **pgAdmin 4** (optional) — for visual DB inspection. Download from [pgadmin.org](https://www.pgadmin.org/).

---

## 2. Environment Configuration

Copy the example env file and edit it:

```bash
cp .env.example .env
```

Minimum required values for local development:

```ini
DATABASE_URL=postgresql+psycopg2://admin:password@localhost:5432/data_cleaning
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=local-dev-secret-change-in-prod
ENVIRONMENT=dev
LOG_LEVEL=INFO
MAX_UPLOAD_SIZE=104857600
```

> [!CAUTION]
> Never commit your `.env` file — it is already in `.gitignore`. Never use `local-dev-secret-change-in-prod` in staging or production.

---

## 3. Starting Services with Docker Compose

Start PostgreSQL and Redis in the background:

```bash
docker compose -f docker-compose.new.yml up -d postgres redis
```

Verify they are running:
```bash
docker compose -f docker-compose.new.yml ps
```

Expected output:
```
NAME                       STATUS
data-cleaning-postgres-1   Up (healthy)
data-cleaning-redis-1      Up
```

### Useful Docker commands

| Command | Purpose |
|---|---|
| `docker compose -f docker-compose.new.yml up -d` | Start all services |
| `docker compose -f docker-compose.new.yml down` | Stop all services |
| `docker compose -f docker-compose.new.yml down -v` | Stop + wipe all volumes (full reset) |
| `docker compose -f docker-compose.new.yml logs -f backend` | Stream backend logs |
| `docker compose -f docker-compose.new.yml ps` | Show service status |

---

## 4. Running Database Migrations

After starting PostgreSQL, apply all pending Alembic migrations:

```bash
# From the repo root
cd backend
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade -> <revision_id>, Initial schema
INFO  [alembic.runtime.migration] Running upgrade <revision_id> -> <revision_id>, ...
```

### Creating a new migration (when you change an ORM model)

```bash
cd backend
alembic revision --autogenerate -m "add users table"
# Review the generated file in backend/alembic/versions/ before running it
alembic upgrade head
```

> [!IMPORTANT]
> Always review auto-generated migrations before running them — Alembic's diff can miss nullable changes, index names, or custom column types. Never run an unreviewed migration against a production database.

---

## 5. Verifying Database Connection

Start the FastAPI server and hit the health endpoint:

```bash
# From repo root
uvicorn backend.app:app --reload --port 8000
```

In a second terminal:
```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "environment": "dev"
}
```

If `database` or `redis` shows `"disconnected"`, check:
1. Docker containers are running (`docker compose ps`).
2. `.env` values match the Docker Compose configuration.
3. No firewall blocking `localhost:5432` or `localhost:6379`.

---

## 6. Connecting via pgAdmin (Optional — Visual Inspection)

1. Open **pgAdmin 4**.
2. Right-click **Servers** → **Register** → **Server...**.
3. **General tab** — Name: `data-cleaning-openenv Local`.
4. **Connection tab**:
   - Host: `localhost`
   - Port: `5432`
   - Database: `data_cleaning`
   - Username: `admin`
   - Password: `password`
   - Check **Save Password**
5. Click **Save**.

Expand **Databases** → **data_cleaning** → **Schemas** → **public** → **Tables** to view:
- `datasets`
- `cleaning_jobs`
- `audit_logs`

---

## 7. Full Reset (Wipe and Restart)

If your DB gets into a bad state during development:

```bash
# Stop everything and wipe volumes
docker compose -f docker-compose.new.yml down -v

# Start fresh
docker compose -f docker-compose.new.yml up -d postgres redis

# Wait ~5 seconds for postgres to be healthy, then migrate
cd backend && alembic upgrade head
```

---

## 8. Connecting to Redis

For debugging Celery task queues, use the Redis CLI:

```bash
docker exec -it $(docker compose -f docker-compose.new.yml ps -q redis) redis-cli
```

Useful commands inside redis-cli:
```
KEYS *              # list all keys
LLEN celery         # queue depth
LRANGE celery 0 5   # inspect first 5 queued tasks
FLUSHDB             # ⚠️ clear all data (dev only)
```

---

## 9. Environment Variables Reference

| Variable | Required | Default (dev) | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | `postgresql+psycopg2://admin:password@localhost:5432/data_cleaning` | SQLAlchemy connection string |
| `REDIS_URL` | Yes | `redis://localhost:6379/0` | Redis connection URL |
| `JWT_SECRET` | Yes | `change-me-in-production` | JWT signing key — must be long and random in prod |
| `ENVIRONMENT` | No | `dev` | `dev` / `staging` / `production` |
| `LOG_LEVEL` | No | `INFO` | Python logging level |
| `MAX_UPLOAD_SIZE` | No | `104857600` (100MB) | Max CSV upload size in bytes |
| `API_PORT` | No | `8000` | FastAPI server port |
