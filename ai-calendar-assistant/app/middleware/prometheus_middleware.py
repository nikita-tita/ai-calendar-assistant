"""Prometheus metrics middleware for HTTP request instrumentation.

INFRA-002: Prometheus + Grafana monitoring setup.

This middleware automatically collects metrics for all HTTP requests:
- Request count by method, endpoint, and status
- Request latency histograms by method and endpoint

Usage:
    from app.middleware.prometheus_middleware import PrometheusMiddleware
    app.add_middleware(PrometheusMiddleware)
"""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog

logger = structlog.get_logger()


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware that instruments HTTP requests with Prometheus metrics.

    Collects:
    - http_requests_total: Counter of total requests by method/endpoint/status
    - http_request_duration_seconds: Histogram of request latency

    Endpoints excluded from metrics:
    - /metrics (to avoid recursive metrics)
    - /health (high frequency, low value)
    """

    # Endpoints to exclude from metrics collection
    EXCLUDED_ENDPOINTS = {"/metrics", "/health"}

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and collect metrics."""
        # Skip metrics collection for excluded endpoints
        endpoint = request.url.path
        if endpoint in self.EXCLUDED_ENDPOINTS:
            return await call_next(request)

        # Normalize endpoint to avoid high cardinality
        # e.g., /api/events/123 -> /api/events/{id}
        normalized_endpoint = self._normalize_endpoint(endpoint)

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            # Record 500 error for unhandled exceptions
            status_code = 500
            logger.error(
                "request_error",
                endpoint=endpoint,
                method=request.method,
                error=str(e)
            )
            raise
        finally:
            # Calculate duration
            duration = time.perf_counter() - start_time

            # Record metrics
            try:
                from app.services.metrics import REQUEST_COUNT, REQUEST_LATENCY

                REQUEST_COUNT.labels(
                    method=request.method,
                    endpoint=normalized_endpoint,
                    status=str(status_code)
                ).inc()

                REQUEST_LATENCY.labels(
                    method=request.method,
                    endpoint=normalized_endpoint
                ).observe(duration)
            except Exception as e:
                # Don't fail request if metrics collection fails
                logger.warning("metrics_collection_failed", error=str(e))

        return response

    def _normalize_endpoint(self, endpoint: str) -> str:
        """Normalize endpoint to reduce cardinality.

        Replaces dynamic path segments with placeholders:
        - /api/events/123 -> /api/events/{id}
        - /api/todos/456 -> /api/todos/{id}
        - /telegram/webhook/abc123 -> /telegram/webhook/{token}

        Args:
            endpoint: Original request path

        Returns:
            Normalized path with placeholders
        """
        parts = endpoint.split("/")
        normalized_parts = []

        for i, part in enumerate(parts):
            if not part:
                normalized_parts.append(part)
                continue

            # Check if this looks like an ID (numeric or UUID-like)
            if self._is_dynamic_segment(part):
                normalized_parts.append("{id}")
            else:
                normalized_parts.append(part)

        return "/".join(normalized_parts)

    def _is_dynamic_segment(self, segment: str) -> bool:
        """Check if a path segment is dynamic (ID, UUID, etc).

        Args:
            segment: Path segment to check

        Returns:
            True if segment appears to be a dynamic value
        """
        # Pure numeric IDs
        if segment.isdigit():
            return True

        # UUID-like patterns (contains mostly hex chars and dashes)
        if len(segment) >= 32:
            hex_chars = sum(1 for c in segment if c in "0123456789abcdefABCDEF-")
            if hex_chars / len(segment) > 0.8:
                return True

        # Telegram user IDs (long numbers)
        if len(segment) >= 8 and segment.isdigit():
            return True

        return False
