"""Security headers middleware for FastAPI.

Adds security headers to all responses to protect against common web vulnerabilities.
SEC-005: Security headers middleware

References:
- https://owasp.org/www-project-secure-headers/
- https://securityheaders.com/
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog

logger = structlog.get_logger()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all HTTP responses.

    Headers added:
    - X-Content-Type-Options: nosniff - Prevent MIME type sniffing
    - X-Frame-Options: DENY - Prevent clickjacking
    - X-XSS-Protection: 1; mode=block - Enable XSS filter (legacy browsers)
    - Referrer-Policy: strict-origin-when-cross-origin - Control referrer info
    - Permissions-Policy: Restrict browser features
    - Content-Security-Policy: Control resource loading (optional, can break things)
    - Strict-Transport-Security: Enforce HTTPS (only in production)
    """

    def __init__(self, app, enable_hsts: bool = True, enable_csp: bool = False):
        """
        Initialize security headers middleware.

        Args:
            app: FastAPI application
            enable_hsts: Enable Strict-Transport-Security header (default True)
            enable_csp: Enable Content-Security-Policy header (default False - can break things)
        """
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.enable_csp = enable_csp

    async def dispatch(self, request: Request, call_next) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking - DENY for API, SAMEORIGIN for webapp
        # Using SAMEORIGIN to allow Telegram WebApp embedding
        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        # Legacy XSS protection (for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Restrict browser features/permissions
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )

        # HSTS - Enforce HTTPS (1 year, include subdomains)
        if self.enable_hsts:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # Content-Security-Policy (optional - can break inline scripts)
        if self.enable_csp:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://telegram.org; "
                "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
                "img-src 'self' data: https:; "
                "font-src 'self' https:; "
                "connect-src 'self' https://api.telegram.org; "
                "frame-ancestors 'self' https://web.telegram.org https://t.me;"
            )

        return response
