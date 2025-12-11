"""Translations for multilingual bot support."""

from enum import Enum
from typing import Dict


class Language(str, Enum):
    """Supported languages."""
    RUSSIAN = "ru"
    ENGLISH = "en"
    SPANISH = "es"
    ARABIC = "ar"


# All translations
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # Language selection
    "select_language": {
        "ru": "🌍 Выберите язык / Select language:",
        "en": "🌍 Select language:",
        "es": "🌍 Seleccione el idioma:",
        "ar": "🌍 اختر اللغة:"
    },
    "language_selected": {
        "ru": "✅ Язык изменен на русский",
        "en": "✅ Language changed to English",
        "es": "✅ Idioma cambiado a español",
        "ar": "✅ تم تغيير اللغة إلى العربية"
    },

    # Welcome message
    "welcome_title": {
        "ru": "🏢 Привет! Я ваш AI-ассистент для работы с недвижимостью.",
        "en": "🏢 Hello! I'm your AI assistant for real estate management.",
        "es": "🏢 ¡Hola! Soy tu asistente AI para gestión inmobiliaria.",
        "ar": "🏢 مرحباً! أنا مساعدك الذكي لإدارة العقارات."
    },
    "welcome_subtitle": {
        "ru": "Помогу организовать рабочий день и не пропустить важные встречи!",
        "en": "I'll help organize your work day and never miss important meetings!",
        "es": "¡Te ayudaré a organizar tu día de trabajo y no perder reuniones importantes!",
        "ar": "سأساعدك في تنظيم يوم عملك وعدم تفويت الاجتماعات المهمة!"
    },
    "examples_header": {
        "ru": "📝 Примеры команд:",
        "en": "📝 Example commands:",
        "es": "📝 Ejemplos de comandos:",
        "ar": "📝 أمثلة على الأوامر:"
    },
    "create_events_header": {
        "ru": "📍 Создание событий:",
        "en": "📍 Creating events:",
        "es": "📍 Crear eventos:",
        "ar": "📍 إنشاء الأحداث:"
    },
    "create_example_1": {
        "ru": "• \"Показ квартиры на Ленина для Андрея завтра в 14:00\"",
        "en": "• \"Apartment showing on Lenin St for Andrew tomorrow at 2 PM\"",
        "es": "• \"Visita de apartamento en la calle Lenin para Andrés mañana a las 14:00\"",
        "ar": "• \"عرض شقة في شارع لينين لأندرو غداً الساعة 2 مساءً\""
    },
    "create_example_2": {
        "ru": "• \"Встреча в офисе с Ивановым послезавтра в 11:00\"",
        "en": "• \"Office meeting with Ivanov day after tomorrow at 11 AM\"",
        "es": "• \"Reunión en la oficina con Ivanov pasado mañana a las 11:00\"",
        "ar": "• \"اجتماع في المكتب مع إيفانوف بعد غد الساعة 11 صباحاً\""
    },
    "create_example_3": {
        "ru": "• \"Звонок клиенту Петрову в пятницу в 10:00\"",
        "en": "• \"Call client Petrov on Friday at 10 AM\"",
        "es": "• \"Llamar al cliente Petrov el viernes a las 10:00\"",
        "ar": "• \"اتصال بالعميل بتروف يوم الجمعة الساعة 10 صباحاً\""
    },
    "create_example_4": {
        "ru": "• \"Сделка у нотариуса в понедельник в 15:00\"",
        "en": "• \"Notary appointment on Monday at 3 PM\"",
        "es": "• \"Cita con el notario el lunes a las 15:00\"",
        "ar": "• \"موعد عند كاتب العدل يوم الإثنين الساعة 3 مساءً\""
    },
    "create_example_5": {
        "ru": "• \"Встреча в банке по ипотеке во вторник в 12:00\"",
        "en": "• \"Bank meeting about mortgage on Tuesday at 12 PM\"",
        "es": "• \"Reunión en el banco sobre hipoteca el martes a las 12:00\"",
        "ar": "• \"اجتماع في البنك حول الرهن العقاري يوم الثلاثاء الساعة 12 ظهراً\""
    },
    "view_schedule_header": {
        "ru": "👀 Просмотр расписания:",
        "en": "👀 View schedule:",
        "es": "👀 Ver calendario:",
        "ar": "👀 عرض الجدول:"
    },
    "view_example_1": {
        "ru": "• \"Какие планы на сегодня?\"",
        "en": "• \"What's on my schedule today?\"",
        "es": "• \"¿Qué tengo hoy?\"",
        "ar": "• \"ما هي خططي اليوم؟\""
    },
    "view_example_2": {
        "ru": "• \"Что у меня завтра?\"",
        "en": "• \"What do I have tomorrow?\"",
        "es": "• \"¿Qué tengo mañana?\"",
        "ar": "• \"ماذا لدي غداً؟\""
    },
    "view_example_3": {
        "ru": "• \"Покажи события на неделю\"",
        "en": "• \"Show events for the week\"",
        "es": "• \"Muestra eventos de la semana\"",
        "ar": "• \"أظهر أحداث الأسبوع\""
    },
    "modify_events_header": {
        "ru": "✏️ Изменение событий:",
        "en": "✏️ Modify events:",
        "es": "✏️ Modificar eventos:",
        "ar": "✏️ تعديل الأحداث:"
    },
    "modify_example_1": {
        "ru": "• \"Перенеси встречу с Андреем на 17:00\"",
        "en": "• \"Reschedule meeting with Andrew to 5 PM\"",
        "es": "• \"Reprograma la reunión con Andrés a las 17:00\"",
        "ar": "• \"أعد جدولة الاجتماع مع أندرو إلى الساعة 5 مساءً\""
    },
    "modify_example_2": {
        "ru": "• \"Отмени показ для Иванова\"",
        "en": "• \"Cancel showing for Ivanov\"",
        "es": "• \"Cancela la visita para Ivanov\"",
        "ar": "• \"إلغاء العرض لإيفانوف\""
    },
    "modify_example_3": {
        "ru": "• \"Удали звонок Петрову\"",
        "en": "• \"Delete call to Petrov\"",
        "es": "• \"Elimina la llamada a Petrov\"",
        "ar": "• \"احذف المكالمة إلى بتروف\""
    },
    "voice_hint": {
        "ru": "🎤 Можете использовать голосовые сообщения - удобно за рулем!",
        "en": "🎤 You can use voice messages - convenient while driving!",
        "es": "🎤 ¡Puedes usar mensajes de voz - conveniente mientras conduces!",
        "ar": "🎤 يمكنك استخدام الرسائل الصوتية - مريح أثناء القيادة!"
    },
    "timezone_command": {
        "ru": "⏰ Команда /timezone - установить ваш часовой пояс",
        "en": "⏰ Command /timezone - set your timezone",
        "es": "⏰ Comando /timezone - establece tu zona horaria",
        "ar": "⏰ الأمر /timezone - حدد منطقتك الزمنية"
    },
    "language_command": {
        "ru": "🌍 Команда /language - изменить язык",
        "en": "🌍 Command /language - change language",
        "es": "🌍 Comando /language - cambiar idioma",
        "ar": "🌍 الأمر /language - تغيير اللغة"
    },
    "calendar_save": {
        "ru": "📅 Все события автоматически сохраняются в личном календаре.",
        "en": "📅 All events are automatically saved to your personal calendar.",
        "es": "📅 Todos los eventos se guardan automáticamente en tu calendario personal.",
        "ar": "📅 يتم حفظ جميع الأحداث تلقائياً في تقويمك الشخصي."
    },

    # Quick buttons
    "btn_today": {
        "ru": "📋 Дела на сегодня",
        "en": "📋 Today's Tasks",
        "es": "📋 Tareas de hoy",
        "ar": "📋 مهام اليوم"
    },
    "btn_tomorrow": {
        "ru": "📅 Дела на завтра",
        "en": "📅 Tomorrow's Tasks",
        "es": "📅 Tareas de mañana",
        "ar": "📅 مهام الغد"
    },
    "btn_week": {
        "ru": "📆 Дела на неделю",
        "en": "📆 Week's Tasks",
        "es": "📆 Tareas de la semana",
        "ar": "📆 مهام الأسبوع"
    },
    "btn_settings": {
        "ru": "⚙️ Настройки",
        "en": "⚙️ Settings",
        "es": "⚙️ Configuración",
        "ar": "⚙️ الإعدادات"
    },
    "btn_cabinet": {
        "ru": "🗓 Кабинет",
        "en": "🗓 Cabinet",
        "es": "🗓 Gabinete",
        "ar": "🗓 المكتب"
    },

    # Settings menu
    "settings_menu_title": {
        "ru": "⚙️ Настройки\n\nВыберите, что вы хотите изменить:",
        "en": "⚙️ Settings\n\nChoose what you want to change:",
        "es": "⚙️ Configuración\n\nElija qué desea cambiar:",
        "ar": "⚙️ الإعدادات\n\nاختر ما تريد تغييره:"
    },
    "settings_btn_language": {
        "ru": "🌐 Язык интерфейса",
        "en": "🌐 Interface Language",
        "es": "🌐 Idioma de la interfaz",
        "ar": "🌐 لغة الواجهة"
    },
    "settings_btn_timezone": {
        "ru": "🌍 Часовой пояс",
        "en": "🌍 Time Zone",
        "es": "🌍 Zona horaria",
        "ar": "🌍 المنطقة الزمنية"
    },

    # System messages
    "processing": {
        "ru": "⏳ Обрабатываю...",
        "en": "⏳ Processing...",
        "es": "⏳ Procesando...",
        "ar": "⏳ جارٍ المعالجة..."
    },
    "recognizing_voice": {
        "ru": "🎤 Распознаю голос...",
        "en": "🎤 Recognizing voice...",
        "es": "🎤 Reconociendo voz...",
        "ar": "🎤 التعرف على الصوت..."
    },
    "you_said": {
        "ru": "Вы сказали: \"{text}\"",
        "en": "You said: \"{text}\"",
        "es": "Dijiste: \"{text}\"",
        "ar": "قلت: \"{text}\""
    },
    "voice_error": {
        "ru": "Извините, не удалось распознать голос. Попробуйте еще раз или используйте текст.",
        "en": "Sorry, couldn't recognize voice. Try again or use text.",
        "es": "Lo siento, no pude reconocer la voz. Intenta de nuevo o usa texto.",
        "ar": "عذراً، لم أتمكن من التعرف على الصوت. حاول مرة أخرى أو استخدم النص."
    },
    "voice_transcription_failed": {
        "ru": "❌ Ошибка при распознавании голоса. Используйте текстовые сообщения.",
        "en": "❌ Voice recognition error. Please use text messages.",
        "es": "❌ Error de reconocimiento de voz. Por favor, usa mensajes de texto.",
        "ar": "❌ خطأ في التعرف على الصوت. الرجاء استخدام الرسائل النصية."
    },
    "calendar_unavailable": {
        "ru": "⚠️ Календарный сервер временно недоступен.\nПопробуйте позже.",
        "en": "⚠️ Calendar server temporarily unavailable.\nPlease try later.",
        "es": "⚠️ Servidor de calendario temporalmente no disponible.\nIntenta más tarde.",
        "ar": "⚠️ خادم التقويم غير متاح مؤقتاً.\nحاول لاحقاً."
    },
    "unknown_message_type": {
        "ru": "Пожалуйста, отправьте текстовое или голосовое сообщение.",
        "en": "Please send a text or voice message.",
        "es": "Por favor, envía un mensaje de texto o de voz.",
        "ar": "يرجى إرسال رسالة نصية أو صوتية."
    },
    "error_processing": {
        "ru": "Произошла ошибка при обработке сообщения. Попробуйте еще раз.",
        "en": "An error occurred while processing the message. Please try again.",
        "es": "Ocurrió un error al procesar el mensaje. Por favor, intenta de nuevo.",
        "ar": "حدث خطأ أثناء معالجة الرسالة. يرجى المحاولة مرة أخرى."
    },

    # Event operations
    "event_created": {
        "ru": "✅ Событие создано!",
        "en": "✅ Event created!",
        "es": "✅ ¡Evento creado!",
        "ar": "✅ تم إنشاء الحدث!"
    },
    "event_updated": {
        "ru": "✅ Событие обновлено!",
        "en": "✅ Event updated!",
        "es": "✅ ¡Evento actualizado!",
        "ar": "✅ تم تحديث الحدث!"
    },
    "event_deleted": {
        "ru": "✅ Событие удалено!",
        "en": "✅ Event deleted!",
        "es": "✅ ¡Evento eliminado!",
        "ar": "✅ تم حذف الحدث!"
    },
    "event_create_failed": {
        "ru": "❌ Не удалось создать событие. Проверьте настройки доступа.",
        "en": "❌ Failed to create event. Check access settings.",
        "es": "❌ No se pudo crear el evento. Verifica la configuración de acceso.",
        "ar": "❌ فشل إنشاء الحدث. تحقق من إعدادات الوصول."
    },
    "event_update_failed": {
        "ru": "❌ Не удалось обновить событие. Возможно, оно было удалено.",
        "en": "❌ Failed to update event. It may have been deleted.",
        "es": "❌ No se pudo actualizar el evento. Puede que haya sido eliminado.",
        "ar": "❌ فشل تحديث الحدث. ربما تم حذفه."
    },
    "event_delete_failed": {
        "ru": "❌ Не удалось удалить событие. Возможно, оно уже было удалено.",
        "en": "❌ Failed to delete event. It may have already been deleted.",
        "es": "❌ No se pudo eliminar el evento. Puede que ya haya sido eliminado.",
        "ar": "❌ فشل حذف الحدث. ربما تم حذفه بالفعل."
    },
    "event_not_found": {
        "ru": "Не удалось определить, какое событие нужно изменить. Попробуйте уточнить.",
        "en": "Couldn't determine which event to modify. Please clarify.",
        "es": "No se pudo determinar qué evento modificar. Por favor, aclara.",
        "ar": "لم أتمكن من تحديد الحدث المراد تعديله. يرجى التوضيح."
    },
    "event_delete_not_found": {
        "ru": "Не удалось определить, какое событие нужно удалить. Попробуйте уточнить.",
        "en": "Couldn't determine which event to delete. Please clarify.",
        "es": "No se pudo determinar qué evento eliminar. Por favor, aclara.",
        "ar": "لم أتمكن من تحديد الحدث المراد حذفه. يرجى التوضيح."
    },
    "event_needs_details": {
        "ru": "Для создания события нужно указать название и время. Попробуйте еще раз.",
        "en": "To create an event, please specify title and time. Try again.",
        "es": "Para crear un evento, especifica el título y la hora. Intenta de nuevo.",
        "ar": "لإنشاء حدث، يرجى تحديد العنوان والوقت. حاول مرة أخرى."
    },
    "error_invalid_recurrence": {
        "ru": "❌ Не удалось создать повторяющиеся события. Проверьте параметры повтора.",
        "en": "❌ Failed to create recurring events. Check recurrence parameters.",
        "es": "❌ No se pudieron crear eventos recurrentes. Verifica los parámetros de recurrencia.",
        "ar": "❌ فشل إنشاء الأحداث المتكررة. تحقق من معاملات التكرار."
    },
    "no_events_found": {
        "ru": "📅 На это время событий не запланировано.",
        "en": "📅 No events scheduled for this time.",
        "es": "📅 No hay eventos programados para este momento.",
        "ar": "📅 لا توجد أحداث مجدولة لهذا الوقت."
    },
    "your_events": {
        "ru": "📅 Ваши события:\n\n",
        "en": "📅 Your events:\n\n",
        "es": "📅 Tus eventos:\n\n",
        "ar": "📅 أحداثك:\n\n"
    },
    "no_free_slots": {
        "ru": "📅 На этот день нет свободных промежутков.",
        "en": "📅 No free slots available for this day.",
        "es": "📅 No hay espacios libres disponibles para este día.",
        "ar": "📅 لا توجد فترات متاحة لهذا اليوم."
    },
    "free_slots": {
        "ru": "🆓 Свободные промежутки:\n\n",
        "en": "🆓 Free slots:\n\n",
        "es": "🆓 Espacios libres:\n\n",
        "ar": "🆓 الفترات المتاحة:\n\n"
    },

    # Timezone
    "current_timezone": {
        "ru": "⏰ Текущий часовой пояс: {tz}\n\nВыберите ваш часовой пояс:",
        "en": "⏰ Current timezone: {tz}\n\nSelect your timezone:",
        "es": "⏰ Zona horaria actual: {tz}\n\nSelecciona tu zona horaria:",
        "ar": "⏰ المنطقة الزمنية الحالية: {tz}\n\nحدد منطقتك الزمنية:"
    },
    "timezone_prompt": {
        "ru": "🌍 Часовой пояс: {tz}\n🕐 Текущее время: {time}\n\nВыберите ваш часовой пояс:",
        "en": "🌍 Timezone: {tz}\n🕐 Current time: {time}\n\nSelect your timezone:",
        "es": "🌍 Zona horaria: {tz}\n🕐 Hora actual: {time}\n\nSelecciona tu zona horaria:",
        "ar": "🌍 المنطقة الزمنية: {tz}\n🕐 الوقت الحالي: {time}\n\nحدد منطقتك الزمنية:"
    },
    "timezone_set": {
        "ru": "✅ Часовой пояс установлен: {tz}",
        "en": "✅ Timezone set: {tz}",
        "es": "✅ Zona horaria establecida: {tz}",
        "ar": "✅ تم تعيين المنطقة الزمنية: {tz}"
    },
    "timezone_error": {
        "ru": "❌ Неверный часовой пояс. Используйте /timezone для списка доступных.",
        "en": "❌ Invalid timezone. Use /timezone for available options.",
        "es": "❌ Zona horaria inválida. Usa /timezone para ver opciones disponibles.",
        "ar": "❌ منطقة زمنية غير صالحة. استخدم /timezone للخيارات المتاحة."
    },
    "timezone_invalid": {
        "ru": "❌ Неверный часовой пояс. Используйте /timezone для списка доступных.",
        "en": "❌ Invalid timezone. Use /timezone for available options.",
        "es": "❌ Zona horaria inválida. Usa /timezone para ver opciones disponibles.",
        "ar": "❌ منطقة زمنية غير صالحة. استخدم /timezone للخيارات المتاحة."
    },
    "timezone_set_error": {
        "ru": "❌ Ошибка при установке часового пояса",
        "en": "❌ Error setting timezone",
        "es": "❌ Error al establecer la zona horaria",
        "ar": "❌ خطأ في تعيين المنطقة الزمنية"
    },

    # Feature not implemented
    "feature_coming_soon": {
        "ru": "Эта функция пока в разработке. Скоро будет доступна!",
        "en": "This feature is under development. Coming soon!",
        "es": "Esta función está en desarrollo. ¡Próximamente disponible!",
        "ar": "هذه الميزة قيد التطوير. قريباً!"
    },

    # Rate limiting and spam protection
    "rate_limit_blocked": {
        "ru": "⛔️ Вы временно заблокированы за спам. Разблокировка через {minutes} мин.",
        "en": "⛔️ You are temporarily blocked for spam. Unblock in {minutes} min.",
        "es": "⛔️ Estás temporalmente bloqueado por spam. Desbloqueo en {minutes} min.",
        "ar": "⛔️ تم حظرك مؤقتاً بسبب الإزعاج. إلغاء الحظر خلال {minutes} دقيقة."
    },
    "rate_limit_minute": {
        "ru": "⏸ Слишком много запросов. Подождите минуту.",
        "en": "⏸ Too many requests. Wait a minute.",
        "es": "⏸ Demasiadas solicitudes. Espera un minuto.",
        "ar": "⏸ طلبات كثيرة جداً. انتظر دقيقة."
    },
    "rate_limit_hour": {
        "ru": "⏸ Превышен лимит запросов в час. Попробуйте позже.",
        "en": "⏸ Hourly request limit exceeded. Try later.",
        "es": "⏸ Límite de solicitudes por hora excedido. Intenta más tarde.",
        "ar": "⏸ تجاوز الحد الأقصى للطلبات في الساعة. حاول لاحقاً."
    },
    "rate_limit_slow_down": {
        "ru": "🐌 Пожалуйста, замедлитесь. Не отправляйте много сообщений подряд.",
        "en": "🐌 Please slow down. Don't send many messages in a row.",
        "es": "🐌 Por favor, ve más despacio. No envíes muchos mensajes seguidos.",
        "ar": "🐌 من فضلك تمهل. لا ترسل العديد من الرسائل على التوالي."
    },
    "rate_limit_spam_blocked": {
        "ru": "🚫 Вы заблокированы на 1 час за спам.",
        "en": "🚫 You are blocked for 1 hour for spamming.",
        "es": "🚫 Estás bloqueado por 1 hora por spam.",
        "ar": "🚫 تم حظرك لمدة ساعة بسبب الإزعاج."
    },

    # Batch operations
    "batch_confirm_header": {
        "ru": "📋 Я правильно понял? Вы хотите выполнить следующие действия:\n\n",
        "en": "📋 Did I understand correctly? You want to perform the following actions:\n\n",
        "es": "📋 ¿Entendí correctamente? Quieres realizar las siguientes acciones:\n\n",
        "ar": "📋 هل فهمت بشكل صحيح؟ تريد تنفيذ الإجراءات التالية:\n\n"
    },
    "batch_confirm_footer": {
        "ru": "\n\n⚠️ Подтвердите выполнение этих операций:",
        "en": "\n\n⚠️ Please confirm these operations:",
        "es": "\n\n⚠️ Por favor confirma estas operaciones:",
        "ar": "\n\n⚠️ يرجى تأكيد هذه العمليات:"
    },
    "batch_confirm_btn": {
        "ru": "✅ Подтвердить",
        "en": "✅ Confirm",
        "es": "✅ Confirmar",
        "ar": "✅ تأكيد"
    },
    "batch_cancel_btn": {
        "ru": "❌ Отменить",
        "en": "❌ Cancel",
        "es": "❌ Cancelar",
        "ar": "❌ إلغاء"
    },
    "batch_single_event_btn": {
        "ru": "📌 Только одно событие",
        "en": "📌 Single event only",
        "es": "📌 Solo un evento",
        "ar": "📌 حدث واحد فقط"
    },
    "batch_confirmed": {
        "ru": "✅ Выполняю операции...",
        "en": "✅ Executing operations...",
        "es": "✅ Ejecutando operaciones...",
        "ar": "✅ جارٍ تنفيذ العمليات..."
    },
    "batch_cancelled": {
        "ru": "❌ Операции отменены",
        "en": "❌ Operations cancelled",
        "es": "❌ Operaciones canceladas",
        "ar": "❌ تم إلغاء العمليات"
    },
    "batch_completed": {
        "ru": "✅ Все операции выполнены!\n\nВыполнено: {success}\nОшибки: {errors}",
        "en": "✅ All operations completed!\n\nSuccess: {success}\nErrors: {errors}",
        "es": "✅ ¡Todas las operaciones completadas!\n\nÉxito: {success}\nErrores: {errors}",
        "ar": "✅ اكتملت جميع العمليات!\n\nنجح: {success}\nأخطاء: {errors}"
    },
    "action_create": {
        "ru": "Создать",
        "en": "Create",
        "es": "Crear",
        "ar": "إنشاء"
    },
    "action_update": {
        "ru": "Обновить",
        "en": "Update",
        "es": "Actualizar",
        "ar": "تحديث"
    },
    "action_delete": {
        "ru": "Удалить",
        "en": "Delete",
        "es": "Eliminar",
        "ar": "حذف"
    },
    "batch_result_deleted": {
        "ru": "Удалено",
        "en": "Deleted",
        "es": "Eliminado",
        "ar": "تم الحذف"
    },
    "batch_result_failed_delete": {
        "ru": "Не удалось удалить",
        "en": "Failed to delete",
        "es": "Error al eliminar",
        "ar": "فشل الحذف"
    },
    "batch_result_error": {
        "ru": "Ошибка",
        "en": "Error",
        "es": "Error",
        "ar": "خطأ"
    },
    "batch_result_unknown": {
        "ru": "Неизвестно",
        "en": "Unknown",
        "es": "Desconocido",
        "ar": "غير معروف"
    },
    "batch_errors_list": {
        "ru": "⚠️ Возникли следующие ошибки:",
        "en": "⚠️ The following errors occurred:",
        "es": "⚠️ Se produjeron los siguientes errores:",
        "ar": "⚠️ حدثت الأخطاء التالية:"
    },

    # LLM clarification messages
    "clarify_rephrase": {
        "ru": "Не могли бы вы переформулировать ваш запрос?",
        "en": "Could you please rephrase your request?",
        "es": "¿Podrías reformular tu solicitud?",
        "ar": "هل يمكنك إعادة صياغة طلبك؟"
    },
    "clarify_more_details": {
        "ru": "Не совсем понял. Можете добавить больше деталей?",
        "en": "I didn't quite understand. Could you add more details?",
        "es": "No entendí del todo. ¿Podrías agregar más detalles?",
        "ar": "لم أفهم تماماً. هل يمكنك إضافة المزيد من التفاصيل؟"
    },
    "clarify_which_event": {
        "ru": "Какое именно событие вы имеете в виду?",
        "en": "Which event exactly do you mean?",
        "es": "¿Qué evento exactamente quieres decir?",
        "ar": "أي حدث تقصد بالضبط؟"
    },
    "clarify_time_unclear": {
        "ru": "Не удалось определить время. Уточните, пожалуйста, дату и время события.",
        "en": "Couldn't determine the time. Please specify the date and time of the event.",
        "es": "No pude determinar la hora. Por favor, especifica la fecha y hora del evento.",
        "ar": "لم أتمكن من تحديد الوقت. يرجى تحديد تاريخ ووقت الحدث."
    },

    # Event reminders
    "event_reminder_30min": {
        "ru": "⏰ Напоминание!\n\n📅 Через 30 минут: {title}\n🕐 Время: {time}",
        "en": "⏰ Reminder!\n\n📅 In 30 minutes: {title}\n🕐 Time: {time}",
        "es": "⏰ ¡Recordatorio!\n\n📅 En 30 minutos: {title}\n🕐 Hora: {time}",
        "ar": "⏰ تذكير!\n\n📅 في 30 دقيقة: {title}\n🕐 الوقت: {time}"
    },

    # Morning motivation button
    "motivation_btn_action": {
        "ru": "Да! 💪",
        "en": "Yes! 💪",
        "es": "¡Sí! 💪",
        "ar": "نعم! 💪"
    },

    # 60 Morning motivational messages
    "morning_motivation_1": {
        "ru": "🌅 Доброе утро! Сегодня отличный день, чтобы стать лучшей версией себя!",
        "en": "🌅 Good morning! Today is a great day to become the best version of yourself!",
        "es": "🌅 ¡Buenos días! ¡Hoy es un gran día para convertirte en la mejor versión de ti mismo!",
        "ar": "🌅 صباح الخير! اليوم يوم رائع لتصبح أفضل نسخة من نفسك!"
    },
    "morning_motivation_2": {
        "ru": "☀️ Каждое утро — новая возможность. Используй её на максимум!",
        "en": "☀️ Every morning is a new opportunity. Make the most of it!",
        "es": "☀️ Cada mañana es una nueva oportunidad. ¡Aprovéchala al máximo!",
        "ar": "☀️ كل صباح فرصة جديدة. استفد منها إلى أقصى حد!"
    },
    "morning_motivation_3": {
        "ru": "💪 Успех — это сумма маленьких усилий, повторяемых день за днём. Вперёд!",
        "en": "💪 Success is the sum of small efforts repeated day after day. Let's go!",
        "es": "💪 El éxito es la suma de pequeños esfuerzos repetidos día tras día. ¡Vamos!",
        "ar": "💪 النجاح هو مجموع الجهود الصغيرة المتكررة يوماً بعد يوم. لنبدأ!"
    },
    "morning_motivation_4": {
        "ru": "🎯 Сегодня ты на шаг ближе к своей цели. Продолжай двигаться!",
        "en": "🎯 Today you're one step closer to your goal. Keep moving forward!",
        "es": "🎯 Hoy estás un paso más cerca de tu objetivo. ¡Sigue adelante!",
        "ar": "🎯 اليوم أنت أقرب خطوة إلى هدفك. استمر في التقدم!"
    },
    "morning_motivation_5": {
        "ru": "🚀 Великие дела начинаются с первого шага. Сделай его сегодня!",
        "en": "🚀 Great things start with the first step. Take it today!",
        "es": "🚀 Las grandes cosas comienzan con el primer paso. ¡Hazlo hoy!",
        "ar": "🚀 الأشياء العظيمة تبدأ بالخطوة الأولى. اتخذها اليوم!"
    },
    "morning_motivation_6": {
        "ru": "✨ Твоя энергия создаёт твою реальность. Заряжайся позитивом!",
        "en": "✨ Your energy creates your reality. Charge yourself with positivity!",
        "es": "✨ Tu energía crea tu realidad. ¡Cárgate de positividad!",
        "ar": "✨ طاقتك تخلق واقعك. اشحن نفسك بالإيجابية!"
    },
    "morning_motivation_7": {
        "ru": "🌟 Верь в себя и в то, что ты способен на большее. Сегодня твой день!",
        "en": "🌟 Believe in yourself and that you're capable of more. Today is your day!",
        "es": "🌟 Cree en ti mismo y en que eres capaz de más. ¡Hoy es tu día!",
        "ar": "🌟 آمن بنفسك وبأنك قادر على المزيد. اليوم هو يومك!"
    },
    "morning_motivation_8": {
        "ru": "🔥 Не жди идеального момента — создай его сам. Начни прямо сейчас!",
        "en": "🔥 Don't wait for the perfect moment — create it yourself. Start right now!",
        "es": "🔥 No esperes el momento perfecto — créalo tú mismo. ¡Empieza ahora!",
        "ar": "🔥 لا تنتظر اللحظة المثالية — اصنعها بنفسك. ابدأ الآن!"
    },
    "morning_motivation_9": {
        "ru": "💎 Ты сильнее, чем думаешь. Покажи миру, на что ты способен!",
        "en": "💎 You're stronger than you think. Show the world what you're capable of!",
        "es": "💎 Eres más fuerte de lo que piensas. ¡Muestra al mundo de lo que eres capaz!",
        "ar": "💎 أنت أقوى مما تعتقد. أظهر للعالم ما أنت قادر عليه!"
    },
    "morning_motivation_10": {
        "ru": "🎨 Каждый день — чистый холст. Нарисуй шедевр!",
        "en": "🎨 Every day is a blank canvas. Paint a masterpiece!",
        "es": "🎨 Cada día es un lienzo en blanco. ¡Pinta una obra maestra!",
        "ar": "🎨 كل يوم لوحة فارغة. ارسم تحفة فنية!"
    },
    "morning_motivation_11": {
        "ru": "⚡️ Энергия и настойчивость побеждают всё. Действуй с полной отдачей!",
        "en": "⚡️ Energy and persistence conquer all. Act with full commitment!",
        "es": "⚡️ La energía y la persistencia lo conquistan todo. ¡Actúa con total compromiso!",
        "ar": "⚡️ الطاقة والمثابرة تتغلبان على كل شيء. تصرف بالتزام كامل!"
    },
    "morning_motivation_12": {
        "ru": "🌈 После любой бури наступает радуга. Твой успех уже близко!",
        "en": "🌈 After every storm comes a rainbow. Your success is near!",
        "es": "🌈 Después de cada tormenta viene un arcoíris. ¡Tu éxito está cerca!",
        "ar": "🌈 بعد كل عاصفة يأتي قوس قزح. نجاحك قريب!"
    },
    "morning_motivation_13": {
        "ru": "🏆 Чемпионы делают то, что другие не хотят делать. Будь чемпионом!",
        "en": "🏆 Champions do what others don't want to do. Be a champion!",
        "es": "🏆 Los campeones hacen lo que otros no quieren hacer. ¡Sé un campeón!",
        "ar": "🏆 الأبطال يفعلون ما لا يريد الآخرون فعله. كن بطلاً!"
    },
    "morning_motivation_14": {
        "ru": "🌺 Твоё будущее создаётся тем, что ты делаешь сегодня, а не завтра.",
        "en": "🌺 Your future is created by what you do today, not tomorrow.",
        "es": "🌺 Tu futuro se crea con lo que haces hoy, no mañana.",
        "ar": "🌺 مستقبلك يُصنع بما تفعله اليوم، وليس غداً."
    },
    "morning_motivation_15": {
        "ru": "🎪 Жизнь — это приключение. Наслаждайся каждым моментом!",
        "en": "🎪 Life is an adventure. Enjoy every moment!",
        "es": "🎪 La vida es una aventura. ¡Disfruta cada momento!",
        "ar": "🎪 الحياة مغامرة. استمتع بكل لحظة!"
    },
    "morning_motivation_16": {
        "ru": "🦅 Расправь крылья и лети к своим мечтам. Небо — не предел!",
        "en": "🦅 Spread your wings and fly to your dreams. The sky is not the limit!",
        "es": "🦅 Despliega tus alas y vuela hacia tus sueños. ¡El cielo no es el límite!",
        "ar": "🦅 افرد جناحيك واطر نحو أحلامك. السماء ليست الحد!"
    },
    "morning_motivation_17": {
        "ru": "💫 Маленькие победы каждый день ведут к большому успеху. Продолжай!",
        "en": "💫 Small victories every day lead to great success. Keep going!",
        "es": "💫 Pequeñas victorias cada día llevan a un gran éxito. ¡Continúa!",
        "ar": "💫 الانتصارات الصغيرة كل يوم تؤدي إلى نجاح كبير. استمر!"
    },
    "morning_motivation_18": {
        "ru": "🎯 Фокусируйся на том, что можешь контролировать. Остальное приложится!",
        "en": "🎯 Focus on what you can control. The rest will follow!",
        "es": "🎯 Concéntrate en lo que puedes controlar. ¡Lo demás seguirá!",
        "ar": "🎯 ركز على ما يمكنك التحكم فيه. الباقي سيتبع!"
    },
    "morning_motivation_19": {
        "ru": "🌻 Улыбнись миру, и он улыбнётся тебе в ответ. Доброе утро!",
        "en": "🌻 Smile at the world, and it will smile back at you. Good morning!",
        "es": "🌻 Sonríe al mundo y te devolverá la sonrisa. ¡Buenos días!",
        "ar": "🌻 ابتسم للعالم وسيبتسم لك في المقابل. صباح الخير!"
    },
    "morning_motivation_20": {
        "ru": "🔑 Ключ к успеху — в постоянном развитии. Учись чему-то новому сегодня!",
        "en": "🔑 The key to success is constant development. Learn something new today!",
        "es": "🔑 La clave del éxito es el desarrollo constante. ¡Aprende algo nuevo hoy!",
        "ar": "🔑 مفتاح النجاح هو التطوير المستمر. تعلم شيئاً جديداً اليوم!"
    },
    "morning_motivation_21": {
        "ru": "🎵 Пусть твой день звучит как любимая песня. Наполни его радостью!",
        "en": "🎵 Let your day sound like your favorite song. Fill it with joy!",
        "es": "🎵 Que tu día suene como tu canción favorita. ¡Llenalo de alegría!",
        "ar": "🎵 دع يومك يبدو مثل أغنيتك المفضلة. املأه بالفرح!"
    },
    "morning_motivation_22": {
        "ru": "🚴 Не останавливайся, когда устал. Останавливайся, когда закончил!",
        "en": "🚴 Don't stop when you're tired. Stop when you're done!",
        "es": "🚴 No te detengas cuando estés cansado. ¡Detente cuando hayas terminado!",
        "ar": "🚴 لا تتوقف عندما تتعب. توقف عندما تنتهي!"
    },
    "morning_motivation_23": {
        "ru": "🌠 Мечтай, верь, достигай. Ты можешь всё, что захочешь!",
        "en": "🌠 Dream, believe, achieve. You can do anything you set your mind to!",
        "es": "🌠 Sueña, cree, logra. ¡Puedes hacer cualquier cosa que te propongas!",
        "ar": "🌠 احلم، آمن، حقق. يمكنك فعل أي شيء تضعه في ذهنك!"
    },
    "morning_motivation_24": {
        "ru": "🏃 Скорость не важна. Важно двигаться вперёд. Не сдавайся!",
        "en": "🏃 Speed doesn't matter. What matters is moving forward. Don't give up!",
        "es": "🏃 La velocidad no importa. Lo que importa es avanzar. ¡No te rindas!",
        "ar": "🏃 السرعة لا تهم. المهم هو التقدم للأمام. لا تستسلم!"
    },
    "morning_motivation_25": {
        "ru": "🌙 Сегодняшний успех — результат вчерашних усилий. Продолжай работать!",
        "en": "🌙 Today's success is the result of yesterday's efforts. Keep working!",
        "es": "🌙 El éxito de hoy es el resultado de los esfuerzos de ayer. ¡Sigue trabajando!",
        "ar": "🌙 نجاح اليوم هو نتيجة جهود الأمس. استمر في العمل!"
    },
    "morning_motivation_26": {
        "ru": "🎁 Каждый новый день — это подарок. Разверни его с энтузиазмом!",
        "en": "🎁 Every new day is a gift. Unwrap it with enthusiasm!",
        "es": "🎁 Cada nuevo día es un regalo. ¡Desenvuélvelo con entusiasmo!",
        "ar": "🎁 كل يوم جديد هدية. افتحه بحماس!"
    },
    "morning_motivation_27": {
        "ru": "🏔 Поднимайся на свою вершину, шаг за шагом. Ты уже в пути!",
        "en": "🏔 Climb to your peak, step by step. You're already on your way!",
        "es": "🏔 Escala tu cima, paso a paso. ¡Ya estás en camino!",
        "ar": "🏔 اصعد إلى قمتك، خطوة بخطوة. أنت بالفعل في الطريق!"
    },
    "morning_motivation_28": {
        "ru": "⭐️ Ты — звезда. Освети этот день своим светом!",
        "en": "⭐️ You are a star. Light up this day with your shine!",
        "es": "⭐️ Eres una estrella. ¡Ilumina este día con tu brillo!",
        "ar": "⭐️ أنت نجم. أضئ هذا اليوم بإشراقتك!"
    },
    "morning_motivation_29": {
        "ru": "🎬 Ты — режиссёр своей жизни. Сделай сегодня отличный эпизод!",
        "en": "🎬 You're the director of your life. Make today a great episode!",
        "es": "🎬 Eres el director de tu vida. ¡Haz de hoy un gran episodio!",
        "ar": "🎬 أنت مخرج حياتك. اجعل اليوم حلقة رائعة!"
    },
    "morning_motivation_30": {
        "ru": "🌊 Будь как океан — спокойный снаружи, сильный внутри!",
        "en": "🌊 Be like the ocean — calm outside, strong inside!",
        "es": "🌊 Sé como el océano — ¡calmado por fuera, fuerte por dentro!",
        "ar": "🌊 كن مثل المحيط — هادئ من الخارج، قوي من الداخل!"
    },
    "morning_motivation_31": {
        "ru": "🎯 Концентрация + действие = результат. Начинай действовать!",
        "en": "🎯 Focus + action = results. Start taking action!",
        "es": "🎯 Concentración + acción = resultados. ¡Empieza a actuar!",
        "ar": "🎯 التركيز + العمل = النتائج. ابدأ في اتخاذ إجراءات!"
    },
    "morning_motivation_32": {
        "ru": "🏅 Будь настолько хорош, что тебя невозможно игнорировать!",
        "en": "🏅 Be so good they can't ignore you!",
        "es": "🏅 ¡Sé tan bueno que no puedan ignorarte!",
        "ar": "🏅 كن جيداً لدرجة أنهم لا يستطيعون تجاهلك!"
    },
    "morning_motivation_33": {
        "ru": "🌸 Расцветай там, где ты посажен. Твоё время пришло!",
        "en": "🌸 Bloom where you are planted. Your time has come!",
        "es": "🌸 Florece donde estés plantado. ¡Tu momento ha llegado!",
        "ar": "🌸 ازهر حيث أنت مزروع. لقد حان وقتك!"
    },
    "morning_motivation_34": {
        "ru": "💡 Великие идеи рождаются из действий. Твори и воплощай!",
        "en": "💡 Great ideas are born from action. Create and implement!",
        "es": "💡 Las grandes ideas nacen de la acción. ¡Crea e implementa!",
        "ar": "💡 الأفكار العظيمة تولد من العمل. أنشئ ونفذ!"
    },
    "morning_motivation_35": {
        "ru": "🦋 Изменения начинаются с тебя. Будь той переменой, которую хочешь видеть!",
        "en": "🦋 Change starts with you. Be the change you want to see!",
        "es": "🦋 El cambio comienza contigo. ¡Sé el cambio que quieres ver!",
        "ar": "🦋 التغيير يبدأ بك. كن التغيير الذي تريد رؤيته!"
    },
    "morning_motivation_36": {
        "ru": "🎪 Живи ярко, мечтай смело, действуй решительно!",
        "en": "🎪 Live brightly, dream boldly, act decisively!",
        "es": "🎪 ¡Vive brillantemente, sueña audazmente, actúa decisivamente!",
        "ar": "🎪 عش بإشراق، احلم بجرأة، تصرف بحزم!"
    },
    "morning_motivation_37": {
        "ru": "🔆 Твоя позитивная энергия заразительна. Поделись ею с миром!",
        "en": "🔆 Your positive energy is contagious. Share it with the world!",
        "es": "🔆 Tu energía positiva es contagiosa. ¡Compártela con el mundo!",
        "ar": "🔆 طاقتك الإيجابية معدية. شاركها مع العالم!"
    },
    "morning_motivation_38": {
        "ru": "🌟 Не бойся неудач — они учат нас быть лучше. Действуй смело!",
        "en": "🌟 Don't fear failure — it teaches us to be better. Act boldly!",
        "es": "🌟 No temas al fracaso — nos enseña a ser mejores. ¡Actúa con valentía!",
        "ar": "🌟 لا تخف من الفشل — إنه يعلمنا أن نكون أفضل. تصرف بجرأة!"
    },
    "morning_motivation_39": {
        "ru": "🎨 Твоя жизнь — твоё искусство. Создавай шедевры каждый день!",
        "en": "🎨 Your life is your art. Create masterpieces every day!",
        "es": "🎨 Tu vida es tu arte. ¡Crea obras maestras cada día!",
        "ar": "🎨 حياتك هي فنك. أنشئ روائع كل يوم!"
    },
    "morning_motivation_40": {
        "ru": "🚀 Невозможное становится возможным, когда ты в это веришь!",
        "en": "🚀 The impossible becomes possible when you believe in it!",
        "es": "🚀 ¡Lo imposible se vuelve posible cuando crees en ello!",
        "ar": "🚀 المستحيل يصبح ممكناً عندما تؤمن به!"
    },
    "morning_motivation_41": {
        "ru": "🌈 Радость — в пути, а не только в цели. Наслаждайся процессом!",
        "en": "🌈 Joy is in the journey, not just the destination. Enjoy the process!",
        "es": "🌈 La alegría está en el viaje, no solo en el destino. ¡Disfruta el proceso!",
        "ar": "🌈 الفرح في الرحلة، وليس فقط في الوجهة. استمتع بالعملية!"
    },
    "morning_motivation_42": {
        "ru": "💪 Сила внутри тебя сильнее любых обстоятельств. Используй её!",
        "en": "💪 The strength within you is stronger than any circumstance. Use it!",
        "es": "💪 La fuerza dentro de ti es más fuerte que cualquier circunstancia. ¡Úsala!",
        "ar": "💪 القوة بداخلك أقوى من أي ظرف. استخدمها!"
    },
    "morning_motivation_43": {
        "ru": "🎯 Целься в луну. Даже если промахнёшься, окажешься среди звёзд!",
        "en": "🎯 Aim for the moon. Even if you miss, you'll land among the stars!",
        "es": "🎯 Apunta a la luna. ¡Incluso si fallas, aterrizarás entre las estrellas!",
        "ar": "🎯 اهدف إلى القمر. حتى لو أخطأت، ستهبط بين النجوم!"
    },
    "morning_motivation_44": {
        "ru": "🏆 Победа начинается с решения попробовать. Попробуй сегодня!",
        "en": "🏆 Victory begins with the decision to try. Try today!",
        "es": "🏆 La victoria comienza con la decisión de intentar. ¡Inténtalo hoy!",
        "ar": "🏆 النصر يبدأ بقرار المحاولة. حاول اليوم!"
    },
    "morning_motivation_45": {
        "ru": "🌺 Твой потенциал безграничен. Раскрывай его каждый день!",
        "en": "🌺 Your potential is limitless. Unlock it every day!",
        "es": "🌺 Tu potencial es ilimitado. ¡Desbloquealo cada día!",
        "ar": "🌺 إمكاناتك غير محدودة. أطلقها كل يوم!"
    },
    "morning_motivation_46": {
        "ru": "⚡️ Действие — мощнейший магнит для успеха. Действуй сейчас!",
        "en": "⚡️ Action is the most powerful magnet for success. Act now!",
        "es": "⚡️ La acción es el imán más poderoso para el éxito. ¡Actúa ahora!",
        "ar": "⚡️ العمل هو أقوى مغناطيس للنجاح. تصرف الآن!"
    },
    "morning_motivation_47": {
        "ru": "🎪 Каждый день — новое шоу. Выступи на все 100%!",
        "en": "🎪 Every day is a new show. Perform at 100%!",
        "es": "🎪 Cada día es un nuevo espectáculo. ¡Rinde al 100%!",
        "ar": "🎪 كل يوم عرض جديد. أدِّ بنسبة 100%!"
    },
    "morning_motivation_48": {
        "ru": "🌅 Утро мудренее вечера. Используй свежие силы с умом!",
        "en": "🌅 Morning is wiser than evening. Use your fresh energy wisely!",
        "es": "🌅 La mañana es más sabia que la noche. ¡Usa tu energía fresca sabiamente!",
        "ar": "🌅 الصباح أحكم من المساء. استخدم طاقتك الطازجة بحكمة!"
    },
    "morning_motivation_49": {
        "ru": "🎁 Ты заслуживаешь успеха. Иди и возьми то, что твоё!",
        "en": "🎁 You deserve success. Go and take what's yours!",
        "es": "🎁 Mereces el éxito. ¡Ve y toma lo que es tuyo!",
        "ar": "🎁 أنت تستحق النجاح. اذهب وخذ ما هو لك!"
    },
    "morning_motivation_50": {
        "ru": "🔥 Страсть + дисциплина = непобедимая комбинация. Зажигай!",
        "en": "🔥 Passion + discipline = unbeatable combination. Light it up!",
        "es": "🔥 Pasión + disciplina = combinación imbatible. ¡Enciéndelo!",
        "ar": "🔥 الشغف + الانضباط = مزيج لا يُقهر. أشعله!"
    },
    "morning_motivation_51": {
        "ru": "🌟 Твой успех вдохновляет других. Продолжай сиять!",
        "en": "🌟 Your success inspires others. Keep shining!",
        "es": "🌟 Tu éxito inspira a otros. ¡Sigue brillando!",
        "ar": "🌟 نجاحك يلهم الآخرين. استمر في الإشراق!"
    },
    "morning_motivation_52": {
        "ru": "🎯 Прицелься, выстрели, попади в цель. Сегодня твой день!",
        "en": "🎯 Aim, shoot, hit the target. Today is your day!",
        "es": "🎯 Apunta, dispara, da en el blanco. ¡Hoy es tu día!",
        "ar": "🎯 صوّب، أطلق، أصب الهدف. اليوم هو يومك!"
    },
    "morning_motivation_53": {
        "ru": "💫 Магия случается за пределами зоны комфорта. Выходи за рамки!",
        "en": "💫 Magic happens outside the comfort zone. Step beyond the limits!",
        "es": "💫 La magia ocurre fuera de la zona de confort. ¡Sal de los límites!",
        "ar": "💫 السحر يحدث خارج منطقة الراحة. اخرج عن الحدود!"
    },
    "morning_motivation_54": {
        "ru": "🚀 Твой взлёт неизбежен. Приготовься к запуску!",
        "en": "🚀 Your takeoff is inevitable. Prepare for launch!",
        "es": "🚀 Tu despegue es inevitable. ¡Prepárate para el lanzamiento!",
        "ar": "🚀 إقلاعك حتمي. استعد للإطلاق!"
    },
    "morning_motivation_55": {
        "ru": "🌻 Посей добро утром, пожнёшь радость вечером!",
        "en": "🌻 Sow good in the morning, reap joy in the evening!",
        "es": "🌻 ¡Siembra el bien por la mañana, cosecha alegría por la noche!",
        "ar": "🌻 ازرع الخير في الصباح، واحصد الفرح في المساء!"
    },
    "morning_motivation_56": {
        "ru": "🏅 Ты не просто участник — ты победитель. Докажи это!",
        "en": "🏅 You're not just a participant — you're a winner. Prove it!",
        "es": "🏅 No eres solo un participante — eres un ganador. ¡Pruébalo!",
        "ar": "🏅 أنت لست مجرد مشارك — أنت فائز. أثبت ذلك!"
    },
    "morning_motivation_57": {
        "ru": "🎨 Креативность + действие = инновация. Твори сегодня!",
        "en": "🎨 Creativity + action = innovation. Create today!",
        "es": "🎨 Creatividad + acción = innovación. ¡Crea hoy!",
        "ar": "🎨 الإبداع + العمل = الابتكار. أبدع اليوم!"
    },
    "morning_motivation_58": {
        "ru": "⭐️ У тебя есть всё необходимое для успеха. Начни использовать это!",
        "en": "⭐️ You have everything you need for success. Start using it!",
        "es": "⭐️ Tienes todo lo que necesitas para el éxito. ¡Empieza a usarlo!",
        "ar": "⭐️ لديك كل ما تحتاجه للنجاح. ابدأ في استخدامه!"
    },
    "morning_motivation_59": {
        "ru": "🌈 Радуйся каждому дню — он больше не повторится. Цени момент!",
        "en": "🌈 Rejoice in every day — it will never come again. Cherish the moment!",
        "es": "🌈 Alégrate de cada día — nunca volverá. ¡Valora el momento!",
        "ar": "🌈 افرح بكل يوم — لن يعود أبداً. اعتز باللحظة!"
    },
    "morning_motivation_60": {
        "ru": "🔥 Сегодня тот самый день, когда всё меняется. Вперёд к переменам!",
        "en": "🔥 Today is the day when everything changes. Forward to change!",
        "es": "🔥 Hoy es el día en que todo cambia. ¡Adelante hacia el cambio!",
        "ar": "🔥 اليوم هو اليوم الذي يتغير فيه كل شيء. إلى الأمام نحو التغيير!"
    },

    # Daily reminders (9:00 AM and 8:00 PM)
    "morning_greeting": {
        "ru": "☀️ Доброе утро!",
        "en": "☀️ Good morning!",
        "es": "☀️ ¡Buenos días!",
        "ar": "☀️ صباح الخير!"
    },
    "no_events_today": {
        "ru": "📅 На сегодня событий не запланировано.\nОтличный день, чтобы всё успеть!",
        "en": "📅 No events scheduled for today.\nA great day to get everything done!",
        "es": "📅 No hay eventos programados para hoy.\n¡Un gran día para hacerlo todo!",
        "ar": "📅 لا توجد أحداث مجدولة لليوم.\nيوم رائع لإنجاز كل شيء!"
    },
    "your_events_today": {
        "ru": "📅 Ваши события на сегодня:",
        "en": "📅 Your events for today:",
        "es": "📅 Tus eventos para hoy:",
        "ar": "📅 أحداثك لهذا اليوم:"
    },
    "successful_day": {
        "ru": "Успешного дня! 💼",
        "en": "Have a successful day! 💼",
        "es": "¡Que tengas un día exitoso! 💼",
        "ar": "أتمنى لك يوماً ناجحاً! 💼"
    },
    "evening_greeting": {
        "ru": "🌟 Отличная работа сегодня!",
        "en": "🌟 Great work today!",
        "es": "🌟 ¡Gran trabajo hoy!",
        "ar": "🌟 عمل رائع اليوم!"
    },
    "evening_message_1": {
        "ru": "🌟 Отличная работа сегодня! Ты молодец, столько всего успел. Завтра будет ещё продуктивнее!",
        "en": "🌟 Great work today! You did so much. Tomorrow will be even more productive!",
        "es": "🌟 ¡Gran trabajo hoy! Hiciste mucho. ¡Mañana será aún más productivo!",
        "ar": "🌟 عمل رائع اليوم! لقد أنجزت الكثير. غداً سيكون أكثر إنتاجية!"
    },
    "evening_message_2": {
        "ru": "🎯 Сегодня был насыщенный день! Ты делаешь большие шаги к своим целям. Продолжай в том же духе!",
        "en": "🎯 Today was a busy day! You're making great strides toward your goals. Keep it up!",
        "es": "🎯 ¡Hoy fue un día ocupado! Estás dando grandes pasos hacia tus objetivos. ¡Sigue así!",
        "ar": "🎯 كان اليوم مليئاً بالنشاط! أنت تخطو خطوات كبيرة نحو أهدافك. استمر!"
    },
    "evening_message_3": {
        "ru": "💪 Ещё один успешный день позади! Твоя целеустремлённость впечатляет. Дальше — больше!",
        "en": "💪 Another successful day behind you! Your determination is impressive. Onward and upward!",
        "es": "💪 ¡Otro día exitoso detrás de ti! Tu determinación es impresionante. ¡Adelante y hacia arriba!",
        "ar": "💪 يوم ناجح آخر خلفك! عزيمتك مثيرة للإعجاب. إلى الأمام وإلى الأعلى!"
    },
    "evening_message_4": {
        "ru": "✨ Ты снова показал отличные результаты! Каждый день приближает тебя к успеху. Так держать!",
        "en": "✨ You showed great results again! Every day brings you closer to success. Keep it up!",
        "es": "✨ ¡Mostraste excelentes resultados otra vez! Cada día te acerca al éxito. ¡Sigue así!",
        "ar": "✨ لقد أظهرت نتائج رائعة مرة أخرى! كل يوم يقربك من النجاح. استمر!"
    },
    "evening_message_5": {
        "ru": "🚀 Сегодня ты был на высоте! Твой прогресс заметен. Завтра покорим новые вершины!",
        "en": "🚀 You were at your best today! Your progress is noticeable. Tomorrow we'll conquer new heights!",
        "es": "🚀 ¡Estuviste en tu mejor momento hoy! Tu progreso es notable. ¡Mañana conquistaremos nuevas alturas!",
        "ar": "🚀 كنت في أفضل حالاتك اليوم! تقدمك ملحوظ. غداً سنغزو آفاقاً جديدة!"
    },
    "events_count_today": {
        "ru": "📊 Сегодня у тебя было {count} событий",
        "en": "📊 You had {count} events today",
        "es": "📊 Tuviste {count} eventos hoy",
        "ar": "📊 كان لديك {count} حدثاً اليوم"
    },
    "rest_well": {
        "ru": "😴 Отдохни и набирайся сил для новых свершений!",
        "en": "😴 Rest and recharge for new achievements!",
        "es": "😴 ¡Descansa y recarga energías para nuevos logros!",
        "ar": "😴 استرح واستعد طاقتك لإنجازات جديدة!"
    },

    # Morning reminders - adapted for real estate agents
    "morning_empty_day": {
        "ru": "📭 На сегодня пока ничего не запланировано.",
        "en": "📭 Nothing scheduled for today yet."
    },
    "morning_empty_suggestions": {
        "ru": "💡 Свободный день — отличный шанс:\n• Обзвонить клиентов из базы\n• Назначить показы на неделю\n• Обновить объявления\n\nНапиши что планируешь — занесу в календарь.",
        "en": "💡 A free day — great chance to:\n• Call clients from your database\n• Schedule showings for the week\n• Update listings\n\nTell me your plans — I'll add them to the calendar."
    },
    "morning_no_meetings": {
        "ru": "📅 Встреч сегодня нет — можно сфокусироваться на делах!",
        "en": "📅 No meetings today — time to focus on tasks!"
    },
    "morning_tasks_header": {
        "ru": "📋 Задачи ({count}):",
        "en": "📋 Tasks ({count}):"
    },
    "morning_meetings_header": {
        "ru": "📅 Сегодня {count} встреч:",
        "en": "📅 Today {count} meetings:"
    },
    "morning_add_tasks": {
        "ru": "📝 Есть задачи на сегодня? Напиши — добавлю!",
        "en": "📝 Any tasks for today? Tell me — I'll add them!"
    },
    "morning_good_deals": {
        "ru": "Удачных сделок! 🏠",
        "en": "Good luck with your deals! 🏠"
    },
    "morning_full_day": {
        "ru": "День для результатов! 💰",
        "en": "A day for results! 💰"
    },
    "morning_and_tasks": {
        "ru": "📋 И {count} задач:",
        "en": "📋 And {count} tasks:"
    },
    "morning_tasks_more": {
        "ru": "...и ещё {count}",
        "en": "...and {count} more"
    },
    "morning_productive": {
        "ru": "Продуктивного дня! 💪",
        "en": "Have a productive day! 💪"
    },

    # Evening reminders - day summary
    "evening_summary_header": {
        "ru": "🌙 День заканчивается!",
        "en": "🌙 Day is ending!"
    },
    "evening_stats": {
        "ru": "📊 Сегодня:\n• {events} встреч проведено ✅\n• {completed} из {total} задач закрыто",
        "en": "📊 Today:\n• {events} meetings completed ✅\n• {completed} of {total} tasks done"
    },
    "evening_stats_events_only": {
        "ru": "📊 Сегодня проведено {events} встреч ✅",
        "en": "📊 Today {events} meetings completed ✅"
    },
    "evening_stats_tasks_only": {
        "ru": "📊 Сегодня закрыто {completed} из {total} задач",
        "en": "📊 Today {completed} of {total} tasks done"
    },
    "evening_remaining_header": {
        "ru": "📋 Осталось:",
        "en": "📋 Remaining:"
    },
    "evening_rest_tomorrow": {
        "ru": "Отдохни — завтра разберёмся! 🏠",
        "en": "Rest up — we'll handle it tomorrow! 🏠"
    },
    "evening_all_done_header": {
        "ru": "🏆 Отличный день!",
        "en": "🏆 Great day!"
    },
    "evening_all_done_stats": {
        "ru": "📊 Всё выполнено:\n• {events} встреч ✅\n• {tasks} задач закрыто ✅",
        "en": "📊 All done:\n• {events} meetings ✅\n• {tasks} tasks completed ✅"
    },
    "evening_keep_going": {
        "ru": "Так держать! Отдыхай, завтра снова в бой 💪",
        "en": "Keep it up! Rest now, back at it tomorrow 💪"
    },
    "evening_quiet_day": {
        "ru": "🌙 Спокойный день сегодня.",
        "en": "🌙 A quiet day today."
    },
    "evening_plan_tomorrow": {
        "ru": "💭 Завтра есть планы?\nНапиши вечером или утром — помогу организовать.\n\nХорошего отдыха!",
        "en": "💭 Any plans for tomorrow?\nWrite me tonight or in the morning — I'll help organize.\n\nHave a good rest!"
    },
}


def get_translation(key: str, lang: Language, **kwargs) -> str:
    """
    Get translation for a key in specified language.

    Args:
        key: Translation key
        lang: Language code
        **kwargs: Format arguments for the translation string

    Returns:
        Translated string, or key if translation not found
    """
    if key not in TRANSLATIONS:
        return key

    translation = TRANSLATIONS[key].get(lang, TRANSLATIONS[key].get(Language.ENGLISH, key))

    # Format with kwargs if provided
    if kwargs:
        try:
            return translation.format(**kwargs)
        except KeyError:
            return translation

    return translation


def get_welcome_message(lang: Language) -> str:
    """Get full welcome message in specified language."""
    parts = [
        get_translation("welcome_title", lang),
        "",
        get_translation("welcome_subtitle", lang),
        "",
        get_translation("examples_header", lang),
        "",
        get_translation("create_events_header", lang),
        get_translation("create_example_1", lang),
        get_translation("create_example_2", lang),
        get_translation("create_example_3", lang),
        get_translation("create_example_4", lang),
        get_translation("create_example_5", lang),
        "",
        get_translation("view_schedule_header", lang),
        get_translation("view_example_1", lang),
        get_translation("view_example_2", lang),
        get_translation("view_example_3", lang),
        "",
        get_translation("modify_events_header", lang),
        get_translation("modify_example_1", lang),
        get_translation("modify_example_2", lang),
        get_translation("modify_example_3", lang),
        "",
        get_translation("voice_hint", lang),
        "",
        get_translation("timezone_command", lang),
        get_translation("language_command", lang),
        "",
        get_translation("calendar_save", lang),
    ]

    return "\n".join(parts)
