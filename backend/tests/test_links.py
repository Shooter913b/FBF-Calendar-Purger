import pytest

from fbf_purge.canvas.models import CalendarEvent
from fbf_purge.classifier.links import (
    classify_event_assignment_link,
    classify_inferred_assignment_link,
    classify_event_link,
    parse_canvas_assignment_id,
)
from tests.conftest import load_fixture


def test_parse_canvas_assignment_id_from_description():
    event = CalendarEvent.from_canvas(load_fixture("fbf_orphan_deleted_assignment.json"))
    assert parse_canvas_assignment_id(event) == 99999


def test_parse_canvas_assignment_id_missing():
    event = CalendarEvent.from_canvas(load_fixture("fbf_read_feedback.json"))
    assert parse_canvas_assignment_id(event) is None


def test_classify_orphan():
    event = CalendarEvent.from_canvas(load_fixture("fbf_orphan_deleted_assignment.json"))
    status, reason, assignment_id = classify_event_link(event, {100, 200})
    assert status == "orphan"
    assert assignment_id == 99999
    assert "no longer exists" in (reason or "")


def test_assignment_calendar_item_parses():
    event = CalendarEvent.from_canvas(load_fixture("canvas_assignment_due.json"))
    assert event.is_assignment_calendar is True
    assert event.id == -55001
    assert parse_canvas_assignment_id(event) == 55001


def test_classify_assignment_calendar_linked():
    event = CalendarEvent.from_canvas(load_fixture("canvas_assignment_due.json"))
    status, reason, assignment_id = classify_event_link(event, {55001})
    assert status == "linked"
    assert assignment_id == 55001


def test_classify_linked():
    event = CalendarEvent.from_canvas(load_fixture("fbf_linked_assignment.json"))
    status, reason, assignment_id = classify_event_link(event, {100, 200})
    assert status == "linked"
    assert assignment_id == 100
    assert "active assignment" in (reason or "")


def test_classify_unknown():
    event = CalendarEvent.from_canvas(load_fixture("fbf_read_feedback.json"))
    status, reason, _ = classify_event_link(event, {100})
    assert status == "unknown"
    assert "No Canvas assignment link" in (reason or "")


def test_classify_inferred_unlinked():
    event = CalendarEvent.from_canvas(load_fixture("fbf_unlinked_calendar_event.json"))
    status, reason, assignment_id = classify_event_assignment_link(
        event,
        {100},
        inferred_assignment_id=100,
    )
    assert status == "unlinked"
    assert assignment_id == 100
    assert "no link in event" in (reason or "")


def test_classify_inferred_orphan():
    event = CalendarEvent.from_canvas(load_fixture("fbf_unlinked_calendar_event.json"))
    status, _, assignment_id = classify_inferred_assignment_link(99999, {100})
    assert status == "orphan"
    assert assignment_id == 99999


@pytest.mark.asyncio
async def test_preview_marks_orphan_count(patterns):
    from unittest.mock import AsyncMock, MagicMock

    from fbf_purge.canvas.models import Course
    from fbf_purge.services.purge import preview_purge

    orphan = CalendarEvent.from_canvas(load_fixture("fbf_orphan_deleted_assignment.json"))
    linked = CalendarEvent.from_canvas(load_fixture("fbf_linked_assignment.json"))
    client = MagicMock()
    client.get_course = AsyncMock(return_value=Course(id=1, name="Test Course"))
    client.list_calendar_events = AsyncMock(return_value=[orphan, linked])
    client.list_assignment_calendar_events = AsyncMock(return_value=[])
    client.list_appointment_groups = AsyncMock(return_value=[])
    client.list_course_assignments = AsyncMock(return_value=[{"id": 100, "workflow_state": "published"}])
    client.list_course_external_tools = AsyncMock(return_value=[])

    report = await preview_purge(client, 1, patterns)
    assert report.matched_count == 2
    assert report.orphan_count == 1
    by_id = {e.event_id: e for e in report.events}
    assert by_id[99001].link_status == "orphan"
    assert by_id[99002].link_status == "linked"
