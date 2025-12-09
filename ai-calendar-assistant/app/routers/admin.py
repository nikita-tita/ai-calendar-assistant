"""Admin API router with 3-password authentication, rate limiting and fake mode."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Header, Query, Body, Request
from datetime import datetime, timedelta
from pydantic import BaseModel
import structlog
import bcrypt
import pytz
import secrets
import os
import jwt
import asyncio
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.services.analytics_service import analytics_service
from app.services.calendar_radicale import calendar_service
from app.services.todos_service import todos_service
from app.models.analytics import (
    AdminDashboardStats, UserDetail, UserDialogEntry
)
from app.config import settings

logger = structlog.get_logger()

# JWT secret key - use existing SECRET_KEY from settings or generate one
JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24  # Token valid for 24 hours

# Rate limiter for admin endpoints (stricter than general API)
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=getattr(settings, 'redis_url', 'memory://'),
)

router = APIRouter()

# Admin passwords - loaded from environment variables for security
# Set these in .env file:
# ADMIN_PASSWORD_1=your_primary_password (or ADMIN_PRIMARY_PASSWORD for backward compatibility)
# ADMIN_PASSWORD_2=your_secondary_password (or ADMIN_SECONDARY_PASSWORD)
# ADMIN_PASSWORD_3=your_tertiary_password (or ADMIN_TERTIARY_PASSWORD)

# Support both old and new env var names for backward compatibility
PASSWORD_1 = os.getenv("ADMIN_PASSWORD_1") or os.getenv("ADMIN_PRIMARY_PASSWORD", "")
PASSWORD_2 = os.getenv("ADMIN_PASSWORD_2") or os.getenv("ADMIN_SECONDARY_PASSWORD", "")
PASSWORD_3 = os.getenv("ADMIN_PASSWORD_3") or os.getenv("ADMIN_TERTIARY_PASSWORD", "")

# SECURITY: All three passwords are now required
if not PASSWORD_1 or not PASSWORD_2 or not PASSWORD_3:
    logger.error("admin_passwords_not_configured",
                message="ADMIN_PASSWORD_1, ADMIN_PASSWORD_2 and ADMIN_PASSWORD_3 must be set in environment")
    raise ValueError("Admin passwords not configured. Set ADMIN_PASSWORD_1, ADMIN_PASSWORD_2 and ADMIN_PASSWORD_3 in .env file")

# SECURITY: Use bcrypt instead of SHA-256 (resistant to rainbow tables, includes salt)
PASSWORD_1_HASH = bcrypt.hashpw(PASSWORD_1.encode('utf-8'), bcrypt.gensalt(rounds=12))
PASSWORD_2_HASH = bcrypt.hashpw(PASSWORD_2.encode('utf-8'), bcrypt.gensalt(rounds=12))
PASSWORD_3_HASH = bcrypt.hashpw(PASSWORD_3.encode('utf-8'), bcrypt.gensalt(rounds=12))


class LoginRequest(BaseModel):
    """Login request with 3 passwords."""
    password1: str
    password2: str
    password3: str


def verify_password(password: str, hashed: bytes) -> bool:
    """Verify password against bcrypt hash (timing-safe comparison)."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed)


def verify_three_passwords(pwd1: str, pwd2: str, pwd3: str) -> str:
    """
    Verify all three admin passwords using bcrypt.

    Logic:
    - All 3 correct -> "real" (full access)
    - Password 1 & 2 correct, Password 3 wrong -> "fake" (fake database error page)
    - Any other combination -> "invalid" (show error)

    Returns:
        - "real" if all 3 passwords correct
        - "fake" if passwords 1 & 2 correct, password 3 wrong
        - "invalid" for any other combination
    """
    # Use bcrypt timing-safe comparison
    pwd1_correct = verify_password(pwd1, PASSWORD_1_HASH)
    pwd2_correct = verify_password(pwd2, PASSWORD_2_HASH)
    pwd3_correct = verify_password(pwd3, PASSWORD_3_HASH)

    # All 3 correct -> real access
    if pwd1_correct and pwd2_correct and pwd3_correct:
        return "real"

    # Passwords 1 & 2 correct, but 3 wrong -> fake mode
    if pwd1_correct and pwd2_correct and not pwd3_correct:
        return "fake"

    # Any other combination -> invalid
    return "invalid"


def create_jwt_token(mode: str) -> str:
    """
    Create a JWT token for admin session.

    Token contains:
    - mode: "real" or "fake"
    - exp: expiration timestamp
    - iat: issued at timestamp
    """
    now = datetime.utcnow()
    payload = {
        "mode": mode,
        "exp": now + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": now
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[str]:
    """
    Verify JWT token from Authorization header.

    Returns:
        - "real" if valid real token
        - "fake" if valid fake token
        - None if invalid or expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("mode")
    except jwt.ExpiredSignatureError:
        logger.debug("admin_token_expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug("admin_token_invalid", error=str(e))
        return None


@router.post("/verify")
@limiter.limit("5/minute")  # SECURITY: Strict rate limit to prevent brute-force attacks
async def verify_passwords(request: Request, login_request: LoginRequest):
    """
    Verify all three admin passwords.

    Rate limited to 5 attempts per minute per IP to prevent brute-force attacks.

    Returns:
        - {"valid": true, "mode": "real", "token": "..."} if all 3 correct
        - {"valid": true, "mode": "fake", "token": "..."} if passwords 1&2 correct, 3 wrong
        - {"valid": false, "error": "invalid_credentials"} for any other combination
    """
    try:
        auth_type = verify_three_passwords(
            login_request.password1,
            login_request.password2,
            login_request.password3
        )

        if auth_type == "invalid":
            logger.warning("admin_login_failed",
                          reason="invalid_credentials",
                          ip=request.client.host if request.client else "unknown")
            return {"valid": False, "error": "invalid_credentials"}

        logger.info("admin_login_success",
                   mode=auth_type,
                   ip=request.client.host if request.client else "unknown")

        # Generate JWT token (survives server restarts)
        token = create_jwt_token(auth_type)

        return {"valid": True, "mode": auth_type, "token": token}

    except Exception as e:
        logger.error("admin_verify_error", error=str(e), exc_info=True)
        return {"valid": False, "error": "server_error"}


@router.get("/stats", response_model=AdminDashboardStats)
async def get_admin_stats(authorization: str = Header(..., alias="Authorization")):
    """
    Get admin dashboard statistics.

    Requires Authorization header with admin password.
    """
    try:
        # Extract token
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization

        auth_type = verify_token(token)

        if not auth_type:
            raise HTTPException(status_code=401, detail="Unauthorized")

        if auth_type == "fake":
            # Return fake stats (all zeros)
            logger.info("admin_stats_accessed_fake_mode")
            return AdminDashboardStats(
                total_logins=0,
                active_users_today=0,
                active_users_week=0,
                active_users_month=0,
                total_users=0,
                total_actions=0,
                total_events_created=0,
                total_messages=0
            )

        # Return real stats
        stats = analytics_service.get_admin_stats()
        logger.info("admin_stats_accessed", stats=stats)
        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_stats_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users", response_model=List[UserDetail])
async def get_all_users(authorization: str = Header(..., alias="Authorization")):
    """
    Get detailed information for all users.

    Requires Authorization header with admin password.
    """
    try:
        # Extract token
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization

        auth_type = verify_token(token)

        if not auth_type:
            raise HTTPException(status_code=401, detail="Unauthorized")

        if auth_type == "fake":
            # Return empty list
            logger.info("admin_users_accessed_fake_mode")
            return []

        # Return real user details
        users = analytics_service.get_all_users_details()
        logger.info("admin_users_accessed", count=len(users))
        return users

    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_users_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/dialog", response_model=List[UserDialogEntry])
async def get_user_dialog(
    user_id: str,
    authorization: str = Header(..., alias="Authorization"),
    limit: int = Query(1000, ge=1, le=10000)
):
    """
    Get complete dialog history for a specific user.

    Requires Authorization header with admin password.
    """
    try:
        # Extract token
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization

        auth_type = verify_token(token)

        if not auth_type:
            raise HTTPException(status_code=401, detail="Unauthorized")

        if auth_type == "fake":
            # Return empty dialog
            logger.info("admin_user_dialog_accessed_fake_mode", user_id=user_id)
            return []

        # Return real dialog
        dialog = analytics_service.get_user_dialog(user_id, limit)
        logger.info("admin_user_dialog_accessed", user_id=user_id, entries=len(dialog))
        return dialog

    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_user_dialog_error", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/events")
async def get_user_events(
    user_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """
    Get all calendar events for a specific user.

    Requires Authorization header with admin password.
    """
    try:
        # Extract token
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization

        auth_type = verify_token(token)

        if not auth_type:
            raise HTTPException(status_code=401, detail="Unauthorized")

        if auth_type == "fake":
            # Return empty list
            logger.info("admin_user_events_accessed_fake_mode", user_id=user_id)
            return []

        # Get events for the last 90 days and next 90 days
        now = datetime.now()
        start = now - timedelta(days=90)
        end = now + timedelta(days=90)

        events = await calendar_service.list_events(user_id, start, end)

        # Convert to dict format
        events_data = [
            {
                "id": e.id,
                "title": e.summary,
                "start": e.start.isoformat(),
                "end": e.end.isoformat(),
                "location": e.location,
                "description": e.description
            }
            for e in events
        ]

        logger.info("admin_user_events_accessed", user_id=user_id, count=len(events_data))
        return events_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_user_events_error", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/todos")
async def get_user_todos(
    user_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """
    Get all todos for a specific user.

    Requires Authorization header with admin token.
    """
    try:
        # Extract token
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization

        auth_type = verify_token(token)

        if not auth_type:
            raise HTTPException(status_code=401, detail="Unauthorized")

        if auth_type == "fake":
            logger.info("admin_user_todos_accessed_fake_mode", user_id=user_id)
            return []

        # Get todos for user
        todos = await todos_service.list_todos(user_id)

        # Convert to dict format
        todos_data = [
            {
                "id": todo.id,
                "title": todo.title,
                "completed": todo.completed,
                "priority": todo.priority,
                "due_date": todo.due_date.isoformat() if todo.due_date else None,
                "created_at": todo.created_at.isoformat() if todo.created_at else None
            }
            for todo in todos
        ]

        logger.info("admin_user_todos_accessed", user_id=user_id, count=len(todos_data))
        return todos_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_user_todos_error", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeline")
async def get_activity_timeline(
    authorization: str = Header(..., alias="Authorization"),
    hours: int = Query(24, ge=1, le=168)
):
    """
    Get activity timeline for the last N hours.

    Requires Authorization header with admin token.
    """
    try:
        # Extract token
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization

        auth_type = verify_token(token)

        if not auth_type:
            raise HTTPException(status_code=401, detail="Unauthorized")

        if auth_type == "fake":
            logger.info("admin_timeline_accessed_fake_mode")
            return []

        # Return real timeline
        timeline = analytics_service.get_activity_timeline(hours)
        logger.info("admin_timeline_accessed", hours=hours, points=len(timeline))

        # Convert to dict format for JSON
        return [
            {"timestamp": point.timestamp.isoformat(), "value": point.value}
            for point in timeline
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_timeline_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actions")
async def get_recent_actions(
    authorization: str = Header(..., alias="Authorization"),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get recent actions from all users.

    Requires Authorization header with admin token.
    """
    try:
        # Extract token
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization

        auth_type = verify_token(token)

        if not auth_type:
            raise HTTPException(status_code=401, detail="Unauthorized")

        if auth_type == "fake":
            logger.info("admin_actions_accessed_fake_mode")
            return []

        # Return real actions
        actions = analytics_service.get_recent_actions(limit)
        logger.info("admin_actions_accessed", count=len(actions))

        # Convert to dict format for JSON
        return [
            {
                "user_id": action.user_id,
                "action_type": action.action_type,
                "timestamp": action.timestamp.isoformat(),
                "details": action.details,
                "success": action.success,
                "username": action.username,
                "first_name": action.first_name,
                "last_name": action.last_name,
                "is_test": action.is_test
            }
            for action in actions
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_actions_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/errors")
async def get_errors(
    authorization: str = Header(..., alias="Authorization"),
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(100, ge=1, le=500)
):
    """
    Get recent errors for admin dashboard.

    Requires Authorization header with admin token.

    Returns errors from the last N hours:
    - LLM errors (API failures, timeouts, parse failures)
    - Calendar errors (Radicale connection issues)
    - STT errors (speech-to-text failures)
    - Intent unclear (user requests that required clarification)
    """
    try:
        # Extract token
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization

        auth_type = verify_token(token)

        if not auth_type:
            raise HTTPException(status_code=401, detail="Unauthorized")

        if auth_type == "fake":
            logger.info("admin_errors_accessed_fake_mode")
            return {"errors": [], "stats": {"total": 0, "by_type": {}, "period_hours": hours}}

        # Get errors and stats
        errors = analytics_service.get_errors(hours, limit)
        error_stats = analytics_service.get_error_stats(hours)

        logger.info("admin_errors_accessed", count=len(errors), hours=hours)

        # Convert to dict format for JSON
        return {
            "errors": [
                {
                    "user_id": action.user_id,
                    "action_type": action.action_type,
                    "timestamp": action.timestamp.isoformat(),
                    "details": action.details,
                    "error_message": action.error_message,
                    "username": action.username,
                    "first_name": action.first_name,
                    "last_name": action.last_name
                }
                for action in errors
            ],
            "stats": error_stats
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_errors_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def admin_health():
    """Health check for admin API (no auth required)."""
    return {"status": "ok"}


@router.get("/report")
async def get_full_report(
    authorization: str = Header(..., alias="Authorization")
):
    """
    Get report with all users (lightweight version).

    Returns basic user info from analytics. Todos and events
    are loaded on demand via /users/{id}/todos and /users/{id}/events.

    Requires Authorization header with admin token.
    """
    try:
        # Extract token
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization

        auth_type = verify_token(token)

        if not auth_type:
            raise HTTPException(status_code=401, detail="Unauthorized")

        if auth_type == "fake":
            logger.info("admin_report_accessed_fake_mode")
            return {"users": [], "summary": {"total_users": 0}}

        # Get all users from analytics (fast - no CalDAV calls)
        all_users = analytics_service.get_all_users_details()

        report_users = []
        for user in all_users:
            report_users.append({
                "user_id": user.user_id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "first_seen": user.first_seen.isoformat() if user.first_seen else None,
                "last_seen": user.last_seen.isoformat() if user.last_seen else None,
                # Todos and events loaded on demand via separate endpoints
                "todos": None,
                "events": None,
                "todos_count": None,
                "events_count": None
            })

        # Sort by last_seen (most recent first)
        report_users.sort(key=lambda u: u.get("last_seen") or "", reverse=True)

        logger.info("admin_report_generated", total_users=len(report_users))

        return {
            "users": report_users,
            "summary": {
                "total_users": len(report_users)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_report_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class BroadcastRequest(BaseModel):
    """Request model for broadcast message."""
    message: str
    button_text: Optional[str] = None  # If provided, adds inline button
    button_action: Optional[str] = None  # "start" to trigger /start command
    test_only: bool = False  # If true, send only to test users


@router.post("/broadcast")
@limiter.limit("1/minute")  # SECURITY: Strict rate limit to prevent spam
async def broadcast_message(
    request: Request,
    broadcast_req: BroadcastRequest,
    authorization: str = Header(..., alias="Authorization")
):
    """
    Send broadcast message to all users.

    Requires Authorization header with admin token (real mode only).
    Rate limited to 1 broadcast per minute per IP.

    Options:
    - message: Text to send
    - button_text: Optional button text (e.g., "🚀 Обновить")
    - button_action: "start" to add button that triggers /start
    - test_only: Send only to test users (for testing)
    """
    try:
        # Extract and verify token
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization

        auth_type = verify_token(token)

        if not auth_type:
            raise HTTPException(status_code=401, detail="Unauthorized")

        if auth_type == "fake":
            logger.info("admin_broadcast_fake_mode")
            return {"status": "fake_mode", "sent": 0, "failed": 0}

        # Get all users from analytics
        users = analytics_service.get_all_users_details()

        if broadcast_req.test_only:
            # Filter to test users only (you can define test user IDs here)
            test_user_ids = ["2296243"]  # Add your test user IDs
            users = [u for u in users if u.user_id in test_user_ids]

        if not users:
            return {"status": "no_users", "sent": 0, "failed": 0}

        # Import telegram bot
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        from app.routers.telegram import get_telegram_app

        # Get initialized telegram app (creates handler if needed)
        telegram_app = await get_telegram_app()
        bot = telegram_app.bot

        # Prepare keyboard if button requested
        keyboard = None
        if broadcast_req.button_text and broadcast_req.button_action == "start":
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    broadcast_req.button_text,
                    callback_data="broadcast:start"
                )]
            ])

        sent = 0
        failed = 0
        failed_users = []

        for user in users:
            try:
                await bot.send_message(
                    chat_id=int(user.user_id),
                    text=broadcast_req.message,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
                sent += 1
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.05)
            except Exception as e:
                failed += 1
                failed_users.append({"user_id": user.user_id, "error": str(e)})
                logger.warning("broadcast_send_failed", user_id=user.user_id, error=str(e))

        logger.info("admin_broadcast_completed",
                   sent=sent,
                   failed=failed,
                   total_users=len(users),
                   test_only=broadcast_req.test_only)

        return {
            "status": "completed",
            "sent": sent,
            "failed": failed,
            "total": len(users),
            "failed_users": failed_users[:10] if failed_users else []  # Return first 10 failures
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_broadcast_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
