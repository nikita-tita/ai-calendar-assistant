"""Analytics service for tracking user actions."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict
from collections import defaultdict
import json
import structlog
from pathlib import Path

from app.models.analytics import (
    UserAction, ActionType, UserStats, DashboardStats,
    TimeSeriesPoint, UserActivityTimeline, EventTypeDistribution,
    AdminDashboardStats, UserDetail, UserDialogEntry
)

logger = structlog.get_logger()


class AnalyticsService:
    """Service for tracking and analyzing user actions."""

    def __init__(self, data_file: str = "/var/lib/calendar-bot/analytics_data.json"):
        """Initialize analytics service with JSON file storage."""
        self.data_file = Path(data_file)
        self.actions: List[UserAction] = []
        self._load_data()

    def _load_data(self):
        """Load analytics data from JSON file."""
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.actions = [
                        UserAction(**action) for action in data.get('actions', [])
                    ]
                logger.info("analytics_data_loaded", count=len(self.actions))
            else:
                logger.info("analytics_data_file_not_found", creating_new=True)
                self._save_data()
        except Exception as e:
            logger.error("analytics_load_error", error=str(e), exc_info=True)
            self.actions = []

    def _save_data(self):
        """Save analytics data to JSON file."""
        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_file, 'w', encoding='utf-8') as f:
                data = {
                    'actions': [
                        {
                            'user_id': action.user_id,
                            'action_type': action.action_type,
                            'timestamp': action.timestamp.isoformat(),
                            'details': action.details,
                            'event_id': action.event_id,
                            'success': action.success,
                            'error_message': action.error_message,
                            'is_test': action.is_test,
                            'username': action.username,
                            'first_name': action.first_name,
                            'last_name': action.last_name
                        }
                        for action in self.actions
                    ]
                }
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("analytics_save_error", error=str(e), exc_info=True)

    def log_action(
        self,
        user_id: str,
        action_type: ActionType,
        details: Optional[str] = None,
        event_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ):
        """Log a user action."""
        action = UserAction(
            user_id=user_id,
            action_type=action_type,
            timestamp=datetime.now(),
            details=details,
            event_id=event_id,
            success=success,
            error_message=error_message,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        self.actions.append(action)
        self._save_data()

        logger.info(
            "action_logged",
            user_id=user_id,
            action_type=action_type,
            success=success
        )

    def get_dashboard_stats(self) -> DashboardStats:
        """Get overall dashboard statistics."""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)

        # Count unique users
        all_users = set(action.user_id for action in self.actions)
        users_today = set(
            action.user_id for action in self.actions
            if action.timestamp >= today_start
        )
        users_week = set(
            action.user_id for action in self.actions
            if action.timestamp >= week_start
        )

        # Count events
        event_actions = [
            a for a in self.actions
            if a.action_type in [ActionType.EVENT_CREATE, ActionType.EVENT_UPDATE, ActionType.EVENT_DELETE]
        ]
        events_today = len([
            a for a in event_actions
            if a.timestamp >= today_start
        ])
        events_week = len([
            a for a in event_actions
            if a.timestamp >= week_start
        ])

        # Count messages
        message_actions = [
            a for a in self.actions
            if a.action_type in [ActionType.TEXT_MESSAGE, ActionType.VOICE_MESSAGE]
        ]
        messages_today = len([
            a for a in message_actions
            if a.timestamp >= today_start
        ])

        # Count errors
        error_actions = [a for a in self.actions if not a.success or a.action_type == ActionType.ERROR]
        errors_today = len([
            a for a in error_actions
            if a.timestamp >= today_start
        ])

        return DashboardStats(
            total_users=len(all_users),
            active_users_today=len(users_today),
            active_users_week=len(users_week),
            total_events=len(event_actions),
            events_today=events_today,
            events_week=events_week,
            total_messages=len(message_actions),
            messages_today=messages_today,
            total_errors=len(error_actions),
            errors_today=errors_today
        )

    def get_user_stats(self, limit: int = 100) -> List[UserStats]:
        """Get statistics for all users."""
        user_data: Dict[str, Dict] = defaultdict(lambda: {
            'first_seen': None,
            'last_seen': None,
            'events': 0,
            'messages': 0,
            'voice': 0,
            'webapp': 0,
            'errors': 0,
            'username': None,
            'first_name': None,
            'last_name': None
        })

        for action in self.actions:
            data = user_data[action.user_id]

            # Update first/last seen
            if data['first_seen'] is None or action.timestamp < data['first_seen']:
                data['first_seen'] = action.timestamp
            if data['last_seen'] is None or action.timestamp > data['last_seen']:
                data['last_seen'] = action.timestamp

            # Update user info from most recent action with data
            if action.username and not data['username']:
                data['username'] = action.username
            if action.first_name and not data['first_name']:
                data['first_name'] = action.first_name
            if action.last_name and not data['last_name']:
                data['last_name'] = action.last_name

            # Count by type
            if action.action_type in [ActionType.EVENT_CREATE, ActionType.EVENT_UPDATE, ActionType.EVENT_DELETE]:
                data['events'] += 1
            elif action.action_type == ActionType.TEXT_MESSAGE:
                data['messages'] += 1
            elif action.action_type == ActionType.VOICE_MESSAGE:
                data['voice'] += 1
            elif action.action_type == ActionType.WEBAPP_OPEN:
                data['webapp'] += 1

            if not action.success:
                data['errors'] += 1

        # Convert to UserStats objects
        stats = [
            UserStats(
                user_id=user_id,
                first_seen=data['first_seen'],
                last_seen=data['last_seen'],
                total_events=data['events'],
                total_messages=data['messages'],
                total_voice_messages=data['voice'],
                total_webapp_opens=data['webapp'],
                total_errors=data['errors'],
                username=data['username'],
                first_name=data['first_name'],
                last_name=data['last_name']
            )
            for user_id, data in user_data.items()
        ]

        # Sort by last seen (most recent first)
        stats.sort(key=lambda x: x.last_seen, reverse=True)
        return stats[:limit]

    def get_activity_timeline(self, hours: int = 24) -> List[TimeSeriesPoint]:
        """Get activity timeline for the last N hours."""
        now = datetime.now()
        start_time = now - timedelta(hours=hours)

        # Group actions by hour
        hourly_counts = defaultdict(int)
        for action in self.actions:
            if action.timestamp >= start_time:
                hour_key = action.timestamp.replace(minute=0, second=0, microsecond=0)
                hourly_counts[hour_key] += 1

        # Create time series
        timeline = []
        current = start_time.replace(minute=0, second=0, microsecond=0)
        while current <= now:
            timeline.append(TimeSeriesPoint(
                timestamp=current,
                value=hourly_counts.get(current, 0)
            ))
            current += timedelta(hours=1)

        return timeline

    def get_action_distribution(self) -> List[EventTypeDistribution]:
        """Get distribution of action types."""
        type_counts = defaultdict(int)
        total = len(self.actions)

        for action in self.actions:
            type_counts[action.action_type] += 1

        distribution = [
            EventTypeDistribution(
                action_type=action_type,
                count=count,
                percentage=round(count / total * 100, 2) if total > 0 else 0
            )
            for action_type, count in type_counts.items()
        ]

        distribution.sort(key=lambda x: x.count, reverse=True)
        return distribution

    def get_recent_actions(self, limit: int = 100, user_id: Optional[str] = None) -> List[UserAction]:
        """Get recent actions, optionally filtered by user."""
        filtered = self.actions
        if user_id:
            filtered = [a for a in filtered if a.user_id == user_id]

        # Sort by timestamp (most recent first)
        filtered.sort(key=lambda x: x.timestamp, reverse=True)
        return filtered[:limit]

    def clear_test_data(self) -> int:
        """Remove all test/mock data. Returns number of removed actions."""
        original_count = len(self.actions)
        self.actions = [a for a in self.actions if not a.is_test]
        removed = original_count - len(self.actions)

        if removed > 0:
            self._save_data()
            logger.info("test_data_cleared", removed=removed, remaining=len(self.actions))

        return removed

    def get_admin_stats(self) -> AdminDashboardStats:
        """Get extended statistics for admin dashboard."""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())  # Monday of current week

        # Month start (first day of current month)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Total logins
        total_logins = len([a for a in self.actions if a.action_type == ActionType.USER_LOGIN])

        # Active users today (at least 1 action)
        users_today = set(
            a.user_id for a in self.actions
            if a.timestamp >= today_start
        )

        # Active users week (3+ active days)
        users_week_active = set()
        for user_id in set(a.user_id for a in self.actions):
            active_days = self._count_active_days(user_id, week_start, today_start + timedelta(days=1))
            if active_days >= 3:
                users_week_active.add(user_id)

        # Active users month (3+ days per week throughout month)
        users_month_active = set()
        for user_id in set(a.user_id for a in self.actions):
            # Count weeks in month
            weeks_in_month = self._count_weeks_in_month(month_start, now)
            active_weeks = 0

            current_week_start = month_start
            while current_week_start < now:
                week_end = min(current_week_start + timedelta(days=7), now)
                active_days = self._count_active_days(user_id, current_week_start, week_end)
                if active_days >= 3:
                    active_weeks += 1
                current_week_start = week_end

            # User is active if they have 3+ active days in most weeks
            if active_weeks >= max(1, weeks_in_month // 2):
                users_month_active.add(user_id)

        # Total stats
        all_users = set(a.user_id for a in self.actions)
        total_actions = len(self.actions)
        total_events = len([
            a for a in self.actions
            if a.action_type == ActionType.EVENT_CREATE
        ])
        total_messages = len([
            a for a in self.actions
            if a.action_type in [ActionType.TEXT_MESSAGE, ActionType.VOICE_MESSAGE]
        ])

        return AdminDashboardStats(
            total_logins=total_logins,
            active_users_today=len(users_today),
            active_users_week=len(users_week_active),
            active_users_month=len(users_month_active),
            total_users=len(all_users),
            total_actions=total_actions,
            total_events_created=total_events,
            total_messages=total_messages
        )

    def get_all_users_details(self) -> List[UserDetail]:
        """Get detailed information for all users."""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        all_users = set(a.user_id for a in self.actions)
        user_details = []

        for user_id in all_users:
            user_actions = [a for a in self.actions if a.user_id == user_id]

            # Get user info from most recent action
            latest_action = max(user_actions, key=lambda x: x.timestamp)
            username = latest_action.username
            first_name = latest_action.first_name
            last_name = latest_action.last_name

            # Telegram link
            telegram_link = f"https://t.me/{username}" if username else None

            # Time metrics
            first_seen = min(a.timestamp for a in user_actions)
            last_seen = max(a.timestamp for a in user_actions)

            # Login count
            total_logins = len([a for a in user_actions if a.action_type == ActionType.USER_LOGIN])
            total_actions = len(user_actions)

            # Period activity
            actions_today = len([a for a in user_actions if a.timestamp >= today_start])
            actions_week = len([a for a in user_actions if a.timestamp >= week_start])
            actions_month = len([a for a in user_actions if a.timestamp >= month_start])

            # Active days
            active_days_week = self._count_active_days(user_id, week_start, today_start + timedelta(days=1))
            active_days_month = self._count_active_days(user_id, month_start, now)

            # Activity status
            is_active_today = actions_today > 0
            is_active_week = active_days_week >= 3

            # For month: check 3+ days per week
            weeks_in_month = self._count_weeks_in_month(month_start, now)
            active_weeks_month = 0
            current_week_start = month_start
            while current_week_start < now:
                week_end = min(current_week_start + timedelta(days=7), now)
                if self._count_active_days(user_id, current_week_start, week_end) >= 3:
                    active_weeks_month += 1
                current_week_start = week_end
            is_active_month = active_weeks_month >= max(1, weeks_in_month // 2)

            user_details.append(UserDetail(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                telegram_link=telegram_link,
                first_seen=first_seen,
                last_seen=last_seen,
                total_logins=total_logins,
                total_actions=total_actions,
                actions_today=actions_today,
                actions_week=actions_week,
                actions_month=actions_month,
                active_days_week=active_days_week,
                active_days_month=active_days_month,
                is_active_today=is_active_today,
                is_active_week=is_active_week,
                is_active_month=is_active_month
            ))

        # Sort by last seen (most recent first)
        user_details.sort(key=lambda x: x.last_seen, reverse=True)
        return user_details

    def get_user_dialog(self, user_id: str, limit: int = 1000) -> List[UserDialogEntry]:
        """Get user's complete dialog history."""
        user_actions = [a for a in self.actions if a.user_id == user_id]

        # Sort by timestamp (oldest first for dialog view)
        user_actions.sort(key=lambda x: x.timestamp)

        dialog = [
            UserDialogEntry(
                timestamp=action.timestamp,
                action_type=action.action_type,
                details=action.details,
                success=action.success,
                error_message=action.error_message
            )
            for action in user_actions[-limit:]
        ]

        return dialog

    def _count_active_days(self, user_id: str, start: datetime, end: datetime) -> int:
        """Count how many distinct days user was active in given period."""
        user_actions = [
            a for a in self.actions
            if a.user_id == user_id and start <= a.timestamp < end
        ]

        # Get unique dates
        active_dates = set(
            a.timestamp.date() for a in user_actions
        )

        return len(active_dates)

    def _count_weeks_in_month(self, month_start: datetime, month_end: datetime) -> int:
        """Count number of weeks in given month period."""
        days = (month_end - month_start).days
        return max(1, days // 7)


# Global instance
analytics_service = AnalyticsService()
