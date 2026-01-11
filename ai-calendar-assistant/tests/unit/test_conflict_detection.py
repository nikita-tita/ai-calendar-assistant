"""
Unit tests for BIZ-004: Event conflict detection.
Tests the _find_conflicts() method in RadicaleService.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import pytz

from app.services.calendar_radicale import RadicaleService
from app.schemas.events import EventDTO


class TestFindConflicts:
    """Test _find_conflicts() method."""

    @pytest.fixture
    def service(self):
        """Create RadicaleService instance."""
        return RadicaleService()

    @pytest.fixture
    def mock_calendar(self):
        """Create mock calendar with events."""
        calendar = Mock()
        return calendar

    def _create_mock_event(self, uid: str, summary: str, start: datetime, end: datetime) -> Mock:
        """Helper to create a mock CalDAV event."""
        ical_data = f"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:{uid}
SUMMARY:{summary}
DTSTART:{start.strftime('%Y%m%dT%H%M%SZ')}
DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}
END:VEVENT
END:VCALENDAR"""
        event = Mock()
        event.data = ical_data
        return event

    def test_no_conflicts_empty_calendar(self, service):
        """Test no conflicts when calendar is empty."""
        with patch.object(service, '_get_user_calendar') as mock_get_cal:
            mock_calendar = Mock()
            mock_calendar.date_search.return_value = []
            mock_get_cal.return_value = mock_calendar

            start = datetime.now(pytz.UTC)
            end = start + timedelta(hours=1)

            conflicts = service._find_conflicts("user123", start, end)
            assert conflicts == []

    def test_no_conflicts_non_overlapping_events(self, service):
        """Test no conflicts when events don't overlap."""
        with patch.object(service, '_get_user_calendar') as mock_get_cal:
            mock_calendar = Mock()

            # Existing event: 10:00-11:00
            existing_start = datetime(2026, 1, 15, 10, 0, 0, tzinfo=pytz.UTC)
            existing_end = datetime(2026, 1, 15, 11, 0, 0, tzinfo=pytz.UTC)
            mock_event = self._create_mock_event(
                "existing-uid", "Existing Event", existing_start, existing_end
            )
            mock_calendar.date_search.return_value = [mock_event]
            mock_get_cal.return_value = mock_calendar

            # New event: 12:00-13:00 (no overlap)
            new_start = datetime(2026, 1, 15, 12, 0, 0, tzinfo=pytz.UTC)
            new_end = datetime(2026, 1, 15, 13, 0, 0, tzinfo=pytz.UTC)

            conflicts = service._find_conflicts("user123", new_start, new_end)
            assert conflicts == []

    def test_conflict_detected_full_overlap(self, service):
        """Test conflict detected when events fully overlap."""
        with patch.object(service, '_get_user_calendar') as mock_get_cal:
            mock_calendar = Mock()

            # Existing event: 10:00-12:00
            existing_start = datetime(2026, 1, 15, 10, 0, 0, tzinfo=pytz.UTC)
            existing_end = datetime(2026, 1, 15, 12, 0, 0, tzinfo=pytz.UTC)
            mock_event = self._create_mock_event(
                "existing-uid", "Meeting", existing_start, existing_end
            )
            mock_calendar.date_search.return_value = [mock_event]
            mock_get_cal.return_value = mock_calendar

            # New event: 10:30-11:30 (inside existing)
            new_start = datetime(2026, 1, 15, 10, 30, 0, tzinfo=pytz.UTC)
            new_end = datetime(2026, 1, 15, 11, 30, 0, tzinfo=pytz.UTC)

            conflicts = service._find_conflicts("user123", new_start, new_end)

            assert len(conflicts) == 1
            assert conflicts[0]['uid'] == "existing-uid"
            assert conflicts[0]['summary'] == "Meeting"

    def test_conflict_detected_partial_overlap_start(self, service):
        """Test conflict when new event starts during existing."""
        with patch.object(service, '_get_user_calendar') as mock_get_cal:
            mock_calendar = Mock()

            # Existing event: 10:00-11:00
            existing_start = datetime(2026, 1, 15, 10, 0, 0, tzinfo=pytz.UTC)
            existing_end = datetime(2026, 1, 15, 11, 0, 0, tzinfo=pytz.UTC)
            mock_event = self._create_mock_event(
                "existing-uid", "Standup", existing_start, existing_end
            )
            mock_calendar.date_search.return_value = [mock_event]
            mock_get_cal.return_value = mock_calendar

            # New event: 10:30-12:00 (starts during existing)
            new_start = datetime(2026, 1, 15, 10, 30, 0, tzinfo=pytz.UTC)
            new_end = datetime(2026, 1, 15, 12, 0, 0, tzinfo=pytz.UTC)

            conflicts = service._find_conflicts("user123", new_start, new_end)

            assert len(conflicts) == 1
            assert conflicts[0]['summary'] == "Standup"

    def test_conflict_detected_partial_overlap_end(self, service):
        """Test conflict when new event ends during existing."""
        with patch.object(service, '_get_user_calendar') as mock_get_cal:
            mock_calendar = Mock()

            # Existing event: 11:00-12:00
            existing_start = datetime(2026, 1, 15, 11, 0, 0, tzinfo=pytz.UTC)
            existing_end = datetime(2026, 1, 15, 12, 0, 0, tzinfo=pytz.UTC)
            mock_event = self._create_mock_event(
                "existing-uid", "Lunch", existing_start, existing_end
            )
            mock_calendar.date_search.return_value = [mock_event]
            mock_get_cal.return_value = mock_calendar

            # New event: 10:00-11:30 (ends during existing)
            new_start = datetime(2026, 1, 15, 10, 0, 0, tzinfo=pytz.UTC)
            new_end = datetime(2026, 1, 15, 11, 30, 0, tzinfo=pytz.UTC)

            conflicts = service._find_conflicts("user123", new_start, new_end)

            assert len(conflicts) == 1
            assert conflicts[0]['summary'] == "Lunch"

    def test_no_conflict_adjacent_events(self, service):
        """Test no conflict for events that touch but don't overlap."""
        with patch.object(service, '_get_user_calendar') as mock_get_cal:
            mock_calendar = Mock()

            # Existing event: 10:00-11:00
            existing_start = datetime(2026, 1, 15, 10, 0, 0, tzinfo=pytz.UTC)
            existing_end = datetime(2026, 1, 15, 11, 0, 0, tzinfo=pytz.UTC)
            mock_event = self._create_mock_event(
                "existing-uid", "First Meeting", existing_start, existing_end
            )
            mock_calendar.date_search.return_value = [mock_event]
            mock_get_cal.return_value = mock_calendar

            # New event: 11:00-12:00 (starts exactly when existing ends)
            new_start = datetime(2026, 1, 15, 11, 0, 0, tzinfo=pytz.UTC)
            new_end = datetime(2026, 1, 15, 12, 0, 0, tzinfo=pytz.UTC)

            conflicts = service._find_conflicts("user123", new_start, new_end)

            # Adjacent events should NOT conflict
            assert len(conflicts) == 0

    def test_exclude_uid_for_updates(self, service):
        """Test that exclude_uid prevents self-conflict during updates."""
        with patch.object(service, '_get_user_calendar') as mock_get_cal:
            mock_calendar = Mock()

            # Existing event being updated: 10:00-11:00
            existing_start = datetime(2026, 1, 15, 10, 0, 0, tzinfo=pytz.UTC)
            existing_end = datetime(2026, 1, 15, 11, 0, 0, tzinfo=pytz.UTC)
            mock_event = self._create_mock_event(
                "event-to-update", "My Meeting", existing_start, existing_end
            )
            mock_calendar.date_search.return_value = [mock_event]
            mock_get_cal.return_value = mock_calendar

            # Updating to: 10:30-11:30 (would conflict with itself)
            new_start = datetime(2026, 1, 15, 10, 30, 0, tzinfo=pytz.UTC)
            new_end = datetime(2026, 1, 15, 11, 30, 0, tzinfo=pytz.UTC)

            # With exclude_uid, should not conflict with itself
            conflicts = service._find_conflicts(
                "user123", new_start, new_end, exclude_uid="event-to-update"
            )
            assert len(conflicts) == 0

    def test_multiple_conflicts(self, service):
        """Test detecting multiple conflicting events."""
        with patch.object(service, '_get_user_calendar') as mock_get_cal:
            mock_calendar = Mock()

            # Event 1: 10:00-11:00
            event1 = self._create_mock_event(
                "uid-1", "Meeting 1",
                datetime(2026, 1, 15, 10, 0, 0, tzinfo=pytz.UTC),
                datetime(2026, 1, 15, 11, 0, 0, tzinfo=pytz.UTC)
            )
            # Event 2: 10:30-11:30
            event2 = self._create_mock_event(
                "uid-2", "Meeting 2",
                datetime(2026, 1, 15, 10, 30, 0, tzinfo=pytz.UTC),
                datetime(2026, 1, 15, 11, 30, 0, tzinfo=pytz.UTC)
            )
            # Event 3: 12:00-13:00 (no conflict)
            event3 = self._create_mock_event(
                "uid-3", "Meeting 3",
                datetime(2026, 1, 15, 12, 0, 0, tzinfo=pytz.UTC),
                datetime(2026, 1, 15, 13, 0, 0, tzinfo=pytz.UTC)
            )

            mock_calendar.date_search.return_value = [event1, event2, event3]
            mock_get_cal.return_value = mock_calendar

            # New event: 10:15-11:15 (conflicts with both event1 and event2)
            new_start = datetime(2026, 1, 15, 10, 15, 0, tzinfo=pytz.UTC)
            new_end = datetime(2026, 1, 15, 11, 15, 0, tzinfo=pytz.UTC)

            conflicts = service._find_conflicts("user123", new_start, new_end)

            assert len(conflicts) == 2
            summaries = [c['summary'] for c in conflicts]
            assert "Meeting 1" in summaries
            assert "Meeting 2" in summaries
            assert "Meeting 3" not in summaries

    def test_calendar_not_found(self, service):
        """Test graceful handling when calendar doesn't exist."""
        with patch.object(service, '_get_user_calendar') as mock_get_cal:
            mock_get_cal.return_value = None

            start = datetime.now(pytz.UTC)
            end = start + timedelta(hours=1)

            conflicts = service._find_conflicts("user123", start, end)
            assert conflicts == []

    def test_date_search_error(self, service):
        """Test graceful handling of date_search errors."""
        with patch.object(service, '_get_user_calendar') as mock_get_cal:
            mock_calendar = Mock()
            mock_calendar.date_search.side_effect = Exception("Connection error")
            mock_get_cal.return_value = mock_calendar

            start = datetime.now(pytz.UTC)
            end = start + timedelta(hours=1)

            conflicts = service._find_conflicts("user123", start, end)
            assert conflicts == []


class TestConflictIntegration:
    """Integration tests for conflict detection in create/update."""

    @pytest.fixture
    def service(self):
        """Create RadicaleService instance."""
        return RadicaleService()

    def test_create_event_logs_conflict_warning(self, service, caplog):
        """Test that create_event logs warning when conflict detected."""
        import logging

        with patch.object(service, '_get_user_calendar') as mock_get_cal, \
             patch.object(service, '_find_conflicts') as mock_find:

            mock_calendar = Mock()
            mock_calendar.save_event = Mock()
            mock_get_cal.return_value = mock_calendar

            # Mock conflict found
            mock_find.return_value = [
                {'uid': 'conflict-uid', 'summary': 'Existing Meeting',
                 'start': datetime.now(pytz.UTC), 'end': datetime.now(pytz.UTC)}
            ]

            event = EventDTO(
                title="New Meeting",
                start_time=datetime.now(pytz.UTC) + timedelta(hours=1),
                duration_minutes=60
            )

            # Should still create event (warning only)
            uid = service._create_event_sync("user123", event)

            # Event should be created despite conflict
            assert uid is not None
            mock_calendar.save_event.assert_called_once()

    def test_update_event_logs_conflict_warning(self, service):
        """Test that update_event logs warning when conflict detected."""
        with patch.object(service, '_get_user_calendar') as mock_get_cal, \
             patch.object(service, '_find_conflicts') as mock_find:

            mock_calendar = Mock()

            # Create mock existing event
            existing_start = datetime(2026, 1, 15, 10, 0, 0, tzinfo=pytz.UTC)
            existing_end = datetime(2026, 1, 15, 11, 0, 0, tzinfo=pytz.UTC)
            ical_data = f"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:event-to-update
SUMMARY:Original Title
DTSTART:{existing_start.strftime('%Y%m%dT%H%M%SZ')}
DTEND:{existing_end.strftime('%Y%m%dT%H%M%SZ')}
END:VEVENT
END:VCALENDAR"""
            mock_event = Mock()
            mock_event.data = ical_data
            mock_event.save = Mock()

            mock_calendar.events.return_value = [mock_event]
            mock_get_cal.return_value = mock_calendar

            # Mock conflict found
            mock_find.return_value = [
                {'uid': 'conflict-uid', 'summary': 'Conflicting Meeting',
                 'start': datetime.now(pytz.UTC), 'end': datetime.now(pytz.UTC)}
            ]

            updated_event = EventDTO(
                title="Updated Title",
                start_time=datetime.now(pytz.UTC) + timedelta(hours=1),
                duration_minutes=60
            )

            # Should still update event (warning only)
            result = service._update_event_sync("user123", "event-to-update", updated_event)

            # Update should succeed despite conflict
            assert result is True
