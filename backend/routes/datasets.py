"""Dataset route handlers."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models.dataset import Dataset
from backend.services.cleaning_service import CleaningService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/datasets", tags=["datasets"])

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class DatasetResponse(BaseModel):
    """Dataset metadata response model."""

    id: UUID
    filename: str
    rows: int
    columns: list[str]
    data_quality_score: float = Field(ge=0.0, le=1.0)

    model_config = {"from_attributes": True}


@router.post("/upload", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    task_name: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> DatasetResponse:
    """Upload a CSV/Excel file, persist metadata, and return profile information."""
    try:
        if file.content_type not in {
            "text/csv",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }:
            raise HTTPException(status_code=400, detail="Invalid format. Please upload CSV or Excel.")

        content = await file.read()
        if len(content) > settings.max_upload_size:
            raise HTTPException(status_code=413, detail="File too large.")

        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in {".csv", ".xlsx", ".xls"}:
            raise HTTPException(status_code=400, detail="Invalid format. Please upload CSV or Excel.")

        saved_path = UPLOAD_DIR / f"{task_name or 'task'}_{Path(file.filename or 'dataset').name}"
        with saved_path.open("wb") as output_file:
            output_file.write(content)

        if suffix == ".csv":
            frame = pd.read_csv(saved_path)
        else:
            frame = pd.read_excel(saved_path)

        missing_pct = float(frame.isna().sum().sum()) / max(frame.shape[0] * max(frame.shape[1], 1), 1)
        duplicate_pct = float(frame.duplicated().sum()) / max(len(frame), 1)
        quality_score = max(0.0, min(1.0, 1.0 - missing_pct - duplicate_pct))

        dataset = Dataset(
            filename=file.filename or saved_path.name,
            file_path=str(saved_path),
            file_size=len(content),
            rows=int(frame.shape[0]),
            columns=[str(col) for col in frame.columns.tolist()],
            data_quality_score=float(quality_score),
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        return DatasetResponse.model_validate(dataset)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Dataset upload failed")
        if "saved_path" in locals() and Path(saved_path).exists():
            Path(saved_path).unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Server error while uploading dataset.") from exc
    finally:
        await file.close()


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(dataset_id: UUID, db: Session = Depends(get_db)) -> DatasetResponse:
    """Fetch dataset metadata by ID."""
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return DatasetResponse.model_validate(dataset)


@router.get("/{dataset_id}/metrics")
async def get_dataset_metrics(dataset_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Return original vs cleaned metrics profile for a dataset."""
    service = CleaningService(db)
    try:
        return await service.calculate_metrics(dataset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to calculate dataset metrics")
        raise HTTPException(status_code=500, detail="Server error while computing metrics.") from exc
