"""Admin API router with 3-password authentication and fake mode."""

from typing import List
from fastapi import APIRouter, HTTPException, Header, Query, Body
from datetime import datetime, timedelta
from pydantic import BaseModel
import structlog
import hashlib
import os
from dotenv import load_dotenv
load_dotenv()

from app.services.analytics_service import analytics_service
from app.services.calendar_radicale import calendar_service
from app.models.analytics import (
    AdminDashboardStats, UserDetail, UserDialogEntry
)

logger = structlog.get_logger()

router = APIRouter()

# Admin passwords - loaded from environment variables for security
# Set these in .env file:
# ADMIN_PASSWORD_1=your_primary_password (or ADMIN_PRIMARY_PASSWORD for backward compatibility)
# ADMIN_PASSWORD_2=your_secondary_password (or ADMIN_SECONDARY_PASSWORD)
# ADMIN_PASSWORD_3=your_tertiary_password (or ADMIN_TERTIARY_PASSWORD)

# Support both old and new env var names for backward compatibility
PASSWORD_1 = os.getenv("ADMIN_PASSWORD_1") or os.getenv("ADMIN_PRIMARY_PASSWORD", "")
PASSWORD_2 = os.getenv("ADMIN_PASSWORD_2") or os.getenv("ADMIN_SECONDARY_PASSWORD", "")
PASSWORD_3 = os.getenv("ADMIN_PASSWORD_3") or os.getenv("ADMIN_TERTIARY_PASSWORD") or "default_tertiary"  # Optional third password

if not PASSWORD_1 or not PASSWORD_2:
    logger.error("admin_passwords_not_configured",
                message="ADMIN_PASSWORD_1 and ADMIN_PASSWORD_2 must be set in environment")
    raise ValueError("Admin passwords not configured. Set ADMIN_PASSWORD_1 and ADMIN_PASSWORD_2 in .env file")

PASSWORD_1_HASH = hashlib.sha256(PASSWORD_1.encode('utf-8')).hexdigest()
PASSWORD_2_HASH = hashlib.sha256(PASSWORD_2.encode('utf-8')).hexdigest()
PASSWORD_3_HASH = hashlib.sha256(PASSWORD_3.encode('utf-8')).hexdigest()


class LoginRequest(BaseModel):
    """Login request with 3 passwords."""
    password1: str
    password2: str
    password3: str


def hash_password(password: str) -> str:
    """Hash password with SHA-256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_three_passwords(pwd1: str, pwd2: str, pwd3: str) -> str:
    """
    Verify all three admin passwords.

    Logic:
    - All 3 correct -> "real" (full access)
    - Password 1 & 2 correct, Password 3 wrong -> "fake" (fake database error page)
    - Any other combination -> "invalid" (show error)

    Returns:
        - "real" if all 3 passwords correct
        - "fake" if passwords 1 & 2 correct, password 3 wrong
        - "invalid" for any other combination
    """
    hash1 = hash_password(pwd1)
    hash2 = hash_password(pwd2)
    hash3 = hash_password(pwd3)

    pwd1_correct = (hash1 == PASSWORD_1_HASH)
    pwd2_correct = (hash2 == PASSWORD_2_HASH)
    pwd3_correct = (hash3 == PASSWORD_3_HASH)

    # All 3 correct -> real access
    if pwd1_correct and pwd2_correct and pwd3_correct:
        return "real"

    # Passwords 1 & 2 correct, but 3 wrong -> fake mode
    if pwd1_correct and pwd2_correct and not pwd3_correct:
        return "fake"

    # Any other combination -> invalid
    return "invalid"


def verify_token(token: str) -> str:
    """
    Verify token from Authorization header.

    Token is SHA256 hash of "password1:password2:password3"

    Returns:
        - "real" if valid real token
        - "fake" if valid fake token
        - None if invalid
    """
    # Generate valid tokens
    real_token = hashlib.sha256(f"{PASSWORD_1}:{PASSWORD_2}:{PASSWORD_3}".encode()).hexdigest()

    # For fake mode: any combination with pwd1 & pwd2 correct but pwd3 wrong
    # We'll accept the token if it matches the real one, otherwise return None
    # (fake mode is only during login, for API calls we only check if token is valid)

    if token == real_token:
        return "real"

    # For simplicity, we'll only support real tokens in API calls
    # Fake mode shows error on login, not in API
    return None


@router.post("/verify")
async def verify_passwords(request: LoginRequest):
    """
    Verify all three admin passwords.

    Returns:
        - {"valid": true, "mode": "real"} if all 3 correct
        - {"valid": true, "mode": "fake"} if passwords 1&2 correct, 3 wrong
        - {"valid": false, "error": "invalid_credentials"} for any other combination
    """
    try:
        auth_type = verify_three_passwords(
            request.password1,
            request.password2,
            request.password3
        )

        if auth_type == "invalid":
            logger.warning("admin_login_failed", reason="invalid_credentials")
            return {"valid": False, "error": "invalid_credentials"}

        logger.info("admin_login_success", mode=auth_type)

        # Generate combined token for subsequent requests
        combined = f"{request.password1}:{request.password2}:{request.password3}"
        token = hashlib.sha256(combined.encode()).hexdigest()

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


@router.get("/health")
async def admin_health():
    """Health check for admin API (no auth required)."""
    return {"status": "ok"}
