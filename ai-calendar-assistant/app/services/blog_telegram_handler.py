"""Telegram bot handler for blog digest functionality."""

from typing import List
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import structlog

from app.config import settings
from app.models.blog import BlogArticle, Base
from app.services.blog.digest_service import BlogDigestService

logger = structlog.get_logger()


class BlogTelegramHandler:
    """Handler for blog-related Telegram bot functionality."""

    def __init__(self, app: Application):
        """Initialize blog handler with Telegram application.

        Args:
            app: Telegram application instance
        """
        self.app = app
        self.bot = app.bot

        # Create database session
        engine = create_engine(settings.database_url)
        Base.metadata.create_all(bind=engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    async def send_digest_to_user(self, user_id: str, articles: List[BlogArticle]) -> bool:
        """Send blog digest to a single user.

        Args:
            user_id: Telegram user ID
            articles: List of articles to send

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if not articles:
                logger.info("no_articles_to_send", user_id=user_id)
                return False

            # Send header message
            header_text = f"📰 <b>Подборка статей о недвижимости</b>\n\n"
            header_text += f"Свежие статьи за последние дни ({len(articles)} шт.):\n"

            await self.bot.send_message(
                chat_id=user_id,
                text=header_text,
                parse_mode='HTML'
            )

            # Get digest service for preview formatting
            db = self.SessionLocal()
            try:
                digest_service = BlogDigestService(db)

                # Send each article with preview and button
                for i, article in enumerate(articles, 1):
                    # Format preview
                    preview = digest_service.format_article_preview(article, max_length=250)

                    # Create message text
                    message_text = f"<b>{i}. {article.title}</b>\n\n"
                    message_text += f"{preview}\n"

                    # Create inline keyboard with "Read more" button
                    # The button opens WebApp with article
                    webapp_url = f"{settings.telegram_webapp_url}/blog/{article.slug}"

                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton(
                            "📖 Читать подробнее",
                            web_app={"url": webapp_url}
                        )]
                    ])

                    await self.bot.send_message(
                        chat_id=user_id,
                        text=message_text,
                        parse_mode='HTML',
                        reply_markup=keyboard
                    )

                logger.info("digest_sent_to_user",
                           user_id=user_id,
                           articles_count=len(articles))

                return True

            finally:
                db.close()

        except Exception as e:
            logger.error("send_digest_error",
                        user_id=user_id,
                        error=str(e),
                        exc_info=True)
            return False

    async def send_digest_to_all_users(self, articles: List[BlogArticle], user_ids: List[str]) -> int:
        """Send blog digest to all users.

        Args:
            articles: List of articles to send
            user_ids: List of user IDs to send to

        Returns:
            Number of users successfully sent to
        """
        if not articles:
            logger.info("no_articles_for_broadcast")
            return 0

        sent_count = 0

        for user_id in user_ids:
            try:
                success = await self.send_digest_to_user(user_id, articles)
                if success:
                    sent_count += 1

            except Exception as e:
                logger.error("broadcast_user_error",
                            user_id=user_id,
                            error=str(e))
                continue

        logger.info("digest_broadcast_completed",
                   total_users=len(user_ids),
                   sent_count=sent_count)

        return sent_count

    async def handle_blog_command(self, update: Update) -> None:
        """Handle /blog command - send latest digest.

        Args:
            update: Telegram update object
        """
        user_id = str(update.effective_user.id)

        try:
            db = self.SessionLocal()
            try:
                digest_service = BlogDigestService(db)

                # Get latest articles (don't exclude sent ones for manual command)
                articles = digest_service.get_digest_articles(
                    limit=3,
                    hours_back=48,
                    exclude_sent=False  # Show latest articles even if sent before
                )

                if not articles:
                    await update.message.reply_text(
                        "📭 Пока нет новых статей.\n\n"
                        "Попробуйте позже!"
                    )
                    return

                # Send digest
                await self.send_digest_to_user(user_id, articles)

            finally:
                db.close()

        except Exception as e:
            logger.error("blog_command_error",
                        user_id=user_id,
                        error=str(e),
                        exc_info=True)

            await update.message.reply_text(
                "❌ Произошла ошибка при получении статей.\n"
                "Попробуйте позже."
            )


# Global instance (will be initialized when bot starts)
blog_telegram_handler = None


def initialize_blog_handler(app: Application):
    """Initialize blog telegram handler.

    Args:
        app: Telegram application instance
    """
    global blog_telegram_handler
    blog_telegram_handler = BlogTelegramHandler(app)
    logger.info("blog_telegram_handler_initialized")
    return blog_telegram_handler
