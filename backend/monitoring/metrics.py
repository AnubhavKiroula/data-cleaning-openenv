"""Prometheus metric definitions and helpers."""

from __future__ import annotations

from contextlib import contextmanager
from time import perf_counter
from typing import Generator

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

cleaning_job_duration_seconds = Histogram(
    "cleaning_job_duration_seconds",
    "Time taken to clean a dataset",
    labelnames=("task_difficulty", "status"),
)

cleaning_accuracy_score = Gauge(
    "cleaning_accuracy_score",
    "Data quality score of cleaned dataset (0-1)",
    labelnames=("task_difficulty",),
)

agent_action_count = Counter(
    "agent_action_count",
    "Number of each action type taken",
    labelnames=("action_type", "agent"),
)

api_request_duration_seconds = Histogram(
    "api_request_duration_seconds",
    "API endpoint response time",
    labelnames=("method", "endpoint", "status"),
)

celery_task_duration_seconds = Histogram(
    "celery_task_duration_seconds",
    "Background task execution time",
    labelnames=("task_name", "status"),
)

inference_latency_ms = Histogram(
    "inference_latency_ms",
    "ML model inference speed",
    labelnames=("model_type", "task"),
)


def export_metrics() -> tuple[bytes, str]:
    """Serialize all Prometheus metrics for `/metrics` endpoint."""
    return generate_latest(), CONTENT_TYPE_LATEST


@contextmanager
def track_inference_latency(model_type: str, task: str) -> Generator[None, None, None]:
    """Record inference latency in milliseconds."""
    start = perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (perf_counter() - start) * 1000.0
        inference_latency_ms.labels(model_type=model_type, task=task).observe(elapsed_ms)


@contextmanager
def track_cleaning_job_duration(task_difficulty: str) -> Generator[dict[str, str], None, None]:
    """Track total cleaning lifecycle duration with completion status label."""
    start = perf_counter()
    metric_state = {"status": "failed"}
    try:
        yield metric_state
    finally:
        elapsed_seconds = perf_counter() - start
        cleaning_job_duration_seconds.labels(
            task_difficulty=task_difficulty,
            status=metric_state["status"],
        ).observe(elapsed_seconds)


@contextmanager
def track_celery_task_duration(task_name: str) -> Generator[dict[str, str], None, None]:
    """Track Celery task duration with completion status label."""
    start = perf_counter()
    metric_state = {"status": "failed"}
    try:
        yield metric_state
    finally:
        elapsed_seconds = perf_counter() - start
        celery_task_duration_seconds.labels(task_name=task_name, status=metric_state["status"]).observe(
            elapsed_seconds
        )
