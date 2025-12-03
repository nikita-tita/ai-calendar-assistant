"""
API endpoints for external calendar synchronization.
"""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from typing import List, Optional
from pydantic import BaseModel
import secrets
import structlog

from app.services.sync_database import sync_db
from app.services.calendar_sync_service import calendar_sync_service
from app.models.calendar_sync import CalendarConnection, CalendarProvider
from datetime import datetime, timedelta

logger = structlog.get_logger()

router = APIRouter(prefix="/sync", tags=["Calendar Sync"])


# ==================== Request/Response Models ====================

class ConnectionResponse(BaseModel):
    """Response model for calendar connection."""
    id: int
    provider: str
    calendar_id: str
    calendar_name: str
    sync_enabled: bool
    last_sync_at: Optional[str] = None
    created_at: str


class SyncStatsResponse(BaseModel):
    """Response model for sync statistics."""
    imported: int
    updated: int
    deleted: int
    errors: int


# ==================== OAuth Flow ====================

# In-memory state storage (in production, use Redis)
_oauth_states = {}


@router.get("/connect/google")
async def connect_google_calendar(user_id: str):
    """
    Start Google Calendar OAuth flow.

    Args:
        user_id: Telegram user ID

    Returns:
        Redirect to Google OAuth consent screen
    """
    if not calendar_sync_service:
        raise HTTPException(status_code=503, detail="Calendar sync service not initialized")

    # Generate random state for CSRF protection
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "user_id": user_id,
        "provider": "google",
        "expires_at": datetime.now() + timedelta(minutes=10)
    }

    # Get authorization URL
    auth_url = calendar_sync_service.google_service.get_authorization_url(state)

    logger.info("google_oauth_started", user_id=user_id, state=state)

    return RedirectResponse(url=auth_url)


@router.get("/oauth/google/callback")
async def google_oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None
):
    """
    Google OAuth callback endpoint.

    Args:
        code: Authorization code from Google
        state: State parameter for CSRF protection
        error: Error message if authorization failed

    Returns:
        Success/error page
    """
    if error:
        logger.error("google_oauth_error", error=error)
        return HTMLResponse(f"""
            <html>
                <body>
                    <h1>Ошибка подключения</h1>
                    <p>Не удалось подключить Google Calendar: {error}</p>
                    <p><a href="javascript:window.close()">Закрыть окно</a></p>
                </body>
            </html>
        """, status_code=400)

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")

    # Validate state
    state_data = _oauth_states.pop(state, None)
    if not state_data:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    if datetime.now() > state_data["expires_at"]:
        raise HTTPException(status_code=400, detail="State expired")

    user_id = state_data["user_id"]

    try:
        # Exchange code for tokens
        tokens = await calendar_sync_service.google_service.exchange_code_for_tokens(code)

        # Calculate token expiration
        expires_at = datetime.now() + timedelta(seconds=tokens.get("expires_in", 3600))

        # Create connection in database
        connection = CalendarConnection(
            user_id=user_id,
            provider=CalendarProvider.GOOGLE,
            calendar_id="primary",  # Default calendar
            calendar_name="Google Calendar",
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            token_expires_at=expires_at,
            sync_enabled=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        connection_id = sync_db.create_connection(connection)

        logger.info("google_calendar_connected",
                   user_id=user_id,
                   connection_id=connection_id)

        # Start initial sync in background
        connection.id = connection_id
        import asyncio
        asyncio.create_task(
            calendar_sync_service.import_events_from_google(user_id, connection)
        )

        return HTMLResponse("""
            <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        body { font-family: Arial; text-align: center; padding: 50px; }
                        .success { color: green; }
                        .button {
                            display: inline-block;
                            padding: 10px 20px;
                            background: #4CAF50;
                            color: white;
                            text-decoration: none;
                            border-radius: 5px;
                            margin-top: 20px;
                        }
                    </style>
                </head>
                <body>
                    <h1 class="success">✅ Google Calendar подключен!</h1>
                    <p>Синхронизация запущена. Ваши события будут импортированы в течение нескольких минут.</p>
                    <p>События, созданные в боте, теперь автоматически добавляются в Google Calendar.</p>
                    <a href="javascript:window.close()" class="button">Закрыть окно</a>
                </body>
            </html>
        """)

    except Exception as e:
        logger.error("google_oauth_callback_error",
                    user_id=user_id,
                    error=str(e),
                    exc_info=True)
        return HTMLResponse(f"""
            <html>
                <body>
                    <h1>Ошибка</h1>
                    <p>Не удалось завершить подключение: {str(e)}</p>
                    <p><a href="javascript:window.close()">Закрыть окно</a></p>
                </body>
            </html>
        """, status_code=500)


# ==================== Connection Management ====================

@router.get("/connections/{user_id}", response_model=List[ConnectionResponse])
async def get_user_connections(user_id: str):
    """
    Get all calendar connections for a user.

    Args:
        user_id: Telegram user ID

    Returns:
        List of calendar connections
    """
    connections = sync_db.get_user_connections(user_id, enabled_only=False)

    return [
        ConnectionResponse(
            id=conn.id,
            provider=conn.provider.value,
            calendar_id=conn.calendar_id,
            calendar_name=conn.calendar_name,
            sync_enabled=conn.sync_enabled,
            last_sync_at=conn.last_sync_at.isoformat() if conn.last_sync_at else None,
            created_at=conn.created_at.isoformat()
        )
        for conn in connections
    ]


@router.post("/connections/{connection_id}/sync")
async def trigger_sync(connection_id: int):
    """
    Manually trigger sync for a connection.

    Args:
        connection_id: Connection ID

    Returns:
        Sync statistics
    """
    if not calendar_sync_service:
        raise HTTPException(status_code=503, detail="Calendar sync service not initialized")

    # Get connection
    import sqlite3
    with sqlite3.connect(sync_db.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM calendar_connections WHERE id = ?",
            (connection_id,)
        )
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Reconstruct connection object
    from app.models.calendar_sync import SyncDirection
    connection = CalendarConnection(
        id=row['id'],
        user_id=row['user_id'],
        provider=CalendarProvider(row['provider']),
        calendar_id=row['calendar_id'],
        calendar_name=row['calendar_name'],
        access_token=sync_db._decrypt(row['access_token']),
        refresh_token=sync_db._decrypt(row['refresh_token']) if row['refresh_token'] else None,
        token_expires_at=datetime.fromisoformat(row['token_expires_at']) if row['token_expires_at'] else None,
        sync_enabled=bool(row['sync_enabled']),
        sync_direction=SyncDirection(row['sync_direction']),
        last_sync_at=datetime.fromisoformat(row['last_sync_at']) if row['last_sync_at'] else None,
        last_sync_token=row['last_sync_token'],
        created_at=datetime.fromisoformat(row['created_at']),
        updated_at=datetime.fromisoformat(row['updated_at'])
    )

    # Trigger sync
    if connection.provider == CalendarProvider.GOOGLE:
        stats = await calendar_sync_service.import_events_from_google(
            connection.user_id,
            connection
        )
    else:
        raise HTTPException(status_code=400, detail=f"Provider {connection.provider} not supported")

    return SyncStatsResponse(**stats)


@router.delete("/connections/{connection_id}")
async def delete_connection(connection_id: int):
    """
    Delete calendar connection.

    Args:
        connection_id: Connection ID

    Returns:
        Success message
    """
    sync_db.delete_connection(connection_id)
    logger.info("connection_deleted_via_api", connection_id=connection_id)
    return {"status": "success", "message": "Connection deleted"}


@router.post("/connections/{connection_id}/toggle")
async def toggle_connection(connection_id: int, enabled: bool = Query(...)):
    """
    Enable/disable sync for a connection.

    Args:
        connection_id: Connection ID
        enabled: True to enable, False to disable

    Returns:
        Success message
    """
    import sqlite3
    with sqlite3.connect(sync_db.db_path) as conn:
        conn.execute(
            "UPDATE calendar_connections SET sync_enabled = ?, updated_at = ? WHERE id = ?",
            (1 if enabled else 0, datetime.now().isoformat(), connection_id)
        )
        conn.commit()

    logger.info("connection_toggled",
               connection_id=connection_id,
               enabled=enabled)

    return {"status": "success", "enabled": enabled}
