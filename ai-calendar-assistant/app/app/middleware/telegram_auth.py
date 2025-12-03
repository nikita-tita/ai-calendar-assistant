"""Telegram Web App authentication middleware."""

import hmac
import hashlib
import json
from typing import Optional
from urllib.parse import parse_qsl
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import structlog

from app.config import settings

logger = structlog.get_logger()


def validate_telegram_init_data(init_data: str, bot_token: str) -> Optional[dict]:
    """
    Validate Telegram WebApp initData HMAC signature.

    Returns parsed data if valid, None if invalid.

    Reference: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        # Parse init_data
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop('hash', None)

        if not received_hash:
            logger.warning("telegram_auth_no_hash", message="No hash in initData")
            return None

        # Create data check string (alphabetically sorted)
        data_check_arr = [f"{k}={v}" for k, v in sorted(parsed.items())]
        data_check_string = '\n'.join(data_check_arr)

        # Create secret key from bot token
        # HMAC-SHA256 of bot token with constant "WebAppData"
        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode(),
            hashlib.sha256
        ).digest()

        # Calculate hash of data_check_string
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # Verify hash matches
        if calculated_hash == received_hash:
            logger.info("telegram_auth_valid", message="Valid Telegram initData")
            return parsed
        else:
            logger.warning(
                "telegram_auth_invalid_hash",
                message="Hash mismatch",
                expected=calculated_hash[:16],
                received=received_hash[:16]
            )
            return None

    except Exception as e:
        logger.error("telegram_auth_error", error=str(e), exc_info=True)
        return None


def extract_user_id_from_init_data(validated_data: dict) -> Optional[str]:
    """
    Extract user_id from validated Telegram initData.

    The 'user' field is a JSON string containing user info.
    """
    try:
        user_json = validated_data.get('user')
        if not user_json:
            logger.warning("telegram_auth_no_user", message="No user field in initData")
            return None

        # Parse user JSON
        user_data = json.loads(user_json)
        user_id = user_data.get('id')

        if user_id:
            logger.info("telegram_auth_user_extracted", user_id=str(user_id))
            return str(user_id)

        logger.warning("telegram_auth_no_user_id", message="No id in user data")
        return None

    except json.JSONDecodeError as e:
        logger.error("telegram_auth_json_error", error=str(e), user_json=validated_data.get('user'))
        return None
    except Exception as e:
        logger.error("telegram_auth_extract_error", error=str(e), exc_info=True)
        return None


async def verify_telegram_webapp_auth(request: Request) -> Optional[str]:
    """
    Verify Telegram WebApp authentication and extract user_id.

    Checks for 'X-Telegram-Init-Data' header and validates HMAC signature.

    Returns:
        user_id (str) if authentication is valid
        None if authentication fails
    """
    # Get initData from header
    init_data = request.headers.get('X-Telegram-Init-Data')

    if not init_data:
        logger.warning(
            "telegram_auth_missing_header",
            message="Missing X-Telegram-Init-Data header",
            path=request.url.path
        )
        return None

    # Validate HMAC signature
    validated_data = validate_telegram_init_data(init_data, settings.telegram_bot_token)

    if not validated_data:
        logger.warning(
            "telegram_auth_validation_failed",
            message="Failed to validate initData",
            path=request.url.path
        )
        return None

    # Extract user_id
    user_id = extract_user_id_from_init_data(validated_data)

    if not user_id:
        logger.warning(
            "telegram_auth_no_user_id",
            message="Could not extract user_id from validated data",
            path=request.url.path
        )
        return None

    logger.info(
        "telegram_auth_success",
        user_id=user_id,
        path=request.url.path
    )

    return user_id


class TelegramAuthMiddleware:
    """
    FastAPI middleware to verify Telegram WebApp authentication.

    Adds 'telegram_user_id' to request.state if authentication is valid.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        # Skip auth for health endpoints and admin routes
        path = scope.get("path", "")
        if path.startswith("/health") or path.startswith("/api/admin"):
            return await self.app(scope, receive, send)

        # Only apply to protected API endpoints: /api/events/ and /api/todos/
        protected_paths = ["/api/events/", "/api/todos/"]
        if not any(path.startswith(prefix) for prefix in protected_paths):
            return await self.app(scope, receive, send)

        # Create Request object to access headers
        from fastapi import Request
        request = Request(scope, receive)

        # Verify authentication
        user_id = await verify_telegram_webapp_auth(request)

        if not user_id:
            # Authentication failed - return 401
            logger.warning(
                "telegram_auth_rejected",
                message="Unauthorized access attempt",
                path=path
            )

            response = JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "Unauthorized: Invalid or missing Telegram authentication",
                    "error": "telegram_auth_required"
                }
            )
            return await response(scope, receive, send)

        # Store validated user_id in request state
        scope["state"] = {"telegram_user_id": user_id}

        return await self.app(scope, receive, send)
