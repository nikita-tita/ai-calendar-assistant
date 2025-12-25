"""Main application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import structlog

from app.config import settings
from app.routers import telegram, events, admin, admin_v2, logs, todos
# Temporarily disabled - calendar_sync is independent microservice
# from app.routers import calendar_sync, health
# ARCHIVED - property is independent microservice (moved to _archived/property_bot_microservice)
# from app.routers import property
from app.utils.logger import setup_logging
from app.middleware import TelegramAuthMiddleware


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

# Add Telegram WebApp authentication middleware
# This validates all /api/events/* requests using HMAC signature
app.add_middleware(TelegramAuthMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
# app.include_router(health.router, tags=["health"])  # Disabled - microservice
app.include_router(telegram.router, prefix="/telegram", tags=["telegram"])
app.include_router(events.router, prefix="/api", tags=["events"])
app.include_router(todos.router, prefix="/api", tags=["todos"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(admin_v2.router, prefix="/api/admin/v2", tags=["admin_v2"])
# app.include_router(property.router, prefix="/api/property", tags=["property"])  # ARCHIVED - independent microservice
app.include_router(logs.router, prefix="/api/logs", tags=["logs"])
# app.include_router(calendar_sync.router, tags=["calendar_sync"])  # Disabled - microservice


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

    # ARCHIVED - Property Bot feed scheduler disabled (independent microservice)
    # if settings.property_feed_url:
    #     try:
    #         from app.services.property.feed_scheduler import feed_scheduler
    #         feed_scheduler.start()
    #         logger.info("property_feed_scheduler_started",
    #                    feed_url=settings.property_feed_url[:50] + "...")
    #     except Exception as e:
    #         logger.error("feed_scheduler_start_error", error=str(e), exc_info=True)
    # else:
    #     logger.warning("property_feed_url_not_configured",
    #                   message="Property feed auto-update disabled. Set PROPERTY_FEED_URL to enable.")

    # Calendar sync disabled - independent microservice
    # if settings.google_oauth_client_id and settings.google_oauth_client_secret:
    #     from app.services.calendar_sync_service import init_calendar_sync_service
    #     init_calendar_sync_service(
    #         google_client_id=settings.google_oauth_client_id,
    #         google_client_secret=settings.google_oauth_client_secret,
    #         google_redirect_uri=settings.google_oauth_redirect_uri or
    #             f"https://этонесамыйдлинныйдомен.рф/sync/oauth/google/callback"
    #     )
    #     logger.info("calendar_sync_initialized")
    #
    #     # Start background sync task
    #     import asyncio
    #     from app.services.calendar_sync_service import calendar_sync_service
    #     asyncio.create_task(_sync_task_loop())
    #     logger.info("background_sync_task_started")
    # else:
    #     logger.warning("google_oauth_not_configured",
    #                   message="Calendar sync disabled. Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET to enable.")


async def _sync_task_loop():
    """Background task that syncs calendars every 10 minutes."""
    import asyncio
    from app.services.calendar_sync_service import calendar_sync_service

    # Wait 30 seconds before first sync (let app startup complete)
    await asyncio.sleep(30)

    while True:
        try:
            if calendar_sync_service:
                await calendar_sync_service.sync_all_users()
        except Exception as e:
            logger.error("sync_task_error", error=str(e), exc_info=True)

        # Wait 10 minutes
        await asyncio.sleep(600)


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
