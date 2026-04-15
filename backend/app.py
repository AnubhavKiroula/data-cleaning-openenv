"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sqlalchemy import create_engine

from backend.config import settings
from backend.database import init_db
from backend.routes.datasets import router as datasets_router
from backend.routes.inference import router as inference_router
from backend.routes.jobs import router as jobs_router


class JsonFormatter(logging.Formatter):
    """Format logs as JSON for production-friendly ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "environment": settings.environment,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging() -> None:
    """Configure root logger with JSON output."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(settings.log_level.upper())


def _probe_database_engine() -> None:
    """Build and dispose an engine to validate configured URL syntax."""
    probe_engine = create_engine(settings.database_url, pool_pre_ping=True, echo=False)
    probe_engine.dispose()


configure_logging()
logger = logging.getLogger(__name__)

REQUEST_METRICS = {
    "health_checks_total": 0,
    "datasets_requests_total": 0,
    "jobs_requests_total": 0,
    "inference_requests_total": 0,
}

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize required runtime components on startup."""
    try:
        _probe_database_engine()
        init_db()
        logger.info("FastAPI backend initialized")
    except Exception:
        logger.exception("Backend startup completed with database initialization warning")
    yield


app = FastAPI(title="Data Cleaning Platform", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
@app.get("/health")
async def health_check() -> dict[str, str]:
    """Simple liveness endpoint."""
    REQUEST_METRICS["health_checks_total"] += 1
    return {
        "status": "ok",
        "environment": settings.environment,
        "port": str(settings.api_port),
    }


app.include_router(datasets_router)
app.include_router(jobs_router)
app.include_router(inference_router)


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> str:
    """Expose basic Prometheus-compatible metrics."""
    lines = []
    for key, value in REQUEST_METRICS.items():
        lines.append(f"# TYPE {key} counter")
        lines.append(f"{key} {value}")
    return "\n".join(lines) + "\n"
