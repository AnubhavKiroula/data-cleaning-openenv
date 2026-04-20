"""Cleaning job ORM model."""

from __future__ import annotations

import enum
import json
import uuid

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, func, text, Text
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator

from backend.database import Base, GUID


class JSONField(TypeDecorator):
    """JSON field that works with both PostgreSQL and SQLite."""
    
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Convert dict to JSON string."""
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        """Convert JSON string back to dict."""
        if value is None:
            return {}
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}


class JobType(str, enum.Enum):
    """Supported cleaning job execution modes."""

    BATCH = "batch"
    INTERACTIVE = "interactive"


class JobStatus(str, enum.Enum):
    """Execution status of a cleaning job."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class CleaningJob(Base):
    """Tracks each data cleaning task lifecycle."""

    __tablename__ = "cleaning_jobs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(
        GUID(),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_type = Column(Enum(JobType, name="job_type_enum"), nullable=False, default=JobType.BATCH)
    status = Column(Enum(JobStatus, name="job_status_enum"), nullable=False, default=JobStatus.QUEUED)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    total_rows = Column(Integer, nullable=False, default=0)
    rows_processed = Column(Integer, nullable=False, default=0)
    error_message = Column(String(2000), nullable=True)
    result_score = Column(Float, nullable=True)
    job_metadata = Column(
        "metadata",
        JSONField,
        nullable=False,
        default=dict,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    dataset = relationship("Dataset", back_populates="cleaning_jobs")
    audit_logs = relationship(
        "AuditLog",
        back_populates="job",
        cascade="all, delete-orphan",
    )
