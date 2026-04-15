"""Audit log ORM model."""

from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from backend.database import Base


class AuditLog(Base):
    """Stores row-level transformations performed during cleaning."""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("cleaning_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type = Column(String(120), nullable=False, index=True)
    row_index = Column(Integer, nullable=True)
    column = Column(String(255), nullable=True)
    old_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)
    reward = Column(Float, nullable=True)
    agent_used = Column(String(120), nullable=True)
    confidence = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    job = relationship("CleaningJob", back_populates="audit_logs")
