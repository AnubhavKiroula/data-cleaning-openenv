"""Database engine and session management."""

from __future__ import annotations

import uuid
from typing import Generator

from sqlalchemy import JSON, Column, DateTime, String, Table, create_engine, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.types import CHAR, TypeDecorator

from backend.config import settings


class GUID(TypeDecorator):
    """Platform-independent GUID type that uses CHAR(32) on SQLite and UUID on PostgreSQL."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Adjust based on dialect."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        """Convert UUID to string for storage."""
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return str(value)
        else:
            if isinstance(value, uuid.UUID):
                return value.hex
            else:
                return value

    def process_result_value(self, value, dialect):
        """Convert string back to UUID."""
        if value is None:
            return value
        else:
            if isinstance(value, uuid.UUID):
                return value
            else:
                return uuid.UUID(value)


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
    Column("id", GUID(), primary_key=True, default=uuid.uuid4),
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
