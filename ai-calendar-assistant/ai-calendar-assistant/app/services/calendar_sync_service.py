"""
Main calendar synchronization service.

Coordinates bidirectional sync between Radicale and external calendars.
"""

import structlog
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import asyncio
from time import time

from app.services.sync_database import sync_db
from app.services.google_calendar_service import GoogleCalendarService
from app.services.calendar_radicale import calendar_service
from app.models.calendar_sync import (
    CalendarConnection,
    SyncEvent,
    SyncLog,
    CalendarProvider
)
from app.schemas.events import EventDTO

logger = structlog.get_logger()


class CalendarSyncService:
    """Service for synchronizing calendars with external providers."""

    def __init__(self, google_client_id: str, google_client_secret: str, google_redirect_uri: str):
        """
        Initialize sync service.

        Args:
            google_client_id: Google OAuth client ID
            google_client_secret: Google OAuth client secret
            google_redirect_uri: OAuth redirect URI
        """
        self.google_service = GoogleCalendarService(
            client_id=google_client_id,
            client_secret=google_client_secret,
            redirect_uri=google_redirect_uri
        )

    # ==================== Import: External → Radicale ====================

    async def import_events_from_google(
        self,
        user_id: str,
        connection: CalendarConnection
    ) -> Dict[str, int]:
        """
        Import events from Google Calendar to Radicale.

        Args:
            user_id: User ID
            connection: Google Calendar connection

        Returns:
            Dict with counts: imported, updated, deleted, errors
        """
        start_time = time()
        stats = {
            "imported": 0,
            "updated": 0,
            "deleted": 0,
            "errors": 0
        }

        try:
            # Check if token needs refresh
            await self._refresh_token_if_needed(connection)

            # Fetch events from Google
            # Use sync token for incremental sync if available
            google_data = await self.google_service.list_events(
                connection=connection,
                sync_token=connection.last_sync_token
            )

            google_events = google_data.get("items", [])
            next_sync_token = google_data.get("nextSyncToken")

            logger.info("google_events_fetched",
                       user_id=user_id,
                       connection_id=connection.id,
                       count=len(google_events))

            # Process each event
            for google_event in google_events:
                try:
                    # Check if event is deleted
                    if google_event.get("status") == "cancelled":
                        # Delete from Radicale if exists
                        await self._handle_deleted_event(user_id, connection, google_event)
                        stats["deleted"] += 1
                        continue

                    # Convert to EventDTO
                    event_dto = self.google_service.google_event_to_dto(google_event)

                    # Check if event already synced
                    external_event_id = google_event["id"]
                    external_updated = datetime.fromisoformat(
                        google_event["updated"].replace("Z", "+00:00")
                    )

                    sync_event = sync_db.get_sync_event_by_external_id(
                        connection.id,
                        external_event_id
                    )

                    if sync_event:
                        # Event exists - check if needs update
                        if external_updated > sync_event.external_updated_at:
                            # Update in Radicale
                            success = await calendar_service.update_event(
                                user_id,
                                sync_event.local_event_id,
                                event_dto
                            )
                            if success:
                                # Update sync mapping
                                sync_event.external_updated_at = external_updated
                                sync_event.sync_status = "synced"
                                sync_db.update_sync_event(sync_event)
                                stats["updated"] += 1
                                logger.info("event_updated_from_google",
                                          user_id=user_id,
                                          event_id=external_event_id)
                    else:
                        # New event - create in Radicale
                        local_event_id = await calendar_service.create_event(user_id, event_dto)
                        if local_event_id:
                            # Create sync mapping
                            new_sync_event = SyncEvent(
                                user_id=user_id,
                                connection_id=connection.id,
                                local_event_id=local_event_id,
                                external_event_id=external_event_id,
                                last_synced_at=datetime.now(),
                                local_updated_at=datetime.now(),
                                external_updated_at=external_updated,
                                sync_status="synced"
                            )
                            sync_db.create_sync_event(new_sync_event)
                            stats["imported"] += 1
                            logger.info("event_imported_from_google",
                                      user_id=user_id,
                                      event_id=external_event_id)

                except Exception as e:
                    logger.error("import_event_error",
                               user_id=user_id,
                               event=google_event.get("id"),
                               error=str(e),
                               exc_info=True)
                    stats["errors"] += 1

            # Update last sync token
            if next_sync_token:
                sync_db.update_last_sync(connection.id, next_sync_token)

            # Log sync operation
            duration = time() - start_time
            sync_log = SyncLog(
                user_id=user_id,
                connection_id=connection.id,
                sync_type="import",
                events_imported=stats["imported"],
                events_exported=0,
                events_updated=stats["updated"],
                events_deleted=stats["deleted"],
                conflicts=0,
                errors=stats["errors"],
                duration_seconds=duration,
                created_at=datetime.now()
            )
            sync_db.create_sync_log(sync_log)

            logger.info("google_import_completed",
                       user_id=user_id,
                       connection_id=connection.id,
                       stats=stats,
                       duration=duration)

        except Exception as e:
            logger.error("google_import_failed",
                        user_id=user_id,
                        connection_id=connection.id,
                        error=str(e),
                        exc_info=True)
            stats["errors"] += 1

            # Log failed sync
            sync_log = SyncLog(
                user_id=user_id,
                connection_id=connection.id,
                sync_type="import",
                events_imported=0,
                events_exported=0,
                events_updated=0,
                events_deleted=0,
                conflicts=0,
                errors=1,
                error_message=str(e),
                duration_seconds=time() - start_time,
                created_at=datetime.now()
            )
            sync_db.create_sync_log(sync_log)

        return stats

    async def _handle_deleted_event(
        self,
        user_id: str,
        connection: CalendarConnection,
        google_event: Dict
    ):
        """Handle deleted event from Google Calendar."""
        external_event_id = google_event["id"]
        sync_event = sync_db.get_sync_event_by_external_id(
            connection.id,
            external_event_id
        )

        if sync_event:
            # Delete from Radicale
            await calendar_service.delete_event(user_id, sync_event.local_event_id)
            # Delete sync mapping
            sync_db.delete_sync_event(sync_event.id)
            logger.info("event_deleted_from_google",
                       user_id=user_id,
                       event_id=external_event_id)

    # ==================== Export: Radicale → External ====================

    async def export_event_to_google(
        self,
        user_id: str,
        connection: CalendarConnection,
        local_event_id: str,
        event_dto: EventDTO
    ) -> bool:
        """
        Export single event from Radicale to Google Calendar.

        Called when user creates event in bot.

        Args:
            user_id: User ID
            connection: Google Calendar connection
            local_event_id: Local event UID in Radicale
            event_dto: Event data

        Returns:
            True if successful
        """
        try:
            # Check if token needs refresh
            await self._refresh_token_if_needed(connection)

            # Create event in Google Calendar
            external_event_id = await self.google_service.create_event(
                connection,
                event_dto
            )

            # Create sync mapping
            sync_event = SyncEvent(
                user_id=user_id,
                connection_id=connection.id,
                local_event_id=local_event_id,
                external_event_id=external_event_id,
                last_synced_at=datetime.now(),
                local_updated_at=datetime.now(),
                external_updated_at=datetime.now(),
                sync_status="synced"
            )
            sync_db.create_sync_event(sync_event)

            logger.info("event_exported_to_google",
                       user_id=user_id,
                       local_event_id=local_event_id,
                       external_event_id=external_event_id)

            return True

        except Exception as e:
            logger.error("export_event_failed",
                        user_id=user_id,
                        local_event_id=local_event_id,
                        error=str(e),
                        exc_info=True)
            return False

    async def export_updated_event_to_google(
        self,
        user_id: str,
        connection: CalendarConnection,
        local_event_id: str,
        event_dto: EventDTO
    ) -> bool:
        """
        Export updated event from Radicale to Google Calendar.

        Args:
            user_id: User ID
            connection: Google Calendar connection
            local_event_id: Local event UID
            event_dto: Updated event data

        Returns:
            True if successful
        """
        try:
            # Find sync mapping
            sync_event = sync_db.get_sync_event_by_local_id(connection.id, local_event_id)

            if not sync_event:
                logger.warning("sync_event_not_found_for_update",
                             user_id=user_id,
                             local_event_id=local_event_id)
                # Create new event instead
                return await self.export_event_to_google(
                    user_id,
                    connection,
                    local_event_id,
                    event_dto
                )

            # Check if token needs refresh
            await self._refresh_token_if_needed(connection)

            # Update event in Google Calendar
            success = await self.google_service.update_event(
                connection,
                sync_event.external_event_id,
                event_dto
            )

            if success:
                # Update sync mapping
                sync_event.local_updated_at = datetime.now()
                sync_event.external_updated_at = datetime.now()
                sync_event.sync_status = "synced"
                sync_db.update_sync_event(sync_event)

                logger.info("event_update_exported_to_google",
                           user_id=user_id,
                           local_event_id=local_event_id)

            return success

        except Exception as e:
            logger.error("export_update_failed",
                        user_id=user_id,
                        local_event_id=local_event_id,
                        error=str(e),
                        exc_info=True)
            return False

    async def export_deleted_event_to_google(
        self,
        user_id: str,
        connection: CalendarConnection,
        local_event_id: str
    ) -> bool:
        """
        Export deleted event from Radicale to Google Calendar.

        Args:
            user_id: User ID
            connection: Google Calendar connection
            local_event_id: Local event UID

        Returns:
            True if successful
        """
        try:
            # Find sync mapping
            sync_event = sync_db.get_sync_event_by_local_id(connection.id, local_event_id)

            if not sync_event:
                logger.warning("sync_event_not_found_for_delete",
                             user_id=user_id,
                             local_event_id=local_event_id)
                return True  # Already deleted

            # Check if token needs refresh
            await self._refresh_token_if_needed(connection)

            # Delete event from Google Calendar
            success = await self.google_service.delete_event(
                connection,
                sync_event.external_event_id
            )

            if success:
                # Delete sync mapping
                sync_db.delete_sync_event(sync_event.id)

                logger.info("event_deletion_exported_to_google",
                           user_id=user_id,
                           local_event_id=local_event_id)

            return success

        except Exception as e:
            logger.error("export_deletion_failed",
                        user_id=user_id,
                        local_event_id=local_event_id,
                        error=str(e),
                        exc_info=True)
            return False

    # ==================== Token Management ====================

    async def _refresh_token_if_needed(self, connection: CalendarConnection):
        """Refresh access token if expired."""
        if not connection.token_expires_at:
            return

        # Refresh if token expires in less than 5 minutes
        if connection.token_expires_at <= datetime.now() + timedelta(minutes=5):
            logger.info("refreshing_google_token", connection_id=connection.id)

            try:
                tokens = await self.google_service.refresh_access_token(
                    connection.refresh_token
                )

                # Update connection with new tokens
                new_expires_at = datetime.now() + timedelta(seconds=tokens.get("expires_in", 3600))
                sync_db.update_connection_tokens(
                    connection.id,
                    tokens["access_token"],
                    connection.refresh_token,  # Keep same refresh token
                    new_expires_at
                )

                # Update connection object in memory
                connection.access_token = tokens["access_token"]
                connection.token_expires_at = new_expires_at

                logger.info("google_token_refreshed", connection_id=connection.id)

            except Exception as e:
                logger.error("token_refresh_failed",
                            connection_id=connection.id,
                            error=str(e),
                            exc_info=True)
                raise

    # ==================== Batch Sync ====================

    async def sync_all_users(self):
        """
        Sync all users with enabled connections.

        Called by background task every 10 minutes.
        """
        logger.info("starting_batch_sync")
        start_time = time()

        try:
            # Get all connections (grouped by user)
            # For now, we'll query all connections and group them
            # In production, might want to paginate this

            # Get all enabled connections from DB
            # We need to iterate through all users
            # For simplicity, we'll use a SQL query to get unique user_ids

            import sqlite3
            with sqlite3.connect(sync_db.db_path) as conn:
                cursor = conn.execute("""
                    SELECT DISTINCT user_id
                    FROM calendar_connections
                    WHERE sync_enabled = 1
                """)
                user_ids = [row[0] for row in cursor.fetchall()]

            logger.info("batch_sync_users_found", count=len(user_ids))

            # Sync each user
            for user_id in user_ids:
                try:
                    await self.sync_user(user_id)
                except Exception as e:
                    logger.error("user_sync_failed",
                                user_id=user_id,
                                error=str(e),
                                exc_info=True)

            duration = time() - start_time
            logger.info("batch_sync_completed",
                       users_synced=len(user_ids),
                       duration=duration)

        except Exception as e:
            logger.error("batch_sync_failed", error=str(e), exc_info=True)

    async def sync_user(self, user_id: str):
        """
        Sync all connections for a single user.

        Args:
            user_id: User ID
        """
        connections = sync_db.get_user_connections(user_id, enabled_only=True)

        if not connections:
            return

        logger.info("syncing_user", user_id=user_id, connections_count=len(connections))

        for connection in connections:
            try:
                if connection.provider == CalendarProvider.GOOGLE:
                    await self.import_events_from_google(user_id, connection)
                # Add other providers here (Yandex, Apple)

            except Exception as e:
                logger.error("connection_sync_failed",
                            user_id=user_id,
                            connection_id=connection.id,
                            error=str(e),
                            exc_info=True)


# Global instance (will be initialized with config)
calendar_sync_service: Optional[CalendarSyncService] = None


def init_calendar_sync_service(
    google_client_id: str,
    google_client_secret: str,
    google_redirect_uri: str
):
    """Initialize global calendar sync service."""
    global calendar_sync_service
    calendar_sync_service = CalendarSyncService(
        google_client_id,
        google_client_secret,
        google_redirect_uri
    )
    logger.info("calendar_sync_service_initialized")
