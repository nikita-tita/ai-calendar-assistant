"""Telegram bot message handler."""

import time
from datetime import datetime, timedelta
from typing import Optional
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application
import structlog

from app.config import settings
from app.services.llm_agent_yandex import llm_agent_yandex as llm_agent
from app.services.calendar_radicale import calendar_service, CalendarServiceError
from app.services.user_preferences import user_preferences
from app.services.todos_service import todos_service
from app.services.referral_service import referral_service
from app.services.followup_service import followup_service

# Analytics service - optional, fallback if not available
try:
    from app.services.analytics_service import analytics_service
    ANALYTICS_ENABLED = True
    logger_temp = structlog.get_logger()
    logger_temp.info("analytics_service_loaded", status="enabled")
except ImportError as e:
    analytics_service = None
    ANALYTICS_ENABLED = False
    logger_temp = structlog.get_logger()
    logger_temp.warning("analytics_service_unavailable", status="disabled", reason=str(e))
except Exception as e:
    analytics_service = None
    ANALYTICS_ENABLED = False
    logger_temp = structlog.get_logger()
    logger_temp.error("analytics_service_load_error", status="disabled", error=str(e))

try:
    from app.services.stt_yandex import STTServiceYandex
    stt_service = STTServiceYandex()
except ImportError:
    from app.services.stt import stt_service
from app.schemas.events import IntentType
from app.utils.datetime_parser import format_datetime_human
from app.utils.lru_dict import LRUDict

# Rate limiter - Redis primary with in-memory fallback
from app.services.rate_limiter_redis import get_rate_limiter

# Forum activity logger (optional)
try:
    from app.services.forum_logger import forum_logger
    FORUM_LOGGER_AVAILABLE = True
except ImportError:
    forum_logger = None
    FORUM_LOGGER_AVAILABLE = False

# ARCHIVED - Property Bot moved to independent microservice (_archived/property_bot_microservice)
# Property Bot imports removed - calendar bot only
PROPERTY_BOT_ENABLED = False

# Event context settings - track recently created events for follow-up commands
# Example: "в 10 утра встреча, в 11 обед" → creates 2 events → "перепиши на сегодня" knows which events
MAX_CONTEXT_EVENTS = 10       # Maximum events to track in context
MAX_CONTEXT_MESSAGES = 5      # Context expires after N messages without reference

# Dialog history settings - for better LLM understanding
# Stores last N message pairs (user + bot response) for context
MAX_DIALOG_HISTORY = 5        # Maximum message pairs to keep per user

logger = structlog.get_logger()


class TelegramHandler:
    """Handler for Telegram bot messages."""

    def __init__(self, app: Application):
        """Initialize handler with Telegram application."""
        self.app = app
        self.bot = app.bot
        # Store conversation history per user with LRU eviction (max 1000 users)
        # Prevents unbounded memory growth with many users
        self.conversation_history: LRUDict[str, list] = LRUDict(max_size=1000)
        # Store user timezone preferences with LRU eviction
        self.user_timezones: LRUDict[str, str] = LRUDict(max_size=1000)
        # Store recently created/modified events for context
        # Allows follow-up commands like "перепиши эти события на сегодня"
        # Structure: {"event_ids": ["uuid1", "uuid2"], "messages_age": 0}
        self.event_context: LRUDict[str, dict] = LRUDict(max_size=1000)
        # Dialog history for LLM context - stores last N message pairs
        # Structure: [{"role": "user", "text": "..."}, {"role": "assistant", "text": "..."}]
        self.dialog_history: LRUDict[str, list] = LRUDict(max_size=1000)

    def _log_bot_response(self, user_id: str, response_text: str, user_text: str = None):
        """Log bot response to analytics, forum logger, and dialog history.

        Args:
            user_id: Telegram user ID
            response_text: Bot's response
            user_text: Original user message (for dialog history)
        """
        # Save to dialog history for LLM context
        if user_text:
            self._add_to_dialog_history(user_id, user_text, response_text)

        # Log to analytics
        if ANALYTICS_ENABLED and analytics_service:
            try:
                from app.models.analytics import ActionType
                analytics_service.log_action(
                    user_id=user_id,
                    action_type=ActionType.BOT_RESPONSE,
                    details=response_text[:500] if response_text else None,
                    success=True
                )
            except Exception as e:
                logger.warning("analytics_bot_response_log_failed", error=str(e))

        # Log to forum
        if FORUM_LOGGER_AVAILABLE and forum_logger:
            forum_logger.log_bot_response(user_id, response_text)

    async def handle_update(self, update: Update) -> None:
        """
        Handle incoming Telegram update.

        Args:
            update: Telegram update object
        """
        if not update.message:
            return

        user_id = str(update.effective_user.id)
        message = update.message

        # Rate limiting check - Redis primary with in-memory fallback
        try:
            limiter = get_rate_limiter()
            is_allowed, reason = limiter.check_rate_limit(user_id)

            if not is_allowed:
                logger.warning("rate_limit_blocked", user_id=user_id, reason=reason)
                # Send rate limit message based on reason
                if "blocked" in reason:
                    rate_msg = "⚠️ Вы временно заблокированы из-за слишком частых запросов. Попробуйте позже."
                    await message.reply_text(rate_msg)
                    self._log_bot_response(user_id, rate_msg)
                else:
                    rate_msg = "⏳ Слишком много запросов. Пожалуйста, подождите немного."
                    await message.reply_text(rate_msg)
                    self._log_bot_response(user_id, rate_msg)
                return

            # Record message for rate limiting
            limiter.record_message(user_id)
        except Exception as e:
            # Fail open - allow request if rate limiter fails
            logger.warning("rate_limit_check_error", user_id=user_id, error=str(e))

        # Get user display name for forum logger
        user_name = update.effective_user.first_name or ""
        if update.effective_user.username:
            user_name += f" (@{update.effective_user.username})"

        # Log incoming message to forum
        if FORUM_LOGGER_AVAILABLE and forum_logger:
            msg_text = message.text if message.text else "[Медиа/Голос]"
            forum_logger.log_user_message(
                user_id=user_id,
                user_name=user_name,
                message_text=msg_text,
                is_voice=bool(message.voice)
            )

        try:
            # Handle /start command
            if message.text and message.text.startswith('/start'):
                await self._handle_start(update, user_id)
                return

            # Handle /calendar command
            if message.text and message.text.startswith('/calendar'):
                await self._handle_calendar_command(update, user_id)
                return

            # ARCHIVED - /property command removed (independent microservice)

            # Handle /settings command
            if message.text and message.text.startswith('/settings'):
                await self._handle_settings_command(update, user_id)
                return

            # Handle /timezone command
            if message.text and message.text.startswith('/timezone'):
                await self._handle_timezone(update, user_id, message.text)
                return

            # Handle /share command
            if message.text and message.text.startswith('/share'):
                await self._handle_share_command(update, user_id)
                return

            # Handle /templates command
            if message.text and message.text.startswith('/templates'):
                from app.services.template_gallery import get_templates_keyboard
                await update.message.reply_text(
                    "Выберите тип шаблона:",
                    reply_markup=get_templates_keyboard()
                )
                return

            # Handle quick buttons
            if message.text and message.text in ['📋 Дела на сегодня', 'Дела на сегодня']:
                await self._handle_text(update, user_id, "Какие планы на сегодня?")
                return

            if message.text and message.text in ['📅 Дела на завтра', 'Дела на завтра']:
                await self._handle_text(update, user_id, "Какие планы на завтра?")
                return

            if message.text and message.text in ['📆 Дела на неделю', 'Дела на неделю']:
                await self._handle_text(update, user_id, "Какие планы на эту неделю?")
                return

            # Handle MenuButton commands
            if message.text and message.text.startswith('/'):
                if message.text == '/calendar':
                    await self._handle_calendar_command(update, user_id)
                    return
                elif message.text == '/settings':
                    await self._handle_settings_command(update, user_id)
                    return
                # ARCHIVED - /property command removed (independent microservice)

            # Handle services button
            if message.text and message.text in ['🛠 Сервисы', 'Сервисы', '🛠️ Сервисы', '💡 Полезное', 'Полезное']:
                await self._handle_services_menu(update, user_id)
                return

            # ARCHIVED - Property button handler removed (independent microservice)

            if message.text and message.text in ['📅 Календарь', 'Календарь']:
                await self._handle_calendar_command(update, user_id)
                return

            if message.text and message.text in ['⚙️ Настройки', 'Настройки']:
                await self._handle_settings_command(update, user_id)
                return

            # Handle todos list button
            if message.text and message.text in ['✅ Задачи', 'Задачи']:
                await self._handle_todos_list(update, user_id)
                return

            # Handle templates button
            if message.text and message.text in ['✉️ Шаблоны', 'Шаблоны']:
                from app.services.template_gallery import get_templates_keyboard
                await update.message.reply_text(
                    "Выберите тип шаблона:",
                    reply_markup=get_templates_keyboard()
                )
                return

            # Handle voice message
            if message.voice:
                await self._handle_voice(update, user_id)
                return

            # Handle text message
            if message.text:
                # All text messages go to calendar
                await self._handle_text(update, user_id, message.text)
                return

            # Unknown message type
            unknown_msg = "Напишите текстом или голосом, что хотите запланировать."
            await message.reply_text(unknown_msg)
            self._log_bot_response(user_id, unknown_msg)

        except Exception as e:
            logger.error(
                "handle_update_error",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            error_msg = "Что-то сломалось. Попробуйте ещё раз."
            await message.reply_text(error_msg)
            self._log_bot_response(user_id, error_msg)

    async def _handle_start(self, update: Update, user_id: str) -> None:
        """Handle /start command."""
        message = update.message

        # Extract deep link parameter (e.g., /start ref_abc123)
        start_param = None
        if message.text and ' ' in message.text:
            start_param = message.text.split(' ', 1)[1].strip()

        # Process referral if present
        if start_param and start_param.startswith('ref_'):
            try:
                referrer_id = referral_service.process_referral(user_id, start_param)
                if referrer_id:
                    # Log referral to analytics
                    if ANALYTICS_ENABLED and analytics_service:
                        from app.models.analytics import ActionType
                        analytics_service.log_action(
                            user_id=user_id,
                            action_type=ActionType.REFERRAL_JOINED,
                            details=f"Joined via referral from {referrer_id}",
                            success=True,
                            username=update.effective_user.username if update.effective_user else None,
                            first_name=update.effective_user.first_name if update.effective_user else None,
                            last_name=update.effective_user.last_name if update.effective_user else None
                        )
                    # Notify referrer
                    await self._notify_referrer(referrer_id, update.effective_user)
            except Exception as e:
                logger.warning("referral_processing_failed", error=str(e))

        # Log user registration
        if ANALYTICS_ENABLED and analytics_service:
            try:
                analytics_service.log_action(
                    user_id=user_id,
                    action_type="user_login",
                    details="/start command",
                    success=True,
                    username=update.effective_user.username if update.effective_user else None,
                    first_name=update.effective_user.first_name if update.effective_user else None,
                    last_name=update.effective_user.last_name if update.effective_user else None
                )
            except Exception as e:
                logger.warning("analytics_log_failed", error=str(e))

        # Notify admin about new /start
        await self._notify_admin_new_user(update.effective_user, user_id)

        # Check if user has already given consents
        advertising_consent = user_preferences.get_advertising_consent(user_id)
        privacy_consent = user_preferences.get_privacy_consent(user_id)

        if not advertising_consent or not privacy_consent:
            # Ask for combined consent (Phase 2.2)
            await self._ask_combined_consent(update, user_id)
            return

        # Both consents given - show welcome message
        await self._send_welcome_message(update.message, user_id)

    async def _notify_admin_new_user(self, user, user_id: str) -> None:
        """Send notification to admin about new /start via separate bot."""
        try:
            token = settings.notify_bot_token
            chat_id = settings.notify_chat_id
            if not token or not chat_id:
                return

            import httpx
            name = user.first_name or "" if user else ""
            last = f" {user.last_name}" if user and user.last_name else ""
            username = f"@{user.username}" if user and user.username else "нет"
            ts = datetime.now().strftime("%d.%m.%Y %H:%M")

            text = (
                f"📱 <b>Новая регистрация AI Calendar</b>\n\n"
                f"👤 {name}{last}\n"
                f"🆔 {username} (ID: {user_id})\n"
                f"🕐 {ts}"
            )

            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                )
        except Exception as e:
            logger.warning("admin_notify_failed", error=str(e))

    async def _send_welcome_message(self, message, user_id: str) -> None:
        """Send welcome message and setup keyboard.

        Reusable helper for both /start command and callback buttons.

        Args:
            message: Telegram Message object (from update.message or query.message)
            user_id: User ID string
        """
        welcome_text = """👋 Привет! Я ваш персональный ИИ-помощник по планированию.

📅 **Создавайте события:**
• "Встреча завтра в 14:00 с клиентом"
• "Показ квартиры в пятницу 10:00"

📝 **Добавляйте задачи:**
• "Обновить персональные данные"
• "Позвонить собственнику"

📊 **Смотрите планы:**
• Используйте кнопки "Дела на сегодня" или "Дела на завтра"
• Откройте 🗓 **Кабинет** для полного обзора

✅ **Управляйте задачами:**
• Нажмите кнопку "Задачи" для списка дел

🎤 Можете использовать голос — удобно за рулем."""

        keyboard = ReplyKeyboardMarkup([
            [KeyboardButton("📋 Дела на сегодня")],
            [KeyboardButton("📅 Дела на завтра"), KeyboardButton("✅ Задачи")],
            [KeyboardButton("⚙️ Настройки"), KeyboardButton("💡 Полезное")]
        ], resize_keyboard=True)

        await message.reply_text(welcome_text, reply_markup=keyboard, parse_mode="Markdown")

        # Setup WebApp MenuButton
        try:
            from telegram import MenuButtonWebApp, WebAppInfo
            webapp_url = f"{settings.telegram_webapp_url}?v=2025103001"
            menu_button = MenuButtonWebApp(
                text="🗓 Кабинет",
                web_app=WebAppInfo(url=webapp_url)
            )
            await self.bot.set_chat_menu_button(
                chat_id=message.chat_id,
                menu_button=menu_button
            )
            logger.info("menu_button_webapp_set", user_id=user_id, webapp_url=webapp_url)
        except Exception as e:
            logger.warning("menu_button_set_failed", error=str(e))

        # Create demo content for new users (Phase 2.1)
        await self._create_demo_content(message, user_id)

    async def _create_demo_content(self, message, user_id: str) -> None:
        """Create demo event and todo for new users on first start.

        Only creates if user has zero events (prevents re-creation on repeat /start).
        Any failure is silently caught — onboarding continues normally.
        """
        try:
            # Check if user already has events (repeat /start guard)
            now = datetime.now()
            existing = await calendar_service.list_events(
                user_id,
                now - timedelta(days=30),
                now + timedelta(days=30)
            )
            if existing:
                return  # Not first time — skip demo

            # Create demo event: tomorrow at 14:00, 1 hour
            tomorrow = now + timedelta(days=1)
            demo_start = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
            demo_end = demo_start + timedelta(hours=1)

            from app.schemas.events import EventDTO, IntentType
            demo_event = EventDTO(
                intent=IntentType.CREATE,
                title="Пример: Встреча с клиентом",
                description="Это демо-событие. Удалите или измените как хотите!",
                start_time=demo_start,
                end_time=demo_end,
                confidence=1.0
            )
            event_uid = await calendar_service.create_event(user_id, demo_event)

            # Create demo todo
            from app.schemas.todos import TodoDTO
            demo_todo = TodoDTO(
                title="Пример: Подготовить документы для встречи"
            )
            todo_id = await todos_service.create_todo(user_id, demo_todo)

            if event_uid or todo_id:
                hint = (
                    "💡 Я добавил пример события и задачи, чтобы вы увидели как это работает.\n\n"
                    "Попробуйте написать:\n"
                    "• «Что на завтра?»\n"
                    "• «Встреча в пятницу в 10:00»\n"
                    "• «Позвонить собственнику»"
                )
                await message.reply_text(hint)

            logger.info("demo_content_created",
                       user_id=user_id,
                       event=bool(event_uid),
                       todo=bool(todo_id))

        except CalendarServiceError:
            # Calendar unavailable — skip demo silently
            logger.warning("demo_content_skipped_calendar_error", user_id=user_id)
        except Exception as e:
            # Don't fail onboarding because of demo
            logger.warning("demo_content_failed", user_id=user_id, error=str(e))

    async def _ask_advertising_consent(self, update: Update, user_id: str) -> None:
        """Ask for advertising consent."""
        message_text = """Для дальнейшего взаимодействия с ботом необходимо дать согласие на получение новостей и рекламных рассылок.

[Соглашение на получение рекламы](https://housler.ru/doc/clients/soglasiya/advertising-agreement/)"""

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Даю согласие", callback_data="consent:advertising:yes"),
                InlineKeyboardButton("❌ Не даю", callback_data="consent:advertising:no")
            ]
        ])

        # Send to correct place (message or callback_query)
        if update.message:
            await update.message.reply_text(message_text, reply_markup=keyboard, parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.message.reply_text(message_text, reply_markup=keyboard, parse_mode="Markdown")

    async def _ask_privacy_consent(self, update: Update, user_id: str) -> None:
        """Ask for privacy policy consent."""
        message = """Для дальнейшего взаимодействия с ботом необходимо дать согласие на обработку персональных данных.

[Политика конфиденциальности](https://housler.ru/doc/clients/politiki/)"""

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Даю согласие", callback_data="consent:privacy:yes"),
                InlineKeyboardButton("❌ Не даю", callback_data="consent:privacy:no")
            ]
        ])

        # Send message either via message or callback_query
        if update.message:
            await update.message.reply_text(message, reply_markup=keyboard, parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.message.reply_text(message, reply_markup=keyboard, parse_mode="Markdown")

    async def _ask_combined_consent(self, update: Update, user_id: str) -> None:
        """Ask for both advertising and privacy consent on one screen (Phase 2.2)."""
        message_text = (
            "Для использования бота необходимо ваше согласие:\n\n"
            "📄 [Соглашение на получение рекламы](https://housler.ru/doc/clients/soglasiya/advertising-agreement/)\n"
            "🔒 [Политика конфиденциальности](https://housler.ru/doc/clients/politiki/)\n\n"
            "Нажимая «Принимаю», вы соглашаетесь с обоими документами."
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Принимаю", callback_data="consent:combined:yes")],
            [InlineKeyboardButton("❌ Не принимаю", callback_data="consent:combined:no")]
        ])

        if update.message:
            await update.message.reply_text(message_text, reply_markup=keyboard, parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.message.reply_text(message_text, reply_markup=keyboard, parse_mode="Markdown")

    async def _notify_referrer(self, referrer_id: str, new_user) -> None:
        """Notify referrer when someone joins via their link."""
        try:
            name = new_user.first_name or "Кто-то"

            text = f"🎉 По твоей ссылке присоединился новый пользователь: {name}!\n\n" \
                   f"Спасибо что рассказываешь о нас друзьям"

            await self.bot.send_message(chat_id=int(referrer_id), text=text)

            # Mark as notified
            referral_service.mark_notified(str(new_user.id))

            logger.info("referrer_notified", referrer_id=referrer_id, new_user_id=new_user.id)

        except Exception as e:
            logger.warning("referrer_notification_failed",
                          referrer_id=referrer_id, error=str(e))

    async def _handle_share_command(self, update: Update, user_id: str) -> None:
        """Handle /share command - show referral link and stats."""
        try:
            stats = referral_service.get_referral_stats(user_id)
            link = stats['referral_link']
            total = stats['total_referred']

            # Invite text for copying
            invite_text = (
                "Попробуй AI-календарь! Веду все дела голосом - "
                "просто говорю боту что запланировать.\n\n"
                f"Присоединяйся: {link}"
            )

            # Message to user
            message = f"""<b>Поделиться с друзьями</b>

Приглашение (нажми чтобы скопировать):

<code>{invite_text}</code>

<b>Твоя статистика:</b>
Присоединились по ссылке: {total}"""

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Переслать друзьям",
                                     switch_inline_query=invite_text)]
            ])

            await update.message.reply_text(
                message,
                parse_mode="HTML",
                reply_markup=keyboard
            )

        except Exception as e:
            logger.error("share_command_failed", user_id=user_id, error=str(e))
            await update.message.reply_text(
                "Не удалось получить ссылку. Попробуйте позже."
            )

    async def _handle_voice(self, update: Update, user_id: str) -> None:
        """Handle voice message using OpenAI Whisper."""
        logger.info("voice_message_received", user_id=user_id)

        # Log voice message to analytics
        if ANALYTICS_ENABLED and analytics_service:
            try:
                analytics_service.log_action(
                    user_id=user_id,
                    action_type="voice_message",
                    details="Voice message received",
                    success=True,
                    username=update.effective_user.username if update.effective_user else None,
                    first_name=update.effective_user.first_name if update.effective_user else None,
                    last_name=update.effective_user.last_name if update.effective_user else None
                )
            except Exception as e:
                logger.warning("analytics_log_failed", error=str(e))

        try:
            await update.message.reply_text("🎤 Слушаю...")

            # Download voice file
            voice = update.message.voice
            voice_file = await self.bot.get_file(voice.file_id)
            voice_bytes = await voice_file.download_as_bytearray()

            # Transcribe using OpenAI Whisper
            text = await stt_service.transcribe_audio(bytes(voice_bytes))

            if not text:
                await update.message.reply_text(
                    "Не разобрал. Попробуйте ещё раз или напишите текстом."
                )
                return

            logger.info("voice_transcribed", user_id=user_id, text=text)

            # Show transcribed text
            await update.message.reply_text(f'Вы: "{text}"')

            # Process as text (from_voice=True to skip double logging)
            await self._handle_text(update, user_id, text, from_voice=True)

        except Exception as e:
            logger.error("voice_transcription_failed", user_id=user_id, error=str(e))
            # Log STT error to analytics
            if ANALYTICS_ENABLED and analytics_service:
                try:
                    from app.models.analytics import ActionType
                    analytics_service.log_action(
                        user_id=user_id,
                        action_type=ActionType.STT_ERROR,
                        details="Voice transcription failed",
                        success=False,
                        error_message=str(e)[:200],
                        username=update.effective_user.username if update.effective_user else None,
                        first_name=update.effective_user.first_name if update.effective_user else None,
                        last_name=update.effective_user.last_name if update.effective_user else None
                    )
                except Exception as analytics_err:
                    logger.warning("analytics_log_failed", error=str(analytics_err))
            await update.message.reply_text(
                "Ошибка распознавания. Напишите текстом."
            )

    async def _handle_timezone(self, update: Update, user_id: str, text: str) -> None:
        """Handle /timezone command to set user timezone."""
        parts = text.split()

        if len(parts) == 1:
            # Show current timezone and available options with inline buttons
            current_tz = user_preferences.get_timezone(user_id)

            # Create inline keyboard with timezone buttons
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏛 Москва (UTC+3)", callback_data="tz:Europe/Moscow")],
                [InlineKeyboardButton("🏛 Самара (UTC+4)", callback_data="tz:Europe/Samara")],
                [InlineKeyboardButton("🏛 Екатеринбург (UTC+5)", callback_data="tz:Asia/Yekaterinburg")],
                [InlineKeyboardButton("🏛 Омск (UTC+6)", callback_data="tz:Asia/Omsk")],
                [InlineKeyboardButton("🏛 Красноярск (UTC+7)", callback_data="tz:Asia/Krasnoyarsk")],
                [InlineKeyboardButton("🏛 Иркутск (UTC+8)", callback_data="tz:Asia/Irkutsk")],
                [InlineKeyboardButton("🏛 Якутск (UTC+9)", callback_data="tz:Asia/Yakutsk")],
                [InlineKeyboardButton("🏛 Владивосток (UTC+10)", callback_data="tz:Asia/Vladivostok")],
                [InlineKeyboardButton("🏛 Магадан (UTC+11)", callback_data="tz:Asia/Magadan")],
                [InlineKeyboardButton("🏛 Камчатка (UTC+12)", callback_data="tz:Asia/Kamchatka")],
                [InlineKeyboardButton("🌍 Киев (UTC+2)", callback_data="tz:Europe/Kiev")],
                [InlineKeyboardButton("🌍 Алматы (UTC+6)", callback_data="tz:Asia/Almaty")],
                [InlineKeyboardButton("🌍 Ташкент (UTC+5)", callback_data="tz:Asia/Tashkent")],
                [InlineKeyboardButton("🌍 Минск (UTC+3)", callback_data="tz:Europe/Minsk")],
            ])

            await update.message.reply_text(
                f"Сейчас: {current_tz}\n\nВыберите часовой пояс:",
                reply_markup=keyboard
            )
            return

        # Set timezone
        timezone = parts[1]
        try:
            import pytz
            pytz.timezone(timezone)  # Validate timezone
            user_preferences.set_timezone(user_id, timezone)
            await update.message.reply_text(f"✅ Установлен: {timezone}")
        except Exception as e:
            logger.error("timezone_set_error", user_id=user_id, timezone=timezone, error=str(e))
            await update.message.reply_text(
                "Неверный пояс. Используйте /timezone для списка."
            )

    async def _handle_calendar_command(self, update: Update, user_id: str) -> None:
        """Handle /calendar command - already in calendar bot."""
        await update.message.reply_text(
            "📅 Вы уже в календарном боте!\n\n"
            "Я помогу вам с планированием дел и событий. Просто напишите, что хотите запланировать."
        )

    async def _handle_todos_list(self, update: Update, user_id: str) -> None:
        """Handle todos list button - show text-based list of todos."""
        try:
            # Fetch all todos for the user
            todos = await todos_service.list_todos(user_id)

            if not todos:
                empty_todos_msg = ("📝 Список задач пуст.\n\n"
                    "Чтобы добавить задачу, просто напишите что нужно сделать, например:\n"
                    "• Обновить персональные данные\n"
                    "• Позвонить собственнику\n\n"
                    "📋 Можно также открыть 🗓 **Кабинет** для управления задачами")
                await update.message.reply_text(empty_todos_msg, parse_mode="Markdown")
                self._log_bot_response(user_id, empty_todos_msg)
                return

            # Filter only active todos
            active_todos = [t for t in todos if not t.completed]

            # Build message
            message_parts = []

            if active_todos:
                message_parts.append(f"📋 <b>Активные задачи ({len(active_todos)}):</b>\n")
                for i, todo in enumerate(active_todos, 1):
                    message_parts.append(f"{i}. {todo.title}")
                message_parts.append("")

            message_parts.append("📝 Отметить выполненные задачи можно в 🗓 Кабинете")

            todos_msg = "\n".join(message_parts)
            await update.message.reply_text(todos_msg, parse_mode="HTML")
            self._log_bot_response(user_id, todos_msg)

        except Exception as e:
            logger.error("todos_list_error", user_id=user_id, error=str(e), exc_info=True)
            error_todos_msg = "⏳ Секунду...\n\nНе удалось загрузить список задач. Попробуйте позже."
            await update.message.reply_text(error_todos_msg)
            self._log_bot_response(user_id, error_todos_msg)

    async def _handle_services_menu(self, update: Update, user_id: str) -> None:
        """Handle services menu button - show Housler and M2 services."""
        message = """💡 <b>Полезное</b>

Housler.ru сделал подборку сервисов, которые помогут вам еще сильнее упростить жизнь
- сервис для расчета оптимальной цены продажи
- новостной блог о недвижимости

С сервисами m2.ru:
- можно легко подать заявку на ипотеку в несколько банков
- провести сделку и регистрацию и расчёты
- конечно же защитить сделку от юридических рисков

А с arenda.yandex.ru можно даже получить доп. комиссию на сделках по аренде

Просто выбери свой сервис"""

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Поделиться с друзьями", callback_data="share:menu")],
            [InlineKeyboardButton("📰 Новости", url="https://housler.ru/blog")],
            [InlineKeyboardButton("🏷 Оценить рыночную стоимость", url="https://housler.ru/calculator")],
            [InlineKeyboardButton("💰 Ипотечный брокер", url="https://m2.ru/ipoteka/calculator/?utm_source=telegram&utm_medium=message&utm_campaign=inhouse_nobrand_rassmotr_ipoteka_b2b_internal_chatbot")],
            [InlineKeyboardButton("🛡 Защита сделки", url="https://m2.ru/services/guaranteed-deal/?utm_source=telegram&utm_medium=message&utm_campaign=inhouse_nobrand_rassmotr_guaranteed-deal_b2b_internal_chatbot")],
            [InlineKeyboardButton("📋 Регистрация и безопасные расчеты", url="https://m2.ru/services/deal/?utm_source=telegram&utm_medium=message&utm_campaign=inhouse_nobrand_rassmotr_sdelka_b2b_internal_chatbot")],
            [InlineKeyboardButton("🏠 Аренда", url="https://arenda.yandex.ru/pages/for-agents/?utm_source=menu_landing")]
        ])

        await update.message.reply_text(
            message,
            parse_mode="HTML",
            reply_markup=keyboard
        )

    # ARCHIVED - Property command handler removed (independent microservice)
    # Method _handle_property_command deleted

    async def _send_settings_menu(self, update: Update, user_id: str, query=None) -> None:
        """Send settings menu (reusable helper)."""
        # Get current settings
        settings_data = user_preferences.get_all_settings(user_id)

        morning_status = "✅" if settings_data["morning_summary_enabled"] else "❌"
        evening_status = "✅" if settings_data["evening_digest_enabled"] else "❌"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"⏰ Часовой пояс: {settings_data['timezone']}", callback_data="settings:timezone")],
            [InlineKeyboardButton(f"{morning_status} Утренняя сводка ({settings_data['morning_summary_time']})", callback_data="settings:morning_toggle")],
            [InlineKeyboardButton(f"{evening_status} Вечерний дайджест ({settings_data['evening_digest_time']})", callback_data="settings:evening_toggle")],
            [InlineKeyboardButton(f"🌙 Тихие часы: {settings_data['quiet_hours_start']}–{settings_data['quiet_hours_end']}", callback_data="settings:quiet_hours")],
            [InlineKeyboardButton("📤 Поделиться с друзьями", callback_data="settings:share")],
            [InlineKeyboardButton("❓ Справка и примеры", callback_data="settings:help")],
            [InlineKeyboardButton("💬 Написать нам", url="https://t.me/iay_pm")],
        ])

        text = "⚙️ Настройки\n\nУправляйте временем и напоминаниями. Коротко и по делу."

        if query:
            # Edit existing message (from callback)
            await query.edit_message_text(text, reply_markup=keyboard)
        else:
            # Send new message (from command)
            await update.message.reply_text(text, reply_markup=keyboard)

    async def _handle_settings_command(self, update: Update, user_id: str) -> None:
        """Handle /settings command."""
        await self._send_settings_menu(update, user_id)

    # ========== Callback Query Handlers (ARCH-002) ==========

    async def _handle_consent_callback(
        self, query, update: Update, user_id: str, data: str
    ) -> bool:
        """
        Handle consent:* callbacks.
        Returns True if handled, False otherwise.
        """
        if not data.startswith("consent:"):
            return False

        parts = data.split(":")
        consent_type = parts[1]  # "advertising", "privacy", or "combined"
        answer = parts[2]  # "yes" or "no"

        if answer == "yes":
            if consent_type == "combined":
                # Phase 2.2: Combined consent — accept both at once
                user_preferences.set_advertising_consent(user_id, True)
                user_preferences.set_privacy_consent(user_id, True)
                logger.info("combined_consent_given", user_id=user_id)
                if ANALYTICS_ENABLED and analytics_service:
                    try:
                        from app.models.analytics import ActionType
                        analytics_service.log_action(
                            user_id=user_id,
                            action_type=ActionType.CONSENT_ADVERTISING_ACCEPTED,
                            details="Согласие на рекламу принято (combined)",
                            success=True,
                            username=update.effective_user.username if update.effective_user else None,
                            first_name=update.effective_user.first_name if update.effective_user else None,
                            last_name=update.effective_user.last_name if update.effective_user else None
                        )
                        analytics_service.log_action(
                            user_id=user_id,
                            action_type=ActionType.CONSENT_PRIVACY_ACCEPTED,
                            details="Согласие на обработку данных принято (combined)",
                            success=True,
                            username=update.effective_user.username if update.effective_user else None,
                            first_name=update.effective_user.first_name if update.effective_user else None,
                            last_name=update.effective_user.last_name if update.effective_user else None
                        )
                    except Exception as e:
                        logger.warning("analytics_consent_log_failed", error=str(e))
                await query.edit_message_text("✅ Согласие принято. Добро пожаловать!")
                await self._send_welcome_message(query.message, user_id)

            elif consent_type == "advertising":
                user_preferences.set_advertising_consent(user_id, True)
                logger.info("advertising_consent_given", user_id=user_id)
                if ANALYTICS_ENABLED and analytics_service:
                    try:
                        from app.models.analytics import ActionType
                        analytics_service.log_action(
                            user_id=user_id,
                            action_type=ActionType.CONSENT_ADVERTISING_ACCEPTED,
                            details="Согласие на рекламу принято",
                            success=True,
                            username=update.effective_user.username if update.effective_user else None,
                            first_name=update.effective_user.first_name if update.effective_user else None,
                            last_name=update.effective_user.last_name if update.effective_user else None
                        )
                    except Exception as e:
                        logger.warning("analytics_consent_log_failed", error=str(e))
                await query.edit_message_text("✅ Согласие на получение рекламы принято")
                await self._ask_privacy_consent(update, user_id)

            elif consent_type == "privacy":
                user_preferences.set_privacy_consent(user_id, True)
                logger.info("privacy_consent_given", user_id=user_id)
                if ANALYTICS_ENABLED and analytics_service:
                    try:
                        from app.models.analytics import ActionType
                        analytics_service.log_action(
                            user_id=user_id,
                            action_type=ActionType.CONSENT_PRIVACY_ACCEPTED,
                            details="Согласие на обработку данных принято",
                            success=True,
                            username=update.effective_user.username if update.effective_user else None,
                            first_name=update.effective_user.first_name if update.effective_user else None,
                            last_name=update.effective_user.last_name if update.effective_user else None
                        )
                    except Exception as e:
                        logger.warning("analytics_consent_log_failed", error=str(e))
                await query.edit_message_text("✅ Согласие на обработку данных принято")
                await self._send_welcome_message(query.message, user_id)
        else:
            # User declined
            if consent_type == "combined":
                # Phase 2.2: Combined decline
                if ANALYTICS_ENABLED and analytics_service:
                    try:
                        from app.models.analytics import ActionType
                        analytics_service.log_action(
                            user_id=user_id,
                            action_type=ActionType.CONSENT_ADVERTISING_DECLINED,
                            details="Согласие отклонено (combined)",
                            success=True,
                            username=update.effective_user.username if update.effective_user else None,
                            first_name=update.effective_user.first_name if update.effective_user else None,
                            last_name=update.effective_user.last_name if update.effective_user else None
                        )
                    except Exception as e:
                        logger.warning("analytics_consent_log_failed", error=str(e))
                await query.edit_message_text(
                    "❌ Без согласия продолжить невозможно.\n\nПопробуйте снова:"
                )
                await self._ask_combined_consent(update, user_id)

            elif consent_type == "advertising":
                if ANALYTICS_ENABLED and analytics_service:
                    try:
                        from app.models.analytics import ActionType
                        analytics_service.log_action(
                            user_id=user_id,
                            action_type=ActionType.CONSENT_ADVERTISING_DECLINED,
                            details="Согласие на рекламу отклонено",
                            success=True,
                            username=update.effective_user.username if update.effective_user else None,
                            first_name=update.effective_user.first_name if update.effective_user else None,
                            last_name=update.effective_user.last_name if update.effective_user else None
                        )
                    except Exception as e:
                        logger.warning("analytics_consent_log_failed", error=str(e))
                await query.edit_message_text(
                    "❌ Без согласия на получение рекламы продолжить невозможно.\n\nПопробуйте снова:"
                )
                await self._ask_advertising_consent(update, user_id)

            elif consent_type == "privacy":
                if ANALYTICS_ENABLED and analytics_service:
                    try:
                        from app.models.analytics import ActionType
                        analytics_service.log_action(
                            user_id=user_id,
                            action_type=ActionType.CONSENT_PRIVACY_DECLINED,
                            details="Согласие на обработку данных отклонено",
                            success=True,
                            username=update.effective_user.username if update.effective_user else None,
                            first_name=update.effective_user.first_name if update.effective_user else None,
                            last_name=update.effective_user.last_name if update.effective_user else None
                        )
                    except Exception as e:
                        logger.warning("analytics_consent_log_failed", error=str(e))
                await query.edit_message_text(
                    "❌ Без согласия на обработку данных продолжить невозможно.\n\nПопробуйте снова:"
                )
                await self._ask_privacy_consent(update, user_id)

        return True

    async def _handle_timezone_callback(
        self, query, user_id: str, data: str
    ) -> bool:
        """
        Handle tz:* callbacks.
        Returns True if handled, False otherwise.
        """
        if not data.startswith("tz:"):
            return False

        timezone = data[3:]  # Remove "tz:" prefix
        try:
            import pytz
            pytz.timezone(timezone)  # Validate timezone
            user_preferences.set_timezone(user_id, timezone)
            city = timezone.split('/')[-1].replace('_', ' ')
            await query.edit_message_text(f"✅ Часовой пояс обновлен: {city}")
            logger.info("timezone_set", user_id=user_id, timezone=timezone)
        except Exception as e:
            logger.error("timezone_set_error", user_id=user_id, error=str(e))
            await query.edit_message_text("Ошибка при установке пояса")

        return True

    async def _handle_settings_callback(
        self, query, update: Update, user_id: str, data: str
    ) -> bool:
        """
        Handle settings:*, morning:*, evening:*, quiet:*, share:* callbacks.
        Returns True if handled, False otherwise.
        """
        # Morning summary toggle
        if data == "settings:morning_toggle":
            current_enabled = user_preferences.get_morning_summary_enabled(user_id)
            current_time = user_preferences.get_morning_summary_time(user_id)
            status_text = "включена" if current_enabled else "выключена"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    f"{'✅ Выключить' if current_enabled else '❌ Включить'}",
                    callback_data="morning:toggle"
                )],
                [InlineKeyboardButton(f"🕐 Изменить время (сейчас: {current_time})", callback_data="morning:change_time")],
                [InlineKeyboardButton("« Назад к настройкам", callback_data="settings:back")],
            ])
            await query.edit_message_text(
                f"🌅 Утренняя сводка\n\nСейчас: {status_text}, в {current_time}\n\nКороткий план на день: встречи, окна, важные напоминания.",
                reply_markup=keyboard
            )
            return True

        elif data == "morning:toggle":
            current = user_preferences.get_morning_summary_enabled(user_id)
            user_preferences.set_morning_summary_enabled(user_id, not current)
            status = "включена" if not current else "выключена"
            await query.edit_message_text(f"✅ Утренняя сводка {status}")
            return True

        elif data == "morning:change_time":
            await query.edit_message_text(
                "🕐 Изменить время утренней сводки\n\nНапишите время в формате ЧЧ:ММ\nНапример: 07:30"
            )
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            self.conversation_history[user_id] = [{"role": "system", "content": "awaiting_morning_time"}]
            return True

        # Evening digest toggle
        elif data == "settings:evening_toggle":
            current_enabled = user_preferences.get_evening_digest_enabled(user_id)
            current_time = user_preferences.get_evening_digest_time(user_id)
            status_text = "включен" if current_enabled else "выключен"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    f"{'✅ Выключить' if current_enabled else '❌ Включить'}",
                    callback_data="evening:toggle"
                )],
                [InlineKeyboardButton(f"🕐 Изменить время (сейчас: {current_time})", callback_data="evening:change_time")],
                [InlineKeyboardButton("« Назад к настройкам", callback_data="settings:back")],
            ])
            await query.edit_message_text(
                f"🌆 Вечерний дайджест\n\nСейчас: {status_text}, в {current_time}\n\nКороткий итог дня. Без лишних слов.",
                reply_markup=keyboard
            )
            return True

        elif data == "evening:toggle":
            current = user_preferences.get_evening_digest_enabled(user_id)
            user_preferences.set_evening_digest_enabled(user_id, not current)
            status = "включен" if not current else "выключен"
            await query.edit_message_text(f"✅ Вечерний дайджест {status}")
            return True

        elif data == "evening:change_time":
            await query.edit_message_text(
                "🕐 Изменить время вечернего дайджеста\n\nНапишите время в формате ЧЧ:ММ\nНапример: 20:00"
            )
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            self.conversation_history[user_id] = [{"role": "system", "content": "awaiting_evening_time"}]
            return True

        # Share menu
        elif data in ("settings:share", "share:menu"):
            try:
                stats = referral_service.get_referral_stats(user_id)
                link = stats['referral_link']
                total = stats['total_referred']
                invite_text = (
                    "Попробуй AI-календарь! Веду все дела голосом - "
                    "просто говорю боту что запланировать.\n\n"
                    f"Присоединяйся: {link}"
                )
                message = f"""<b>Поделиться с друзьями</b>

Приглашение (нажми чтобы скопировать):

<code>{invite_text}</code>

<b>Твоя статистика:</b>
Присоединились по ссылке: {total}"""
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Переслать друзьям", switch_inline_query=invite_text)],
                    [InlineKeyboardButton("« Назад", callback_data="settings:back")]
                ])
                await query.edit_message_text(message, parse_mode="HTML", reply_markup=keyboard)
            except Exception as e:
                logger.error("share_callback_failed", user_id=user_id, error=str(e))
                await query.edit_message_text("Не удалось получить ссылку. Попробуйте позже.")
            return True

        elif data == "settings:help":
            help_text = """❓ Справка и примеры команд

Я понимаю простые фразы:
• "Показ завтра 14:00"
• "Перенеси встречу на 16:00"
• "Что у меня на неделе?"
• "Напомни через 2 часа"
• "Удали встречу с Ивановым"
• "Есть свободные слоты на завтра?"

Можете писать текстом или голосом."""
            await query.edit_message_text(help_text)
            return True

        elif data == "settings:timezone":
            current_tz = user_preferences.get_timezone(user_id)
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏛 Москва (UTC+3)", callback_data="tz:Europe/Moscow")],
                [InlineKeyboardButton("🌍 Санкт-Петербург (UTC+3)", callback_data="tz:Europe/Moscow")],
                [InlineKeyboardButton("🌍 Екатеринбург (UTC+5)", callback_data="tz:Asia/Yekaterinburg")],
                [InlineKeyboardButton("🌍 Новосибирск (UTC+7)", callback_data="tz:Asia/Novosibirsk")],
                [InlineKeyboardButton("🌍 Владивосток (UTC+10)", callback_data="tz:Asia/Vladivostok")],
                [InlineKeyboardButton("🌍 Киев (UTC+2)", callback_data="tz:Europe/Kiev")],
                [InlineKeyboardButton("🌍 Ташкент (UTC+5)", callback_data="tz:Asia/Tashkent")],
                [InlineKeyboardButton("🌍 Минск (UTC+3)", callback_data="tz:Europe/Minsk")],
            ])
            await query.edit_message_text(
                f"⏰ Часовой пояс\n\nСейчас: {current_tz}\n\nВыберите ваш часовой пояс, чтобы напоминания приходили вовремя.",
                reply_markup=keyboard
            )
            return True

        elif data == "settings:quiet_hours":
            quiet_start, quiet_end = user_preferences.get_quiet_hours(user_id)
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🕐 Изменить начало", callback_data="quiet:change_start")],
                [InlineKeyboardButton("🕐 Изменить конец", callback_data="quiet:change_end")],
                [InlineKeyboardButton("« Назад к настройкам", callback_data="settings:back")],
            ])
            await query.edit_message_text(
                f"🌙 Тихие часы\n\nСейчас: {quiet_start}–{quiet_end}\n\nВ это время я не присылаю уведомления.",
                reply_markup=keyboard
            )
            return True

        elif data == "quiet:change_start":
            quiet_start, quiet_end = user_preferences.get_quiet_hours(user_id)
            await query.edit_message_text(
                f"🕐 Изменить начало тихих часов\n\nСейчас: {quiet_start}–{quiet_end}\n\nНапишите время начала в формате ЧЧ:ММ\nНапример: 23:00"
            )
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            self.conversation_history[user_id] = [{"role": "system", "content": "awaiting_quiet_start"}]
            return True

        elif data == "quiet:change_end":
            quiet_start, quiet_end = user_preferences.get_quiet_hours(user_id)
            await query.edit_message_text(
                f"🕐 Изменить конец тихих часов\n\nСейчас: {quiet_start}–{quiet_end}\n\nНапишите время окончания в формате ЧЧ:ММ\nНапример: 08:00"
            )
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            self.conversation_history[user_id] = [{"role": "system", "content": "awaiting_quiet_end"}]
            return True

        elif data == "settings:back":
            await self._send_settings_menu(update, user_id, query=query)
            return True

        return False

    async def _handle_deletion_callback(
        self, query, user_id: str, data: str
    ) -> bool:
        """
        Handle confirm_delete_* and cancel_delete:* callbacks.
        Returns True if handled, False otherwise.
        """
        if data.startswith("confirm_delete_"):
            await query.answer("Удаляю...")

            if user_id not in self.conversation_history or len(self.conversation_history[user_id]) == 0:
                await query.edit_message_text("Время истекло. Попробуйте ещё раз.")
                return True

            last_msg = self.conversation_history[user_id][-1]
            pending_action = last_msg.get("content")

            if pending_action == "pending_delete_duplicates" and data.startswith("confirm_delete_duplicates:"):
                event_ids = last_msg.get("duplicates", [])
                action_name = "дубликатов"
            elif pending_action == "pending_delete_by_criteria" and data.startswith("confirm_delete_criteria:"):
                event_ids = last_msg.get("events", [])
                action_name = "событий"
            else:
                await query.edit_message_text("Неверная команда.")
                return True

            await query.edit_message_text(f"⏳ Удаляю {len(event_ids)} {action_name}...")

            deleted_count = 0
            for event_id in event_ids:
                success = await calendar_service.delete_event(user_id, event_id)
                if success:
                    deleted_count += 1

            self.conversation_history[user_id] = []
            await query.edit_message_text(f"✅ Удалено {action_name}: {deleted_count}")
            return True

        elif data.startswith("cancel_delete:"):
            await query.answer()
            self.conversation_history[user_id] = []
            await query.edit_message_text("Отменено.")
            return True

        return False

    async def _handle_broadcast_callback(
        self, query, update: Update, user_id: str, data: str
    ) -> bool:
        """
        Handle broadcast:* callbacks.
        Returns True if handled, False otherwise.
        """
        if data != "broadcast:start":
            return False

        # Log broadcast click for conversion tracking
        if ANALYTICS_ENABLED and analytics_service:
            try:
                from app.models.analytics import ActionType
                analytics_service.log_action(
                    user_id=user_id,
                    action_type=ActionType.BROADCAST_CLICK,
                    details="Clicked broadcast button",
                    success=True,
                    username=update.effective_user.username if update.effective_user else None,
                    first_name=update.effective_user.first_name if update.effective_user else None,
                    last_name=update.effective_user.last_name if update.effective_user else None
                )
            except Exception as e:
                logger.warning("analytics_broadcast_click_log_failed", error=str(e))

        await query.answer()

        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

        advertising_consent = user_preferences.get_advertising_consent(user_id)
        privacy_consent = user_preferences.get_privacy_consent(user_id)

        if not advertising_consent or not privacy_consent:
            await self._ask_combined_consent(update, user_id)
            return True

        await self._send_welcome_message(query.message, user_id)
        return True

    async def handle_callback_query(self, update: Update) -> None:
        """
        Handle callback queries from inline buttons.

        ARCH-002: Refactored from ~371 lines to ~30 lines using helper methods.
        Routes callbacks to specialized handlers based on prefix.
        """
        query = update.callback_query
        if not query:
            return

        await query.answer()

        user_id = str(update.effective_user.id)
        data = query.data

        # Route to specialized handlers (each returns True if handled)
        if await self._handle_consent_callback(query, update, user_id, data):
            return

        if await self._handle_timezone_callback(query, user_id, data):
            return

        if await self._handle_settings_callback(query, update, user_id, data):
            return

        if await self._handle_deletion_callback(query, user_id, data):
            return

        if await self._handle_broadcast_callback(query, update, user_id, data):
            return

        if await self._handle_hint_callback(query, update, user_id, data):
            return

        if await self._handle_template_callback(query, update, user_id, data):
            return

        if await self._handle_followup_callback(query, update, user_id, data):
            return

        if await self._handle_followup_action_callback(query, update, user_id, data):
            return

        # Unknown callback - log for debugging
        logger.warning("unknown_callback_query", user_id=user_id, data=data)

    # ========== Quick-start Hints (Phase 2.3) ==========

    def _should_show_hints(self, user_id: str) -> bool:
        """Check if user is new enough to show quick-start hints.

        Hides hints after 10+ successful interactions to reduce noise.
        """
        if not ANALYTICS_ENABLED or not analytics_service:
            return True  # Show by default if analytics unavailable
        try:
            count = analytics_service.get_user_action_count(user_id)
            return count < 10
        except Exception:
            return True  # Show by default on error

    def _get_quick_hints_keyboard(self) -> InlineKeyboardMarkup:
        """Get inline keyboard with quick-start action hints."""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📋 Что на завтра?", callback_data="hint:query_tomorrow"),
                InlineKeyboardButton("✅ Мои задачи", callback_data="hint:my_todos"),
            ],
            [
                InlineKeyboardButton("➕ Добавить встречу", callback_data="hint:add_meeting"),
            ]
        ])

    async def _handle_hint_callback(
        self, query, update: Update, user_id: str, data: str
    ) -> bool:
        """Handle hint:* callbacks — simulate user typing a common phrase."""
        if not data.startswith("hint:"):
            return False

        hint_type = data[5:]  # Remove "hint:" prefix

        # Map hint types to simulated user text
        hint_texts = {
            "query_tomorrow": "Что на завтра?",
            "my_todos": "Мои задачи",
            "add_meeting": "Встреча завтра в 15:00",
        }

        simulated_text = hint_texts.get(hint_type)
        if not simulated_text:
            return False

        # Remove hint buttons from the message to avoid re-clicks
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

        # Process as if user typed the text
        await self._handle_text(update, user_id, simulated_text)
        return True

    async def _handle_template_callback(
        self, query, update: Update, user_id: str, data: str
    ) -> bool:
        """Handle template:* callbacks — template gallery navigation."""
        if not data.startswith("template:"):
            return False

        from app.services.template_gallery import (
            get_client_templates_keyboard, get_event_templates_keyboard,
            get_templates_keyboard, CLIENT_TEMPLATES, EVENT_TEMPLATES,
            render_client_template, get_field_prompt,
        )

        action = data[9:]  # Remove "template:" prefix

        if action == "client_menu":
            await query.edit_message_text(
                "✉️ Тексты для клиентов\nВыберите шаблон:",
                reply_markup=get_client_templates_keyboard()
            )
            return True

        elif action == "event_menu":
            await query.edit_message_text(
                "📅 Создать событие\nВыберите тип:",
                reply_markup=get_event_templates_keyboard()
            )
            return True

        elif action == "back":
            await query.edit_message_text(
                "Выберите тип шаблона:",
                reply_markup=get_templates_keyboard()
            )
            return True

        elif action.startswith("client:"):
            tpl_id = action[7:]  # Remove "client:"
            tpl = CLIENT_TEMPLATES.get(tpl_id)
            if not tpl:
                return False

            # Show template preview with empty fields
            fields = {f: f"[{get_field_prompt(f)}]" for f in tpl["fields"]}
            preview = render_client_template(tpl_id, fields)

            msg = (
                f"**{tpl['title']}**\n\n"
                f"{preview}\n\n"
                f"Отправьте данные одним сообщением или голосом.\n"
                f"Нужные поля: {', '.join(get_field_prompt(f) for f in tpl['fields'])}"
            )

            # Store template context for next message
            if not hasattr(self, '_template_context'):
                self._template_context = {}
            self._template_context[user_id] = {
                "type": "client",
                "template_id": tpl_id,
                "fields": {},
                "pending_fields": list(tpl["fields"]),
            }

            try:
                await query.edit_message_text(msg)
            except Exception:
                await query.message.reply_text(msg)
            return True

        elif action.startswith("event:"):
            tpl_id = action[6:]  # Remove "event:"
            tpl = EVENT_TEMPLATES.get(tpl_id)
            if not tpl:
                return False

            # Start guided event creation
            if not hasattr(self, '_template_context'):
                self._template_context = {}
            self._template_context[user_id] = {
                "type": "event",
                "template_id": tpl_id,
                "fields": {},
                "pending_fields": list(tpl["field_names"]),
                "prompts": list(tpl["prompts"]),
                "current_prompt_idx": 0,
            }

            # Ask first question
            first_prompt = tpl["prompts"][0]
            try:
                await query.edit_message_text(f"{tpl['title']}\n\n{first_prompt}")
            except Exception:
                await query.message.reply_text(f"{tpl['title']}\n\n{first_prompt}")
            return True

        return False

    def _check_template_context(self, user_id: str, text: str) -> Optional[str]:
        """Check if user is in template filling mode and process input.

        Returns response message if handled, None otherwise.
        """
        if not hasattr(self, '_template_context'):
            return None

        ctx = self._template_context.get(user_id)
        if not ctx:
            return None

        if ctx["type"] == "client":
            return self._process_client_template_input(user_id, text, ctx)
        elif ctx["type"] == "event":
            return self._process_event_template_input(user_id, text, ctx)
        return None

    def _process_client_template_input(self, user_id: str, text: str, ctx: dict) -> Optional[str]:
        """Process input for client text template."""
        from app.services.template_gallery import (
            render_client_template, extract_fields_from_text, get_field_prompt,
            CLIENT_TEMPLATES,
        )

        tpl_id = ctx["template_id"]
        pending = ctx["pending_fields"]

        # Try bulk extraction first
        if len(ctx["fields"]) == 0:
            extracted = extract_fields_from_text(text, pending)
            if extracted:
                ctx["fields"].update(extracted)
                pending = [f for f in pending if f not in extracted]

        # If still have pending fields, fill next one
        if pending:
            field = pending[0]
            if field not in ctx["fields"]:
                ctx["fields"][field] = text.strip()
            pending = pending[1:]
            ctx["pending_fields"] = pending

        if pending:
            # Ask for next field
            next_field = pending[0]
            return f"Укажите: {get_field_prompt(next_field)}"

        # All fields filled — render template
        result = render_client_template(tpl_id, ctx["fields"])
        del self._template_context[user_id]

        return f"✅ Готово! Скопируйте и отправьте клиенту:\n\n{result}"

    def _process_event_template_input(self, user_id: str, text: str, ctx: dict) -> Optional[str]:
        """Process input for event template. Returns None when event should be created."""
        pending = ctx["pending_fields"]
        idx = ctx["current_prompt_idx"]

        if pending:
            field = pending[0]
            ctx["fields"][field] = text.strip()
            ctx["pending_fields"] = pending[1:]
            ctx["current_prompt_idx"] = idx + 1

        if ctx["pending_fields"]:
            # Ask next question
            prompts = ctx["prompts"]
            next_idx = ctx["current_prompt_idx"]
            if next_idx < len(prompts):
                return prompts[next_idx]
            return f"Укажите: {ctx['pending_fields'][0]}"

        # All fields collected — create event via normal flow
        from app.services.template_gallery import EVENT_TEMPLATES
        tpl = EVENT_TEMPLATES.get(ctx["template_id"])
        fields = ctx["fields"]
        del self._template_context[user_id]

        # Build natural language command for existing parser
        parts = [tpl["title"].split(" ", 1)[-1]]  # Remove emoji
        if "client_name" in fields:
            parts.append(fields["client_name"])
        if "address" in fields:
            parts.append(fields["address"])
        if "developer" in fields:
            parts.append(fields["developer"])
        if "topic" in fields:
            parts.append(fields["topic"])
        if "parties" in fields:
            parts.append(fields["parties"])
        if "time_text" in fields:
            parts.append(fields["time_text"])

        # Return special marker so caller knows to process as event creation
        return f"__CREATE_EVENT__:{' '.join(parts)}"

    async def _handle_followup_callback(
        self, query, update: Update, user_id: str, data: str
    ) -> bool:
        """Handle followup:* callbacks — record follow-up response."""
        if not data.startswith("followup:"):
            return False

        parts = data.split(":")
        if len(parts) < 3:
            return False

        response_type = parts[1]  # positive, negative, reschedule, skip
        fu_id = int(parts[2])

        if not followup_service:
            return False

        # Record response
        fu_data = followup_service.record_response(fu_id, response_type)

        # Remove buttons
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

        if response_type == "skip":
            await query.message.reply_text("⏭ Пропущено")
            return True

        # Post-response feedback
        _response_messages = {
            "positive": "👍 Отлично!",
            "negative": "📝 Понял, записал",
            "reschedule": "🔄 Записал",
        }
        msg = _response_messages.get(response_type, "✅ Записал")

        # Post-event quick actions for positive follow-ups (Sprint 5)
        if response_type == "positive" and fu_data and fu_data.get("event_type") == "showing":
            buttons = [
                [
                    InlineKeyboardButton("📅 Повторный показ", callback_data=f"followup_action:reschedule:{fu_id}"),
                    InlineKeyboardButton("📞 Позвонить завтра", callback_data=f"followup_action:call_tomorrow:{fu_id}"),
                ],
                [
                    InlineKeyboardButton("📋 Подготовить документы", callback_data=f"followup_action:prepare_docs:{fu_id}"),
                ],
            ]
            msg += "\nЧто дальше?"
            await query.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(buttons))
        elif response_type == "reschedule" and fu_data:
            title = fu_data.get("event_title", "Событие")
            await query.message.reply_text(f"{msg}\nНапишите когда перенести: «{title} завтра в 14:00»")
        else:
            await query.message.reply_text(msg)

        return True

    async def _handle_followup_action_callback(
        self, query, update: Update, user_id: str, data: str
    ) -> bool:
        """Handle followup_action:* callbacks — post-follow-up quick actions."""
        if not data.startswith("followup_action:"):
            return False

        parts = data.split(":")
        if len(parts) < 3:
            return False

        action = parts[1]
        fu_id = int(parts[2])

        # Remove buttons
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

        if not followup_service:
            return False

        # Get follow-up data to extract title
        try:
            import sqlite3
            conn = sqlite3.connect(str(followup_service.db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT event_title FROM follow_ups WHERE id = ?", (fu_id,))
            row = cursor.fetchone()
            conn.close()
            title = row[0] if row else "Событие"
        except Exception:
            title = "Событие"

        if action == "call_tomorrow":
            # Create todo for tomorrow call
            from app.schemas.events import EventDTO, IntentType
            todo_dto = EventDTO(
                intent=IntentType.TODO,
                title=f"Позвонить клиенту по: {title}",
                confidence=1.0,
            )
            await self._handle_create_todo(update, user_id, todo_dto)
        elif action == "prepare_docs":
            from app.schemas.events import EventDTO, IntentType
            todo_dto = EventDTO(
                intent=IntentType.TODO,
                title=f"Подготовить документы: {title}",
                confidence=1.0,
            )
            await self._handle_create_todo(update, user_id, todo_dto)
        elif action == "reschedule":
            await query.message.reply_text(
                f"Напишите когда повторный показ:\n«{title} послезавтра в 14:00»"
            )
        else:
            return False

        return True

    def _get_user_timezone(self, update: Update) -> str:
        """Get user timezone from stored preferences or default to Moscow."""
        user_id = str(update.effective_user.id)
        return user_preferences.get_timezone(user_id)

    # ========== Event Context Methods ==========
    # Track recently created events for follow-up commands like "перепиши эти события"

    def _add_to_event_context(self, user_id: str, event_ids: list) -> None:
        """
        Add event IDs to user's context for follow-up commands.

        Args:
            user_id: Telegram user ID
            event_ids: List of event UUIDs to add
        """
        if not event_ids:
            return

        ctx = self.event_context.get(user_id, {"event_ids": [], "messages_age": 0})

        # Add new IDs, avoid duplicates
        existing_ids = set(ctx.get("event_ids", []))
        for eid in event_ids:
            if eid and eid not in existing_ids:
                existing_ids.add(eid)

        # Limit to MAX_CONTEXT_EVENTS
        all_ids = list(existing_ids)[-MAX_CONTEXT_EVENTS:]

        self.event_context[user_id] = {
            "event_ids": all_ids,
            "messages_age": 0  # Reset age when new events added
        }
        logger.debug("event_context_updated", user_id=user_id, event_ids=all_ids)

    def _remove_from_event_context(self, user_id: str, event_ids: list) -> None:
        """
        Remove event IDs from user's context (after deletion).

        Args:
            user_id: Telegram user ID
            event_ids: List of event UUIDs to remove
        """
        if user_id not in self.event_context:
            return

        ctx = self.event_context[user_id]
        current_ids = set(ctx.get("event_ids", []))

        for eid in event_ids:
            current_ids.discard(eid)

        if current_ids:
            self.event_context[user_id] = {
                "event_ids": list(current_ids),
                "messages_age": ctx.get("messages_age", 0)
            }
        else:
            # No events left, clear context
            self.event_context.pop(user_id, None)

    def _get_event_context(self, user_id: str) -> list:
        """
        Get event IDs from user's context if not expired.

        Args:
            user_id: Telegram user ID

        Returns:
            List of event UUIDs or empty list if expired/not found
        """
        if user_id not in self.event_context:
            return []

        ctx = self.event_context[user_id]

        # Check if context expired
        if ctx.get("messages_age", 0) >= MAX_CONTEXT_MESSAGES:
            self.event_context.pop(user_id, None)
            return []

        return ctx.get("event_ids", [])

    def _age_event_context(self, user_id: str) -> None:
        """
        Increment context age after each message.
        Called after processing each user message.

        Args:
            user_id: Telegram user ID
        """
        if user_id not in self.event_context:
            return

        ctx = self.event_context[user_id]
        ctx["messages_age"] = ctx.get("messages_age", 0) + 1

        # Clear if expired
        if ctx["messages_age"] >= MAX_CONTEXT_MESSAGES:
            self.event_context.pop(user_id, None)
            logger.debug("event_context_expired", user_id=user_id)

    def _reset_context_age(self, user_id: str) -> None:
        """
        Reset context age when user references context events.
        Called when LLM uses context for update/delete.

        Args:
            user_id: Telegram user ID
        """
        if user_id in self.event_context:
            self.event_context[user_id]["messages_age"] = 0

    # ========== End Event Context Methods ==========

    # ========== Dialog History Methods ==========
    # Track conversation history for better LLM context understanding

    def _add_to_dialog_history(self, user_id: str, user_text: str, bot_response: str) -> None:
        """
        Add a message pair to user's dialog history.

        Args:
            user_id: Telegram user ID
            user_text: User's message
            bot_response: Bot's response
        """
        if user_id not in self.dialog_history:
            self.dialog_history[user_id] = []

        # Add user message and bot response
        self.dialog_history[user_id].append({
            "role": "user",
            "text": user_text[:500]  # Limit to 500 chars
        })
        self.dialog_history[user_id].append({
            "role": "assistant",
            "text": bot_response[:500]  # Limit to 500 chars
        })

        # Keep only last MAX_DIALOG_HISTORY pairs (2 messages per pair)
        max_messages = MAX_DIALOG_HISTORY * 2
        if len(self.dialog_history[user_id]) > max_messages:
            self.dialog_history[user_id] = self.dialog_history[user_id][-max_messages:]

        logger.debug("dialog_history_updated", user_id=user_id,
                    history_len=len(self.dialog_history[user_id]))

    def _get_dialog_history(self, user_id: str) -> list:
        """
        Get dialog history for user.

        Args:
            user_id: Telegram user ID

        Returns:
            List of message dicts with role and text
        """
        return self.dialog_history.get(user_id, [])

    def _clear_dialog_history(self, user_id: str) -> None:
        """Clear dialog history for user."""
        if user_id in self.dialog_history:
            del self.dialog_history[user_id]

    # ========== End Dialog History Methods ==========

    # ========== DateTime Parsing Helpers ==========

    def _parse_action_datetime(self, dt_value) -> Optional[datetime]:
        """
        Parse datetime from batch action value.
        Handles string ISO format, datetime objects, and None.

        Args:
            dt_value: Can be ISO string, datetime, or None

        Returns:
            datetime object or None if parsing fails
        """
        from datetime import datetime
        import pytz

        if dt_value is None:
            return None

        if isinstance(dt_value, datetime):
            # Already datetime - ensure timezone
            if dt_value.tzinfo is None:
                tz = pytz.timezone(settings.default_timezone)
                return tz.localize(dt_value)
            return dt_value

        if isinstance(dt_value, str):
            try:
                dt = datetime.fromisoformat(dt_value)
                # Add timezone if naive
                if dt.tzinfo is None:
                    tz = pytz.timezone(settings.default_timezone)
                    dt = tz.localize(dt)
                return dt
            except (ValueError, TypeError):
                logger.warning("datetime_parse_failed", value=dt_value)
                return None

        return None

    # ========== End DateTime Parsing Helpers ==========

    # ========== Context Enrichment Helpers ==========

    def _enrich_short_response(self, user_text: str, user_id: str) -> str:
        """
        Enrich short user response with previous context.

        When user replies with just a time ("12:00") or short phrase ("завтра")
        to a clarify question, combine it with the original request.

        Args:
            user_text: Current user message
            user_id: User ID for context lookup

        Returns:
            Enriched text or original text if no enrichment needed
        """
        # Only enrich very short messages (1-3 words)
        words = user_text.strip().split()
        if len(words) > 3:
            return user_text

        # Check if we have clarify context
        history = self.conversation_history.get(user_id, [])
        if len(history) < 2:
            return user_text

        last_bot = history[-1]
        prev_user = history[-2]

        # Must be assistant clarify followed by short user response
        if last_bot.get("role") != "assistant" or prev_user.get("role") != "user":
            return user_text

        bot_response = last_bot.get("content", "").lower()
        prev_request = prev_user.get("content", "")

        # Detect if bot asked for time clarification
        time_clarify_patterns = ["уточните время", "во сколько", "какое время", "укажите время"]
        if any(p in bot_response for p in time_clarify_patterns):
            # Combine: "Брокер тур" + "12:00" → "Брокер тур в 12:00"
            enriched = f"{prev_request} в {user_text}"
            logger.info("short_response_enriched",
                       user_id=user_id,
                       original=user_text,
                       enriched=enriched,
                       reason="time_clarify")
            return enriched

        # Detect if bot asked for date clarification
        date_clarify_patterns = ["уточните дату", "какой день", "когда", "укажите день"]
        if any(p in bot_response for p in date_clarify_patterns):
            # Combine: "Встреча" + "завтра" → "Встреча завтра"
            enriched = f"{prev_request} {user_text}"
            logger.info("short_response_enriched",
                       user_id=user_id,
                       original=user_text,
                       enriched=enriched,
                       reason="date_clarify")
            return enriched

        return user_text

    # ========== End Context Enrichment Helpers ==========

    async def _handle_settings_time_input(
        self, update: Update, user_id: str, text: str, pending_action: str
    ) -> bool:
        """
        Handle time input for settings (morning/evening time, quiet hours).

        Args:
            update: Telegram update
            user_id: User ID
            text: User input text
            pending_action: What setting is being changed

        Returns:
            True if handled, False if not a valid time input
        """
        import re
        time_pattern = r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$'
        match = re.match(time_pattern, text.strip())

        if not match:
            await update.message.reply_text("Неверный формат. Введите время как ЧЧ:ММ (например, 07:30)")
            return True  # Handled (with error)

        time_str = text.strip()

        if pending_action == "awaiting_morning_time":
            user_preferences.set_morning_summary_time(user_id, time_str)
            self.conversation_history[user_id] = []
            await update.message.reply_text(f"✅ Время утренней сводки изменено на {time_str}")

        elif pending_action == "awaiting_evening_time":
            user_preferences.set_evening_digest_time(user_id, time_str)
            self.conversation_history[user_id] = []
            await update.message.reply_text(f"✅ Время вечернего дайджеста изменено на {time_str}")

        elif pending_action == "awaiting_quiet_start":
            quiet_start, quiet_end = user_preferences.get_quiet_hours(user_id)
            user_preferences.set_quiet_hours(user_id, time_str, quiet_end)
            self.conversation_history[user_id] = []
            await update.message.reply_text(f"✅ Начало тихих часов изменено на {time_str}")

        elif pending_action == "awaiting_quiet_end":
            quiet_start, quiet_end = user_preferences.get_quiet_hours(user_id)
            user_preferences.set_quiet_hours(user_id, quiet_start, time_str)
            self.conversation_history[user_id] = []
            await update.message.reply_text(f"✅ Конец тихих часов изменён на {time_str}")

        else:
            return False  # Unknown action

        return True

    async def _handle_delete_confirmation(
        self, update: Update, user_id: str, text: str, pending_action: str, last_msg: dict
    ) -> bool:
        """
        Handle deletion confirmation (duplicates or by criteria).

        Args:
            update: Telegram update
            user_id: User ID
            text: User input text
            pending_action: Type of deletion pending
            last_msg: Last message in conversation history

        Returns:
            True if handled, False otherwise
        """
        text_lower = text.lower().strip()

        if text_lower in ['удалить', 'да', 'ok', 'yes', 'удали']:
            # Get event IDs to delete
            if pending_action == "pending_delete_duplicates":
                event_ids = last_msg.get("duplicates", [])
            else:  # pending_delete_by_criteria
                event_ids = last_msg.get("events", [])

            # Delete events
            deleted_count = 0
            for event_id in event_ids:
                success = await calendar_service.delete_event(user_id, event_id)
                if success:
                    deleted_count += 1

            self.conversation_history[user_id] = []
            await update.message.reply_text(f"✅ Удалено {deleted_count}")
            return True

        elif text_lower in ['отмена', 'нет', 'cancel', 'no']:
            self.conversation_history[user_id] = []
            await update.message.reply_text("Отменено.")
            return True

        return False  # Not a confirmation/cancellation

    async def _handle_text(self, update: Update, user_id: str, text: str, from_voice: bool = False) -> None:
        """Handle text message - only calendar mode.

        Args:
            from_voice: If True, skip analytics logging (already logged as voice_message)
        """
        _handle_start = time.perf_counter()
        logger.info("text_message_received", user_id=user_id, text=text, from_voice=from_voice)

        # Log message to analytics (skip if from voice - already logged as voice_message)
        if ANALYTICS_ENABLED and analytics_service and not from_voice:
            try:
                analytics_service.log_action(
                    user_id=user_id,
                    action_type="text_message",
                    details=f"Text: {text[:200]}" if len(text) <= 200 else f"Text: {text[:197]}...",
                    success=True,
                    username=update.effective_user.username if update.effective_user else None,
                    first_name=update.effective_user.first_name if update.effective_user else None,
                    last_name=update.effective_user.last_name if update.effective_user else None
                )
            except Exception as e:
                logger.warning("analytics_log_failed", error=str(e))

        text_lower = text.lower().strip()

        # ========== Template context check (guided template filling) ==========
        template_response = self._check_template_context(user_id, text)
        if template_response:
            if template_response.startswith("__CREATE_EVENT__:"):
                # Event template completed — process as natural language event creation
                event_text = template_response[17:]
                # Fall through to normal text processing with constructed text
                text = event_text
                text_lower = text.lower().strip()
            else:
                await update.message.reply_text(template_response)
                self._log_bot_response(user_id, template_response, text)
                return

        # ========== Pre-LLM Handlers (avoid expensive LLM calls) ==========

        # Handle greetings
        greeting_patterns = ["привет", "здравствуй", "добрый день", "добрый вечер",
                            "доброе утро", "hello", "hi", "хай", "здарова"]
        if any(text_lower.startswith(g) or text_lower == g for g in greeting_patterns):
            greeting_response = ("👋 Привет! Чем могу помочь?\n\n"
                                "📅 Создать событие: «Встреча завтра в 15:00»\n"
                                "📝 Добавить задачу: «Позвонить клиенту»\n"
                                "📋 Посмотреть планы: «Что на сегодня?»")
            reply_markup = self._get_quick_hints_keyboard() if self._should_show_hints(user_id) else None
            await update.message.reply_text(greeting_response, reply_markup=reply_markup)
            self._log_bot_response(user_id, greeting_response, text)
            return

        # Handle small talk
        small_talk_patterns = ["как дела", "как ты", "что нового", "как жизнь"]
        if any(p in text_lower for p in small_talk_patterns):
            small_talk_response = ("Отлично, готов работать! 💪\n\nЧто запланируем?")
            await update.message.reply_text(small_talk_response)
            self._log_bot_response(user_id, small_talk_response, text)
            return

        # Handle timezone complaints
        time_complaint_patterns = ["неправильно время", "сбился календарь", "неверное время",
                                  "какое сегодня число", "какой сейчас час", "какое время",
                                  "не то время", "время неправильное"]
        if any(p in text_lower for p in time_complaint_patterns):
            import pytz
            current_tz = user_preferences.get_timezone(user_id)
            now = datetime.now(pytz.timezone(current_tz))
            tz_response = (f"🕐 Моё время: {now.strftime('%H:%M')} ({current_tz})\n"
                          f"📅 Дата: {now.strftime('%d.%m.%Y')}\n\n"
                          f"Если нужно изменить часовой пояс — /timezone")
            await update.message.reply_text(tz_response)
            self._log_bot_response(user_id, tz_response, text)
            return

        # ========== End Pre-LLM Handlers ==========

        # Calendar mode only
        # Check calendar service connection
        if not calendar_service.is_connected():
            await update.message.reply_text(
                "⚠️ Календарный сервер временно недоступен.\nПопробуйте позже."
            )
            return

        # Check if user is in a settings or deletion flow
        if user_id in self.conversation_history and len(self.conversation_history[user_id]) > 0:
            last_msg = self.conversation_history[user_id][-1]
            pending_action = last_msg.get("content")

            # Handle time input for settings
            if last_msg.get("role") == "system":
                handled = await self._handle_settings_time_input(update, user_id, text, pending_action)
                if handled:
                    return

            # Handle deletion confirmation
            if (last_msg.get("role") == "assistant" and
                pending_action in ["pending_delete_duplicates", "pending_delete_by_criteria"]):
                handled = await self._handle_delete_confirmation(
                    update, user_id, text, pending_action, last_msg
                )
                if handled:
                    return

        # Process with LLM
        await update.message.reply_text("⏳ Секунду...")

        # Get or create conversation history for this user
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []

        # Get user timezone
        user_tz = self._get_user_timezone(update)

        # ALWAYS load events from calendar before processing request
        # This allows Claude to see what exists and make informed decisions
        from datetime import datetime, timedelta
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=7)
        end = now + timedelta(days=60)
        calendar_had_error = False
        try:
            existing_events = await calendar_service.list_events(user_id, start, end)
        except CalendarServiceError:
            existing_events = []
            calendar_had_error = True
            logger.warning("calendar_unavailable_for_context", user_id=user_id)
        _events_duration_ms = (time.perf_counter() - _handle_start) * 1000

        logger.info("events_loaded_for_context", user_id=user_id, count=len(existing_events), duration_ms=round(_events_duration_ms, 1), calendar_error=calendar_had_error)

        # Get recent context events (for follow-up commands like "перепиши эти события")
        context_event_ids = self._get_event_context(user_id)
        recent_context_events = []
        if context_event_ids and existing_events:
            context_ids_set = set(context_event_ids)
            recent_context_events = [e for e in existing_events if e.id in context_ids_set]
            logger.debug("recent_context_loaded", user_id=user_id, count=len(recent_context_events))

        # Get dialog history for better LLM context understanding
        # This helps LLM understand what user wants based on previous messages
        dialog_history = self._get_dialog_history(user_id)

        # Also check if last message was a clarify question (for immediate context)
        clarify_context = []
        if len(self.conversation_history[user_id]) >= 2:
            last_assistant = self.conversation_history[user_id][-1]
            prev_user = self.conversation_history[user_id][-2]
            if (last_assistant.get("role") == "assistant" and
                prev_user.get("role") == "user"):
                clarify_context = [prev_user, last_assistant]

        # Combine dialog history with clarify context
        # Format: older messages first, then clarify context if any
        combined_history = dialog_history + clarify_context

        # Enrich short responses with context from previous clarify question
        # Example: "12:00" after "Уточните время" → "Брокер тур в 12:00"
        enriched_text = self._enrich_short_response(text, user_id)

        event_dto = await llm_agent.extract_event(
            enriched_text,
            user_id,
            conversation_history=combined_history,
            timezone=user_tz,
            existing_events=existing_events,
            recent_context=recent_context_events
        )
        _total_duration_ms = (time.perf_counter() - _handle_start) * 1000
        _llm_duration_ms = _total_duration_ms - _events_duration_ms
        # Get intent as string (may be enum or already string)
        _intent_str = event_dto.intent.value if hasattr(event_dto.intent, 'value') else str(event_dto.intent) if event_dto.intent else "unknown"
        logger.info("handle_text_llm_done",
                   user_id=user_id,
                   events_ms=round(_events_duration_ms, 1),
                   llm_ms=round(_llm_duration_ms, 1),
                   total_ms=round(_total_duration_ms, 1),
                   intent=_intent_str)

        # Update conversation history based on intent
        if event_dto.intent == IntentType.CLARIFY:
            # Store user request and clarify question
            self.conversation_history[user_id] = [
                {"role": "user", "content": text},
                {"role": "assistant", "content": event_dto.clarify_question or "Уточните детали"}
            ]
        else:
            # Clear history after successful action
            self.conversation_history[user_id] = []

        # Age event context (expires after MAX_CONTEXT_MESSAGES without reference)
        # Note: context is reset in _handle_create/_handle_batch_confirm when new events created
        self._age_event_context(user_id)

        # Handle different intents
        if event_dto.intent == IntentType.CLARIFY:
            # Log intent unclear to analytics (helps identify confusing user requests)
            if ANALYTICS_ENABLED and analytics_service:
                try:
                    from app.models.analytics import ActionType
                    analytics_service.log_action(
                        user_id=user_id,
                        action_type=ActionType.INTENT_UNCLEAR,
                        details=f"User: {text[:100]}. Question: {event_dto.clarify_question[:100] if event_dto.clarify_question else 'N/A'}",
                        success=False,  # Mark as unsuccessful to track in errors
                        username=update.effective_user.username if update.effective_user else None,
                        first_name=update.effective_user.first_name if update.effective_user else None,
                        last_name=update.effective_user.last_name if update.effective_user else None
                    )
                except Exception as analytics_err:
                    logger.warning("analytics_log_failed", error=str(analytics_err))
            clarify_msg = event_dto.clarify_question or "Уточните, пожалуйста."
            await update.message.reply_text(clarify_msg)
            self._log_bot_response(user_id, clarify_msg, text)  # Save to dialog history
            return

        if event_dto.intent == IntentType.CREATE:
            await self._handle_create(update, user_id, event_dto, text)
            return

        if event_dto.intent == IntentType.UPDATE:
            await self._handle_update(update, user_id, event_dto, text)
            return

        if event_dto.intent == IntentType.DELETE:
            await self._handle_delete(update, user_id, event_dto, text)
            return

        if event_dto.intent == IntentType.QUERY:
            await self._handle_query(update, user_id, event_dto, text)
            return

        if event_dto.intent == IntentType.FIND_FREE_SLOTS:
            await self._handle_free_slots(update, user_id, event_dto, text)
            return

        if event_dto.intent == IntentType.BATCH_CONFIRM:
            await self._handle_batch_confirm(update, user_id, event_dto, text)
            return

        if event_dto.intent == IntentType.CREATE_RECURRING:
            await self._handle_create_recurring(update, user_id, event_dto, text)
            return

        if event_dto.intent == IntentType.DELETE_BY_CRITERIA:
            await self._handle_delete_by_criteria(update, user_id, event_dto, text)
            return

        if event_dto.intent == IntentType.DELETE_DUPLICATES:
            await self._handle_delete_duplicates(update, user_id, event_dto, text)
            return


        if event_dto.intent == IntentType.TODO:
            await self._handle_create_todo(update, user_id, event_dto, text)
            return
        # Other intents not yet implemented
        await update.message.reply_text(
            "Эта функция пока в разработке. Скоро будет доступна!"
        )

    async def _handle_create(self, update: Update, user_id: str, event_dto, user_text: str = None) -> None:
        """Handle event creation."""
        # Validate required fields with helpful error messages
        if not event_dto.title:
            msg = "Не понял название. Скажите, например: «Встреча в 15:00»"
            await update.message.reply_text(msg)
            self._log_bot_response(user_id, msg, user_text)
            return

        # start_time should always be set after default time fallback,
        # but keep safety check just in case
        if not event_dto.start_time:
            msg = "Не понял время. Укажите: «завтра в 10:00» или «в 15:30»"
            await update.message.reply_text(msg)
            self._log_bot_response(user_id, msg, user_text)
            return

        # Safeguard: if start_time is in the past (user's timezone), shift to tomorrow
        # Unless user explicitly said "сегодня"
        try:
            import pytz
            user_tz = self._get_user_timezone(update)
            tz = pytz.timezone(user_tz)
            now_user = datetime.now(tz).replace(tzinfo=None)
            if event_dto.start_time < now_user:
                user_said_today = user_text and "сегодня" in user_text.lower()
                if not user_said_today:
                    event_duration = (event_dto.end_time - event_dto.start_time) if event_dto.end_time else timedelta(hours=1)
                    event_dto.start_time += timedelta(days=1)
                    event_dto.end_time = event_dto.start_time + event_duration
                    logger.info("past_time_shifted_to_tomorrow",
                                user_id=user_id,
                                new_start=str(event_dto.start_time))
        except Exception as e:
            logger.warning("past_time_check_failed", error=str(e))

        # Create event
        event_uid = await calendar_service.create_event(user_id, event_dto)

        if event_uid:
            # Save to context for follow-up commands ("перепиши эти события")
            self._add_to_event_context(user_id, [event_uid])

            # Log event creation to analytics
            if ANALYTICS_ENABLED and analytics_service:
                try:
                    analytics_service.log_action(
                        user_id=user_id,
                        action_type="event_create",
                        details=f"Event: {event_dto.title}",
                        event_id=event_uid,
                        success=True,
                        username=update.effective_user.username if update.effective_user else None,
                        first_name=update.effective_user.first_name if update.effective_user else None,
                        last_name=update.effective_user.last_name if update.effective_user else None
                    )
                except Exception as e:
                    logger.warning("analytics_log_failed", error=str(e))

            # Schedule follow-up for domain events
            event_type = getattr(event_dto, 'event_type', None) or "generic"
            if followup_service and event_type not in ("generic", "dev_meeting"):
                try:
                    end_time = event_dto.end_time or (event_dto.start_time + timedelta(hours=1))
                    followup_service.schedule_follow_up(
                        user_id=user_id,
                        chat_id=update.effective_chat.id,
                        event_uid=event_uid,
                        event_type=event_type,
                        event_title=event_dto.title or "Событие",
                        event_end_time=end_time,
                        user_timezone=self._get_user_timezone(update),
                    )
                except Exception as e:
                    logger.warning("followup_schedule_failed", error=str(e))

            time_str = format_datetime_human(event_dto.start_time, self._get_user_timezone(update))
            # Type-aware confirmation
            event_type = getattr(event_dto, 'event_type', None) or "generic"
            _type_labels = {
                "showing": "Записал показ",
                "client_call": "Записал звонок",
                "doc_signing": "Записал подписание",
                "dev_meeting": "Записал встречу с застройщиком",
            }
            label = _type_labels.get(event_type, "Записал")
            message = f"✅ {label}\n{time_str} • {event_dto.title}"
            if event_dto.location:
                message += f"\n📍 {event_dto.location}"
            if getattr(event_dto, 'client_name', None):
                message += f"\n👤 {event_dto.client_name}"
            reply_markup = self._get_quick_hints_keyboard() if self._should_show_hints(user_id) else None
            await update.message.reply_text(message, reply_markup=reply_markup)
            self._log_bot_response(user_id, message, user_text)
        else:
            error_msg = "Не получилось. Попробуйте ещё раз одной фразой."
            await update.message.reply_text(error_msg)
            self._log_bot_response(user_id, error_msg, user_text)

    async def _handle_update(self, update: Update, user_id: str, event_dto, user_text: str = None) -> None:
        """Handle event update."""
        if not event_dto.event_id or event_dto.event_id == "none":
            no_event_msg = "Не понял, какое событие менять. Уточните."
            await update.message.reply_text(no_event_msg)
            self._log_bot_response(user_id, no_event_msg, user_text)
            return

        # Get original event to show what changed
        from datetime import datetime, timedelta
        now = datetime.now()
        original_events = await calendar_service.list_events(user_id, now - timedelta(days=30), now + timedelta(days=90))
        original_event = next((e for e in original_events if e.id == event_dto.event_id), None)

        success = await calendar_service.update_event(user_id, event_dto.event_id, event_dto)

        if success:
            # Log event update to analytics
            if ANALYTICS_ENABLED and analytics_service:
                try:
                    analytics_service.log_action(
                        user_id=user_id,
                        action_type="event_update",
                        details=f"Event: {event_dto.title or 'updated'}",
                        event_id=event_dto.event_id,
                        success=True,
                        username=update.effective_user.username if update.effective_user else None,
                        first_name=update.effective_user.first_name if update.effective_user else None,
                        last_name=update.effective_user.last_name if update.effective_user else None
                    )
                except Exception as e:
                    logger.warning("analytics_log_failed", error=str(e))

            if original_event:
                # Show what was changed
                title = event_dto.title or original_event.summary
                new_time = event_dto.start_time if event_dto.start_time else original_event.start
                time_str = format_datetime_human(new_time, self._get_user_timezone(update))
                location = event_dto.location if event_dto.location else original_event.location

                message = f"""✅ Изменил

📅 {title}
🕐 {time_str}
{f"📍 {location}" if location else ""}"""
            else:
                # Fallback if couldn't find original
                time_str = format_datetime_human(event_dto.start_time, self._get_user_timezone(update)) if event_dto.start_time else ""
                message = f"""✅ Изменил

📅 {event_dto.title if event_dto.title else 'Событие'}
{f"🕐 {time_str}" if time_str else ""}
{f"📍 {event_dto.location}" if event_dto.location else ""}"""

            await update.message.reply_text(message)
            self._log_bot_response(user_id, message, user_text)
        else:
            fail_msg = "Не получилось. Возможно, событие уже удалено."
            await update.message.reply_text(fail_msg)
            self._log_bot_response(user_id, fail_msg, user_text)

    async def _handle_delete(self, update: Update, user_id: str, event_dto, user_text: str = None) -> None:
        """Handle event deletion."""
        if not event_dto.event_id or event_dto.event_id == "none":
            no_delete_msg = "Не понял, что удалить. Уточните."
            await update.message.reply_text(no_delete_msg)
            self._log_bot_response(user_id, no_delete_msg, user_text)
            return

        # Get event details before deleting to show what was deleted
        from datetime import datetime, timedelta
        now = datetime.now()
        events = await calendar_service.list_events(user_id, now - timedelta(days=30), now + timedelta(days=90))
        event_to_delete = next((e for e in events if e.id == event_dto.event_id), None)

        success = await calendar_service.delete_event(user_id, event_dto.event_id)

        if success:
            # Remove from context (no longer exists)
            self._remove_from_event_context(user_id, [event_dto.event_id])

            # Log event deletion to analytics
            if ANALYTICS_ENABLED and analytics_service:
                try:
                    event_title = event_to_delete.summary if event_to_delete else "deleted"
                    analytics_service.log_action(
                        user_id=user_id,
                        action_type="event_delete",
                        details=f"Event: {event_title}",
                        event_id=event_dto.event_id,
                        success=True,
                        username=update.effective_user.username if update.effective_user else None,
                        first_name=update.effective_user.first_name if update.effective_user else None,
                        last_name=update.effective_user.last_name if update.effective_user else None
                    )
                except Exception as e:
                    logger.warning("analytics_log_failed", error=str(e))

            if event_to_delete:
                time_str = format_datetime_human(event_to_delete.start, self._get_user_timezone(update))
                del_msg = f"""✅ Событие удалено!

📅 {event_to_delete.summary}
🕐 {time_str}
{f"📍 {event_to_delete.location}" if event_to_delete.location else ""}"""
                await update.message.reply_text(del_msg)
                self._log_bot_response(user_id, del_msg, user_text)
            else:
                del_msg = "✅ Удалено"
                await update.message.reply_text(del_msg)
                self._log_bot_response(user_id, del_msg, user_text)
        else:
            fail_del_msg = "Не получилось. Возможно, уже удалено."
            await update.message.reply_text(fail_del_msg)
            self._log_bot_response(user_id, fail_del_msg, user_text)

    async def _handle_query(self, update: Update, user_id: str, event_dto, user_text: str = None) -> None:
        """Handle events query."""
        from datetime import datetime, timedelta

        # Log query to analytics
        if ANALYTICS_ENABLED and analytics_service:
            try:
                from app.models.analytics import ActionType
                analytics_service.log_action(
                    user_id=user_id,
                    action_type=ActionType.EVENT_QUERY,
                    details=f"Query: {event_dto.query_date_start} to {event_dto.query_date_end}",
                    success=True,
                    username=update.effective_user.username if update.effective_user else None,
                    first_name=update.effective_user.first_name if update.effective_user else None,
                    last_name=update.effective_user.last_name if update.effective_user else None
                )
            except Exception as e:
                logger.warning("analytics_log_failed", error=str(e))

        # Default to today if no date specified
        start_date = event_dto.query_date_start or datetime.now()

        # If no end_date specified, use END of the same day as start_date (not next day!)
        # This ensures "Дела на сегодня" only shows today's events
        if event_dto.query_date_end:
            end_date = event_dto.query_date_end
        else:
            # Set end_date to end of same day as start_date
            end_date = start_date.replace(hour=23, minute=59, second=59)

        # Ensure start_date covers from beginning of day
        if start_date.hour == 0 and start_date.minute == 0 and start_date.second == 0:
            start_date = start_date.replace(hour=0, minute=0, second=0)

        # If end_date is at midnight (00:00:00), it means end of PREVIOUS day,
        # so extend to end of that day
        if end_date.hour == 0 and end_date.minute == 0 and end_date.second == 0:
            end_date = end_date.replace(hour=23, minute=59, second=59)

        try:
            events = await calendar_service.list_events(user_id, start_date, end_date)
        except CalendarServiceError:
            error_msg = "⚠️ Календарь временно недоступен. Ваши данные в порядке — попробуйте через минуту."
            await update.message.reply_text(error_msg)
            self._log_bot_response(user_id, error_msg, user_text)
            return

        if not events:
            # Contextual hint based on query date
            today = datetime.now().date()
            query_date = (event_dto.query_date_start or datetime.now()).date()

            if query_date == today:
                day_word = "сегодня"
            elif query_date == today + timedelta(days=1):
                day_word = "завтра"
            else:
                day_word = query_date.strftime("%d.%m")

            # Try to find next upcoming event
            user_tz = self._get_user_timezone(update)
            now = datetime.now()
            try:
                future_events = await calendar_service.list_events(
                    user_id, now, now + timedelta(days=30)
                )
            except CalendarServiceError:
                future_events = []

            if future_events:
                # Show nearest event as helpful context
                next_event = sorted(future_events, key=lambda e: e.start)[0]
                next_time = format_datetime_human(next_event.start, user_tz)
                empty_msg = f"""📭 На {day_word} пусто.

📌 Ближайшее событие:
• {next_time} — {next_event.summary}

Добавить событие? Просто напишите:
«Встреча завтра в 15:00»"""
            else:
                # No events at all - show examples
                empty_msg = f"""📭 На {day_word} пусто.

📅 Добавьте событие:
• «Показ на Ленина в 14:00»
• «Встреча с клиентом завтра в 11:00»

📋 Или задачу без времени:
• «Подготовить документы по сделке»"""

            reply_markup = self._get_quick_hints_keyboard() if self._should_show_hints(user_id) else None
            await update.message.reply_text(empty_msg, reply_markup=reply_markup)
            self._log_bot_response(user_id, empty_msg, user_text)
            return

        # Sort events by start time
        sorted_events = sorted(events, key=lambda e: e.start)

        # Format events list with more details
        message = f"📅 Ваши события:\n\n"
        user_tz = self._get_user_timezone(update)
        for event in sorted_events:
            time_str = format_datetime_human(event.start, user_tz)
            message += f"• {time_str} - {event.summary}\n"
            if event.location:
                message += f"  📍 {event.location}\n"

        await update.message.reply_text(message)
        self._log_bot_response(user_id, message, user_text)

    async def _handle_free_slots(self, update: Update, user_id: str, event_dto, user_text: str = None) -> None:
        """Handle free slots query."""
        from datetime import datetime

        date = event_dto.query_date_start or datetime.now()

        free_slots = await calendar_service.find_free_slots(user_id, date)

        if not free_slots:
            no_slots_msg = "Свободного времени нет."
            await update.message.reply_text(no_slots_msg)
            self._log_bot_response(user_id, no_slots_msg, user_text)
            return

        # Format and show free slots
        # Format date without time (just "31 октября")
        from datetime import datetime
        months_ru = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                     'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
        date_str = f"{date.day} {months_ru[date.month - 1]}"
        message = f"Свободно {date_str}:\n\n"

        for slot in free_slots[:10]:  # Show up to 10 slots
            start_time = slot.start.strftime('%H:%M')
            end_time = slot.end.strftime('%H:%M')
            duration_minutes = slot.duration_minutes

            if duration_minutes >= 60:
                duration_str = f"{duration_minutes // 60}ч"
                if duration_minutes % 60 > 0:
                    duration_str += f" {duration_minutes % 60}м"
            else:
                duration_str = f"{duration_minutes}м"

            message += f"• {start_time}–{end_time} ({duration_str})\n"

        if len(free_slots) > 10:
            message += f"\n...ещё {len(free_slots) - 10} слотов"

        await update.message.reply_text(message)
        self._log_bot_response(user_id, message, user_text)

    async def _handle_batch_confirm(self, update: Update, user_id: str, event_dto, user_text: str = None) -> None:
        """Handle batch event/todo creation."""
        if not event_dto.batch_actions or len(event_dto.batch_actions) == 0:
            no_batch_msg = "Не смог распознать события."
            await update.message.reply_text(no_batch_msg)
            self._log_bot_response(user_id, no_batch_msg, user_text)
            return

        # Create all events/todos and collect results
        created_events = []
        created_todos = []
        created_uids = []  # Track UUIDs for context
        failed_count = 0

        for action in event_dto.batch_actions:
            try:
                action_intent = action.get("intent", "").lower()
                title = action.get("title")

                # Handle TODO items (no start_time required)
                if action_intent == "todo":
                    from app.schemas.todos import TodoDTO
                    todo_dto = TodoDTO(title=title)
                    todo_id = await todos_service.create_todo(user_id, todo_dto)
                    if todo_id:
                        created_todos.append({'title': title})
                        logger.info("batch_todo_created", user_id=user_id, title=title)
                    else:
                        failed_count += 1
                        logger.warning("batch_todo_creation_failed", user_id=user_id, title=title)
                    continue

                # Handle calendar EVENTS (require start_time)
                # Parse datetime from string/datetime/None
                start_time = self._parse_action_datetime(action.get("start_time"))
                end_time = self._parse_action_datetime(action.get("end_time"))

                # Skip events without start_time - log and count as failed
                if not start_time:
                    logger.warning("batch_action_missing_start_time",
                                  user_id=user_id,
                                  title=title)
                    failed_count += 1
                    continue

                # Create EventDTO for each action
                from app.schemas.events import EventDTO, IntentType
                single_event = EventDTO(
                    intent=IntentType.CREATE,
                    title=title,
                    start_time=start_time,
                    end_time=end_time,
                    location=action.get("location"),
                    description=action.get("description")
                )

                event_uid = await calendar_service.create_event(user_id, single_event)
                if event_uid:
                    created_events.append({
                        'title': title,
                        'start': start_time,  # Now datetime, not string
                        'end': end_time
                    })
                    created_uids.append(event_uid)
                else:
                    failed_count += 1
            except Exception as e:
                logger.error("batch_creation_error", error=str(e), user_id=user_id,
                            title=action.get("title"))
                failed_count += 1

        # Save to context for follow-up commands ("перепиши эти события")
        if created_uids:
            self._add_to_event_context(user_id, created_uids)

        # Build result message
        total_created = len(created_events) + len(created_todos)

        if total_created > 0:
            message = ""

            # Format todos
            if created_todos:
                message += "✅ Добавил в задачи:\n"
                for todo in created_todos:
                    message += f"• {todo['title']}\n"
                message += "\n"

            # Format events
            if created_events:
                message += "✅ Записал в календарь:\n"
                for evt in created_events:
                    time_str = format_datetime_human(evt['start'], self._get_user_timezone(update))
                    message += f"• {time_str} — {evt['title']}\n"

            if failed_count > 0:
                message += f"\nНе создано: {failed_count}"

            await update.message.reply_text(message.strip())
            self._log_bot_response(user_id, message.strip(), user_text)
        else:
            fail_batch_msg = "Не получилось создать. Попробуйте ещё раз."
            await update.message.reply_text(fail_batch_msg)
            self._log_bot_response(user_id, fail_batch_msg, user_text)

    async def _handle_create_recurring(self, update: Update, user_id: str, event_dto, user_text: str = None) -> None:
        """Handle recurring event creation."""
        from datetime import datetime, timedelta

        # Validate required fields
        if not event_dto.title or not event_dto.start_time:
            no_data_msg = "Недостаточно данных. Укажите название и время."
            await update.message.reply_text(no_data_msg)
            self._log_bot_response(user_id, no_data_msg, user_text)
            return

        if not event_dto.recurrence_type:
            no_recur_msg = "Не указан тип повторения (ежедневно, еженедельно, ежемесячно)."
            await update.message.reply_text(no_recur_msg)
            self._log_bot_response(user_id, no_recur_msg, user_text)
            return

        # Safety check: start_time required for recurring events
        if not event_dto.start_time:
            msg = "Для повторяющихся событий укажите время: «каждый день в 10:00»"
            await update.message.reply_text(msg)
            self._log_bot_response(user_id, msg, user_text)
            return

        # Default: create recurring events for 30 days
        recurrence_end = event_dto.recurrence_end_date or (event_dto.start_time + timedelta(days=30))

        created_count = 0
        failed_count = 0
        current_date = event_dto.start_time

        # Create individual events based on recurrence type
        while current_date <= recurrence_end:
            # Create a copy of event_dto for this occurrence
            from app.schemas.events import EventDTO, IntentType
            occurrence = EventDTO(
                intent=IntentType.CREATE,
                title=event_dto.title,
                start_time=current_date,
                end_time=current_date + timedelta(minutes=event_dto.duration_minutes or 60) if event_dto.duration_minutes else None,
                location=event_dto.location,
                description=event_dto.description
            )

            # Create the event
            event_uid = await calendar_service.create_event(user_id, occurrence)
            if event_uid:
                created_count += 1
            else:
                failed_count += 1

            # Move to next occurrence
            if event_dto.recurrence_type == "daily":
                current_date += timedelta(days=1)
            elif event_dto.recurrence_type == "weekly":
                current_date += timedelta(weeks=1)
            elif event_dto.recurrence_type == "monthly":
                # Add one month (approximate - use 30 days for simplicity)
                current_date += timedelta(days=30)
            else:
                # Unknown recurrence type
                break

            # Safety limit: don't create more than 100 events
            if created_count >= 100:
                break

        # Send confirmation
        if created_count > 0:
            recurrence_name = {
                "daily": "ежедневное",
                "weekly": "еженедельное",
                "monthly": "ежемесячное"
            }.get(event_dto.recurrence_type, "повторяющееся")

            time_str = format_datetime_human(event_dto.start_time, self._get_user_timezone(update))
            message = f"✅ Создано {recurrence_name} событие\n{time_str} • {event_dto.title}\n\nСоздано повторений: {created_count}"
            if failed_count > 0:
                message += f"\nНе создано: {failed_count}"
            await update.message.reply_text(message)
            self._log_bot_response(user_id, message, user_text)
        else:
            fail_recur_msg = "Не получилось создать повторяющиеся события."
            await update.message.reply_text(fail_recur_msg)
            self._log_bot_response(user_id, fail_recur_msg, user_text)

    async def _handle_delete_by_criteria(self, update: Update, user_id: str, event_dto, user_text: str = None) -> None:
        """Handle mass deletion by criteria (title contains, date range, etc)."""
        from datetime import datetime, timedelta

        # Get date range
        start_date = event_dto.query_date_start
        end_date = event_dto.query_date_end

        # If no date range, default to next year (365 days) for "delete all X" queries
        # This ensures we catch recurring events that span long periods
        if not start_date:
            start_date = datetime.now()
        if not end_date:
            end_date = start_date + timedelta(days=365)

        # Ensure we cover the full day(s)
        # If times are 00:00:00, extend end_date to end of day (23:59:59)
        if start_date and end_date:
            if start_date.hour == 0 and start_date.minute == 0 and start_date.second == 0:
                start_date = start_date.replace(hour=0, minute=0, second=0)
            if end_date.hour == 0 and end_date.minute == 0 and end_date.second == 0:
                end_date = end_date.replace(hour=23, minute=59, second=59)

        # Get all events in range
        events = await calendar_service.list_events(user_id, start_date, end_date)

        if not events:
            empty_msg = "Пусто — ничего не найдено."
            await update.message.reply_text(empty_msg)
            self._log_bot_response(user_id, empty_msg, user_text)
            return

        # Filter by criteria
        events_to_delete = []

        # Filter by title contains
        if event_dto.delete_criteria_title_contains:
            search_term = event_dto.delete_criteria_title_contains.lower()
            events_to_delete = [e for e in events if search_term in e.summary.lower()]
        # Filter by exact title match
        elif event_dto.delete_criteria_title:
            events_to_delete = [e for e in events if e.summary == event_dto.delete_criteria_title]
        else:
            # No specific criteria - delete ALL events in date range (with confirmation)
            events_to_delete = events

        if not events_to_delete:
            not_found_msg = f"Не найдено: \"{event_dto.delete_criteria_title_contains or event_dto.delete_criteria_title}\""
            await update.message.reply_text(not_found_msg)
            self._log_bot_response(user_id, not_found_msg, user_text)
            return

        # Show list of events and ask for confirmation
        message = f"Найдено: {len(events_to_delete)}\n\n"
        message += "Удалить:\n"

        user_tz = self._get_user_timezone(update)
        for i, event in enumerate(events_to_delete[:10]):  # Show first 10
            time_str = format_datetime_human(event.start, user_tz)
            message += f"• {event.summary} ({time_str})\n"

        if len(events_to_delete) > 10:
            message += f"\n...ещё {len(events_to_delete) - 10}\n"

        message += "\nПодтвердите:"

        # Store events in conversation history for later confirmation
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []

        self.conversation_history[user_id] = [{
            "role": "assistant",
            "content": "pending_delete_by_criteria",
            "events": [e.id for e in events_to_delete],
            "message": message
        }]

        # Create inline keyboard with confirmation buttons
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Удалить", callback_data=f"confirm_delete_criteria:{user_id}"),
                InlineKeyboardButton("❌ Отмена", callback_data=f"cancel_delete:{user_id}")
            ]
        ])

        await update.message.reply_text(message, reply_markup=keyboard)
        self._log_bot_response(user_id, message, user_text)

    async def _handle_delete_duplicates(self, update: Update, user_id: str, event_dto, user_text: str = None) -> None:
        """Handle deletion of duplicate events (same title and time)."""
        from datetime import datetime, timedelta
        from collections import defaultdict

        # Get date range
        start_date = event_dto.query_date_start
        end_date = event_dto.query_date_end

        # If no date range, default to next 7 days
        if not start_date:
            start_date = datetime.now()
        if not end_date:
            end_date = start_date + timedelta(days=7)

        # Ensure we cover the full day(s)
        if start_date and end_date:
            if start_date.hour == 0 and start_date.minute == 0 and start_date.second == 0:
                start_date = start_date.replace(hour=0, minute=0, second=0)
            if end_date.hour == 0 and end_date.minute == 0 and end_date.second == 0:
                end_date = end_date.replace(hour=23, minute=59, second=59)

        # Get all events in range
        events = await calendar_service.list_events(user_id, start_date, end_date)

        if not events:
            empty_dup_msg = "Пусто — ничего не найдено."
            await update.message.reply_text(empty_dup_msg)
            self._log_bot_response(user_id, empty_dup_msg, user_text)
            return

        # Find duplicates: group by (title, start_time)
        event_groups = defaultdict(list)
        for event in events:
            # Create key: title + start time (rounded to minute)
            key = (event.summary.strip().lower(), event.start.replace(second=0, microsecond=0))
            event_groups[key].append(event)

        # Find groups with duplicates (more than 1 event)
        duplicates_to_delete = []
        for key, group in event_groups.items():
            if len(group) > 1:
                # Keep first, delete rest
                duplicates_to_delete.extend(group[1:])

        if not duplicates_to_delete:
            no_dup_msg = "Дубликатов нет."
            await update.message.reply_text(no_dup_msg)
            self._log_bot_response(user_id, no_dup_msg, user_text)
            return

        # Show list of duplicates and ask for confirmation
        message = f"Найдено дубликатов: {len(duplicates_to_delete)}\n\n"
        message += "Удалить:\n"

        user_tz = self._get_user_timezone(update)
        for i, event in enumerate(duplicates_to_delete[:10]):  # Show first 10
            time_str = format_datetime_human(event.start, user_tz)
            message += f"• {event.summary} ({time_str})\n"

        if len(duplicates_to_delete) > 10:
            message += f"\n...ещё {len(duplicates_to_delete) - 10}\n"

        message += "\nПодтвердите:"

        # Store duplicates in conversation history for later confirmation
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []

        self.conversation_history[user_id] = [{
            "role": "assistant",
            "content": "pending_delete_duplicates",
            "duplicates": [e.id for e in duplicates_to_delete],
            "message": message
        }]

        # Create inline keyboard with confirmation buttons
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Удалить", callback_data=f"confirm_delete_duplicates:{user_id}"),
                InlineKeyboardButton("❌ Отмена", callback_data=f"cancel_delete:{user_id}")
            ]
        ])

        await update.message.reply_text(message, reply_markup=keyboard)
        self._log_bot_response(user_id, message, user_text)

    async def _handle_create_todo(self, update: Update, user_id: str, event_dto, user_text: str = None) -> None:
        """Handle todo creation from LLM intent."""
        from app.schemas.todos import TodoDTO

        title = event_dto.title or event_dto.raw_text
        if not title:
            no_todo_msg = "Не понял, что добавить в задачи."
            await update.message.reply_text(no_todo_msg)
            self._log_bot_response(user_id, no_todo_msg, user_text)
            return

        todo_dto = TodoDTO(title=title)
        todo_id = await todos_service.create_todo(user_id, todo_dto)

        if todo_id:
            todo_msg = f"✅ Добавил в задачи: {title}"
            await update.message.reply_text(todo_msg)
            self._log_bot_response(user_id, todo_msg, user_text)
        else:
            fail_todo_msg = "Не получилось создать задачу. Попробуйте ещё раз."
            await update.message.reply_text(fail_todo_msg)
            self._log_bot_response(user_id, fail_todo_msg, user_text)

# Global instance (will be initialized in router)
telegram_handler: Optional[TelegramHandler] = None
