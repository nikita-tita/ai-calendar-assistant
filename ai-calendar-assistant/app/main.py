"""Main application entry point."""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.config import settings
from app.routers import telegram, events, admin, logs, webapp
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

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(telegram.router, prefix="/telegram", tags=["telegram"])
app.include_router(events.router, prefix="/api", tags=["events"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(logs.router, prefix="/api/logs", tags=["logs"])
app.include_router(webapp.router, prefix="/webapp", tags=["webapp"])
# app.include_router(calendar_sync.router, tags=["calendar_sync"])  # Disabled - microservice
# app.include_router(property.router, prefix="/api/property", tags=["property"])  # ARCHIVED - independent microservice
# app.include_router(health.router, tags=["health"])  # Disabled - microservice


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info(
        "application_started",
        environment=settings.app_env,
        debug=settings.debug,
    )

    await setup_telegram_webhook()

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

# async def _sync_task_loop():
#     """Background task that syncs calendars every 10 minutes."""
#     import asyncio
#     from app.services.calendar_sync_service import calendar_sync_service

#     # Wait 30 seconds before first sync (let app startup complete)
#     await asyncio.sleep(30)

#     while True:
#         try:
#             if calendar_sync_service:
#                 await calendar_sync_service.sync_all_users()
#         except Exception as e:
#             logger.error("sync_task_error", error=str(e), exc_info=True)

#         # Wait 10 minutes
#         await asyncio.sleep(600)

async def setup_telegram_webhook():
    """Setup Telegram webhook on application startup."""
    try:
        from app.routers.telegram import telegram_handler
        await telegram_handler.initialize()
        webhook_url = f"{settings.app_base_url}/telegram/webhook"
        
        # Устанавливаем вебхук
        success = await telegram_handler.set_webhook(
            url=webhook_url,
            secret_token=settings.telegram_webhook_secret
        )
        if success:
            logger.info(
                "telegram_webhook_setup_success",
                webhook_url=webhook_url,
                has_secret=bool(settings.telegram_webhook_secret)
            )
        else:
            logger.error(
                "telegram_webhook_setup_failed",
                webhook_url=webhook_url
            )
    except Exception as e:
        logger.error(
            "telegram_webhook_setup_error",
            error=str(e),
            exc_info=True
        )


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("application_shutdown")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}

@app.get("/")
async def root():
    """Root endpoint."""
    return RedirectResponse(url="/webapp")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
