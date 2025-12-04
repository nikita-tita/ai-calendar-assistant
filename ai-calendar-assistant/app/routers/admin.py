"""Admin API router with 3-password authentication, rate limiting and fake mode."""

from typing import List
from fastapi import APIRouter, HTTPException, Header, Query, Body, Request
from datetime import datetime, timedelta
from pydantic import BaseModel
import structlog
import bcrypt
import secrets
import os
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.services.analytics_service import analytics_service
from app.services.calendar_radicale import calendar_service
from app.models.analytics import (
    AdminDashboardStats, UserDetail, UserDialogEntry
)
from app.config import settings

logger = structlog.get_logger()

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


# Session token storage (in production, use Redis or database)
_valid_tokens: dict = {}


def generate_session_token() -> str:
    """Generate cryptographically secure session token."""
    return secrets.token_urlsafe(32)


def verify_token(token: str) -> str:
    """
    Verify token from Authorization header.

    Returns:
        - "real" if valid real token
        - "fake" if valid fake token
        - None if invalid
    """
    if token in _valid_tokens:
        token_data = _valid_tokens[token]
        # Check expiration (1 hour)
        if datetime.now() - token_data['created'] < timedelta(hours=1):
            return token_data['mode']
        else:
            # Token expired, remove it
            del _valid_tokens[token]
            return None
    return None


def create_session_token(mode: str) -> str:
    """Create a new session token for the given mode."""
    token = generate_session_token()
    _valid_tokens[token] = {
        'mode': mode,
        'created': datetime.now()
    }
    return token


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

        # Generate cryptographically secure session token (not derived from passwords)
        token = create_session_token(auth_type)

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
