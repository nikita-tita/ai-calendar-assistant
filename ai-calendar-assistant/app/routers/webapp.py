"""WebApp router for Telegram Web App interface."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import structlog

logger = structlog.get_logger()

# Create router
router = APIRouter()

# Setup templates - используем общую папку
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def webapp_main(request: Request):
    """Main Web App interface for Telegram."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )


@router.get("/health", response_class=HTMLResponse)
async def webapp_health(request: Request):
    """WebApp health check."""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebApp Health</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body>
        <h1>✅ WebApp is healthy</h1>
        <p>Telegram Web App interface is working</p>
    </body>
    </html>
    """)