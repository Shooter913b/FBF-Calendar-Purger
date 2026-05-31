from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from fbf_purge.canvas.models import CalendarEvent, Course
from fbf_purge.services.purge import execute_purge, preview_purge
from tests.conftest import load_fixture


def _event_from_fixture(name: str) -> CalendarEvent:
    return CalendarEvent.from_canvas(load_fixture(name))


@pytest.mark.asyncio
async def test_preview_purge_matched_only(patterns):
    client = MagicMock()
    client.get_course = AsyncMock(return_value=Course(id=1, name="Test Course"))
    client.list_calendar_events = AsyncMock(
        return_value=[
            _event_from_fixture("fbf_give_feedback.json"),
            _event_from_fixture("non_fbf_office_hours.json"),
        ]
    )
    client.list_active_assignment_ids = AsyncMock(return_value=set())

    report = await preview_purge(client, 1, patterns)
    assert report.dry_run is True
    assert report.matched_count == 1
    assert report.deleted_count == 0
    assert report.events[0].status == "matched"


@pytest.mark.asyncio
async def test_execute_purge_deletes_selected_only(patterns):
    fbf1 = _event_from_fixture("fbf_give_feedback.json")
    fbf2 = _event_from_fixture("fbf_read_feedback.json")
    client = MagicMock()
    client.get_course = AsyncMock(return_value=Course(id=1, name="Test Course"))
    client.list_calendar_events = AsyncMock(return_value=[fbf1, fbf2])
    client.list_active_assignment_ids = AsyncMock(return_value=set())
    client.delete_calendar_event = AsyncMock(return_value={})

    report = await execute_purge(client, 1, patterns, event_ids=[fbf1.id])
    assert report.deleted_count == 1
    client.delete_calendar_event.assert_called_once_with(fbf1.id)


@pytest.mark.asyncio
async def test_execute_purge_deletes_fbf_only(patterns):
    fbf = _event_from_fixture("fbf_give_feedback.json")
    client = MagicMock()
    client.get_course = AsyncMock(return_value=Course(id=1, name="Test Course"))
    client.list_calendar_events = AsyncMock(return_value=[fbf])
    client.list_active_assignment_ids = AsyncMock(return_value=set())
    client.delete_calendar_event = AsyncMock(return_value={})

    report = await execute_purge(client, 1, patterns)
    assert report.dry_run is False
    assert report.deleted_count == 1
    client.delete_calendar_event.assert_called_once_with(fbf.id)
