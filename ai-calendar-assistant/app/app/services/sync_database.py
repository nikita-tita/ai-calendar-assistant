"""
SQLite database service for calendar synchronization.
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List
from pathlib import Path
import structlog
from cryptography.fernet import Fernet
import os

from app.models.calendar_sync import (
    CalendarConnection,
    SyncEvent,
    SyncLog,
    CalendarProvider,
    SyncDirection
)

logger = structlog.get_logger()


class SyncDatabase:
    """SQLite database for managing external calendar sync."""

    def __init__(self, db_path: str = "/var/lib/calendar-bot/sync.db"):
        self.db_path = db_path
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)
        self._init_database()

    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for OAuth tokens."""
        key_path = Path("/var/lib/calendar-bot/sync_encryption.key")

        if key_path.exists():
            return key_path.read_bytes()
        else:
            key = Fernet.generate_key()
            key_path.parent.mkdir(parents=True, exist_ok=True)
            key_path.write_bytes(key)
            key_path.chmod(0o600)  # Restrict permissions
            logger.info("encryption_key_generated", path=str(key_path))
            return key

    def _encrypt(self, data: str) -> str:
        """Encrypt sensitive data."""
        return self.cipher.encrypt(data.encode()).decode()

    def _decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        return self.cipher.decrypt(encrypted_data.encode()).decode()

    def _init_database(self):
        """Initialize database schema."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS calendar_connections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    calendar_id TEXT NOT NULL,
                    calendar_name TEXT NOT NULL,

                    access_token TEXT NOT NULL,
                    refresh_token TEXT,
                    token_expires_at TEXT,

                    sync_enabled INTEGER DEFAULT 1,
                    sync_direction TEXT DEFAULT 'bidirectional',
                    last_sync_at TEXT,
                    last_sync_token TEXT,

                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,

                    UNIQUE(user_id, provider, calendar_id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    connection_id INTEGER NOT NULL,

                    local_event_id TEXT NOT NULL,
                    external_event_id TEXT NOT NULL,

                    last_synced_at TEXT NOT NULL,
                    local_updated_at TEXT NOT NULL,
                    external_updated_at TEXT NOT NULL,
                    sync_status TEXT DEFAULT 'synced',

                    conflict_data TEXT,

                    FOREIGN KEY (connection_id) REFERENCES calendar_connections(id) ON DELETE CASCADE,
                    UNIQUE(connection_id, local_event_id),
                    UNIQUE(connection_id, external_event_id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    connection_id INTEGER NOT NULL,

                    sync_type TEXT NOT NULL,
                    events_imported INTEGER DEFAULT 0,
                    events_exported INTEGER DEFAULT 0,
                    events_updated INTEGER DEFAULT 0,
                    events_deleted INTEGER DEFAULT 0,
                    conflicts INTEGER DEFAULT 0,
                    errors INTEGER DEFAULT 0,

                    error_message TEXT,
                    duration_seconds REAL DEFAULT 0,

                    created_at TEXT NOT NULL,

                    FOREIGN KEY (connection_id) REFERENCES calendar_connections(id) ON DELETE CASCADE
                )
            """)

            # Create indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_connections_user
                ON calendar_connections(user_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sync_events_local
                ON sync_events(local_event_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sync_events_external
                ON sync_events(external_event_id)
            """)

            conn.commit()
            logger.info("sync_database_initialized", db_path=self.db_path)

    # ==================== Calendar Connections ====================

    def create_connection(self, connection: CalendarConnection) -> int:
        """Create new calendar connection."""
        now = datetime.now().isoformat()
        connection.created_at = datetime.fromisoformat(now)
        connection.updated_at = datetime.fromisoformat(now)

        # Encrypt tokens
        encrypted_access = self._encrypt(connection.access_token)
        encrypted_refresh = self._encrypt(connection.refresh_token) if connection.refresh_token else None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO calendar_connections (
                    user_id, provider, calendar_id, calendar_name,
                    access_token, refresh_token, token_expires_at,
                    sync_enabled, sync_direction, last_sync_at, last_sync_token,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                connection.user_id, connection.provider.value, connection.calendar_id,
                connection.calendar_name, encrypted_access, encrypted_refresh,
                connection.token_expires_at.isoformat() if connection.token_expires_at else None,
                1 if connection.sync_enabled else 0, connection.sync_direction.value,
                connection.last_sync_at.isoformat() if connection.last_sync_at else None,
                connection.last_sync_token, now, now
            ))
            conn.commit()
            connection_id = cursor.lastrowid

        logger.info("calendar_connection_created",
                   connection_id=connection_id,
                   user_id=connection.user_id,
                   provider=connection.provider.value)
        return connection_id

    def get_user_connections(self, user_id: str, enabled_only: bool = True) -> List[CalendarConnection]:
        """Get all calendar connections for a user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM calendar_connections WHERE user_id = ?"
            params = [user_id]

            if enabled_only:
                query += " AND sync_enabled = 1"

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

        connections = []
        for row in rows:
            # Decrypt tokens
            access_token = self._decrypt(row['access_token'])
            refresh_token = self._decrypt(row['refresh_token']) if row['refresh_token'] else None

            conn = CalendarConnection(
                id=row['id'],
                user_id=row['user_id'],
                provider=CalendarProvider(row['provider']),
                calendar_id=row['calendar_id'],
                calendar_name=row['calendar_name'],
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=datetime.fromisoformat(row['token_expires_at']) if row['token_expires_at'] else None,
                sync_enabled=bool(row['sync_enabled']),
                sync_direction=SyncDirection(row['sync_direction']),
                last_sync_at=datetime.fromisoformat(row['last_sync_at']) if row['last_sync_at'] else None,
                last_sync_token=row['last_sync_token'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at'])
            )
            connections.append(conn)

        return connections

    def update_connection_tokens(
        self,
        connection_id: int,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ):
        """Update OAuth tokens for a connection."""
        encrypted_access = self._encrypt(access_token)
        encrypted_refresh = self._encrypt(refresh_token) if refresh_token else None

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE calendar_connections
                SET access_token = ?, refresh_token = ?, token_expires_at = ?, updated_at = ?
                WHERE id = ?
            """, (
                encrypted_access,
                encrypted_refresh,
                expires_at.isoformat() if expires_at else None,
                datetime.now().isoformat(),
                connection_id
            ))
            conn.commit()

        logger.info("connection_tokens_updated", connection_id=connection_id)

    def update_last_sync(self, connection_id: int, sync_token: Optional[str] = None):
        """Update last sync timestamp and token."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE calendar_connections
                SET last_sync_at = ?, last_sync_token = ?, updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), sync_token, datetime.now().isoformat(), connection_id))
            conn.commit()

    def delete_connection(self, connection_id: int):
        """Delete calendar connection (cascades to sync_events and sync_logs)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM calendar_connections WHERE id = ?", (connection_id,))
            conn.commit()

        logger.info("calendar_connection_deleted", connection_id=connection_id)

    # ==================== Sync Events ====================

    def create_sync_event(self, sync_event: SyncEvent) -> int:
        """Create sync event mapping."""
        now = datetime.now()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO sync_events (
                    user_id, connection_id, local_event_id, external_event_id,
                    last_synced_at, local_updated_at, external_updated_at, sync_status,
                    conflict_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sync_event.user_id, sync_event.connection_id,
                sync_event.local_event_id, sync_event.external_event_id,
                now.isoformat(),
                sync_event.local_updated_at.isoformat(),
                sync_event.external_updated_at.isoformat(),
                sync_event.sync_status,
                sync_event.conflict_data
            ))
            conn.commit()
            return cursor.lastrowid

    def get_sync_event_by_local_id(self, connection_id: int, local_event_id: str) -> Optional[SyncEvent]:
        """Get sync event by local event ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM sync_events
                WHERE connection_id = ? AND local_event_id = ?
            """, (connection_id, local_event_id))
            row = cursor.fetchone()

        if not row:
            return None

        return SyncEvent(
            id=row['id'],
            user_id=row['user_id'],
            connection_id=row['connection_id'],
            local_event_id=row['local_event_id'],
            external_event_id=row['external_event_id'],
            last_synced_at=datetime.fromisoformat(row['last_synced_at']),
            local_updated_at=datetime.fromisoformat(row['local_updated_at']),
            external_updated_at=datetime.fromisoformat(row['external_updated_at']),
            sync_status=row['sync_status'],
            conflict_data=row['conflict_data']
        )

    def get_sync_event_by_external_id(self, connection_id: int, external_event_id: str) -> Optional[SyncEvent]:
        """Get sync event by external event ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM sync_events
                WHERE connection_id = ? AND external_event_id = ?
            """, (connection_id, external_event_id))
            row = cursor.fetchone()

        if not row:
            return None

        return SyncEvent(
            id=row['id'],
            user_id=row['user_id'],
            connection_id=row['connection_id'],
            local_event_id=row['local_event_id'],
            external_event_id=row['external_event_id'],
            last_synced_at=datetime.fromisoformat(row['last_synced_at']),
            local_updated_at=datetime.fromisoformat(row['local_updated_at']),
            external_updated_at=datetime.fromisoformat(row['external_updated_at']),
            sync_status=row['sync_status'],
            conflict_data=row['conflict_data']
        )

    def update_sync_event(self, sync_event: SyncEvent):
        """Update sync event mapping."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE sync_events
                SET last_synced_at = ?, local_updated_at = ?, external_updated_at = ?,
                    sync_status = ?, conflict_data = ?
                WHERE id = ?
            """, (
                datetime.now().isoformat(),
                sync_event.local_updated_at.isoformat(),
                sync_event.external_updated_at.isoformat(),
                sync_event.sync_status,
                sync_event.conflict_data,
                sync_event.id
            ))
            conn.commit()

    def delete_sync_event(self, sync_event_id: int):
        """Delete sync event mapping."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM sync_events WHERE id = ?", (sync_event_id,))
            conn.commit()

    # ==================== Sync Logs ====================

    def create_sync_log(self, sync_log: SyncLog) -> int:
        """Create sync log entry."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO sync_logs (
                    user_id, connection_id, sync_type,
                    events_imported, events_exported, events_updated, events_deleted,
                    conflicts, errors, error_message, duration_seconds, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sync_log.user_id, sync_log.connection_id, sync_log.sync_type,
                sync_log.events_imported, sync_log.events_exported,
                sync_log.events_updated, sync_log.events_deleted,
                sync_log.conflicts, sync_log.errors,
                sync_log.error_message, sync_log.duration_seconds,
                datetime.now().isoformat()
            ))
            conn.commit()
            return cursor.lastrowid


# Singleton instance
sync_db = SyncDatabase()
