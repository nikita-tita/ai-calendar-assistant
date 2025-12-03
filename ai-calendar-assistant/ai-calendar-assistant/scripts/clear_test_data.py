"""Clear all test/mock data from analytics."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.analytics_service import analytics_service

def clear_test_data():
    """Remove all test data from analytics."""
    print("🧹 Очистка тестовых данных...")

    before = len(analytics_service.actions)
    removed = analytics_service.clear_test_data()
    after = len(analytics_service.actions)

    print(f"\n✅ Готово!")
    print(f"  Было записей: {before}")
    print(f"  Удалено тестовых: {removed}")
    print(f"  Осталось реальных: {after}")

    if removed == 0:
        print("\n💡 Тестовых данных не найдено")


if __name__ == "__main__":
    clear_test_data()
