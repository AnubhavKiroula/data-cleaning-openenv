"""Tests for Celery cleaning tasks."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from celery.exceptions import Retry

from backend.models.cleaning_job import JobStatus
from backend.tasks import cleaning_tasks


class FakeSession:
    """Simple DB session double for Celery task tests."""

    def __init__(self) -> None:
        self.job = SimpleNamespace(
            id=uuid4(),
            dataset_id=uuid4(),
            status=JobStatus.QUEUED,
            rows_processed=0,
            total_rows=10,
            result_score=None,
            error_message=None,
            job_metadata={"cleaning_mode": "conservative"},
        )

    def get(self, _model, item_id):
        if item_id == self.job.id:
            return self.job
        return None

    def commit(self) -> None:
        return None

    def refresh(self, _item) -> None:
        return None

    def close(self) -> None:
        return None


@pytest.fixture()
def eager_celery():
    original_always_eager = cleaning_tasks.celery_app.conf.task_always_eager
    original_eager_propagates = cleaning_tasks.celery_app.conf.task_eager_propagates
    cleaning_tasks.celery_app.conf.task_always_eager = True
    cleaning_tasks.celery_app.conf.task_eager_propagates = True
    yield
    cleaning_tasks.celery_app.conf.task_always_eager = original_always_eager
    cleaning_tasks.celery_app.conf.task_eager_propagates = original_eager_propagates


def test_clean_dataset_task(monkeypatch: pytest.MonkeyPatch, eager_celery) -> None:
    fake_db = FakeSession()

    monkeypatch.setattr(cleaning_tasks, "SessionLocal", lambda: fake_db)

    async def _clean_existing_job(_self, job, _cleaning_mode):
        job.status = JobStatus.COMPLETED
        job.rows_processed = job.total_rows
        job.result_score = 0.91
        return job

    monkeypatch.setattr(cleaning_tasks.CleaningService, "clean_existing_job", _clean_existing_job)

    result = cleaning_tasks.clean_dataset.delay(str(fake_db.job.id)).get()

    assert result["status"] == "completed"
    assert result["rows_processed"] == fake_db.job.total_rows
    assert result["result_score"] == 0.91


def test_task_retry_on_failure(monkeypatch: pytest.MonkeyPatch, eager_celery) -> None:
    fake_db = FakeSession()
    monkeypatch.setattr(cleaning_tasks, "SessionLocal", lambda: fake_db)

    async def _raise_error(_self, _job, _cleaning_mode):
        raise RuntimeError("boom")

    monkeypatch.setattr(cleaning_tasks.CleaningService, "clean_existing_job", _raise_error)

    with pytest.raises(Retry):
        cleaning_tasks.clean_dataset.delay(str(fake_db.job.id)).get()

    assert fake_db.job.status == JobStatus.FAILED
    assert fake_db.job.error_message is not None


def test_progress_update(monkeypatch: pytest.MonkeyPatch, eager_celery) -> None:
    fake_db = FakeSession()
    monkeypatch.setattr(cleaning_tasks, "SessionLocal", lambda: fake_db)

    async def _update_progress(_self, job, _cleaning_mode):
        job.status = JobStatus.COMPLETED
        job.rows_processed = 8
        job.total_rows = 10
        job.result_score = 0.75
        return job

    monkeypatch.setattr(cleaning_tasks.CleaningService, "clean_existing_job", _update_progress)

    result = cleaning_tasks.clean_dataset.delay(str(fake_db.job.id)).get()
    assert result["rows_processed"] == 8
    assert result["total_rows"] == 10
