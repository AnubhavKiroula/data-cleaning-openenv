"""Request middleware for API latency metrics."""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from backend.monitoring.metrics import api_request_duration_seconds


class MetricsMiddleware(BaseHTTPMiddleware):
    """Capture request duration/status and emit Prometheus metrics."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            elapsed = time.perf_counter() - start
            api_request_duration_seconds.labels(
                method=request.method,
                endpoint=request.url.path,
                status=str(status_code),
            ).observe(elapsed)
