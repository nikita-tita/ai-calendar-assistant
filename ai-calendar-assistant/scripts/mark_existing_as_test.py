"""Mark all existing analytics data as test data."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.analytics_service import analytics_service

def mark_all_as_test():
    """Mark all existing actions as test data."""
    print("🏷️  Помечаю все существующие данные как тестовые...")

    before_test = sum(1 for a in analytics_service.actions if a.is_test)

    # Mark all as test
    for action in analytics_service.actions:
        action.is_test = True

    # Save
    analytics_service._save_data()

    after_test = sum(1 for a in analytics_service.actions if a.is_test)

    print(f"\n✅ Готово!")
    print(f"  Всего записей: {len(analytics_service.actions)}")
    print(f"  Было тестовых: {before_test}")
    print(f"  Стало тестовых: {after_test}")
    print(f"  Помечено: {after_test - before_test}")


if __name__ == "__main__":
    mark_all_as_test()
