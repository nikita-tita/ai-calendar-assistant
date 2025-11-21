#!/usr/bin/env python3
"""Script to set Telegram webhook."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from telegram import Bot
from app.config import settings


async def set_webhook():
    """Set webhook for Telegram bot."""
    bot = Bot(token=settings.telegram_bot_token)

    if not settings.telegram_webhook_url:
        print("❌ TELEGRAM_WEBHOOK_URL not set in .env")
        return False

    try:
        # Delete existing webhook
        await bot.delete_webhook(drop_pending_updates=True)
        print("🗑️  Deleted existing webhook")

        # Set new webhook
        await bot.set_webhook(
            url=settings.telegram_webhook_url,
            secret_token=settings.telegram_webhook_secret,
            drop_pending_updates=True
        )

        # Verify webhook
        webhook_info = await bot.get_webhook_info()
        print(f"\n✅ Webhook set successfully!")
        print(f"📍 URL: {webhook_info.url}")
        print(f"🔗 Pending updates: {webhook_info.pending_update_count}")

        return True

    except Exception as e:
        print(f"❌ Error setting webhook: {e}")
        return False


async def delete_webhook():
    """Delete Telegram webhook."""
    bot = Bot(token=settings.telegram_bot_token)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Webhook deleted successfully!")
        return True

    except Exception as e:
        print(f"❌ Error deleting webhook: {e}")
        return False


async def get_webhook_info():
    """Get current webhook info."""
    bot = Bot(token=settings.telegram_bot_token)

    try:
        info = await bot.get_webhook_info()
        print(f"\n📊 Webhook Info:")
        print(f"URL: {info.url or 'Not set'}")
        print(f"Pending updates: {info.pending_update_count}")
        print(f"Last error: {info.last_error_message or 'None'}")
        if info.last_error_date:
            print(f"Last error date: {info.last_error_date}")

        return True

    except Exception as e:
        print(f"❌ Error getting webhook info: {e}")
        return False


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Manage Telegram webhook")
    parser.add_argument(
        'action',
        choices=['set', 'delete', 'info'],
        help='Action to perform'
    )

    args = parser.parse_args()

    if args.action == 'set':
        asyncio.run(set_webhook())
    elif args.action == 'delete':
        asyncio.run(delete_webhook())
    elif args.action == 'info':
        asyncio.run(get_webhook_info())


if __name__ == "__main__":
    main()
