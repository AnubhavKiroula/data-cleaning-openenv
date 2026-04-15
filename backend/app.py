"""FastAPI application entrypoint."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sqlalchemy import create_engine

from backend.config import settings
from backend.database import init_db


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

app = FastAPI(title="Data Cleaning Platform", version="1.0.0")
REQUEST_METRICS = {
    "health_checks_total": 0,
    "datasets_requests_total": 0,
    "jobs_requests_total": 0,
    "inference_requests_total": 0,
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    """Initialize required runtime components."""
    _probe_database_engine()
    init_db()
    logger.info("FastAPI backend initialized")


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Simple liveness endpoint."""
    REQUEST_METRICS["health_checks_total"] += 1
    return {
        "status": "ok",
        "environment": settings.environment,
        "port": str(settings.api_port),
        "cwd": os.getcwd(),
    }


@app.get("/api/datasets")
async def list_datasets() -> dict[str, list[Any]]:
    """Placeholder datasets listing endpoint."""
    REQUEST_METRICS["datasets_requests_total"] += 1
    return {"items": []}


@app.post("/api/datasets")
async def create_dataset() -> dict[str, str]:
    """Placeholder dataset create endpoint."""
    REQUEST_METRICS["datasets_requests_total"] += 1
    return {"message": "Dataset create endpoint scaffolded"}


@app.get("/api/datasets/{dataset_id}")
async def get_dataset(dataset_id: str) -> dict[str, str]:
    """Placeholder dataset retrieval endpoint."""
    REQUEST_METRICS["datasets_requests_total"] += 1
    raise HTTPException(status_code=501, detail=f"Dataset lookup not implemented: {dataset_id}")


@app.put("/api/datasets/{dataset_id}")
async def update_dataset(dataset_id: str) -> dict[str, str]:
    """Placeholder dataset update endpoint."""
    REQUEST_METRICS["datasets_requests_total"] += 1
    raise HTTPException(status_code=501, detail=f"Dataset update not implemented: {dataset_id}")


@app.delete("/api/datasets/{dataset_id}")
async def delete_dataset(dataset_id: str) -> dict[str, str]:
    """Placeholder dataset delete endpoint."""
    REQUEST_METRICS["datasets_requests_total"] += 1
    raise HTTPException(status_code=501, detail=f"Dataset delete not implemented: {dataset_id}")


@app.get("/api/jobs")
async def list_jobs() -> dict[str, list[Any]]:
    """Placeholder jobs listing endpoint."""
    REQUEST_METRICS["jobs_requests_total"] += 1
    return {"items": []}


@app.post("/api/jobs")
async def create_job() -> dict[str, str]:
    """Placeholder job creation endpoint."""
    REQUEST_METRICS["jobs_requests_total"] += 1
    return {"message": "Job creation endpoint scaffolded"}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str) -> dict[str, str]:
    """Placeholder job detail endpoint."""
    REQUEST_METRICS["jobs_requests_total"] += 1
    raise HTTPException(status_code=501, detail=f"Job lookup not implemented: {job_id}")


@app.post("/api/inference")
async def run_inference() -> dict[str, str]:
    """Placeholder inference endpoint."""
    REQUEST_METRICS["inference_requests_total"] += 1
    return {"message": "Inference endpoint scaffolded"}


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> str:
    """Expose basic Prometheus-compatible metrics."""
    lines = []
    for key, value in REQUEST_METRICS.items():
        lines.append(f"# TYPE {key} counter")
        lines.append(f"{key} {value}")
    return "\n".join(lines) + "\n"
