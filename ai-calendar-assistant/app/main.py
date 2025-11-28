from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import structlog
import traceback

from app.config import settings
from app.routers import telegram, events, admin, logs, webapp
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

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Глобальный обработчик исключений для отладки."""
    error_details = {
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "path": request.url.path,
        "method": request.method,
    }
    
    # Логируем полный traceback
    logger.error(
        "unhandled_exception",
        **error_details,
        traceback=traceback.format_exc()
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "error": str(exc) if settings.debug else "Internal server error"
        }
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
app.add_middleware(TelegramAuthMiddleware)

# Include routers
app.include_router(telegram.router, prefix="/telegram", tags=["telegram"])
app.include_router(events.router, prefix="/api", tags=["events"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(logs.router, prefix="/api/logs", tags=["logs"])
app.include_router(webapp.router, prefix="/webapp", tags=["webapp"])


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info(
        "application_started",
        environment=settings.app_env,
        debug=settings.debug,
    )
    
    await setup_telegram_webhook()

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
