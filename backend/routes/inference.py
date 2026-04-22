"""Interactive inference route handlers."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.cleaning_service import CleaningService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/inference", tags=["inference"])


class InferenceStepRequest(BaseModel):
    """Request payload for interactive next-step inference."""

    job_id: UUID
    row_data: dict[str, Any] = Field(default_factory=dict)
    issues_detected: list[str] = Field(default_factory=list)


@router.post("/step")
async def interactive_step(
    payload: InferenceStepRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return next recommended cleaning action for the active row."""
    service = CleaningService(db)
    try:
        return await service.get_next_action(
            job_id=payload.job_id,
            row_data=payload.row_data,
            issues_detected=payload.issues_detected,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Inference step failed")
        raise HTTPException(status_code=500, detail="Server error during inference step.") from exc
