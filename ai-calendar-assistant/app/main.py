"""Main application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import structlog
from pathlib import Path

from app.config import settings
from app.routers import telegram, events, admin, logs, todos
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

# Mount static files BEFORE middleware (so they bypass auth)
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Telegram-Init-Data"],
)

# Add Telegram WebApp authentication middleware
# This validates /api/events/* and /api/todos/* requests using HMAC signature
app.add_middleware(TelegramAuthMiddleware)

# Include routers
app.include_router(telegram.router, prefix="/telegram", tags=["telegram"])
app.include_router(events.router, prefix="/api", tags=["events"])
app.include_router(todos.router, prefix="/api", tags=["todos"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(logs.router, prefix="/api/logs", tags=["logs"])


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info(
        "application_started",
        environment=settings.app_env,
        debug=settings.debug,
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
    return {
        "message": "AI Calendar Assistant API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/todos")
async def todos_webapp():
    """Serve todos webapp page."""
    static_path = Path(__file__).parent / "static" / "todos.html"
    if static_path.exists():
        return FileResponse(static_path)
    else:
        return {"error": "Todos webapp not found"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
