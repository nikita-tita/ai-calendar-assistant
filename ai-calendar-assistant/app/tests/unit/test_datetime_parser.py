"""Test datetime parsing utilities."""

import pytest
from datetime import datetime, timedelta
from app.utils.datetime_parser import extract_duration, parse_datetime_range


def test_extract_duration_hours():
    """Test duration extraction in hours."""
    assert extract_duration("на час") == 60
    assert extract_duration("на 2 часа") == 120


def test_extract_duration_minutes():
    """Test duration extraction in minutes."""
    assert extract_duration("на 30 минут") == 30
    assert extract_duration("на полчаса") == 30


def test_extract_duration_not_found():
    """Test when duration is not found."""
    assert extract_duration("встреча с командой") is None


def test_parse_datetime_range_basic():
    """Test basic datetime range parsing."""
    text = "в 10:00 на час"
    start, end, duration = parse_datetime_range(text)

    # Should parse time (date may vary)
    assert start is not None
    assert start.hour == 10
    assert start.minute == 0
    assert duration == 60


@pytest.mark.skip(reason="Integration test - requires specific date context")
def test_parse_datetime_range_tomorrow():
    """Test parsing 'tomorrow'."""
    text = "завтра в 15:00"
    start, end, duration = parse_datetime_range(text)

    tomorrow = datetime.now() + timedelta(days=1)
    assert start.day == tomorrow.day
    assert start.hour == 15
