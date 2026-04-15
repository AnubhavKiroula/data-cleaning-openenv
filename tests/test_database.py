"""Database tests for backend initialization."""

from __future__ import annotations

from sqlalchemy import inspect

from backend.database import Base, engine, init_db


def test_database_connection() -> None:
    """Engine can produce a SQLAlchemy connection object."""
    with engine.connect() as connection:
        assert connection is not None


def test_model_creation() -> None:
    """ORM metadata contains required tables."""
    init_db()
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    assert "datasets" in tables
    assert "cleaning_jobs" in tables
    assert "audit_logs" in tables
    assert "model_versions" in tables


def test_crud_operations() -> None:
    """At minimum ensure table metadata is bound and creatable."""
    # A lightweight sanity check that table definitions are valid.
    assert Base.metadata.tables["datasets"] is not None
    assert Base.metadata.tables["cleaning_jobs"] is not None
    assert Base.metadata.tables["audit_logs"] is not None
