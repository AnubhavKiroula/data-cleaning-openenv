"""Celery task definitions for asynchronous cleaning jobs."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from celery import Task

from backend.config.celery_config import celery_app
from backend.database import SessionLocal
from backend.models.cleaning_job import CleaningJob, JobStatus
from backend.services.cleaning_service import CleaningService

logger = logging.getLogger(__name__)


@celery_app.task(
    name="clean_dataset",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def clean_dataset(self: Task, job_id: str) -> dict[str, Any]:
    """Process a queued cleaning job and persist progress/results."""
    db = SessionLocal()
    try:
        parsed_job_id = UUID(job_id)
        job = db.get(CleaningJob, parsed_job_id)
        if job is None:
            raise ValueError("Job not found")

        job.status = JobStatus.PROCESSING
        db.commit()
        db.refresh(job)

        cleaning_mode = "conservative"
        if isinstance(job.job_metadata, dict):
            cleaning_mode = str(job.job_metadata.get("cleaning_mode", cleaning_mode))

        service = CleaningService(db)
        job = asyncio.run(service.clean_existing_job(job, cleaning_mode))
        return {
            "job_id": str(job.id),
            "status": job.status.value if hasattr(job.status, "value") else str(job.status),
            "rows_processed": job.rows_processed,
            "total_rows": job.total_rows,
            "result_score": job.result_score,
        }
    except Exception as exc:
        logger.exception("Celery task clean_dataset failed for job %s", job_id)
        try:
            parsed_job_id = UUID(job_id)
            failed_job = db.get(CleaningJob, parsed_job_id)
            if failed_job is not None:
                failed_job.status = JobStatus.FAILED
                failed_job.error_message = str(exc)
                db.commit()
        except Exception:  # pragma: no cover - defensive path for DB failure
            logger.exception("Failed to persist failure state for job %s", job_id)
        raise
    finally:
        db.close()
