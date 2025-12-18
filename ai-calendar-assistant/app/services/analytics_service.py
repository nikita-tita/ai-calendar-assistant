"""Analytics service with SQLite storage for reliable multi-process access."""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from collections import defaultdict
from pathlib import Path
import structlog

from app.models.analytics import (
    UserAction, ActionType, UserStats, DashboardStats,
    TimeSeriesPoint, UserActivityTimeline, EventTypeDistribution,
    AdminDashboardStats, UserDetail, UserDialogEntry
)
from app.utils.pii_masking import safe_log_params
from app.services.encrypted_storage import EncryptedStorage
from app.utils.test_detection import is_test_user

logger = structlog.get_logger()


class AnalyticsService:
    """
    Analytics service with SQLite storage.

    Benefits over JSON storage:
    - Atomic writes - no data loss on crash
    - Multi-process safe - both uvicorn and polling bot can write
    - No flush needed - writes are immediate
    - Efficient queries - SQL instead of list iteration
    """

    def __init__(self, db_path: str = "/var/lib/calendar-bot/analytics.db"):
        """Initialize analytics service with SQLite database."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        self._migrate_encrypted_actions()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with WAL mode for better concurrency."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def _init_database(self):
        """Initialize SQLite database schema."""
        conn = self._get_connection()
        try:
            # Users table - single source of truth
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    chat_id INTEGER NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    is_hidden_in_admin INTEGER DEFAULT 0
                )
            ''')

            # Migration: add is_hidden_in_admin column if missing
            cursor = conn.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'is_hidden_in_admin' not in columns:
                conn.execute('ALTER TABLE users ADD COLUMN is_hidden_in_admin INTEGER DEFAULT 0')
                logger.info("migration_added_is_hidden_in_admin_column")

            # Actions table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    details TEXT,
                    event_id TEXT,
                    success INTEGER DEFAULT 1,
                    error_message TEXT,
                    is_test INTEGER DEFAULT 0,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    total_tokens INTEGER,
                    cost_rub REAL,
                    llm_model TEXT
                )
            ''')

            # Indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_actions_user_timestamp ON actions(user_id, timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_actions_timestamp ON actions(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_actions_type ON actions(action_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_actions_success ON actions(success)')

            conn.commit()
            logger.info("analytics_database_initialized", db_path=str(self.db_path))
        except Exception as e:
            logger.error("analytics_database_init_error", error=str(e), exc_info=True)
            raise
        finally:
            conn.close()

    def _migrate_encrypted_actions(self):
        """
        One-time migration of historical actions from encrypted JSON to SQLite.

        Checks if analytics_data.json.enc exists and has more actions than SQLite.
        If so, migrates all actions and renames the file to .migrated.
        """
        encrypted_file = self.db_path.parent / "analytics_data.json.enc"
        if not encrypted_file.exists():
            return

        try:
            # Check current SQLite actions count
            conn = self._get_connection()
            sqlite_count = conn.execute('SELECT COUNT(*) FROM actions').fetchone()[0]
            conn.close()

            # Load encrypted data
            storage = EncryptedStorage(str(self.db_path.parent))
            json_data = storage.load("analytics_data.json")

            if not json_data or 'actions' not in json_data:
                logger.info("encrypted_actions_migration_skipped", reason="no_actions_in_json")
                return

            json_actions = json_data['actions']
            json_count = len(json_actions)

            # Skip if SQLite already has more or equal actions
            if sqlite_count >= json_count:
                logger.info("encrypted_actions_migration_skipped",
                           reason="sqlite_has_enough",
                           sqlite=sqlite_count, json=json_count)
                return

            logger.info("encrypted_actions_migration_starting",
                       sqlite_count=sqlite_count, json_count=json_count)

            # Migrate actions
            conn = self._get_connection()
            migrated = 0

            for action in json_actions:
                try:
                    conn.execute('''
                        INSERT INTO actions
                        (user_id, action_type, timestamp, details, event_id, success,
                         error_message, is_test, input_tokens, output_tokens, total_tokens,
                         cost_rub, llm_model)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        action.get('user_id'),
                        action.get('action_type'),
                        action.get('timestamp'),
                        action.get('details'),
                        action.get('event_id'),
                        1 if action.get('success', True) else 0,
                        action.get('error_message'),
                        1 if action.get('is_test', False) else 0,
                        action.get('input_tokens'),
                        action.get('output_tokens'),
                        action.get('total_tokens'),
                        action.get('cost_rub'),
                        action.get('llm_model')
                    ))

                    # Also update user info if present
                    user_id = action.get('user_id')
                    if user_id and any([action.get('username'), action.get('first_name'), action.get('last_name')]):
                        conn.execute('''
                            UPDATE users SET
                                username = COALESCE(?, username),
                                first_name = COALESCE(?, first_name),
                                last_name = COALESCE(?, last_name)
                            WHERE user_id = ?
                        ''', (
                            action.get('username'),
                            action.get('first_name'),
                            action.get('last_name'),
                            user_id
                        ))

                    migrated += 1
                except Exception as e:
                    logger.warning("action_migration_error",
                                  action_type=action.get('action_type'),
                                  error=str(e))

            conn.commit()
            conn.close()

            # Rename encrypted file to .migrated
            migrated_path = encrypted_file.with_suffix('.enc.migrated')
            encrypted_file.rename(migrated_path)

            logger.info("encrypted_actions_migration_completed",
                       migrated=migrated,
                       backup_path=str(migrated_path))

        except Exception as e:
            logger.error("encrypted_actions_migration_error", error=str(e), exc_info=True)

    def ensure_user(
        self,
        user_id: str,
        chat_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ):
        """
        Ensure user exists in database (upsert).

        Used by DailyRemindersService for registration.
        """
        conn = self._get_connection()
        try:
            now = datetime.now().isoformat()
            conn.execute('''
                INSERT INTO users (user_id, chat_id, username, first_name, last_name, first_seen, last_seen, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(user_id) DO UPDATE SET
                    chat_id = excluded.chat_id,
                    username = COALESCE(excluded.username, users.username),
                    first_name = COALESCE(excluded.first_name, users.first_name),
                    last_name = COALESCE(excluded.last_name, users.last_name),
                    last_seen = excluded.last_seen,
                    is_active = 1
            ''', (user_id, chat_id, username, first_name, last_name, now, now))
            conn.commit()
        except Exception as e:
            logger.error("ensure_user_error", user_id=user_id, error=str(e))
        finally:
            conn.close()

    def deactivate_user(self, user_id: str):
        """Mark user as inactive (e.g., blocked bot)."""
        conn = self._get_connection()
        try:
            conn.execute('UPDATE users SET is_active = 0 WHERE user_id = ?', (user_id,))
            conn.commit()
            logger.info("user_deactivated", user_id=user_id)
        except Exception as e:
            logger.error("deactivate_user_error", user_id=user_id, error=str(e))
        finally:
            conn.close()

    def get_active_users(self) -> Dict[str, int]:
        """Get active users for reminders. Returns {user_id: chat_id}."""
        conn = self._get_connection()
        try:
            cursor = conn.execute('SELECT user_id, chat_id FROM users WHERE is_active = 1')
            return {row['user_id']: row['chat_id'] for row in cursor.fetchall()}
        except Exception as e:
            logger.error("get_active_users_error", error=str(e))
            return {}
        finally:
            conn.close()

    def toggle_user_hidden(self, user_id: str) -> bool:
        """
        Toggle user's hidden status in admin dashboard.

        Returns new is_hidden value (True if now hidden, False if now visible).
        """
        conn = self._get_connection()
        try:
            # Get current value
            cursor = conn.execute(
                'SELECT is_hidden_in_admin FROM users WHERE user_id = ?',
                (user_id,)
            )
            row = cursor.fetchone()
            if not row:
                logger.warning("toggle_user_hidden_not_found", user_id=user_id)
                return False

            # Toggle value
            new_value = 0 if row['is_hidden_in_admin'] else 1
            conn.execute(
                'UPDATE users SET is_hidden_in_admin = ? WHERE user_id = ?',
                (new_value, user_id)
            )
            conn.commit()
            logger.info("user_hidden_toggled", user_id=user_id, is_hidden=bool(new_value))
            return bool(new_value)
        except Exception as e:
            logger.error("toggle_user_hidden_error", user_id=user_id, error=str(e))
            return False
        finally:
            conn.close()

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
        last_name: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        cost_rub: Optional[float] = None,
        llm_model: Optional[str] = None,
        is_test: Optional[bool] = None
    ):
        """
        Log a user action. Writes directly to SQLite (atomic).
        
        Args:
            user_id: User ID
            action_type: Type of action
            details: Action details
            event_id: Related event ID (if applicable)
            success: Whether action was successful
            error_message: Error message (if applicable)
            username: Telegram username
            first_name: User first name
            last_name: User last name
            input_tokens: LLM input tokens (for cost tracking)
            output_tokens: LLM output tokens (for cost tracking)
            total_tokens: LLM total tokens (for cost tracking)
            cost_rub: LLM cost in rubles (for cost tracking)
            llm_model: LLM model used
            is_test: Whether this is test data. If None, auto-detected via is_test_user()
        """
        conn = self._get_connection()
        try:
            now = datetime.now().isoformat()

            # Convert ActionType enum to string
            action_type_str = action_type.value if isinstance(action_type, ActionType) else str(action_type)

            # Auto-detect test users if not explicitly specified
            if is_test is None:
                is_test = is_test_user(user_id, username)

            conn.execute('''
                INSERT INTO actions
                (user_id, action_type, timestamp, details, event_id, success,
                 error_message, is_test, input_tokens, output_tokens, total_tokens, cost_rub, llm_model)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, action_type_str, now, details, event_id,
                  1 if success else 0, error_message,
                  1 if is_test else 0,
                  input_tokens, output_tokens, total_tokens, cost_rub, llm_model))

            # Update user info if provided
            if username or first_name or last_name:
                conn.execute('''
                    UPDATE users SET
                        username = COALESCE(?, username),
                        first_name = COALESCE(?, first_name),
                        last_name = COALESCE(?, last_name),
                        last_seen = ?
                    WHERE user_id = ?
                ''', (username, first_name, last_name, now, user_id))
            else:
                conn.execute('UPDATE users SET last_seen = ? WHERE user_id = ?', (now, user_id))

            conn.commit()

            logger.info(
                "action_logged",
                **safe_log_params(user_id=user_id, details=details),
                action_type=action_type_str,
                success=success
            )
        except Exception as e:
            logger.error("log_action_error", user_id=user_id, error=str(e))
        finally:
            conn.close()

    def flush(self):
        """No-op for SQLite (writes are immediate). Kept for API compatibility."""
        pass

    def get_dashboard_stats(self) -> DashboardStats:
        """Get overall dashboard statistics (excluding test data)."""
        conn = self._get_connection()
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            week_start = (datetime.now() - timedelta(days=7)).isoformat()

            # Total users (from users table - single source of truth, excluding test users)
            # We count distinct user_ids from actions that are not test data
            total_users = conn.execute(
                'SELECT COUNT(DISTINCT user_id) FROM actions WHERE is_test = 0'
            ).fetchone()[0]

            # Active users today
            active_today = conn.execute(
                'SELECT COUNT(DISTINCT user_id) FROM actions WHERE timestamp >= ? AND is_test = 0',
                (today_start,)
            ).fetchone()[0]

            # Active users this week
            active_week = conn.execute(
                'SELECT COUNT(DISTINCT user_id) FROM actions WHERE timestamp >= ? AND is_test = 0',
                (week_start,)
            ).fetchone()[0]

            # Events
            event_types = "('event_create', 'event_update', 'event_delete')"
            total_events = conn.execute(
                f'SELECT COUNT(*) FROM actions WHERE action_type IN {event_types} AND is_test = 0'
            ).fetchone()[0]
            events_today = conn.execute(
                f'SELECT COUNT(*) FROM actions WHERE action_type IN {event_types} AND timestamp >= ? AND is_test = 0',
                (today_start,)
            ).fetchone()[0]
            events_week = conn.execute(
                f'SELECT COUNT(*) FROM actions WHERE action_type IN {event_types} AND timestamp >= ? AND is_test = 0',
                (week_start,)
            ).fetchone()[0]

            # Messages
            msg_types = "('text_message', 'voice_message')"
            total_messages = conn.execute(
                f'SELECT COUNT(*) FROM actions WHERE action_type IN {msg_types} AND is_test = 0'
            ).fetchone()[0]
            messages_today = conn.execute(
                f'SELECT COUNT(*) FROM actions WHERE action_type IN {msg_types} AND timestamp >= ? AND is_test = 0',
                (today_start,)
            ).fetchone()[0]

            # Errors
            total_errors = conn.execute('SELECT COUNT(*) FROM actions WHERE success = 0 AND is_test = 0').fetchone()[0]
            errors_today = conn.execute(
                'SELECT COUNT(*) FROM actions WHERE success = 0 AND timestamp >= ? AND is_test = 0',
                (today_start,)
            ).fetchone()[0]

            return DashboardStats(
                total_users=total_users,
                active_users_today=active_today,
                active_users_week=active_week,
                total_events=total_events,
                events_today=events_today,
                events_week=events_week,
                total_messages=total_messages,
                messages_today=messages_today,
                total_errors=total_errors,
                errors_today=errors_today
            )
        except Exception as e:
            logger.error("get_dashboard_stats_error", error=str(e))
            return DashboardStats(
                total_users=0, active_users_today=0, active_users_week=0,
                total_events=0, events_today=0, events_week=0,
                total_messages=0, messages_today=0,
                total_errors=0, errors_today=0
            )
        finally:
            conn.close()

    def get_admin_stats(self) -> AdminDashboardStats:
        """Get extended statistics for admin dashboard (excluding test data)."""
        conn = self._get_connection()
        try:
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            week_start = (now - timedelta(days=7)).isoformat()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

            # Total logins
            total_logins = conn.execute(
                "SELECT COUNT(*) FROM actions WHERE action_type = 'user_login' AND is_test = 0"
            ).fetchone()[0]

            # Active users today
            active_today = conn.execute(
                'SELECT COUNT(DISTINCT user_id) FROM actions WHERE timestamp >= ? AND is_test = 0',
                (today_start,)
            ).fetchone()[0]

            # Active users week (3+ days)
            cursor = conn.execute('''
                SELECT user_id, COUNT(DISTINCT date(timestamp)) as active_days
                FROM actions WHERE timestamp >= ? AND is_test = 0
                GROUP BY user_id HAVING active_days >= 3
            ''', (week_start,))
            active_week = len(cursor.fetchall())

            # Active users month (simplified: 3+ days)
            cursor = conn.execute('''
                SELECT user_id, COUNT(DISTINCT date(timestamp)) as active_days
                FROM actions WHERE timestamp >= ? AND is_test = 0
                GROUP BY user_id HAVING active_days >= 3
            ''', (month_start,))
            active_month = len(cursor.fetchall())

            # Totals
            total_users = conn.execute('SELECT COUNT(DISTINCT user_id) FROM actions WHERE is_test = 0').fetchone()[0]
            total_actions = conn.execute('SELECT COUNT(*) FROM actions WHERE is_test = 0').fetchone()[0]
            total_events = conn.execute(
                "SELECT COUNT(*) FROM actions WHERE action_type = 'event_create' AND is_test = 0"
            ).fetchone()[0]
            total_messages = conn.execute(
                "SELECT COUNT(*) FROM actions WHERE action_type IN ('text_message', 'voice_message') AND is_test = 0"
            ).fetchone()[0]

            return AdminDashboardStats(
                total_logins=total_logins,
                active_users_today=active_today,
                active_users_week=active_week,
                active_users_month=active_month,
                total_users=total_users,
                total_actions=total_actions,
                total_events_created=total_events,
                total_messages=total_messages
            )
        except Exception as e:
            logger.error("get_admin_stats_error", error=str(e))
            return AdminDashboardStats(
                total_logins=0, active_users_today=0, active_users_week=0,
                active_users_month=0, total_users=0, total_actions=0,
                total_events_created=0, total_messages=0
            )
        finally:
            conn.close()

    def get_all_users_details(self) -> List[UserDetail]:
        """Get detailed information for all users (excluding test data)."""
        conn = self._get_connection()
        try:
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            week_start = (now - timedelta(days=7)).isoformat()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

            # Get all unique users from actions (excluding test users)
            cursor = conn.execute('''
                SELECT
                    user_id,
                    MAX(CASE WHEN username IS NOT NULL THEN username END) as username,
                    MAX(CASE WHEN first_name IS NOT NULL THEN first_name END) as first_name,
                    MAX(CASE WHEN last_name IS NOT NULL THEN last_name END) as last_name
                FROM (
                    SELECT user_id, NULL as username, NULL as first_name, NULL as last_name 
                    FROM actions WHERE is_test = 0
                    UNION ALL
                    SELECT user_id, username, first_name, last_name FROM users
                )
                GROUP BY user_id
            ''')

            users_basic = cursor.fetchall()
            result = []

            for user_row in users_basic:
                user_id = user_row['user_id']

                # Get user info from users table if available
                user_info = conn.execute(
                    'SELECT username, first_name, last_name, is_hidden_in_admin FROM users WHERE user_id = ?',
                    (user_id,)
                ).fetchone()

                username = user_info['username'] if user_info else user_row['username']
                first_name = user_info['first_name'] if user_info else user_row['first_name']
                last_name = user_info['last_name'] if user_info else user_row['last_name']
                is_hidden_in_admin = bool(user_info['is_hidden_in_admin']) if user_info else False

                # Activity metrics (excluding test data)
                metrics = conn.execute('''
                    SELECT
                        MIN(timestamp) as first_seen,
                        MAX(timestamp) as last_seen,
                        COUNT(*) as total_actions,
                        SUM(CASE WHEN action_type = 'user_login' THEN 1 ELSE 0 END) as total_logins,
                        SUM(CASE WHEN timestamp >= ? THEN 1 ELSE 0 END) as actions_today,
                        SUM(CASE WHEN timestamp >= ? THEN 1 ELSE 0 END) as actions_week,
                        SUM(CASE WHEN timestamp >= ? THEN 1 ELSE 0 END) as actions_month
                    FROM actions WHERE user_id = ? AND is_test = 0
                ''', (today_start, week_start, month_start, user_id)).fetchone()

                # Active days (excluding test data)
                active_days_week = conn.execute('''
                    SELECT COUNT(DISTINCT date(timestamp)) FROM actions
                    WHERE user_id = ? AND timestamp >= ? AND is_test = 0
                ''', (user_id, week_start)).fetchone()[0]

                active_days_month = conn.execute('''
                    SELECT COUNT(DISTINCT date(timestamp)) FROM actions
                    WHERE user_id = ? AND timestamp >= ? AND is_test = 0
                ''', (user_id, month_start)).fetchone()[0]

                first_seen = datetime.fromisoformat(metrics['first_seen']) if metrics['first_seen'] else now
                last_seen = datetime.fromisoformat(metrics['last_seen']) if metrics['last_seen'] else now

                # Handle None values from SQL aggregates
                actions_today = metrics['actions_today'] or 0
                actions_week = metrics['actions_week'] or 0
                actions_month = metrics['actions_month'] or 0
                total_logins = metrics['total_logins'] or 0
                total_actions = metrics['total_actions'] or 0
                active_days_week = active_days_week or 0
                active_days_month = active_days_month or 0

                result.append(UserDetail(
                    user_id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    telegram_link=f"https://t.me/{username}" if username else None,
                    first_seen=first_seen,
                    last_seen=last_seen,
                    total_logins=total_logins,
                    total_actions=total_actions,
                    actions_today=actions_today,
                    actions_week=actions_week,
                    actions_month=actions_month,
                    active_days_week=active_days_week,
                    active_days_month=active_days_month,
                    is_active_today=actions_today > 0,
                    is_active_week=active_days_week >= 3,
                    is_active_month=active_days_month >= 3,
                    is_hidden_in_admin=is_hidden_in_admin
                ))

            # Sort by activity: total_actions DESC, actions_week DESC, last_seen DESC
            result.sort(key=lambda x: (x.total_actions, x.actions_week, x.last_seen), reverse=True)
            return result
        except Exception as e:
            logger.error("get_all_users_details_error", error=str(e), exc_info=True)
            return []
        finally:
            conn.close()

    def get_user_dialog(self, user_id: str, limit: int = 1000) -> List[UserDialogEntry]:
        """Get user's dialog history (excluding test data by default)."""
        conn = self._get_connection()
        try:
            cursor = conn.execute('''
                SELECT action_type, timestamp, details, success, error_message
                FROM actions WHERE user_id = ? AND is_test = 0
                ORDER BY timestamp ASC
                LIMIT ?
            ''', (user_id, limit))

            return [
                UserDialogEntry(
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    action_type=ActionType(row['action_type']) if row['action_type'] in [e.value for e in ActionType] else ActionType.TEXT_MESSAGE,
                    details=row['details'],
                    success=bool(row['success']),
                    error_message=row['error_message']
                )
                for row in cursor.fetchall()
            ]
        except Exception as e:
            logger.error("get_user_dialog_error", user_id=user_id, error=str(e))
            return []
        finally:
            conn.close()

    def get_activity_timeline(self, hours: int = 24) -> List[TimeSeriesPoint]:
        """Get activity timeline for the last N hours (excluding test data)."""
        conn = self._get_connection()
        try:
            start_time = (datetime.now() - timedelta(hours=hours)).isoformat()

            cursor = conn.execute('''
                SELECT strftime('%Y-%m-%d %H:00:00', timestamp) as hour, COUNT(*) as count
                FROM actions WHERE timestamp >= ? AND is_test = 0
                GROUP BY hour ORDER BY hour
            ''', (start_time,))

            hourly_data = {row['hour']: row['count'] for row in cursor.fetchall()}

            # Fill in missing hours
            timeline = []
            current = datetime.now() - timedelta(hours=hours)
            current = current.replace(minute=0, second=0, microsecond=0)

            while current <= datetime.now():
                hour_key = current.strftime('%Y-%m-%d %H:00:00')
                timeline.append(TimeSeriesPoint(
                    timestamp=current,
                    value=hourly_data.get(hour_key, 0)
                ))
                current += timedelta(hours=1)

            return timeline
        except Exception as e:
            logger.error("get_activity_timeline_error", error=str(e))
            return []
        finally:
            conn.close()

    def get_recent_actions(self, limit: int = 100, user_id: Optional[str] = None) -> List[UserAction]:
        """Get recent actions (excluding test data)."""
        conn = self._get_connection()
        try:
            if user_id:
                cursor = conn.execute('''
                    SELECT * FROM actions WHERE user_id = ? AND is_test = 0
                    ORDER BY timestamp DESC LIMIT ?
                ''', (user_id, limit))
            else:
                cursor = conn.execute('''
                    SELECT * FROM actions WHERE is_test = 0 
                    ORDER BY timestamp DESC LIMIT ?
                ''', (limit,))

            return [self._row_to_action(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error("get_recent_actions_error", error=str(e))
            return []
        finally:
            conn.close()

    def _row_to_action(self, row) -> UserAction:
        """Convert database row to UserAction."""
        try:
            action_type = ActionType(row['action_type']) if row['action_type'] in [e.value for e in ActionType] else ActionType.TEXT_MESSAGE
        except ValueError:
            action_type = ActionType.TEXT_MESSAGE

        return UserAction(
            id=row['id'],
            user_id=row['user_id'],
            action_type=action_type,
            timestamp=datetime.fromisoformat(row['timestamp']),
            details=row['details'],
            event_id=row['event_id'],
            success=bool(row['success']),
            error_message=row['error_message'],
            is_test=bool(row['is_test']),
            input_tokens=row['input_tokens'],
            output_tokens=row['output_tokens'],
            total_tokens=row['total_tokens'],
            cost_rub=row['cost_rub'],
            llm_model=row['llm_model']
        )

    def get_errors(self, hours: int = 24, limit: int = 100) -> List[UserAction]:
        """Get recent errors (excluding test data)."""
        conn = self._get_connection()
        try:
            start_time = (datetime.now() - timedelta(hours=hours)).isoformat()

            error_types = [
                'error', 'llm_error', 'llm_parse_error', 'llm_timeout',
                'calendar_error', 'stt_error', 'intent_unclear'
            ]
            placeholders = ','.join('?' * len(error_types))

            cursor = conn.execute(f'''
                SELECT * FROM actions
                WHERE timestamp >= ? AND (success = 0 OR action_type IN ({placeholders})) AND is_test = 0
                ORDER BY timestamp DESC LIMIT ?
            ''', (start_time, *error_types, limit))

            return [self._row_to_action(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error("get_errors_error", error=str(e))
            return []
        finally:
            conn.close()

    def get_error_stats(self, hours: int = 24) -> Dict:
        """Get error statistics (excluding test data)."""
        conn = self._get_connection()
        try:
            start_time = (datetime.now() - timedelta(hours=hours)).isoformat()

            cursor = conn.execute('''
                SELECT action_type, COUNT(*) as count
                FROM actions WHERE timestamp >= ? AND success = 0 AND is_test = 0
                GROUP BY action_type
            ''', (start_time,))

            by_type = {row['action_type']: row['count'] for row in cursor.fetchall()}
            total = sum(by_type.values())

            return {
                'total': total,
                'by_type': by_type,
                'period_hours': hours
            }
        except Exception as e:
            logger.error("get_error_stats_error", error=str(e))
            return {'total': 0, 'by_type': {}, 'period_hours': hours}
        finally:
            conn.close()

    def get_llm_cost_stats(self, hours: int = 24) -> Dict:
        """Get LLM usage and cost statistics (excluding test data)."""
        conn = self._get_connection()
        try:
            start_time = (datetime.now() - timedelta(hours=hours)).isoformat()

            cursor = conn.execute('''
                SELECT
                    COUNT(*) as total_requests,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(SUM(cost_rub), 0) as total_cost,
                    COUNT(DISTINCT user_id) as unique_users
                FROM actions
                WHERE action_type = 'llm_request' AND timestamp >= ? AND is_test = 0
            ''', (start_time,))

            row = cursor.fetchone()

            if not row or row['total_requests'] == 0:
                return {
                    'total_requests': 0,
                    'total_tokens': 0,
                    'total_cost_rub': 0.0,
                    'unique_users': 0,
                    'avg_cost_per_user': 0.0,
                    'avg_tokens_per_request': 0,
                    'by_model': {},
                    'period_hours': hours
                }

            total_requests = row['total_requests']
            total_tokens = row['total_tokens']
            total_cost = row['total_cost']
            unique_users = row['unique_users']

            # By model
            cursor = conn.execute('''
                SELECT llm_model,
                    COUNT(*) as requests,
                    COALESCE(SUM(total_tokens), 0) as tokens,
                    COALESCE(SUM(cost_rub), 0) as cost
                FROM actions
                WHERE action_type = 'llm_request' AND timestamp >= ? AND is_test = 0
                GROUP BY llm_model
            ''', (start_time,))

            by_model = {
                row['llm_model'] or 'unknown': {
                    'requests': row['requests'],
                    'tokens': row['tokens'],
                    'cost': row['cost']
                }
                for row in cursor.fetchall()
            }

            return {
                'total_requests': total_requests,
                'total_tokens': total_tokens,
                'total_cost_rub': round(total_cost, 2),
                'unique_users': unique_users,
                'avg_cost_per_user': round(total_cost / unique_users, 2) if unique_users else 0.0,
                'avg_tokens_per_request': total_tokens // total_requests if total_requests else 0,
                'by_model': by_model,
                'period_hours': hours
            }
        except Exception as e:
            logger.error("get_llm_cost_stats_error", error=str(e))
            return {
                'total_requests': 0, 'total_tokens': 0, 'total_cost_rub': 0.0,
                'unique_users': 0, 'avg_cost_per_user': 0.0, 'avg_tokens_per_request': 0,
                'by_model': {}, 'period_hours': hours
            }
        finally:
            conn.close()

    def get_action_distribution(self) -> List[EventTypeDistribution]:
        """Get distribution of action types (excluding test data)."""
        conn = self._get_connection()
        try:
            cursor = conn.execute('''
                SELECT action_type, COUNT(*) as count
                FROM actions WHERE is_test = 0
                GROUP BY action_type
            ''')

            rows = cursor.fetchall()
            total = sum(row['count'] for row in rows)

            return [
                EventTypeDistribution(
                    action_type=ActionType(row['action_type']) if row['action_type'] in [e.value for e in ActionType] else ActionType.TEXT_MESSAGE,
                    count=row['count'],
                    percentage=round(row['count'] / total * 100, 2) if total > 0 else 0
                )
                for row in rows
            ]
        except Exception as e:
            logger.error("get_action_distribution_error", error=str(e))
            return []
        finally:
            conn.close()

    def get_user_stats(self, limit: int = 100) -> List[UserStats]:
        """Get statistics for users (excluding test data)."""
        conn = self._get_connection()
        try:
            cursor = conn.execute('''
                SELECT
                    user_id,
                    MIN(timestamp) as first_seen,
                    MAX(timestamp) as last_seen,
                    SUM(CASE WHEN action_type IN ('event_create', 'event_update', 'event_delete') THEN 1 ELSE 0 END) as events,
                    SUM(CASE WHEN action_type = 'text_message' THEN 1 ELSE 0 END) as messages,
                    SUM(CASE WHEN action_type = 'voice_message' THEN 1 ELSE 0 END) as voice,
                    SUM(CASE WHEN action_type = 'webapp_open' THEN 1 ELSE 0 END) as webapp,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as errors
                FROM actions WHERE is_test = 0
                GROUP BY user_id
                ORDER BY last_seen DESC LIMIT ?
            ''', (limit,))

            result = []
            for row in cursor.fetchall():
                # Get user info
                user_info = conn.execute(
                    'SELECT username, first_name, last_name FROM users WHERE user_id = ?',
                    (row['user_id'],)
                ).fetchone()

                result.append(UserStats(
                    user_id=row['user_id'],
                    first_seen=datetime.fromisoformat(row['first_seen']),
                    last_seen=datetime.fromisoformat(row['last_seen']),
                    total_events=row['events'],
                    total_messages=row['messages'],
                    total_voice_messages=row['voice'],
                    total_webapp_opens=row['webapp'],
                    total_errors=row['errors'],
                    username=user_info['username'] if user_info else None,
                    first_name=user_info['first_name'] if user_info else None,
                    last_name=user_info['last_name'] if user_info else None
                ))

            return result
        except Exception as e:
            logger.error("get_user_stats_error", error=str(e))
            return []
        finally:
            conn.close()

    def clear_test_data(self) -> int:
        """Remove test data. Returns count of removed actions."""
        conn = self._get_connection()
        try:
            cursor = conn.execute('DELETE FROM actions WHERE is_test = 1')
            deleted = cursor.rowcount
            conn.commit()
            logger.info("test_data_cleared", removed=deleted)
            return deleted
        except Exception as e:
            logger.error("clear_test_data_error", error=str(e))
            return 0
        finally:
            conn.close()

    def migrate_from_json(self, json_data: Dict, daily_reminder_users: Dict[str, int]):
        """
        Migrate data from old JSON format to SQLite.

        Args:
            json_data: Data from analytics_data.json (with 'actions' key)
            daily_reminder_users: Data from daily_reminder_users.json
        """
        conn = self._get_connection()
        try:
            # Migrate users from daily_reminder_users.json
            for user_id, chat_id in daily_reminder_users.items():
                conn.execute('''
                    INSERT OR IGNORE INTO users (user_id, chat_id, first_seen, is_active)
                    VALUES (?, ?, CURRENT_TIMESTAMP, 1)
                ''', (str(user_id), int(chat_id)))

            # Migrate actions from analytics_data.json
            actions = json_data.get('actions', [])
            for action in actions:
                conn.execute('''
                    INSERT INTO actions
                    (user_id, action_type, timestamp, details, event_id, success,
                     error_message, is_test, input_tokens, output_tokens, total_tokens,
                     cost_rub, llm_model)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    action.get('user_id'),
                    action.get('action_type'),
                    action.get('timestamp'),
                    action.get('details'),
                    action.get('event_id'),
                    1 if action.get('success', True) else 0,
                    action.get('error_message'),
                    1 if action.get('is_test', False) else 0,
                    action.get('input_tokens'),
                    action.get('output_tokens'),
                    action.get('total_tokens'),
                    action.get('cost_rub'),
                    action.get('llm_model')
                ))

                # Update user info if available
                if any([action.get('username'), action.get('first_name'), action.get('last_name')]):
                    conn.execute('''
                        UPDATE users SET
                            username = COALESCE(?, username),
                            first_name = COALESCE(?, first_name),
                            last_name = COALESCE(?, last_name)
                        WHERE user_id = ?
                    ''', (
                        action.get('username'),
                        action.get('first_name'),
                        action.get('last_name'),
                        action.get('user_id')
                    ))

            conn.commit()
            logger.info("migration_completed",
                       users=len(daily_reminder_users),
                       actions=len(actions))
        except Exception as e:
            logger.error("migration_error", error=str(e), exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()


# Global instance
analytics_service = AnalyticsService()
