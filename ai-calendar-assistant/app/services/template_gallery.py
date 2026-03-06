"""Template gallery for real estate agents.

Two galleries:
1. Client text templates (copy-paste to WhatsApp/Telegram)
2. Event templates (quick event creation with guided prompts)
"""

import re
from typing import Optional, Dict, List, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import structlog

logger = structlog.get_logger()

# ==================== Client Text Templates ====================

CLIENT_TEMPLATES = {
    "showing_confirm": {
        "title": "📍 Подтверждение показа",
        "fields": ["client_name", "address", "date", "time"],
        "text": (
            "Здравствуйте, {client_name}!\n"
            "Подтверждаю показ квартиры по адресу: {address}\n"
            "{date} в {time}\n"
            "Жду вас! Если что-то изменится — напишите заранее."
        ),
    },
    "showing_followup": {
        "title": "📞 После показа",
        "fields": ["client_name"],
        "text": (
            "Здравствуйте, {client_name}!\n"
            "Спасибо, что нашли время на просмотр. Как впечатления?\n"
            "Готов ответить на любые вопросы."
        ),
    },
    "doc_reminder": {
        "title": "📋 Документы",
        "fields": ["client_name", "doc_list"],
        "text": (
            "Здравствуйте, {client_name}!\n"
            "Напоминаю о необходимых документах:\n{doc_list}\n"
            "Если есть вопросы по сбору — звоните."
        ),
    },
    "meeting_reminder": {
        "title": "📅 Напоминание о встрече",
        "fields": ["client_name", "date", "time", "address"],
        "text": (
            "{client_name}, напоминаю о нашей встрече {date} в {time}.\n"
            "Адрес: {address}\n"
            "До встречи!"
        ),
    },
    "thank_you": {
        "title": "🎉 Благодарность за сделку",
        "fields": ["client_name"],
        "text": (
            "{client_name}, поздравляю с покупкой!\n"
            "Было приятно работать с вами. По любым вопросам — на связи.\n"
            "Удачного новоселья! 🏠"
        ),
    },
}

# ==================== Event Templates ====================

EVENT_TEMPLATES = {
    "showing": {
        "title": "🏠 Показ квартиры",
        "prompts": ["Адрес квартиры?", "Имя клиента?", "Время? (напр. завтра в 14:00)"],
        "field_names": ["address", "client_name", "time_text"],
        "event_type": "showing",
    },
    "client_call": {
        "title": "📞 Звонок клиенту",
        "prompts": ["Кому звонить?", "Время? (напр. сегодня в 10:00)", "Тема звонка?"],
        "field_names": ["client_name", "time_text", "topic"],
        "event_type": "client_call",
    },
    "doc_signing": {
        "title": "📝 Подписание документов",
        "prompts": ["Адрес/место?", "Стороны сделки?", "Время?"],
        "field_names": ["address", "parties", "time_text"],
        "event_type": "doc_signing",
    },
    "dev_meeting": {
        "title": "🏗 Встреча с застройщиком",
        "prompts": ["Застройщик/ЖК?", "Время?", "Тема?"],
        "field_names": ["developer", "time_text", "topic"],
        "event_type": "dev_meeting",
    },
}


def get_templates_keyboard() -> InlineKeyboardMarkup:
    """Main templates menu: choose between client texts and event templates."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✉️ Тексты для клиентов", callback_data="template:client_menu"),
            InlineKeyboardButton("📅 Создать событие", callback_data="template:event_menu"),
        ],
    ])


def get_client_templates_keyboard() -> InlineKeyboardMarkup:
    """Gallery of client text templates."""
    buttons = []
    row = []
    for tpl_id, tpl in CLIENT_TEMPLATES.items():
        row.append(InlineKeyboardButton(tpl["title"], callback_data=f"template:client:{tpl_id}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="template:back")])
    return InlineKeyboardMarkup(buttons)


def get_event_templates_keyboard() -> InlineKeyboardMarkup:
    """Gallery of event creation templates."""
    buttons = []
    for tpl_id, tpl in EVENT_TEMPLATES.items():
        buttons.append([InlineKeyboardButton(tpl["title"], callback_data=f"template:event:{tpl_id}")])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="template:back")])
    return InlineKeyboardMarkup(buttons)


def render_client_template(template_id: str, fields: Dict[str, str]) -> Optional[str]:
    """Render a client text template with provided fields."""
    tpl = CLIENT_TEMPLATES.get(template_id)
    if not tpl:
        return None

    text = tpl["text"]
    for field_name in tpl["fields"]:
        value = fields.get(field_name, f"[{field_name}]")
        text = text.replace(f"{{{field_name}}}", value)
    return text


def get_template_fields(template_id: str) -> Optional[List[str]]:
    """Get required fields for a client template."""
    tpl = CLIENT_TEMPLATES.get(template_id)
    return tpl["fields"] if tpl else None


def get_event_template(template_id: str) -> Optional[Dict]:
    """Get event template by ID."""
    return EVENT_TEMPLATES.get(template_id)


# Field labels for user prompts
_FIELD_LABELS = {
    "client_name": "Имя клиента",
    "address": "Адрес",
    "date": "Дата",
    "time": "Время",
    "doc_list": "Список документов",
    "topic": "Тема",
    "parties": "Стороны",
    "developer": "Застройщик/ЖК",
    "time_text": "Время",
}


def get_field_prompt(field_name: str) -> str:
    """Get human-readable prompt for a field."""
    return _FIELD_LABELS.get(field_name, field_name)


def extract_fields_from_text(text: str, field_names: List[str]) -> Dict[str, str]:
    """Try to extract multiple fields from a single text message (voice or typed).

    Heuristic: if user sends all info at once, try to parse it.
    E.g. "Иванов, Пионерская 12, завтра в 14:00" for showing template.
    """
    fields = {}

    # Try to extract client name (first capitalized word or phrase before comma)
    if "client_name" in field_names:
        name_match = re.match(r'^([А-ЯЁA-Z][а-яёa-z]+(?:\s+[А-ЯЁA-Z][а-яёa-z]+)?)', text)
        if name_match:
            fields["client_name"] = name_match.group(1)

    # Try to extract address (street patterns)
    if "address" in field_names:
        addr_match = re.search(
            r'(?:ул\.?\s*|улица\s+|пр\.?\s*|проспект\s+|пер\.?\s*|переулок\s+|наб\.?\s*|набережная\s+)'
            r'[А-ЯЁа-яё\s]+\d*',
            text, re.IGNORECASE
        )
        if addr_match:
            fields["address"] = addr_match.group(0).strip()

    # Try to extract time references
    if "time_text" in field_names or "time" in field_names:
        time_match = re.search(
            r'(?:сегодня|завтра|послезавтра|понедельник|вторник|среда|четверг|пятница|суббота|воскресенье)'
            r'(?:\s+в\s+\d{1,2}[:.]\d{2})?'
            r'|в\s+\d{1,2}[:.]\d{2}',
            text, re.IGNORECASE
        )
        if time_match:
            key = "time_text" if "time_text" in field_names else "time"
            fields[key] = time_match.group(0).strip()

    return fields
