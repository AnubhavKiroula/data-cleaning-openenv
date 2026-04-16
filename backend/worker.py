"""Celery worker startup entrypoint."""

from backend.config.celery_config import celery_app
from backend.tasks import cleaning_tasks  # noqa: F401

__all__ = ["celery_app"]
