"""Telegram bot message handler."""

from typing import Optional
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application
import structlog

from app.config import settings
from app.services.llm_agent_yandex import llm_agent_yandex as llm_agent
from app.services.calendar_radicale import calendar_service
from app.services.user_preferences import user_preferences

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

# ARCHIVED - Property Bot moved to independent microservice (_archived/property_bot_microservice)
# Property Bot imports removed - calendar bot only
PROPERTY_BOT_ENABLED = False

logger = structlog.get_logger()


class TelegramHandler:
    """Handler for Telegram bot messages."""

    def __init__(self, app: Application):
        """Initialize handler with Telegram application."""
        self.app = app
        self.bot = app.bot
        # Store conversation history per user (last 10 messages)
        self.conversation_history = {}
        # Store user timezone preferences (user_id -> timezone string)
        self.user_timezones = {}

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
            await message.reply_text(
                "Напишите текстом или голосом, что хотите запланировать."
            )

        except Exception as e:
            logger.error(
                "handle_update_error",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            await message.reply_text(
                "Что-то сломалось. Попробуйте ещё раз."
            )

    async def _handle_start(self, update: Update, user_id: str) -> None:
        """Handle /start command."""
        # Log user registration
        if ANALYTICS_ENABLED and analytics_service:
            try:
                analytics_service.log_action(
                    user_id=user_id,
                    action_type="user_start",
                    details="/start command",
                    success=True,
                    username=update.effective_user.username if update.effective_user else None,
                    first_name=update.effective_user.first_name if update.effective_user else None,
                    last_name=update.effective_user.last_name if update.effective_user else None
                )
            except Exception as e:
                logger.warning("analytics_log_failed", error=str(e))

        # Check if user has already given consents
        advertising_consent = user_preferences.get_advertising_consent(user_id)
        privacy_consent = user_preferences.get_privacy_consent(user_id)

        if not advertising_consent:
            # Ask for advertising consent first
            await self._ask_advertising_consent(update, user_id)
            return

        if not privacy_consent:
            # Ask for privacy consent second
            await self._ask_privacy_consent(update, user_id)
            return

        # Both consents given - show welcome message
        welcome_message = """👋 Привет! Я ваш персональный ИИ-помощник по планированию.

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

        # Создаем клавиатуру с кнопками (чистые текстовые кнопки без WebApp)
        keyboard = ReplyKeyboardMarkup([
            [KeyboardButton("📋 Дела на сегодня")],
            [KeyboardButton("📅 Дела на завтра"), KeyboardButton("✅ Задачи")],
            [KeyboardButton("⚙️ Настройки"), KeyboardButton("💡 Полезное")]
        ], resize_keyboard=True)

        await update.message.reply_text(welcome_message, reply_markup=keyboard, parse_mode="Markdown")

        # Устанавливаем WebApp button слева от поля ввода (кабинет календаря)
        try:
            from telegram import MenuButtonWebApp, WebAppInfo
            # Use webapp URL from config (add version parameter to bust Telegram cache)
            webapp_url = f"{settings.telegram_webapp_url}?v=2025103001"
            menu_button = MenuButtonWebApp(
                text="🗓 Кабинет",
                web_app=WebAppInfo(url=webapp_url)
            )
            await self.bot.set_chat_menu_button(
                chat_id=update.effective_chat.id,
                menu_button=menu_button
            )
            logger.info("menu_button_webapp_set", user_id=user_id, webapp_url=webapp_url)
        except Exception as e:
            logger.warning("menu_button_set_failed", error=str(e))

    async def _ask_advertising_consent(self, update: Update, user_id: str) -> None:
        """Ask for advertising consent."""
        message = """Для дальнейшего взаимодействия с ботом необходимо дать согласие на получение новостей и рекламных рассылок.

[Соглашение на получение рекламы](https://m2.ru/doc/realtors/soglasiya/advertising-agreement/)"""

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Даю согласие", callback_data="consent:advertising:yes"),
                InlineKeyboardButton("❌ Не даю", callback_data="consent:advertising:no")
            ]
        ])

        await update.message.reply_text(message, reply_markup=keyboard, parse_mode="Markdown")

    async def _ask_privacy_consent(self, update: Update, user_id: str) -> None:
        """Ask for privacy policy consent."""
        message = """Для дальнейшего взаимодействия с ботом необходимо дать согласие на обработку персональных данных.

[Политика конфиденциальности](https://m2.ru/doc/realtors/politiki/privacy-policy/)"""

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

            # Process as text (will route to correct handler based on mode)
            await self._handle_text(update, user_id, text)

        except Exception as e:
            logger.error("voice_transcription_failed", user_id=user_id, error=str(e))
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
            [InlineKeyboardButton("📰 Новости", url="https://housler.ru/blog")],
            [InlineKeyboardButton("🏷 Оценить рыночную стоимость", url="https://housler.ru/calculator")],
            [InlineKeyboardButton("💰 Ипотечный брокер", url="https://m2.ru/ipoteka/calculator/")],
            [InlineKeyboardButton("🛡 Защита сделки", url="https://m2.ru/services/guaranteed-deal/")],
            [InlineKeyboardButton("📋 Регистрация и безопасные расчеты", url="https://m2.ru/services/deal/")],
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
            [InlineKeyboardButton("❓ Справка и примеры", callback_data="settings:help")],
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

    async def handle_callback_query(self, update: Update) -> None:
        """Handle callback queries from inline buttons."""
        query = update.callback_query
        if not query:
            return

        await query.answer()

        user_id = str(update.effective_user.id)
        data = query.data

        # Handle consent callbacks
        if data.startswith("consent:"):
            parts = data.split(":")
            consent_type = parts[1]  # "advertising" or "privacy"
            answer = parts[2]  # "yes" or "no"

            if answer == "yes":
                # User gave consent
                if consent_type == "advertising":
                    user_preferences.set_advertising_consent(user_id, True)
                    logger.info("advertising_consent_given", user_id=user_id)
                    await query.edit_message_text("✅ Согласие на получение рекламы принято")

                    # Now ask for privacy consent
                    await self._ask_privacy_consent(update, user_id)

                elif consent_type == "privacy":
                    user_preferences.set_privacy_consent(user_id, True)
                    logger.info("privacy_consent_given", user_id=user_id)
                    await query.edit_message_text("✅ Согласие на обработку данных принято")

                    # Now show welcome message - call _handle_start but pass a message object
                    # Create a fake update with message
                    from telegram import Message
                    fake_update = Update(
                        update_id=update.update_id,
                        message=query.message
                    )
                    await self._handle_start(fake_update, user_id)

            else:
                # User declined
                if consent_type == "advertising":
                    await query.edit_message_text(
                        "❌ Без согласия на получение рекламы продолжить невозможно.\n\nПопробуйте снова:"
                    )
                    # Ask again
                    await self._ask_advertising_consent(update, user_id)

                elif consent_type == "privacy":
                    await query.edit_message_text(
                        "❌ Без согласия на обработку данных продолжить невозможно.\n\nПопробуйте снова:"
                    )
                    # Ask again
                    await self._ask_privacy_consent(update, user_id)

        # Handle timezone selection
        elif data.startswith("tz:"):
            timezone = data[3:]  # Remove "tz:" prefix
            try:
                import pytz
                pytz.timezone(timezone)  # Validate timezone
                user_preferences.set_timezone(user_id, timezone)

                # Extract city name from timezone
                city = timezone.split('/')[-1].replace('_', ' ')
                await query.edit_message_text(f"✅ Часовой пояс обновлен: {city}")

                logger.info("timezone_set", user_id=user_id, timezone=timezone)
            except Exception as e:
                logger.error("timezone_set_error", user_id=user_id, error=str(e))
                await query.edit_message_text("Ошибка при установке пояса")

        # Handle settings callbacks
        elif data == "settings:morning_toggle":
            # Show morning summary submenu
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

        elif data == "morning:toggle":
            current = user_preferences.get_morning_summary_enabled(user_id)
            user_preferences.set_morning_summary_enabled(user_id, not current)
            status = "включена" if not current else "выключена"
            await query.edit_message_text(f"✅ Утренняя сводка {status}")

        elif data == "morning:change_time":
            await query.edit_message_text(
                "🕐 Изменить время утренней сводки\n\nНапишите время в формате ЧЧ:ММ\nНапример: 07:30"
            )
            # Store state for next message
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            self.conversation_history[user_id] = [{"role": "system", "content": "awaiting_morning_time"}]

        elif data == "settings:evening_toggle":
            # Show evening digest submenu
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

        elif data == "evening:toggle":
            current = user_preferences.get_evening_digest_enabled(user_id)
            user_preferences.set_evening_digest_enabled(user_id, not current)
            status = "включен" if not current else "выключен"
            await query.edit_message_text(f"✅ Вечерний дайджест {status}")

        elif data == "evening:change_time":
            await query.edit_message_text(
                "🕐 Изменить время вечернего дайджеста\n\nНапишите время в формате ЧЧ:ММ\nНапример: 20:00"
            )
            # Store state for next message
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            self.conversation_history[user_id] = [{"role": "system", "content": "awaiting_evening_time"}]

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

        elif data == "settings:timezone":
            # Show timezone selection
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

        elif data == "quiet:change_start":
            quiet_start, quiet_end = user_preferences.get_quiet_hours(user_id)
            await query.edit_message_text(
                f"🕐 Изменить начало тихих часов\n\nСейчас: {quiet_start}–{quiet_end}\n\nНапишите время начала в формате ЧЧ:ММ\nНапример: 23:00"
            )
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            self.conversation_history[user_id] = [{"role": "system", "content": "awaiting_quiet_start"}]

        elif data == "quiet:change_end":
            quiet_start, quiet_end = user_preferences.get_quiet_hours(user_id)
            await query.edit_message_text(
                f"🕐 Изменить конец тихих часов\n\nСейчас: {quiet_start}–{quiet_end}\n\nНапишите время окончания в формате ЧЧ:ММ\nНапример: 08:00"
            )
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            self.conversation_history[user_id] = [{"role": "system", "content": "awaiting_quiet_end"}]

        elif data == "settings:back":
            # Return to main settings menu
            await self._send_settings_menu(update, user_id, query=query)

        # ARCHIVED - services:property_search callback removed (independent microservice)

        # Handle deletion confirmation
        elif data.startswith("confirm_delete_"):
            if user_id not in self.conversation_history or len(self.conversation_history[user_id]) == 0:
                await query.edit_message_text("Время истекло. Попробуйте ещё раз.")
                return

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
                return

            # Delete events
            deleted_count = 0
            for event_id in event_ids:
                success = await calendar_service.delete_event(user_id, event_id)
                if success:
                    deleted_count += 1

            self.conversation_history[user_id] = []  # Clear history
            await query.edit_message_text(f"✅ Удалено {action_name}: {deleted_count}")

        # Handle deletion cancellation
        elif data.startswith("cancel_delete:"):
            self.conversation_history[user_id] = []  # Clear history
            await query.edit_message_text("Отменено.")

    def _get_user_timezone(self, update: Update) -> str:
        """Get user timezone from stored preferences or default to Moscow."""
        user_id = str(update.effective_user.id)
        return user_preferences.get_timezone(user_id)

    async def _handle_text(self, update: Update, user_id: str, text: str) -> None:
        """Handle text message - only calendar mode."""
        logger.info("text_message_received", user_id=user_id, text=text)

        # Log message to analytics
        if ANALYTICS_ENABLED and analytics_service:
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

        # Calendar mode only
        # Check calendar service connection
        if not calendar_service.is_connected():
            await update.message.reply_text(
                "⚠️ Календарный сервер временно недоступен.\nПопробуйте позже."
            )
            return

        # Check if user is in a settings flow (awaiting time input)
        if user_id in self.conversation_history and len(self.conversation_history[user_id]) > 0:
            last_msg = self.conversation_history[user_id][-1]
            pending_action = last_msg.get("content")

            # Handle time input for settings
            if last_msg.get("role") == "system":
                import re
                time_pattern = r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$'
                match = re.match(time_pattern, text.strip())

                if not match:
                    await update.message.reply_text("Неверный формат. Введите время как ЧЧ:ММ (например, 07:30)")
                    return

                time_str = text.strip()

                if pending_action == "awaiting_morning_time":
                    user_preferences.set_morning_summary_time(user_id, time_str)
                    self.conversation_history[user_id] = []
                    await update.message.reply_text(f"✅ Время утренней сводки изменено на {time_str}")
                    return

                elif pending_action == "awaiting_evening_time":
                    user_preferences.set_evening_digest_time(user_id, time_str)
                    self.conversation_history[user_id] = []
                    await update.message.reply_text(f"✅ Время вечернего дайджеста изменено на {time_str}")
                    return

                elif pending_action == "awaiting_quiet_start":
                    quiet_start, quiet_end = user_preferences.get_quiet_hours(user_id)
                    user_preferences.set_quiet_hours(user_id, time_str, quiet_end)
                    self.conversation_history[user_id] = []
                    await update.message.reply_text(f"✅ Начало тихих часов изменено на {time_str}")
                    return

                elif pending_action == "awaiting_quiet_end":
                    quiet_start, quiet_end = user_preferences.get_quiet_hours(user_id)
                    user_preferences.set_quiet_hours(user_id, quiet_start, time_str)
                    self.conversation_history[user_id] = []
                    await update.message.reply_text(f"✅ Конец тихих часов изменён на {time_str}")
                    return

            # Check if user is confirming deletion
            if (last_msg.get("role") == "assistant" and
                pending_action in ["pending_delete_duplicates", "pending_delete_by_criteria"]):

                text_lower = text.lower().strip()
                if text_lower in ['удалить', 'да', 'ok', 'yes', 'удали']:
                    # Confirm and delete
                    if pending_action == "pending_delete_duplicates":
                        event_ids = last_msg.get("duplicates", [])
                    else:  # pending_delete_by_criteria
                        event_ids = last_msg.get("events", [])

                    deleted_count = 0
                    for event_id in event_ids:
                        success = await calendar_service.delete_event(user_id, event_id)
                        if success:
                            deleted_count += 1

                    self.conversation_history[user_id] = []  # Clear history

                    if pending_action == "pending_delete_duplicates":
                        await update.message.reply_text(f"✅ Удалено {deleted_count}")
                    else:
                        await update.message.reply_text(f"✅ Удалено {deleted_count}")
                    return

                elif text_lower in ['отмена', 'нет', 'cancel', 'no']:
                    # Cancel
                    self.conversation_history[user_id] = []  # Clear history
                    await update.message.reply_text("Отменено.")
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
        existing_events = await calendar_service.list_events(user_id, start, end)

        logger.info("events_loaded_for_context", user_id=user_id, count=len(existing_events))

        # Pass conversation history ONLY if last message was a clarify question
        # Include both user request and assistant clarify question
        limited_history = []
        if len(self.conversation_history[user_id]) >= 2:
            # Check if last assistant message was clarify
            last_assistant = self.conversation_history[user_id][-1]
            prev_user = self.conversation_history[user_id][-2]

            if (last_assistant.get("role") == "assistant" and
                prev_user.get("role") == "user"):
                # Include both user request and clarify question for full context
                limited_history = [prev_user, last_assistant]

        event_dto = await llm_agent.extract_event(
            text,
            user_id,
            conversation_history=limited_history,
            timezone=user_tz,
            existing_events=existing_events
        )

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

        # Handle different intents
        if event_dto.intent == IntentType.CLARIFY:
            await update.message.reply_text(
                event_dto.clarify_question or "Уточните, пожалуйста."
            )
            return

        if event_dto.intent == IntentType.CREATE:
            await self._handle_create(update, user_id, event_dto)
            return

        if event_dto.intent == IntentType.UPDATE:
            await self._handle_update(update, user_id, event_dto)
            return

        if event_dto.intent == IntentType.DELETE:
            await self._handle_delete(update, user_id, event_dto)
            return

        if event_dto.intent == IntentType.QUERY:
            await self._handle_query(update, user_id, event_dto)
            return

        if event_dto.intent == IntentType.FIND_FREE_SLOTS:
            await self._handle_free_slots(update, user_id, event_dto)
            return

        if event_dto.intent == IntentType.BATCH_CONFIRM:
            await self._handle_batch_confirm(update, user_id, event_dto)
            return

        if event_dto.intent == IntentType.CREATE_RECURRING:
            await self._handle_create_recurring(update, user_id, event_dto)
            return

        if event_dto.intent == IntentType.DELETE_BY_CRITERIA:
            await self._handle_delete_by_criteria(update, user_id, event_dto)
            return

        if event_dto.intent == IntentType.DELETE_DUPLICATES:
            await self._handle_delete_duplicates(update, user_id, event_dto)
            return

        # Other intents not yet implemented
        await update.message.reply_text(
            "Эта функция пока в разработке. Скоро будет доступна!"
        )

    async def _handle_create(self, update: Update, user_id: str, event_dto) -> None:
        """Handle event creation."""
        # Validate required fields
        if not event_dto.title or not event_dto.start_time:
            await update.message.reply_text(
                "Недостаточно данных. Укажите название и время."
            )
            return

        # Create event
        event_uid = await calendar_service.create_event(user_id, event_dto)

        if event_uid:
            time_str = format_datetime_human(event_dto.start_time, self._get_user_timezone(update))
            message = f"✅ Записал\n{time_str} • {event_dto.title}"
            if event_dto.location:
                message += f" ({event_dto.location})"
            await update.message.reply_text(message)
        else:
            await update.message.reply_text(
                "Не получилось. Попробуйте ещё раз одной фразой."
            )

    async def _handle_update(self, update: Update, user_id: str, event_dto) -> None:
        """Handle event update."""
        if not event_dto.event_id or event_dto.event_id == "none":
            await update.message.reply_text(
                "Не понял, какое событие менять. Уточните."
            )
            return

        # Get original event to show what changed
        from datetime import datetime, timedelta
        now = datetime.now()
        original_events = await calendar_service.list_events(user_id, now - timedelta(days=30), now + timedelta(days=90))
        original_event = next((e for e in original_events if e.id == event_dto.event_id), None)

        success = await calendar_service.update_event(user_id, event_dto.event_id, event_dto)

        if success:
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
        else:
            await update.message.reply_text(
                "Не получилось. Возможно, событие уже удалено."
            )

    async def _handle_delete(self, update: Update, user_id: str, event_dto) -> None:
        """Handle event deletion."""
        if not event_dto.event_id or event_dto.event_id == "none":
            await update.message.reply_text(
                "Не понял, что удалить. Уточните."
            )
            return

        # Get event details before deleting to show what was deleted
        from datetime import datetime, timedelta
        now = datetime.now()
        events = await calendar_service.list_events(user_id, now - timedelta(days=30), now + timedelta(days=90))
        event_to_delete = next((e for e in events if e.id == event_dto.event_id), None)

        success = await calendar_service.delete_event(user_id, event_dto.event_id)

        if success:
            if event_to_delete:
                time_str = format_datetime_human(event_to_delete.start, self._get_user_timezone(update))
                message = f"""✅ Событие удалено!

📅 {event_to_delete.summary}
🕐 {time_str}
{f"📍 {event_to_delete.location}" if event_to_delete.location else ""}"""
                await update.message.reply_text(message)
            else:
                await update.message.reply_text("✅ Удалено")
        else:
            await update.message.reply_text(
                "Не получилось. Возможно, уже удалено."
            )

    async def _handle_query(self, update: Update, user_id: str, event_dto) -> None:
        """Handle events query."""
        from datetime import datetime, timedelta

        # Default to today if no date specified
        start_date = event_dto.query_date_start or datetime.now()
        end_date = event_dto.query_date_end or (start_date + timedelta(days=1))

        # Ensure we cover the full day(s)
        # If times are 00:00:00, extend end_date to end of day (23:59:59)
        if start_date and end_date:
            if start_date.hour == 0 and start_date.minute == 0 and start_date.second == 0:
                start_date = start_date.replace(hour=0, minute=0, second=0)
            if end_date.hour == 0 and end_date.minute == 0 and end_date.second == 0:
                end_date = end_date.replace(hour=23, minute=59, second=59)

        events = await calendar_service.list_events(user_id, start_date, end_date)

        if not events:
            await update.message.reply_text("Пусто — ничего не запланировано.")
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

    async def _handle_free_slots(self, update: Update, user_id: str, event_dto) -> None:
        """Handle free slots query."""
        from datetime import datetime

        date = event_dto.query_date_start or datetime.now()

        free_slots = await calendar_service.find_free_slots(user_id, date)

        if not free_slots:
            await update.message.reply_text("Свободного времени нет.")
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

    async def _handle_batch_confirm(self, update: Update, user_id: str, event_dto) -> None:
        """Handle batch event creation."""
        if not event_dto.batch_actions or len(event_dto.batch_actions) == 0:
            await update.message.reply_text(
                "Не смог распознать события."
            )
            return

        # Create all events and collect results
        created_events = []
        failed_count = 0

        for action in event_dto.batch_actions:
            try:
                # Create EventDTO for each action
                from app.schemas.events import EventDTO, IntentType
                single_event = EventDTO(
                    intent=IntentType.CREATE,
                    title=action.get("title"),
                    start_time=action.get("start_time"),
                    end_time=action.get("end_time"),
                    location=action.get("location"),
                    description=action.get("description")
                )

                event_uid = await calendar_service.create_event(user_id, single_event)
                if event_uid:
                    created_events.append({
                        'title': action.get("title"),
                        'start': action.get("start_time"),
                        'end': action.get("end_time")
                    })
                else:
                    failed_count += 1
            except Exception as e:
                logger.error("batch_event_creation_error", error=str(e), user_id=user_id)
                failed_count += 1

        # Send result with event list
        if len(created_events) > 0:
            # Format list of created events
            message = "✅ Записал:\n\n"
            for evt in created_events:
                time_str = format_datetime_human(evt['start'], self._get_user_timezone(update))
                message += f"• {time_str} — {evt['title']}\n"

            if failed_count > 0:
                message += f"\nНе создано: {failed_count}"

            await update.message.reply_text(message)
        else:
            await update.message.reply_text(
                "Не получилось создать. Попробуйте ещё раз."
            )

    async def _handle_create_recurring(self, update: Update, user_id: str, event_dto) -> None:
        """Handle recurring event creation."""
        from datetime import datetime, timedelta

        # Validate required fields
        if not event_dto.title or not event_dto.start_time:
            await update.message.reply_text(
                "Недостаточно данных. Укажите название и время."
            )
            return

        if not event_dto.recurrence_type:
            await update.message.reply_text(
                "Не указан тип повторения (ежедневно, еженедельно, ежемесячно)."
            )
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
        else:
            await update.message.reply_text(
                "Не получилось создать повторяющиеся события."
            )

    async def _handle_delete_by_criteria(self, update: Update, user_id: str, event_dto) -> None:
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
            await update.message.reply_text("Пусто — ничего не найдено.")
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
            await update.message.reply_text(
                f"Не найдено: \"{event_dto.delete_criteria_title_contains or event_dto.delete_criteria_title}\""
            )
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

    async def _handle_delete_duplicates(self, update: Update, user_id: str, event_dto) -> None:
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
            await update.message.reply_text("Пусто — ничего не найдено.")
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
            await update.message.reply_text("Дубликатов нет.")
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


# Global instance (will be initialized in router)
telegram_handler: Optional[TelegramHandler] = None
