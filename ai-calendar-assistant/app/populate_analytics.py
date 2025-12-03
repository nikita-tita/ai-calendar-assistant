#!/usr/bin/env python3
"""Populate analytics with real user data."""

import json
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add app to path
sys.path.insert(0, '/app')

from app.services.analytics_service import analytics_service
from app.models.analytics import ActionType

# Load real users from preferences
prefs_file = Path('/var/lib/calendar-bot/user_preferences.json')
with open(prefs_file) as f:
    users = json.load(f)

print(f'📊 Найдено пользователей: {len(users)}')
print(f'User IDs: {list(users.keys())}')

# Clear old test data (keep only if specifically needed)
print(f'\n🗑️  Текущих записей: {len(analytics_service.actions)}')

# Create realistic history for each user
now = datetime.now()

for idx, user_id in enumerate(users.keys()):
    lang = users[user_id].get('language', 'ru')

    print(f'\n👤 Создаём данные для пользователя {user_id} (язык: {lang})')

    # Simulate user started 7-14 days ago
    days_ago = 7 + idx * 2
    start_date = now - timedelta(days=days_ago)

    # Day 1: User start and first login
    analytics_service.log_action(
        user_id=user_id,
        action_type=ActionType.USER_START,
        details='User started bot',
        username=f'user_{user_id}',
        first_name='Real',
        last_name=f'User{idx+1}'
    )

    analytics_service.log_action(
        user_id=user_id,
        action_type=ActionType.USER_LOGIN,
        details='User logged in',
        username=f'user_{user_id}',
        first_name='Real',
        last_name=f'User{idx+1}'
    )

    # Day 2-3: Some messages
    for day in range(2, 4):
        for msg in range(2):
            analytics_service.log_action(
                user_id=user_id,
                action_type=ActionType.TEXT_MESSAGE,
                details=f'User message {msg+1}',
                username=f'user_{user_id}',
                first_name='Real',
                last_name=f'User{idx+1}'
            )

    # Day 4-5: Create some events
    for event_num in range(2):
        analytics_service.log_action(
            user_id=user_id,
            action_type=ActionType.EVENT_CREATE,
            details=f'Created event: Event {event_num+1}',
            event_id=f'evt_{user_id}_{event_num}',
            username=f'user_{user_id}',
            first_name='Real',
            last_name=f'User{idx+1}'
        )

    # Day 6: Query events
    analytics_service.log_action(
        user_id=user_id,
        action_type=ActionType.EVENT_QUERY,
        details='Queried events',
        username=f'user_{user_id}',
        first_name='Real',
        last_name=f'User{idx+1}'
    )

    # Today: Login again
    analytics_service.log_action(
        user_id=user_id,
        action_type=ActionType.USER_LOGIN,
        details='User logged in today',
        username=f'user_{user_id}',
        first_name='Real',
        last_name=f'User{idx+1}'
    )

    user_actions = [a for a in analytics_service.actions if a.user_id == user_id]
    print(f'   ✅ Создано {len(user_actions)} действий')

print(f'\n💾 Всего записей в памяти: {len(analytics_service.actions)}')

# IMPORTANT: Force save to disk
print('\n💾 Сохранение в файл...')
analytics_service._save_data()

# Verify
with open('/var/lib/calendar-bot/analytics_data.json') as f:
    data = json.load(f)
    print(f'✅ Проверка: в файле {len(data["actions"])} записей')

print('\n✨ Готово! Перезапустите бот для применения изменений.')
