"""Dataset ORM model."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from backend.database import Base


class DatasetStatus(str, enum.Enum):
    """Lifecycle states of an uploaded dataset."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    CLEANED = "cleaned"


class Dataset(Base):
    """Stores uploaded dataset metadata."""

    __tablename__ = "datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False, index=True)
    file_path = Column(String(1024), nullable=False)
    file_size = Column(Integer, nullable=False)
    rows = Column(Integer, nullable=False, default=0)
    columns = Column(ARRAY(String), nullable=False, default=list)
    data_quality_score = Column(Float, nullable=False, default=0.0)
    status = Column(
        Enum(DatasetStatus, name="dataset_status_enum"),
        nullable=False,
        default=DatasetStatus.UPLOADED,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    cleaning_jobs = relationship(
        "CleaningJob",
        back_populates="dataset",
        cascade="all, delete-orphan",
    )
