from fastapi import APIRouter, Request, Header, HTTPException, BackgroundTasks, Depends
import structlog

from app.config import settings
from app.services.telegram_handler import TelegramHandler

logger = structlog.get_logger()
router = APIRouter()
telegram_handler = TelegramHandler()

async def get_telegram_handler() -> TelegramHandler:
    """Dependency for Telegram handler with ensured initialization."""
    global telegram_handler
    await telegram_handler.ensure_initialized()
    return telegram_handler


async def safe_process_webhook_update(handler: TelegramHandler, update_data: dict):
    """Safe wrapper for background task with error handling."""
    try:
        await handler.process_webhook_update(update_data)
        logger.info("webhook_update_processed", update_id=update_data.get('update_id'))
    except Exception as e:
        logger.error(
            "webhook_background_task_failed",
            update_id=update_data.get('update_id'),
            error=str(e),
            exc_info=True
        )
        # TODO: отправка в Sentry/мониторинг


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str = Header(None),
    handler: TelegramHandler = Depends(get_telegram_handler)
):
    """
    Handle incoming Telegram webhooks.
    """
    # Проверка секрета
    if settings.telegram_webhook_secret:
        if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
            logger.warning(
                "webhook_unauthorized",
                provided_token=x_telegram_bot_api_secret_token[:8] + "..." if x_telegram_bot_api_secret_token else None,
                remote_addr=request.client.host if request.client else None
            )
            raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        data = await request.json()
        
        logger.info(
            "webhook_received",
            update_id=data.get('update_id'),
            has_message='message' in data,
            has_callback_query='callback_query' in data
        )

        background_tasks.add_task(
            safe_process_webhook_update,
            handler,
            data
        )

        return {"status": "accepted"}
        
    except Exception as e:
        logger.error("webhook_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/status")
async def telegram_status(
    handler: TelegramHandler = Depends(get_telegram_handler)
):
    """Get Telegram bot status."""
    try:
        me = await handler.bot.get_me()
        return {
            "status": "ok",
            "bot_username": me.username,
            "bot_id": me.id,
            "webhook_configured": bool(settings.telegram_webhook_secret)
        }
    except Exception as e:
        logger.error("status_check_error", error=str(e))
        return {"status": "error", "error": str(e)}


@router.post("/webhook/setup")
async def setup_webhook(
    handler: TelegramHandler = Depends(get_telegram_handler)
):
    """Setup webhook URL for Telegram."""
    webhook_url = f"{settings.app_base_url}/webhook"
    success = await handler.set_webhook(
        url=webhook_url,
        secret_token=settings.telegram_webhook_secret
    )
    
    return {
        "status": "success" if success else "error",
        "webhook_url": webhook_url,
        "secret_configured": bool(settings.telegram_webhook_secret)
    }