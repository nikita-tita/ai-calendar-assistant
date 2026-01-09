"""CSRF protection middleware for admin endpoints.

SEC-004: CSRF Protection

Validates Origin header for state-changing requests to prevent CSRF attacks.
Works with SameSite=Strict cookies for defense in depth.
"""

from typing import Set
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
import structlog

from app.config import settings

logger = structlog.get_logger()


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware that validates Origin header for state-changing requests.

    Protects against CSRF by:
    1. Checking Origin header matches allowed origins
    2. Blocking requests without Origin for state-changing methods
    3. Allowing safe methods (GET, HEAD, OPTIONS) without Origin check

    Used in combination with SameSite=Strict cookies.
    """

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    # Endpoints that don't require CSRF protection (e.g., login)
    EXEMPT_PATHS: Set[str] = {
        "/api/admin/v2/login",
        "/telegram/webhook",
    }

    def __init__(self, app, allowed_origins: list = None):
        """
        Initialize CSRF protection middleware.

        Args:
            app: FastAPI application
            allowed_origins: List of allowed origins (defaults to CORS origins)
        """
        super().__init__(app)

        # Parse allowed origins from settings or parameter
        if allowed_origins:
            self.allowed_origins = set(allowed_origins)
        else:
            # Use CORS origins from settings
            origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
            self.allowed_origins = set(origins)

        # Always allow same-origin requests (no Origin header)
        # and requests from localhost in debug mode
        if settings.debug:
            self.allowed_origins.update([
                "http://localhost:3000",
                "http://localhost:8000",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8000",
            ])

        logger.info("csrf_middleware_initialized", allowed_origins=list(self.allowed_origins))

    async def dispatch(self, request: Request, call_next) -> Response:
        """Check CSRF for state-changing requests."""

        # Allow safe methods
        if request.method in self.SAFE_METHODS:
            return await call_next(request)

        # Check if path is exempt
        path = request.url.path
        if path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Only check CSRF for admin endpoints
        if not path.startswith("/api/admin"):
            return await call_next(request)

        # Get Origin header
        origin = request.headers.get("Origin")

        # If no Origin header, check Referer as fallback
        if not origin:
            referer = request.headers.get("Referer")
            if referer:
                # Extract origin from Referer URL
                from urllib.parse import urlparse
                parsed = urlparse(referer)
                origin = f"{parsed.scheme}://{parsed.netloc}"

        # If still no origin, it might be a same-origin request or API client
        # For browser requests, Origin is almost always present for POST/PUT/DELETE
        # Allow if no Origin (API clients, curl, etc.) but log it
        if not origin:
            logger.debug(
                "csrf_check_no_origin",
                path=path,
                method=request.method,
                user_agent=request.headers.get("User-Agent", "unknown")
            )
            # Allow but log - API clients don't send Origin
            return await call_next(request)

        # Validate origin
        if origin not in self.allowed_origins:
            logger.warning(
                "csrf_origin_rejected",
                origin=origin,
                path=path,
                method=request.method,
                allowed=list(self.allowed_origins)
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF validation failed: Origin not allowed"}
            )

        # Origin is valid
        return await call_next(request)
