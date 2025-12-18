"""Admin API router v2 with login/password + 2FA authentication."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Header, Query, Body, Request, Response
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from pydantic import BaseModel
import structlog
import pytz
import asyncio
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.services.admin_auth_service import get_admin_auth, init_admin_auth_service
from app.services.analytics_service import analytics_service
from app.services.calendar_radicale import calendar_service
from app.services.todos_service import todos_service
from app.models.analytics import (
    AdminDashboardStats, UserDetail, UserDialogEntry
)
from app.models.admin_user import (
    AdminLoginRequest, AdminLoginResponse, AdminSessionInfo
)
from app.config import settings

logger = structlog.get_logger()

# Initialize admin auth service
try:
    init_admin_auth_service()
    logger.info("admin_auth_service_initialized_in_router")
except Exception as e:
    logger.error("failed_to_initialize_admin_auth", error=str(e))

# Rate limiter for admin endpoints
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=getattr(settings, 'redis_url', 'memory://'),
)

router = APIRouter()


def get_client_ip(request: Request) -> str:
    """Get client IP from request."""
    # Check X-Forwarded-For header (for proxies/load balancers)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to request.client
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """Get user agent from request."""
    return request.headers.get("User-Agent", "unknown")


async def verify_admin_token(request: Request) -> dict:
    """
    Verify admin JWT token from cookie and return payload.

    Raises HTTPException if invalid.
    """
    try:
        # Get token from cookie
        token = request.cookies.get("admin_access_token")

        if not token:
            # Also check Authorization header for API clients
            auth_header = request.headers.get("Authorization")
            if auth_header:
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:]
                else:
                    token = auth_header

        if not token:
            raise HTTPException(status_code=401, detail="No authentication token provided")

        # Get IP and UA
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)

        # Verify token
        auth_service = get_admin_auth()
        payload = auth_service.verify_token(token, ip_address, user_agent, "access")

        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        return payload

    except HTTPException:
        raise
    except Exception as e:
        logger.error("token_verification_error", error=str(e))
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/login")
@limiter.limit("5/minute")  # Reasonable limit: allows retries but prevents brute force
async def login(
    request: Request,
    login_request: AdminLoginRequest
):
    """
    Login to admin panel.
    
    Rate limited to 3 attempts per 5 minutes per IP.
    
    Returns:
        - success=True, mode="real" if authenticated
        - success=True, mode="fake" if panic password used
        - success=False with error message if failed
        - totp_required=True if 2FA code needed
    """
    try:
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)
        
        auth_service = get_admin_auth()
        access_token, refresh_token, login_response = auth_service.authenticate(
            login_request, ip_address, user_agent
        )
        
        if not login_response.success:
            return login_response
        
        # Create JSONResponse and set cookies directly on it
        # NOTE: Cannot use response param + return Pydantic model - FastAPI ignores cookies!
        json_response = JSONResponse(
            content={
                "success": True,
                "mode": login_response.mode,
                "message": "Login successful",
                "totp_required": False
            }
        )

        # Set httpOnly cookies (more secure than localStorage)
        json_response.set_cookie(
            key="admin_access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=3600,  # 1 hour
            path="/"
        )

        json_response.set_cookie(
            key="admin_refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=604800,  # 7 days
            path="/"
        )

        return json_response
    
    except Exception as e:
        logger.error("admin_login_error", error=str(e), exc_info=True)
        return AdminLoginResponse(
            success=False,
            mode="invalid",
            message="Server error"
        )


@router.post("/logout")
async def logout():
    """Logout and clear cookies."""
    json_response = JSONResponse(content={"success": True, "message": "Logged out successfully"})
    json_response.delete_cookie("admin_access_token", path="/")
    json_response.delete_cookie("admin_refresh_token", path="/")
    return json_response


@router.get("/me", response_model=AdminSessionInfo)
async def get_current_admin(request: Request):
    """Get current admin user info."""
    payload = await verify_admin_token(request)
    
    auth_service = get_admin_auth()
    user = auth_service.get_admin_user(payload["user_id"])
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return AdminSessionInfo(
        user_id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        last_login_at=user.last_login_at,
        last_login_ip=user.last_login_ip,
        totp_enabled=user.totp_enabled
    )


@router.post("/setup-2fa")
async def setup_2fa(request: Request):
    """Setup 2FA for current admin user."""
    payload = await verify_admin_token(request)
    
    auth_service = get_admin_auth()
    totp_setup = auth_service.setup_totp(payload["user_id"])
    
    return {
        "success": True,
        "qr_code": f"data:image/png;base64,{totp_setup.qr_code}",
        "manual_entry_key": totp_setup.manual_entry_key,
        "issuer": totp_setup.issuer
    }


@router.get("/stats", response_model=AdminDashboardStats)
async def get_admin_stats(request: Request):
    """
    Get admin dashboard statistics.
    
    Requires valid admin token.
    Returns fake stats if in fake mode.
    """
    try:
        payload = await verify_admin_token(request)
        
        # Check mode
        if payload.get("mode") == "fake":
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
        logger.info("admin_stats_accessed", user_id=payload["user_id"], username=payload["username"])
        return stats
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_stats_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users", response_model=List[UserDetail])
async def get_all_users(request: Request):
    """
    Get detailed information for all users.
    
    Requires valid admin token.
    """
    try:
        payload = await verify_admin_token(request)
        
        if payload.get("mode") == "fake":
            # Return empty list
            logger.info("admin_users_accessed_fake_mode")
            return []
        
        # Return real user details
        users = analytics_service.get_all_users_details()
        logger.info("admin_users_accessed", user_id=payload["user_id"], count=len(users))
        return users
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_users_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/dialog", response_model=List[UserDialogEntry])
async def get_user_dialog(
    request: Request,
    user_id: str,
    limit: int = Query(1000, ge=1, le=10000)
):
    """
    Get complete dialog history for a specific user.
    
    Requires valid admin token.
    """
    try:
        payload = await verify_admin_token(request)
        
        if payload.get("mode") == "fake":
            # Return empty dialog
            logger.info("admin_user_dialog_accessed_fake_mode", user_id=user_id)
            return []
        
        # Return real dialog
        dialog = analytics_service.get_user_dialog(user_id, limit)
        logger.info("admin_user_dialog_accessed", 
                   admin_id=payload["user_id"], 
                   target_user_id=user_id, 
                   entries=len(dialog))
        return dialog
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_user_dialog_error", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/events")
async def get_user_events(request: Request, user_id: str):
    """Get all calendar events for a specific user."""
    try:
        payload = await verify_admin_token(request)
        
        if payload.get("mode") == "fake":
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
        
        logger.info("admin_user_events_accessed", 
                   admin_id=payload["user_id"],
                   target_user_id=user_id, 
                   count=len(events_data))
        return events_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_user_events_error", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/todos")
async def get_user_todos(request: Request, user_id: str):
    """Get all todos for a specific user."""
    try:
        payload = await verify_admin_token(request)
        
        if payload.get("mode") == "fake":
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
        
        logger.info("admin_user_todos_accessed", 
                   admin_id=payload["user_id"],
                   target_user_id=user_id, 
                   count=len(todos_data))
        return todos_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_user_todos_error", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{user_id}/toggle-hidden")
async def toggle_user_hidden(request: Request, user_id: str):
    """
    Toggle user's hidden status in admin dashboard.
    
    Requires valid admin token (real mode only).
    Returns new hidden state.
    """
    try:
        payload = await verify_admin_token(request)
        
        if payload.get("mode") == "fake":
            logger.info("admin_toggle_hidden_fake_mode", user_id=user_id)
            return {"user_id": user_id, "is_hidden": False}
        
        # Toggle hidden status
        new_hidden = analytics_service.toggle_user_hidden(user_id)
        
        # Log audit
        auth_service = get_admin_auth()
        auth_service._log_audit(
            admin_user_id=payload["user_id"],
            username=payload["username"],
            action_type="hide_user",
            details=f"User {user_id} hidden={new_hidden}",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            success=True
        )
        
        logger.info("admin_user_hidden_toggled", 
                   admin_id=payload["user_id"],
                   target_user_id=user_id, 
                   is_hidden=new_hidden)
        
        return {"user_id": user_id, "is_hidden": new_hidden}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_toggle_hidden_error", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeline")
async def get_activity_timeline(
    request: Request,
    hours: int = Query(24, ge=1, le=168)
):
    """Get activity timeline for the last N hours."""
    try:
        payload = await verify_admin_token(request)
        
        if payload.get("mode") == "fake":
            logger.info("admin_timeline_accessed_fake_mode")
            return []
        
        # Return real timeline
        timeline = analytics_service.get_activity_timeline(hours)
        logger.info("admin_timeline_accessed", 
                   admin_id=payload["user_id"],
                   hours=hours, 
                   points=len(timeline))
        
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
    request: Request,
    limit: int = Query(100, ge=1, le=1000)
):
    """Get recent actions from all users."""
    try:
        payload = await verify_admin_token(request)
        
        if payload.get("mode") == "fake":
            logger.info("admin_actions_accessed_fake_mode")
            return []
        
        # Return real actions
        actions = analytics_service.get_recent_actions(limit)
        logger.info("admin_actions_accessed", 
                   admin_id=payload["user_id"],
                   count=len(actions))
        
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
    request: Request,
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(100, ge=1, le=500)
):
    """Get recent errors for admin dashboard."""
    try:
        payload = await verify_admin_token(request)
        
        if payload.get("mode") == "fake":
            logger.info("admin_errors_accessed_fake_mode")
            return {"errors": [], "stats": {"total": 0, "by_type": {}, "period_hours": hours}}
        
        # Get errors and stats
        errors = analytics_service.get_errors(hours, limit)
        error_stats = analytics_service.get_error_stats(hours)
        
        logger.info("admin_errors_accessed", 
                   admin_id=payload["user_id"],
                   count=len(errors), 
                   hours=hours)
        
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


# ==================== EXTENDED ANALYTICS ENDPOINTS ====================

@router.get("/timeline/daily")
async def get_daily_timeline(
    request: Request,
    days: int = Query(30, ge=1, le=90)
):
    """
    Get daily statistics for the last N days.

    Returns: list of {date, actions, users, events, messages, errors}
    """
    try:
        payload = await verify_admin_token(request)

        if payload.get("mode") == "fake":
            return {"data": [], "period_days": days}

        data = analytics_service.get_daily_timeline(days)

        logger.info("admin_daily_timeline_accessed",
                   admin_id=payload["user_id"],
                   days=days,
                   data_points=len(data))

        return {"data": data, "period_days": days}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_daily_timeline_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/llm/costs")
async def get_llm_costs(
    request: Request,
    days: int = Query(30, ge=1, le=90)
):
    """
    Get LLM cost breakdown by day, model, and user.

    Returns: {daily_costs, by_model, by_user, totals, period_days}
    """
    try:
        payload = await verify_admin_token(request)

        if payload.get("mode") == "fake":
            return {
                "daily_costs": [],
                "by_model": {},
                "by_user": [],
                "totals": {"cost_rub": 0, "tokens": 0, "requests": 0,
                          "unique_users": 0, "avg_cost_per_user": 0, "avg_cost_per_request": 0},
                "period_days": days
            }

        data = analytics_service.get_llm_cost_breakdown(days)

        logger.info("admin_llm_costs_accessed",
                   admin_id=payload["user_id"],
                   days=days,
                   total_cost=data["totals"]["cost_rub"])

        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_llm_costs_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/metrics")
async def get_user_metrics(
    request: Request,
    days: int = Query(30, ge=1, le=90)
):
    """
    Get user engagement metrics: DAU/MAU, retention, segments.

    Returns: {dau, mau, avg_dau, dau_mau_ratio, segments, retention, new_users, period_days}
    """
    try:
        payload = await verify_admin_token(request)

        if payload.get("mode") == "fake":
            return {
                "dau": [],
                "mau": 0,
                "avg_dau": 0,
                "dau_mau_ratio": 0,
                "segments": {"power_users": 0, "regular_users": 0, "casual_users": 0, "dormant_users": 0},
                "retention": {"day_1": 0, "day_7": 0},
                "new_users": {"today": 0, "this_week": 0, "this_month": 0},
                "period_days": days
            }

        data = analytics_service.get_user_engagement_metrics(days)

        logger.info("admin_user_metrics_accessed",
                   admin_id=payload["user_id"],
                   days=days,
                   mau=data["mau"],
                   avg_dau=data["avg_dau"])

        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_user_metrics_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/top")
async def get_top_users(
    request: Request,
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(30, ge=1, le=90)
):
    """
    Get top active users for the period.

    Returns: list of {user_id, username, first_name, total_actions, events, messages, llm_cost, last_seen}
    """
    try:
        payload = await verify_admin_token(request)

        if payload.get("mode") == "fake":
            return {"users": [], "limit": limit, "period_days": days}

        users = analytics_service.get_top_users(limit, days)

        logger.info("admin_top_users_accessed",
                   admin_id=payload["user_id"],
                   limit=limit,
                   days=days,
                   returned=len(users))

        return {"users": users, "limit": limit, "period_days": days}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_top_users_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def admin_health():
    """Health check for admin API (no auth required)."""
    return {"status": "ok", "version": "v2"}


class BroadcastRequest(BaseModel):
    """Request model for broadcast message."""
    message: str
    button_text: Optional[str] = None
    button_action: Optional[str] = None
    test_only: bool = False


@router.post("/broadcast")
@limiter.limit("1/minute")  # SECURITY: Strict rate limit to prevent spam
async def broadcast_message(
    request: Request,
    broadcast_req: BroadcastRequest
):
    """
    Send broadcast message to all users.
    
    Requires valid admin token (real mode only).
    Rate limited to 1 broadcast per minute.
    """
    try:
        payload = await verify_admin_token(request)
        
        if payload.get("mode") == "fake":
            logger.info("admin_broadcast_fake_mode")
            return {"status": "fake_mode", "sent": 0, "failed": 0}
        
        # Get all users from analytics
        users = analytics_service.get_all_users_details()
        
        if broadcast_req.test_only:
            # For testing - only send to admin if they have a user_id
            test_user_ids = [str(payload["user_id"])]  # Admin's user ID if available
            users = [u for u in users if u.user_id in test_user_ids]
        
        if not users:
            return {"status": "no_users", "sent": 0, "failed": 0}
        
        # Import telegram bot
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        from app.routers.telegram import get_telegram_app
        
        # Get initialized telegram app
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
        
        # Log audit
        auth_service = get_admin_auth()
        auth_service._log_audit(
            admin_user_id=payload["user_id"],
            username=payload["username"],
            action_type="broadcast",
            details=f"Sent to {sent} users, {failed} failed. Message: {broadcast_req.message[:50]}...",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            success=True
        )
        
        logger.info("admin_broadcast_completed",
                   admin_id=payload["user_id"],
                   sent=sent,
                   failed=failed,
                   total_users=len(users),
                   test_only=broadcast_req.test_only)
        
        return {
            "status": "completed",
            "sent": sent,
            "failed": failed,
            "total": len(users),
            "failed_users": failed_users[:10] if failed_users else []
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_broadcast_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit-logs")
async def get_audit_logs(
    request: Request,
    limit: int = Query(100, ge=1, le=500)
):
    """Get admin audit logs."""
    try:
        payload = await verify_admin_token(request)
        
        if payload.get("mode") == "fake":
            logger.info("admin_audit_logs_accessed_fake_mode")
            return []
        
        # Get audit logs
        auth_service = get_admin_auth()
        logs = auth_service.get_audit_logs(limit=limit)
        
        logger.info("admin_audit_logs_accessed", 
                   admin_id=payload["user_id"],
                   count=len(logs))
        
        return [
            {
                "id": log.id,
                "admin_user_id": log.admin_user_id,
                "username": log.username,
                "action_type": log.action_type,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "details": log.details,
                "ip_address": log.ip_address,
                "success": log.success
            }
            for log in logs
        ]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_audit_logs_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

