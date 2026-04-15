"""Database engine and session management."""

from __future__ import annotations

from typing import Generator

from sqlalchemy import JSON, Column, DateTime, String, Table, create_engine, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


model_versions = Table(
    "model_versions",
    Base.metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("model_name", String(255), nullable=False, index=True),
    Column("version", String(50), nullable=False, index=True),
    Column("metrics", JSON, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)


def init_db() -> None:
    """Create all metadata-defined tables."""
    # Import ORM models so SQLAlchemy registers their metadata before create_all.
    from backend.models.audit_log import AuditLog  # noqa: F401
    from backend.models.cleaning_job import CleaningJob  # noqa: F401
    from backend.models.dataset import Dataset  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator:
    """Yield database session for request-scoped usage."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
