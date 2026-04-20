"""Dataset ORM model."""

from __future__ import annotations

import enum
import json
import uuid

from sqlalchemy import Column, DateTime, Enum, Float, Integer, String, func, Text
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator

from backend.database import Base, GUID


class StringArray(TypeDecorator):
    """Hybrid type for storing string arrays, works with both PostgreSQL and SQLite."""
    
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Convert list to JSON string for storage."""
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        """Convert JSON string back to list on retrieval."""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []


class DatasetStatus(str, enum.Enum):
    """Lifecycle states of an uploaded dataset."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    CLEANED = "cleaned"


class Dataset(Base):
    """Stores uploaded dataset metadata."""

    __tablename__ = "datasets"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False, index=True)
    file_path = Column(String(1024), nullable=False)
    file_size = Column(Integer, nullable=False)
    rows = Column(Integer, nullable=False, default=0)
    columns = Column(StringArray, nullable=False, default=list)
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
