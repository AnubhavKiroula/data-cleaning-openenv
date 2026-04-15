"""API tests for core Phase 2.2 endpoints."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.database import get_db
from backend.models.cleaning_job import JobStatus
from backend.routes import datasets as datasets_routes
from backend.services.cleaning_service import CleaningService


@dataclass
class DummyDataset:
    """Simple test double for Dataset ORM instances."""

    id: UUID = field(default_factory=uuid4)
    filename: str = "sample.csv"
    file_path: str = ""
    file_size: int = 128
    rows: int = 3
    columns: list[str] = field(default_factory=lambda: ["name", "age"])
    data_quality_score: float = 0.7


@dataclass
class DummyJob:
    """Simple test double for CleaningJob ORM instances."""

    id: UUID = field(default_factory=uuid4)
    dataset_id: UUID = field(default_factory=uuid4)
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    rows_processed: int = 0
    total_rows: int = 0
    result_score: float = 0.0


class FakeQuery:
    def __init__(self, logs: list[dict[str, Any]]) -> None:
        self.logs = logs

    def filter(self, *_args: Any, **_kwargs: Any) -> "FakeQuery":
        return self

    def order_by(self, *_args: Any, **_kwargs: Any) -> "FakeQuery":
        return self

    def all(self) -> list[dict[str, Any]]:
        return self.logs


class FakeDB:
    """Minimal fake DB session for API tests."""

    def __init__(self, dataset: DummyDataset, job: DummyJob, logs: list[dict[str, Any]]) -> None:
        self.dataset = dataset
        self.job = job
        self.logs = logs

    def add(self, item: Any) -> None:
        if hasattr(item, "filename"):
            item.id = self.dataset.id
            self.dataset = item
        if hasattr(item, "dataset_id") and hasattr(item, "status"):
            item.id = self.job.id
            item.created_at = self.job.created_at
            self.job = item

    def commit(self) -> None:
        return None

    def flush(self) -> None:
        return None

    def refresh(self, item: Any) -> None:
        if hasattr(item, "rows_processed"):
            item.status = self.job.status
            item.result_score = self.job.result_score
        return None

    def get(self, model: Any, item_id: UUID) -> Any:
        name = getattr(model, "__name__", "")
        if name == "Dataset" and item_id == self.dataset.id:
            return self.dataset
        if name == "CleaningJob" and item_id == self.job.id:
            return self.job
        return None

    def query(self, _model: Any) -> FakeQuery:
        return FakeQuery(self.logs)


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    dataset_file = tmp_path / "sample.csv"
    dataset_file.write_text("name,age\nalice,30\nbob,\ncharlie,22\n", encoding="utf-8")

    dataset = DummyDataset(file_path=str(dataset_file))
    job = DummyJob(dataset_id=dataset.id, total_rows=3)
    logs = [
        {
            "id": str(uuid4()),
            "job_id": job.id,
            "action_type": "fill_missing",
            "row_index": 1,
            "column": "age",
            "old_value": None,
            "new_value": 25,
            "reward": 0.2,
            "agent_used": "FillMissingAgent",
            "confidence": 0.88,
            "timestamp": datetime.now(timezone.utc),
        }
    ]
    fake_db = FakeDB(dataset=dataset, job=job, logs=logs)

    def _get_test_db() -> Any:
        yield fake_db

    app.dependency_overrides[get_db] = _get_test_db
    monkeypatch.setattr(datasets_routes, "UPLOAD_DIR", tmp_path)

    async def _mock_clean_batch(self: CleaningService, dataset_id: UUID, cleaning_mode: str) -> Any:
        assert cleaning_mode in {"aggressive", "conservative"}
        assert dataset_id == dataset.id
        fake_db.job.status = JobStatus.COMPLETED
        fake_db.job.rows_processed = fake_db.job.total_rows
        fake_db.job.result_score = 0.92
        return fake_db.job

    monkeypatch.setattr(CleaningService, "clean_batch", _mock_clean_batch)
    app.state.test_dataset_id = dataset.id
    app.state.test_job_id = job.id
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def test_upload_dataset(client: TestClient) -> None:
    response = client.post(
        "/api/datasets/upload",
        files={"file": ("upload.csv", b"name,age\nalice,30\nbob,\n", "text/csv")},
        data={"task_name": "easy"},
    )
    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert body["filename"] == "upload.csv"
    assert body["rows"] == 2
    assert body["columns"] == ["name", "age"]


def test_get_dataset(client: TestClient) -> None:
    known_dataset_id = str(app.state.test_dataset_id)
    response = client.get(f"/api/datasets/{known_dataset_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == known_dataset_id


def test_start_batch_job(client: TestClient) -> None:
    dataset_id = str(app.state.test_dataset_id)
    response = client.post(
        "/api/jobs/batch",
        json={"dataset_id": dataset_id, "cleaning_mode": "conservative"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] in {"completed", "queued", "processing"}
    assert "job_id" in payload


def test_get_job_status(client: TestClient) -> None:
    job_id = str(app.state.test_job_id)
    response = client.get(f"/api/jobs/{job_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == job_id
    assert 0.0 <= payload["progress"] <= 1.0


def test_interactive_step(client: TestClient) -> None:
    job_id = str(app.state.test_job_id)
    response = client.post(
        "/api/inference/step",
        json={
            "job_id": job_id,
            "row_data": {"name": "bob", "age": None},
            "issues_detected": ["missing:age"],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert "action" in payload
    assert "confidence" in payload
    assert "agent_used" in payload
    assert "explanation" in payload


def test_metrics_calculation(client: TestClient) -> None:
    dataset_id = str(app.state.test_dataset_id)
    response = client.get(f"/api/datasets/{dataset_id}/metrics")
    assert response.status_code == 200
    payload = response.json()
    assert "original" in payload
    assert "cleaned" in payload
    assert "improvement" in payload


def test_upload_dataset_invalid_format(client: TestClient) -> None:
    response = client.post(
        "/api/datasets/upload",
        files={"file": ("bad.txt", b"not,a,csv", "text/plain")},
        data={"task_name": "easy"},
    )
    assert response.status_code == 400
    assert "Invalid format" in response.json()["detail"]


def test_get_dataset_not_found(client: TestClient) -> None:
    unknown_dataset_id = str(uuid4())
    response = client.get(f"/api/datasets/{unknown_dataset_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset not found"


