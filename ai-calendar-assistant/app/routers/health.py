"""Health check endpoints for monitoring system stability."""

from fastapi import APIRouter
import structlog
from datetime import datetime

from app.services.calendar_radicale import calendar_service
# Temporarily disabled - property service is independent microservice
# from app.services.property.property_service import property_service

logger = structlog.get_logger()

router = APIRouter(prefix="/healthcheck", tags=["health"])


@router.get("")
async def health_check():
    """Overall system health check."""
    calendar_status = await _check_calendar_health()
    # Property service disabled - independent microservice
    # property_status = await _check_property_health()

    overall_healthy = calendar_status["healthy"]

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "calendar": calendar_status,
            # "property": property_status,
        }
    }


@router.get("/calendar")
async def check_calendar_health():
    """Public endpoint for calendar health check."""
    return await _check_calendar_health()


async def _check_calendar_health():
    """Check calendar service health."""
    try:
        # Try to list calendars for a test user
        # This checks: DB connection, Radicale connection, basic functionality
        test_result = await calendar_service.get_calendar_name("health_check_user")

        return {
            "healthy": True,
            "message": "Calendar service is operational",
            "checks": {
                "radicale_connection": True,
                "database_connection": True,
            }
        }
    except Exception as e:
        logger.error("calendar_health_check_failed", error=str(e))
        return {
            "healthy": False,
            "message": f"Calendar service error: {str(e)}",
            "checks": {
                "radicale_connection": False,
                "database_connection": False,
            }
        }


# @router.get("/property")
# async def check_property_health():
#     """Public endpoint for property health check."""
#     return await _check_property_health()


# async def _check_property_health():
#     """Check property search service health."""
#     try:
#         # Try a simple database query
#         # This checks: DB connection, property module functionality
#         return {
#             "healthy": True,
#             "message": "Property service is operational",
#             "checks": {
#                 "database_connection": True,
#                 "property_module": True,
#             }
#         }
#     except Exception as e:
#         logger.error("property_health_check_failed", error=str(e))
#         return {
#             "healthy": False,
#             "message": f"Property service error: {str(e)}",
#             "checks": {
#                 "database_connection": False,
#                 "property_module": False,
#             }
#         }
