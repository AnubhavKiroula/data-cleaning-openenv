"""Audit log ORM model."""

from __future__ import annotations

import json
import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func, Text
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
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return None


class AuditLog(Base):
    """Stores row-level transformations performed during cleaning."""

    __tablename__ = "audit_logs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        GUID(),
        ForeignKey("cleaning_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type = Column(String(120), nullable=False, index=True)
    row_index = Column(Integer, nullable=True)
    column = Column(String(255), nullable=True)
    old_value = Column(JSONField, nullable=True)
    new_value = Column(JSONField, nullable=True)
    reward = Column(Float, nullable=True)
    agent_used = Column(String(120), nullable=True)
    confidence = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    job = relationship("CleaningJob", back_populates="audit_logs")
