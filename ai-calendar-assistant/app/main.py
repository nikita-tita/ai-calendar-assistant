"""Main application entry point."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import structlog

from app.config import settings
from app.routers import telegram, events, admin, admin_v2, logs, todos
from app.utils.logger import setup_logging
from app.middleware import TelegramAuthMiddleware, SecurityHeadersMiddleware, CSRFProtectionMiddleware, PrometheusMiddleware


# Setup logging
setup_logging(settings.log_level)
logger = structlog.get_logger()

# Create FastAPI application
app = FastAPI(
    title="AI Calendar Assistant",
    description="Интеллектуальный календарный ассистент с поддержкой естественного языка",
    version="0.1.0",
    debug=settings.debug,
)

# SEC-006: Register slowapi rate limiter for admin endpoints
# This enables distributed rate limiting via Redis
from app.routers.admin_v2 import limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware with restricted origins
# Parse CORS origins from config (comma-separated string)
allowed_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]

# Allow localhost/127.0.0.1 in development mode
if settings.debug:
    allowed_origins.extend([
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000"
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Telegram-Init-Data"],
)

# Add security headers middleware (SEC-005)
# Adds X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, etc.
app.add_middleware(
    SecurityHeadersMiddleware,
    enable_hsts=not settings.debug,  # HSTS only in production
    enable_csp=False  # CSP disabled by default - can break inline scripts
)

# Add CSRF protection middleware (SEC-004)
# Validates Origin header for state-changing requests to admin endpoints
app.add_middleware(CSRFProtectionMiddleware)

# Add Telegram WebApp authentication middleware
# This validates all /api/events/* requests using HMAC signature
app.add_middleware(TelegramAuthMiddleware)

# INFRA-002: Add Prometheus metrics middleware
# Instruments all HTTP requests with timing and count metrics
app.add_middleware(PrometheusMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(telegram.router, prefix="/telegram", tags=["telegram"])
app.include_router(events.router, prefix="/api", tags=["events"])
app.include_router(todos.router, prefix="/api", tags=["todos"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(admin_v2.router, prefix="/api/admin/v2", tags=["admin_v2"])
app.include_router(logs.router, prefix="/api/logs", tags=["logs"])


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info(
        "application_started",
        environment=settings.app_env,
        debug=settings.debug,
    )

    # Initialize Prometheus metrics
    try:
        from app.services.metrics import init_metrics
        init_metrics()
    except Exception as e:
        logger.warning("metrics_init_failed", error=str(e))

    # Initialize Redis rate limiter
    try:
        from app.services.rate_limiter_redis import init_redis_rate_limiter
        init_redis_rate_limiter()
        logger.info("redis_rate_limiter_enabled")
    except Exception as e:
        logger.warning("redis_rate_limiter_failed_using_memory", error=str(e))


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event - flush all buffers and close connections."""
    logger.info("application_shutdown_started")

    # Flush analytics buffer
    try:
        from app.services.analytics_service import analytics_service
        if analytics_service:
            analytics_service.flush()
            logger.info("analytics_flushed_on_shutdown")
    except Exception as e:
        logger.error("analytics_flush_error", error=str(e))

    # Flush user preferences
    try:
        from app.services.user_preferences import user_preferences
        if user_preferences:
            user_preferences.flush()
            logger.info("preferences_flushed_on_shutdown")
    except Exception as e:
        logger.error("preferences_flush_error", error=str(e))

    # Close LLM agent HTTP client
    try:
        from app.services.llm_agent_yandex import llm_agent_yandex
        if llm_agent_yandex:
            await llm_agent_yandex.close()
            logger.info("llm_agent_closed_on_shutdown")
    except Exception as e:
        logger.error("llm_agent_close_error", error=str(e))

    logger.info("application_shutdown_complete")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    from fastapi.responses import PlainTextResponse
    try:
        from app.services.metrics import get_metrics_text
        return PlainTextResponse(
            content=get_metrics_text(),
            media_type="text/plain; charset=utf-8"
        )
    except ImportError:
        return PlainTextResponse(
            content="# Metrics not available\n",
            media_type="text/plain"
        )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AI Calendar Assistant API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/app")
async def webapp():
    """WebApp endpoint - serve index.html with no-cache headers."""
    return FileResponse(
        "app/static/index.html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@app.get("/admin")
async def admin_panel():
    """Admin panel endpoint - serve admin.html with no-cache headers."""
    return FileResponse(
        "app/static/admin.html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
