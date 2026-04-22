"""Tests for Prometheus metrics and middleware instrumentation."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app import app


def test_metrics_exported() -> None:
    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    body = response.text
    assert "cleaning_job_duration_seconds" in body
    assert "api_request_duration_seconds" in body
    assert "celery_task_duration_seconds" in body


def test_prometheus_format() -> None:
    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    assert "# HELP" in response.text
    assert "# TYPE" in response.text


def test_middleware_tracks_requests() -> None:
    with TestClient(app) as client:
        client.get("/health")
        metrics_response = client.get("/metrics")

    assert metrics_response.status_code == 200
    body = metrics_response.text
    assert "api_request_duration_seconds" in body
    assert 'endpoint="/health"' in body
