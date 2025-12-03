"""Logs API router for testing and debugging."""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
import structlog
from datetime import datetime, timedelta

logger = structlog.get_logger()

router = APIRouter(prefix="/logs", tags=["logs"])

# In-memory log storage for testing
# В production используйте реальную БД или систему логирования
_logs_storage = {}


def add_log_entry(user_id: int, log_type: str, data: dict):
    """Add log entry for a user."""
    if user_id not in _logs_storage:
        _logs_storage[user_id] = []

    _logs_storage[user_id].append({
        "timestamp": datetime.now().isoformat(),
        "type": log_type,
        "data": data
    })

    # Ограничиваем хранение последними 100 записями на пользователя
    if len(_logs_storage[user_id]) > 100:
        _logs_storage[user_id] = _logs_storage[user_id][-100:]


@router.get("/user/{user_id}")
async def get_user_logs(
    user_id: int,
    limit: int = 50,
    log_type: Optional[str] = None
):
    """Get logs for a specific user."""
    try:
        user_logs = _logs_storage.get(user_id, [])

        # Фильтруем по типу если указан
        if log_type:
            user_logs = [log for log in user_logs if log.get("type") == log_type]

        # Ограничиваем количество
        user_logs = user_logs[-limit:]

        return {
            "user_id": user_id,
            "logs": user_logs,
            "total": len(user_logs)
        }

    except Exception as e:
        logger.error("get_user_logs_error", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent")
async def get_recent_logs(limit: int = 100):
    """Get recent logs from all users."""
    try:
        all_logs = []

        for user_id, logs in _logs_storage.items():
            for log in logs:
                log_entry = log.copy()
                log_entry["user_id"] = user_id
                all_logs.append(log_entry)

        # Сортируем по времени
        all_logs.sort(key=lambda x: x["timestamp"], reverse=True)

        return {
            "logs": all_logs[:limit],
            "total": len(all_logs)
        }

    except Exception as e:
        logger.error("get_recent_logs_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/user/{user_id}")
async def clear_user_logs(user_id: int):
    """Clear logs for a specific user."""
    try:
        if user_id in _logs_storage:
            count = len(_logs_storage[user_id])
            del _logs_storage[user_id]
            return {
                "user_id": user_id,
                "cleared": count,
                "status": "success"
            }
        else:
            return {
                "user_id": user_id,
                "cleared": 0,
                "status": "no_logs_found"
            }

    except Exception as e:
        logger.error("clear_user_logs_error", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_logs_stats():
    """Get logging statistics."""
    try:
        total_users = len(_logs_storage)
        total_logs = sum(len(logs) for logs in _logs_storage.values())

        # Подсчет по типам
        type_counts = {}
        for logs in _logs_storage.values():
            for log in logs:
                log_type = log.get("type", "unknown")
                type_counts[log_type] = type_counts.get(log_type, 0) + 1

        return {
            "total_users": total_users,
            "total_logs": total_logs,
            "type_counts": type_counts
        }

    except Exception as e:
        logger.error("get_logs_stats_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
