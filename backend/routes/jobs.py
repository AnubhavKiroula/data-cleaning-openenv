"""Cleaning jobs route handlers."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.audit_log import AuditLog
from backend.models.cleaning_job import CleaningJob, JobStatus, JobType
from backend.models.dataset import Dataset
from backend.tasks.cleaning_tasks import clean_dataset

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class BatchJobRequest(BaseModel):
    """Request payload to create a batch job."""

    dataset_id: UUID
    cleaning_mode: Literal["aggressive", "conservative"] = "conservative"


class BatchJobResponse(BaseModel):
    """Response payload for queued batch job."""

    job_id: UUID
    status: str
    created_at: datetime


@router.post("/batch", response_model=BatchJobResponse, status_code=status.HTTP_201_CREATED)
async def start_batch_job(payload: BatchJobRequest, db: Session = Depends(get_db)) -> BatchJobResponse:
    """Queue a batch cleaning job for asynchronous worker processing."""
    dataset = db.get(Dataset, payload.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    try:
        job = CleaningJob(
            dataset_id=payload.dataset_id,
            job_type=JobType.BATCH,
            status=JobStatus.QUEUED,
            total_rows=dataset.rows,
            rows_processed=0,
            job_metadata={"cleaning_mode": payload.cleaning_mode},
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        clean_dataset.delay(str(job.id))
        return BatchJobResponse(
            job_id=job.id,
            status=job.status.value if hasattr(job.status, "value") else str(job.status),
            created_at=job.created_at or datetime.now(timezone.utc),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to start batch job")
        raise HTTPException(status_code=500, detail="Server error while starting batch job.") from exc


@router.get("/{job_id}")
async def get_job_status(job_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Get job status and progress details."""
    job = db.get(CleaningJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    progress = 0.0
    if job.total_rows > 0:
        progress = min(1.0, float(job.rows_processed) / float(job.total_rows))

    status_value = job.status.value if hasattr(job.status, "value") else str(job.status)
    return {
        "id": job.id,
        "status": status_value,
        "progress": round(progress, 6),
        "rows_processed": job.rows_processed,
        "total_rows": job.total_rows,
        "current_score": job.result_score if job.result_score is not None else 0.0,
    }


@router.get("/{job_id}/audit-log")
async def get_job_audit_log(job_id: UUID, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """Return all persisted audit entries for a job."""
    job = db.get(CleaningJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    logs = (
        db.query(AuditLog)
        .filter(AuditLog.job_id == job_id)
        .order_by(AuditLog.timestamp.asc())
        .all()
    )
    response: list[dict[str, Any]] = []
    for item in logs:
        response.append(
            {
                "id": item.id,
                "job_id": item.job_id,
                "action_type": item.action_type,
                "row_index": item.row_index,
                "column": item.column,
                "old_value": item.old_value,
                "new_value": item.new_value,
                "reward": item.reward,
                "agent_used": item.agent_used,
                "confidence": item.confidence,
                "timestamp": item.timestamp,
            }
        )
    return response
