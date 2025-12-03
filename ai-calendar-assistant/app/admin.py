"""Admin API router with 3-password authentication and fake mode."""

from typing import List
from fastapi import APIRouter, HTTPException, Header, Query
from datetime import datetime, timedelta
import structlog
import hashlib

from app.services.analytics_service import analytics_service
from app.services.calendar_radicale import calendar_service
from app.models.analytics import (
    AdminDashboardStats, UserDetail, UserDialogEntry
)

logger = structlog.get_logger()

router = APIRouter()

# Admin passwords (SHA-256 hashed)
# Password 1: "CalendarAdmin_2025_Primary_Key!"
PASSWORD_1_HASH = "8a2f1e9c4d6b7a3f5e8c2a1b4d7e9f3c6a8b2d5e7f1c4a9b3e6d8f2c5a7b4e9d"

# Password 2: "SecondaryAdmin_SuperSecret_2025"
PASSWORD_2_HASH = "3b5d7f9e2c4a6b8d1f3e5c7a9b2d4f6e8c1a3b5d7f9e2c4a6b8d1f3e5c7a9b2"

# Password 3 (fake mode): "FakeAdmin_NoData_Access"
PASSWORD_3_HASH = "7e9f2c4a6b8d1f3e5c7a9b2d4f6e8c1a3b5d7f9e2c4a6b8d1f3e5c7a9b2d4f"

def hash_password(password: str) -> str:
    """Hash password with SHA-256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# Generate real hashes on first run (replace hardcoded hashes above after first run)
PASSWORD_1 = "CalendarAdmin_2025_Primary_Key!"
PASSWORD_2 = "SecondaryAdmin_SuperSecret_2025"
PASSWORD_3 = "FakeAdmin_NoData_Access"

PASSWORD_1_HASH = hash_password(PASSWORD_1)
PASSWORD_2_HASH = hash_password(PASSWORD_2)
PASSWORD_3_HASH = hash_password(PASSWORD_3)


def verify_admin(password: str) -> str:
    """
    Verify admin password.

    Returns:
        - "real" if real admin password (1 or 2)
        - "fake" if fake password (3)
        - None if invalid
    """
    pwd_hash = hash_password(password)

    if pwd_hash == PASSWORD_1_HASH or pwd_hash == PASSWORD_2_HASH:
        return "real"
    elif pwd_hash == PASSWORD_3_HASH:
        return "fake"
    else:
        return None


@router.post("/verify")
async def verify_password(authorization: str = Header(..., alias="Authorization")):
    """
    Verify admin password.

    Returns {"valid": true, "mode": "real"|"fake"} or {"valid": false}
    """
    try:
        # Extract token from "Bearer {token}"
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization

        auth_type = verify_admin(token)

        if not auth_type:
            return {"valid": False}

        logger.info("admin_password_verified", mode=auth_type)
        return {"valid": True, "mode": auth_type}

    except Exception as e:
        logger.error("admin_verify_error", error=str(e), exc_info=True)
        return {"valid": False}


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

        auth_type = verify_admin(token)

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

        auth_type = verify_admin(token)

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

        auth_type = verify_admin(token)

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

        auth_type = verify_admin(token)

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
