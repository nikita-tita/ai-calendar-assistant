"""Mark mock user IDs as test data."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.analytics_service import analytics_service

# Mock user IDs from generate_mock_data.py
MOCK_USER_IDS = [
    "1234567",
    "2345678",
    "3456789",
    "4567890",
    "5678901",
    "6789012",
    "7890123",
]

def mark_mock_users():
    """Mark all actions from mock users as test data."""
    print("🏷️  Помечаю моковых пользователей как тестовых...")

    marked = 0
    for action in analytics_service.actions:
        if action.user_id in MOCK_USER_IDS:
            if not action.is_test:
                action.is_test = True
                marked += 1

    # Save
    analytics_service._save_data()

    print(f"\n✅ Готово!")
    print(f"  Всего записей: {len(analytics_service.actions)}")
    print(f"  Помечено моковых: {marked}")
    print(f"  Всего тестовых: {sum(1 for a in analytics_service.actions if a.is_test)}")
    print(f"\n📋 Моковые пользователи:")
    for user_id in MOCK_USER_IDS:
        count = sum(1 for a in analytics_service.actions if a.user_id == user_id)
        print(f"  {user_id}: {count} действий")


if __name__ == "__main__":
    mark_mock_users()
