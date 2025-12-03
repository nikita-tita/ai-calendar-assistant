"""Telegram webhook router."""

from fastapi import APIRouter, Request, Header, HTTPException, BackgroundTasks
from telegram import Update
from telegram.ext import Application
import structlog

from app.config import settings
from app.services.telegram_handler import TelegramHandler

logger = structlog.get_logger()

router = APIRouter()

# Initialize Telegram bot application
telegram_app: Application = None
telegram_handler: TelegramHandler = None


async def get_telegram_app() -> Application:
    """Get or create Telegram application instance."""
    global telegram_app, telegram_handler

    if telegram_app is None:
        telegram_app = (
            Application.builder()
            .token(settings.telegram_bot_token)
            .build()
        )
        await telegram_app.initialize()
        telegram_handler = TelegramHandler(telegram_app)

    return telegram_app


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str = Header(None)
):
    """
    Handle incoming Telegram webhooks.

    Security: Validates webhook secret token.
    """
    # Verify webhook secret
    if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        logger.warning(
            "webhook_unauthorized",
            provided_token=x_telegram_bot_api_secret_token[:10] + "..." if x_telegram_bot_api_secret_token else None
        )
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Parse update
    try:
        data = await request.json()
        update = Update.de_json(data, await get_telegram_app())

        # Determine message type for logging
        msg_type = "unknown"
        if update.message:
            if update.message.voice:
                msg_type = "voice"
            else:
                msg_type = "text"
        elif update.callback_query:
            msg_type = "callback_query"

        logger.info(
            "webhook_received",
            update_id=update.update_id,
            user_id=update.effective_user.id if update.effective_user else None,
            message_type=msg_type
        )

        # Process update in background - handles both messages and callback queries
        if update.callback_query:
            background_tasks.add_task(telegram_handler.handle_callback_query, update)
        else:
            background_tasks.add_task(telegram_handler.handle_update, update)

        return {"status": "ok"}

    except Exception as e:
        logger.error("webhook_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/status")
async def telegram_status():
    """Get Telegram bot status."""
    app = await get_telegram_app()
    bot = app.bot

    try:
        me = await bot.get_me()
        return {
            "status": "ok",
            "bot_username": me.username,
            "bot_id": me.id,
        }
    except Exception as e:
        logger.error("status_check_error", error=str(e))
        return {"status": "error", "error": str(e)}
