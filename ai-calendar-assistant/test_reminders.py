#!/usr/bin/env python3
"""Test daily reminders system."""

import sys
sys.path.insert(0, '/app')

import asyncio
from datetime import datetime
import pytz
from app.services.translations import get_translation, Language
from app.services.user_preferences import UserPreferencesService
from app.services.calendar_radicale import calendar_service

# Initialize preferences service
prefs = UserPreferencesService(data_file="/tmp/test_user_preferences.json")

# Test user
test_user_id = "test_123"

# Set language to Russian
prefs.set_language(test_user_id, Language.RUSSIAN)
prefs.set_timezone(test_user_id, "Europe/Moscow")

async def test_morning_reminder():
    """Test morning reminder message construction."""
    print("=== Testing Morning Reminder ===\n")

    lang = prefs.get_language(test_user_id)
    user_tz_str = prefs.get_timezone(test_user_id)
    user_tz = pytz.timezone(user_tz_str)

    # Get current date in user's timezone
    now_user_tz = datetime.now(user_tz)
    today = now_user_tz.date()

    print(f"User timezone: {user_tz_str}")
    print(f"Current time: {now_user_tz}")
    print(f"Today's date: {today}\n")

    # Test with no events
    print("--- Test 1: No events ---")
    greeting = get_translation("morning_greeting", lang)
    no_events = get_translation("no_events_today", lang)
    message = f"{greeting}\n\n{no_events}"
    print(message)
    print()

    # Test with events
    print("--- Test 2: With events ---")
    mock_events = [
        {'start': now_user_tz.replace(hour=10, minute=0), 'title': 'Meeting with team'},
        {'start': now_user_tz.replace(hour=14, minute=30), 'title': 'Client call'},
        {'start': now_user_tz.replace(hour=16, minute=0), 'title': 'Project review'},
    ]

    events_list = "\n".join([
        f"• {e['start'].strftime('%H:%M')} - {e['title']}"
        for e in sorted(mock_events, key=lambda x: x['start'])
    ])
    events_header = get_translation("your_events_today", lang)
    successful_day = get_translation("successful_day", lang)
    message = f"{greeting}\n\n{events_header}\n\n{events_list}\n\n{successful_day}"
    print(message)
    print()

async def test_evening_reminder():
    """Test evening reminder message construction."""
    print("\n=== Testing Evening Reminder ===\n")

    lang = prefs.get_language(test_user_id)
    user_tz_str = prefs.get_timezone(test_user_id)
    user_tz = pytz.timezone(user_tz_str)

    # Get current date in user's timezone
    now_user_tz = datetime.now(user_tz)

    print(f"User timezone: {user_tz_str}")
    print(f"Current time: {now_user_tz}\n")

    # Test all 5 evening messages
    message_keys = [
        "evening_message_1",
        "evening_message_2",
        "evening_message_3",
        "evening_message_4",
        "evening_message_5",
    ]

    for i, key in enumerate(message_keys, 1):
        print(f"--- Evening Message {i} ---")
        base_message = get_translation(key, lang)

        # Test with events
        events_count = 3
        stats = "\n\n" + get_translation("events_count_today", lang, count=events_count)
        rest_message = get_translation("rest_well", lang)
        message = base_message + stats + f"\n\n{rest_message}"

        print(message)
        print()

async def test_all_languages():
    """Test translations in all languages."""
    print("\n=== Testing All Languages ===\n")

    for lang in [Language.RUSSIAN, Language.ENGLISH, Language.SPANISH, Language.ARABIC]:
        print(f"--- {lang.value.upper()} ---")
        greeting = get_translation("morning_greeting", lang)
        no_events = get_translation("no_events_today", lang)
        print(f"{greeting}\n{no_events}\n")

async def main():
    await test_morning_reminder()
    await test_evening_reminder()
    await test_all_languages()
    print("✅ All reminder tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
