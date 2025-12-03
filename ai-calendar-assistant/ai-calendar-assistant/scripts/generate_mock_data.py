"""Generate mock analytics data for admin panel demonstration."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
import random
from app.services.analytics_service import analytics_service
from app.models.analytics import ActionType

# Mock user IDs
USER_IDS = [
    "2296243",  # Real user
    "1234567",
    "2345678",
    "3456789",
    "4567890",
    "5678901",
    "6789012",
    "7890123",
]

# Action types with weights (probability)
ACTION_WEIGHTS = {
    ActionType.USER_START: 0.05,
    ActionType.TEXT_MESSAGE: 0.30,
    ActionType.VOICE_MESSAGE: 0.10,
    ActionType.EVENT_CREATE: 0.20,
    ActionType.EVENT_UPDATE: 0.10,
    ActionType.EVENT_DELETE: 0.05,
    ActionType.EVENT_QUERY: 0.15,
    ActionType.ERROR: 0.05,
}

# Event titles for mock data
EVENT_TITLES = [
    "Показ квартиры на Ленина",
    "Встреча с клиентом Ивановым",
    "Звонок Петрову",
    "Сделка у нотариуса",
    "Встреча в банке",
    "Осмотр объекта",
    "Подписание договора",
    "Консультация по ипотеке",
    "Оценка недвижимости",
    "Встреча с застройщиком",
]

# Text messages for mock data
TEXT_MESSAGES = [
    "Какие планы на сегодня?",
    "Покажи события на завтра",
    "Что у меня на неделе?",
    "Создай встречу завтра в 10:00",
    "Перенеси встречу на 15:00",
    "Отмени показ",
]


def generate_mock_data(days_back: int = 7, actions_per_day: int = 50):
    """
    Generate mock analytics data.

    Args:
        days_back: Number of days to generate data for
        actions_per_day: Average number of actions per day
    """
    print(f"Generating mock data for last {days_back} days...")
    print(f"Target: ~{actions_per_day} actions per day\n")

    now = datetime.now()
    total_actions = 0

    # Generate data for each day
    for day_offset in range(days_back, -1, -1):
        day_start = now - timedelta(days=day_offset)
        day_start = day_start.replace(hour=8, minute=0, second=0, microsecond=0)

        # Random number of actions for this day (80-120% of target)
        num_actions = random.randint(
            int(actions_per_day * 0.8),
            int(actions_per_day * 1.2)
        )

        print(f"Day -{day_offset}: Generating {num_actions} actions...")

        for _ in range(num_actions):
            # Random user
            user_id = random.choice(USER_IDS)

            # Random action type based on weights
            action_type = random.choices(
                list(ACTION_WEIGHTS.keys()),
                weights=list(ACTION_WEIGHTS.values()),
                k=1
            )[0]

            # Random time during business hours (8-20)
            hour = random.randint(8, 20)
            minute = random.randint(0, 59)
            timestamp = day_start.replace(hour=hour, minute=minute)

            # Generate details based on action type
            details = None
            event_id = None

            if action_type == ActionType.USER_START:
                details = f"User {user_id} started bot"
            elif action_type == ActionType.TEXT_MESSAGE:
                details = random.choice(TEXT_MESSAGES)
            elif action_type == ActionType.VOICE_MESSAGE:
                details = f"Transcribed: {random.choice(TEXT_MESSAGES)}"
            elif action_type == ActionType.EVENT_CREATE:
                event_title = random.choice(EVENT_TITLES)
                event_id = f"mock-{random.randint(1000, 9999)}"
                details = f"Created: {event_title}"
            elif action_type == ActionType.EVENT_UPDATE:
                event_id = f"mock-{random.randint(1000, 9999)}"
                details = f"Updated event: {event_id}"
            elif action_type == ActionType.EVENT_DELETE:
                event_id = f"mock-{random.randint(1000, 9999)}"
                details = f"Deleted event: {event_id}"
            elif action_type == ActionType.EVENT_QUERY:
                num_found = random.randint(0, 10)
                details = f"Queried events: {num_found} found"
            elif action_type == ActionType.ERROR:
                errors = [
                    "Calendar service unavailable",
                    "Failed to parse datetime",
                    "LLM API timeout",
                    "Invalid event data"
                ]
                details = random.choice(errors)

            # Create action directly with custom timestamp and TEST flag
            from app.models.analytics import UserAction
            action = UserAction(
                user_id=user_id,
                action_type=action_type,
                timestamp=timestamp,
                details=details,
                event_id=event_id,
                is_test=True  # Mark as test data
            )
            analytics_service.actions.append(action)

            total_actions += 1

    # Save all data at once
    analytics_service._save_data()

    print(f"\n✅ Generated {total_actions} mock actions")
    print(f"📊 Data saved to: {analytics_service.data_file}")

    # Show statistics
    stats = analytics_service.get_dashboard_stats()
    print(f"\n📈 Dashboard Statistics:")
    print(f"  Total Users: {stats.total_users}")
    print(f"  Total Events: {stats.total_events}")
    print(f"  Total Messages: {stats.total_messages}")
    print(f"  Total Errors: {stats.errors_today}")


if __name__ == "__main__":
    # Generate data for last 7 days with ~50 actions per day
    generate_mock_data(days_back=7, actions_per_day=50)
