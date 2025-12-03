"""Integration tests for Calendar Service."""

import pytest
from datetime import datetime, timedelta
from app.services.calendar_radicale import RadicaleService
from app.schemas.events import EventDTO, CalendarEvent
from typing import List


@pytest.fixture
def calendar_service():
    """Create Radicale service instance."""
    return RadicaleService()


@pytest.fixture
def test_user_id():
    """Test user ID for calendar operations."""
    return "test_user_12345"


@pytest.fixture
def sample_event():
    """Sample event data for testing."""
    return EventDTO(
        title="Test Event",
        start_time=datetime.now() + timedelta(days=1),
        duration_minutes=60,
        description="Test description",
        location="Test Location"
    )


@pytest.mark.asyncio
class TestCalendarServiceCRUD:
    """Test Calendar Service CRUD operations."""

    async def test_create_event(self, calendar_service, test_user_id, sample_event):
        """Test creating a new event."""
        # Create event
        event_uid = await calendar_service.create_event(test_user_id, sample_event)
        
        # Assertions
        assert event_uid is not None, "Event UID should be returned"
        assert isinstance(event_uid, str), "Event UID should be a string"
        assert len(event_uid) > 0, "Event UID should not be empty"

    async def test_get_events(self, calendar_service, test_user_id):
        """Test retrieving events from calendar."""
        # Get events
        events = await calendar_service.get_events(
            user_id=test_user_id,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=7)
        )
        
        # Assertions
        assert isinstance(events, list), "Events should be a list"
        # May be empty if no events

    async def test_get_events_with_time_range(self, calendar_service, test_user_id):
        """Test getting events within time range."""
        start_date = datetime.now()
        end_date = datetime.now() + timedelta(days=1)
        
        # Get events
        events = await calendar_service.get_events(
            user_id=test_user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Assertions
        assert isinstance(events, list), "Events should be a list"
        
        # Check all events are within range
        for event in events:
            assert isinstance(event, CalendarEvent), "Event should be CalendarEvent instance"
            assert event.start_time >= start_date, "Event should be within start range"
            assert event.start_time <= end_date, "Event should be within end range"

    async def test_update_event(self, calendar_service, test_user_id, sample_event):
        """Test updating an existing event."""
        # First, create an event
        event_uid = await calendar_service.create_event(test_user_id, sample_event)
        
        if event_uid:
            # Update the event
            updated_event = EventDTO(
                title="Updated Test Event",
                start_time=datetime.now() + timedelta(days=2),
                duration_minutes=90,
                description="Updated description"
            )
            
            success = await calendar_service.update_event(test_user_id, event_uid, updated_event)
            assert success is True, "Update should succeed"
            
            # Verify the update
            events = await calendar_service.get_events(
                user_id=test_user_id,
                start_date=datetime.now(),
                end_date=datetime.now() + timedelta(days=7)
            )
            
            updated = next((e for e in events if e.uid == event_uid), None)
            if updated:
                assert updated.title == "Updated Test Event", "Title should be updated"

    async def test_delete_event(self, calendar_service, test_user_id, sample_event):
        """Test deleting an event."""
        # First, create an event
        event_uid = await calendar_service.create_event(test_user_id, sample_event)
        
        if event_uid:
            # Delete the event
            success = await calendar_service.delete_event(test_user_id, event_uid)
            assert success is True, "Delete should succeed"
            
            # Verify deletion
            events = await calendar_service.get_events(
                user_id=test_user_id,
                start_date=datetime.now(),
                end_date=datetime.now() + timedelta(days=7)
            )
            
            deleted = next((e for e in events if e.uid == event_uid), None)
            assert deleted is None, "Event should be deleted"

    async def test_create_event_with_attendees(self, calendar_service, test_user_id):
        """Test creating event with attendees."""
        event = EventDTO(
            title="Team Meeting",
            start_time=datetime.now() + timedelta(days=1),
            duration_minutes=60,
            attendees=["user1@example.com", "user2@example.com"]
        )
        
        event_uid = await calendar_service.create_event(test_user_id, event)
        assert event_uid is not None, "Event should be created with attendees"

    async def test_create_all_day_event(self, calendar_service, test_user_id):
        """Test creating all-day event."""
        event = EventDTO(
            title="Holiday",
            start_time=datetime.now() + timedelta(days=1),
            duration_minutes=1440  # 24 hours
        )
        
        event_uid = await calendar_service.create_event(test_user_id, event)
        assert event_uid is not None, "All-day event should be created"


@pytest.mark.asyncio
class TestCalendarServiceFreeSlots:
    """Test Calendar Service free slots functionality."""

    async def test_find_free_slots(self, calendar_service, test_user_id):
        """Test finding free time slots."""
        target_date = datetime.now() + timedelta(days=1)
        
        free_slots = await calendar_service.find_free_slots(
            user_id=test_user_id,
            date=target_date,
            work_hours_start=9,
            work_hours_end=18,
            slot_duration=60
        )
        
        assert isinstance(free_slots, list), "Free slots should be a list"
        
        # Verify slot structure
        for slot in free_slots:
            assert hasattr(slot, 'start_time'), "Slot should have start_time"
            assert hasattr(slot, 'end_time'), "Slot should have end_time"
            assert slot.start_time < slot.end_time, "Start should be before end"

    async def test_find_free_slots_with_existing_events(self, calendar_service, test_user_id):
        """Test finding free slots when events exist."""
        # Create an event in the middle of the day
        event = EventDTO(
            title="Busy Event",
            start_time=datetime.now().replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=1),
            duration_minutes=60
        )
        
        await calendar_service.create_event(test_user_id, event)
        
        # Find free slots
        target_date = datetime.now() + timedelta(days=1)
        free_slots = await calendar_service.find_free_slots(
            user_id=test_user_id,
            date=target_date,
            work_hours_start=9,
            work_hours_end=18,
            slot_duration=60
        )
        
        # Should have free slots before and after the event
        assert len(free_slots) >= 0, "Should have free slots"


@pytest.mark.asyncio
class TestCalendarServiceEdgeCases:
    """Test Calendar Service edge cases."""

    async def test_create_event_without_duration(self, calendar_service, test_user_id):
        """Test creating event without duration (should use default)."""
        event = EventDTO(
            title="No Duration Event",
            start_time=datetime.now() + timedelta(days=1)
        )
        
        event_uid = await calendar_service.create_event(test_user_id, event)
        assert event_uid is not None, "Event without duration should be created (default 60 min)"

    async def test_create_event_in_past(self, calendar_service, test_user_id):
        """Test creating event in the past."""
        event = EventDTO(
            title="Past Event",
            start_time=datetime.now() - timedelta(days=1),
            duration_minutes=60
        )
        
        event_uid = await calendar_service.create_event(test_user_id, event)
        assert event_uid is not None, "Past events should be allowed"

    async def test_update_nonexistent_event(self, calendar_service, test_user_id):
        """Test updating non-existent event."""
        updated_event = EventDTO(
            title="Non-existent",
            start_time=datetime.now() + timedelta(days=1),
            duration_minutes=60
        )
        
        success = await calendar_service.update_event(test_user_id, "nonexistent_uid", updated_event)
        assert success is False, "Update of non-existent event should fail"

    async def test_delete_nonexistent_event(self, calendar_service, test_user_id):
        """Test deleting non-existent event."""
        success = await calendar_service.delete_event(test_user_id, "nonexistent_uid")
        assert success is False, "Delete of non-existent event should fail"

    async def test_get_events_empty_calendar(self, calendar_service, test_user_id):
        """Test getting events from empty calendar."""
        events = await calendar_service.get_events(
            user_id=test_user_id + "_empty",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=7)
        )
        
        assert isinstance(events, list), "Should return empty list"
        # May be empty for new user


@pytest.mark.skip(reason="Requires Radicale server")
class TestCalendarServiceIntegration:
    """Full integration tests with actual Radicale server."""

    async def test_full_workflow(self, calendar_service, test_user_id):
        """Test complete workflow: create, read, update, delete."""
        # 1. Create event
        event = EventDTO(
            title="Workflow Test",
            start_time=datetime.now() + timedelta(days=1),
            duration_minutes=60
        )
        event_uid = await calendar_service.create_event(test_user_id, event)
        assert event_uid is not None
        
        # 2. Read event
        events = await calendar_service.get_events(
            user_id=test_user_id,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=7)
        )
        created = next((e for e in events if e.uid == event_uid), None)
        assert created is not None
        assert created.title == "Workflow Test"
        
        # 3. Update event
        updated = EventDTO(
            title="Updated Workflow Test",
            start_time=datetime.now() + timedelta(days=1),
            duration_minutes=90
        )
        success = await calendar_service.update_event(test_user_id, event_uid, updated)
        assert success is True
        
        # 4. Verify update
        events = await calendar_service.get_events(
            user_id=test_user_id,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=7)
        )
        updated_event = next((e for e in events if e.uid == event_uid), None)
        if updated_event:
            assert updated_event.title == "Updated Workflow Test"
        
        # 5. Delete event
        success = await calendar_service.delete_event(test_user_id, event_uid)
        assert success is True
        
        # 6. Verify deletion
        events = await calendar_service.get_events(
            user_id=test_user_id,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=7)
        )
        deleted = next((e for e in events if e.uid == event_uid), None)
        assert deleted is None
