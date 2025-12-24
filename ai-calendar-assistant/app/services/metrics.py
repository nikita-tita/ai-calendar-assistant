"""Prometheus metrics for AI Calendar Assistant.

This module provides application metrics for monitoring with Prometheus.

Metrics collected:
- HTTP request count and latency
- Telegram message processing
- LLM API calls and token usage
- Rate limiting events
- Calendar operations

Usage:
    from app.services.metrics import (
        REQUEST_COUNT, REQUEST_LATENCY,
        TELEGRAM_MESSAGES, LLM_TOKENS
    )

    # Increment counter
    TELEGRAM_MESSAGES.labels(user_id="123", action="message").inc()

    # Observe histogram
    REQUEST_LATENCY.labels(method="POST", endpoint="/api/events").observe(0.5)
"""

from prometheus_client import Counter, Histogram, Gauge, Info, REGISTRY
import structlog

logger = structlog.get_logger()

# Application info
APP_INFO = Info(
    "calendar_bot",
    "AI Calendar Assistant application info"
)

# HTTP request metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Telegram metrics
TELEGRAM_MESSAGES = Counter(
    "telegram_messages_total",
    "Total Telegram messages processed",
    ["action", "success"]
)

TELEGRAM_ACTIVE_USERS = Gauge(
    "telegram_active_users",
    "Number of active users in the last hour"
)

# LLM metrics
LLM_REQUESTS = Counter(
    "llm_requests_total",
    "Total LLM API requests",
    ["model", "success"]
)

LLM_TOKENS = Counter(
    "llm_tokens_total",
    "Total LLM tokens used",
    ["model", "type"]  # type: input/output
)

LLM_LATENCY = Histogram(
    "llm_request_duration_seconds",
    "LLM request latency",
    ["model"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

LLM_COST = Counter(
    "llm_cost_rubles_total",
    "Total LLM cost in rubles",
    ["model"]
)

# Rate limiting metrics
RATE_LIMIT_EVENTS = Counter(
    "rate_limit_events_total",
    "Rate limiting events",
    ["action"]  # allowed, blocked, spam_detected
)

BLOCKED_USERS = Gauge(
    "blocked_users_current",
    "Current number of blocked users"
)

# Calendar metrics
CALENDAR_OPERATIONS = Counter(
    "calendar_operations_total",
    "Calendar operations",
    ["operation", "success"]  # operation: create, update, delete, query
)

# Error metrics
ERRORS = Counter(
    "errors_total",
    "Total errors",
    ["component", "error_type"]
)


def init_metrics():
    """Initialize application metrics with version info."""
    try:
        from app.config import settings
        APP_INFO.info({
            "version": "0.1.0",
            "environment": settings.app_env,
        })
        logger.info("prometheus_metrics_initialized")
    except Exception as e:
        logger.warning("prometheus_metrics_init_failed", error=str(e))


def get_metrics_text():
    """Generate Prometheus metrics text format."""
    from prometheus_client import generate_latest
    return generate_latest(REGISTRY).decode("utf-8")
