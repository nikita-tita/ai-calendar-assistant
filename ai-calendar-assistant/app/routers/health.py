"""Health check endpoints for monitoring service dependencies."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
import structlog

router = APIRouter()
logger = structlog.get_logger()


@router.get("/health")
async def health_check():
    """
    Comprehensive health check for all service dependencies.

    Returns JSON with status of each component:
    - radicale: CalDAV calendar server
    - redis: Rate limiter / cache
    - llm: YandexGPT API key configured
    - analytics: SQLite analytics DB

    HTTP 200 if all critical services are healthy.
    HTTP 503 if any critical service is down.
    """
    checks = {}
    overall_healthy = True

    # 1. Check Radicale CalDAV
    try:
        from app.services.calendar_radicale import calendar_service
        if calendar_service and calendar_service.is_connected():
            checks["radicale"] = {"status": "healthy", "detail": "CalDAV connected"}
        else:
            checks["radicale"] = {"status": "unhealthy", "detail": "CalDAV not connected"}
            overall_healthy = False
    except Exception as e:
        checks["radicale"] = {"status": "unhealthy", "detail": str(e)}
        overall_healthy = False

    # 2. Check Redis
    try:
        from app.services.rate_limiter_redis import is_redis_available
        if is_redis_available():
            checks["redis"] = {"status": "healthy", "detail": "Redis connected"}
        else:
            checks["redis"] = {"status": "degraded", "detail": "Redis unavailable, using in-memory fallback"}
            # Redis down is degraded, not critical
    except Exception as e:
        checks["redis"] = {"status": "degraded", "detail": str(e)}

    # 3. Check LLM API key
    try:
        from app.config import settings
        if settings.yandex_gpt_api_key:
            checks["llm"] = {"status": "healthy", "detail": "YandexGPT API key configured"}
        else:
            checks["llm"] = {"status": "unhealthy", "detail": "YandexGPT API key not set"}
            overall_healthy = False
    except Exception as e:
        checks["llm"] = {"status": "unhealthy", "detail": str(e)}
        overall_healthy = False

    # 4. Check Analytics DB
    try:
        from app.services.analytics_service import analytics_service
        if analytics_service:
            # Quick query to verify DB is accessible
            count = analytics_service.get_user_action_count("__health_check__")
            checks["analytics"] = {"status": "healthy", "detail": "SQLite accessible"}
        else:
            checks["analytics"] = {"status": "degraded", "detail": "Analytics not initialized"}
    except Exception as e:
        checks["analytics"] = {"status": "degraded", "detail": str(e)}

    status_code = 200 if overall_healthy else 503
    result = {
        "status": "healthy" if overall_healthy else "unhealthy",
        "checks": checks
    }

    logger.info("health_check", status=result["status"], checks={k: v["status"] for k, v in checks.items()})
    return JSONResponse(content=result, status_code=status_code)
