"""Scheduler for daily blog digest delivery."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import structlog
import asyncio

from app.config import settings
from app.services.blog.digest_service import BlogDigestService
from app.models.blog import Base

logger = structlog.get_logger()


class DigestScheduler:
    """Scheduler for sending daily blog digests."""

    def __init__(self):
        """Initialize digest scheduler."""
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

        # Create database session
        engine = create_engine(settings.database_url)
        Base.metadata.create_all(bind=engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    async def send_daily_digest(self):
        """Send daily blog digest to all users."""
        try:
            logger.info("digest_scheduled_job_started")

            db = self.SessionLocal()
            try:
                digest_service = BlogDigestService(db)

                # Get articles for digest (3 articles from last 48 hours, excluding already sent)
                articles = digest_service.get_digest_articles(
                    limit=3,
                    hours_back=48,
                    exclude_sent=True
                )

                if not articles:
                    logger.info("no_articles_for_digest", message="No new articles found for digest")
                    return

                logger.info("digest_articles_found", count=len(articles))

                # Import here to avoid circular imports
                from app.services.telegram_bot_service import telegram_bot_service

                if not telegram_bot_service or not telegram_bot_service.bot:
                    logger.error("telegram_bot_not_initialized")
                    return

                # Send digest to all users
                # For now, we'll send to all users who have interacted with the bot
                # In production, you'd query your users table
                from app.services.calendar_service import calendar_service

                # Get all user IDs from calendar service (users who have calendars)
                # This is a placeholder - adjust based on your user management
                user_ids = set()

                # For testing, you can hardcode user IDs or get them from environment
                test_user_ids = settings.telegram_bot_token.split(',') if hasattr(settings, 'digest_test_users') else []

                # Get unique user IDs from calendar service
                try:
                    # This is a simplified approach - you should have a proper users table
                    # For now, we'll just log and skip actual sending
                    logger.info("digest_ready_to_send",
                               article_count=len(articles),
                               message="Ready to send digest (user management not implemented yet)")

                    # Create digest record with article IDs
                    article_ids = [article.id for article in articles]
                    digest = digest_service.create_digest(
                        article_ids=article_ids,
                        total_users_sent=len(user_ids)
                    )

                    logger.info("digest_job_completed",
                               digest_id=digest.id,
                               articles=len(articles))

                except Exception as e:
                    logger.error("digest_send_error", error=str(e), exc_info=True)

            finally:
                db.close()

        except Exception as e:
            logger.error("digest_job_error", error=str(e), exc_info=True)

    def start(self):
        """Start the digest scheduler."""
        if self.is_running:
            logger.warning("digest_scheduler_already_running")
            return

        # Schedule daily digest at 14:00 Moscow time
        # APScheduler uses local timezone by default, so we'll use cron expression
        self.scheduler.add_job(
            self.send_daily_digest,
            CronTrigger(hour=14, minute=0),  # Daily at 14:00
            id='daily_blog_digest',
            name='Daily Blog Digest',
            replace_existing=True
        )

        self.scheduler.start()
        self.is_running = True

        logger.info("digest_scheduler_started",
                   trigger="Daily at 14:00",
                   message="Blog digest scheduler started successfully")

    def stop(self):
        """Stop the digest scheduler."""
        if not self.is_running:
            return

        self.scheduler.shutdown()
        self.is_running = False
        logger.info("digest_scheduler_stopped")

    async def send_digest_now(self):
        """Manually trigger digest sending (for testing)."""
        logger.info("manual_digest_trigger")
        await self.send_daily_digest()


# Global scheduler instance
digest_scheduler = DigestScheduler()
