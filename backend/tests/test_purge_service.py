from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from fbf_purge.canvas.models import AppointmentGroup, CalendarEvent, Course
from fbf_purge.services.purge import execute_purge, preview_purge
from tests.conftest import load_fixture


def _event_from_fixture(name: str) -> CalendarEvent:
    return CalendarEvent.from_canvas(load_fixture(name))


@pytest.mark.asyncio
async def test_preview_includes_assignment_calendar_fbf_all_day(patterns):
    client = MagicMock()
    client.base_url = "https://canvas.wisc.edu"
    client.get_course = AsyncMock(return_value=Course(id=1, name="Test Course"))
    client.list_calendar_events = AsyncMock(return_value=[])
    client.list_assignment_calendar_events = AsyncMock(
        return_value=[CalendarEvent.from_canvas(load_fixture("fbf_assignment_due_all_day.json"))]
    )
    client.list_appointment_groups = AsyncMock(return_value=[])
    client.list_course_assignments = AsyncMock(
        return_value=[load_fixture("fbf_external_tool_assignment.json")]
    )
    client.list_course_external_tools = AsyncMock(return_value=[])

    report = await preview_purge(client, 1, patterns)
    row = report.events[0]
    assert row.start_at == "2025-09-10T23:59:00-04:00"
    assert row.assignment_due_at == "2025-09-10T23:59:00-04:00"


@pytest.mark.asyncio
async def test_preview_includes_assignment_calendar_fbf(patterns):
    client = MagicMock()
    client.base_url = "https://canvas.wisc.edu"
    client.get_course = AsyncMock(return_value=Course(id=1, name="Test Course"))
    client.list_calendar_events = AsyncMock(return_value=[])
    client.list_assignment_calendar_events = AsyncMock(
        return_value=[CalendarEvent.from_canvas(load_fixture("fbf_assignment_due_calendar.json"))]
    )
    client.list_appointment_groups = AsyncMock(return_value=[])
    client.list_course_assignments = AsyncMock(
        return_value=[load_fixture("fbf_external_tool_assignment.json")]
    )
    client.list_course_external_tools = AsyncMock(return_value=[])

    report = await preview_purge(client, 1, patterns)
    assert report.matched_count == 1
    row = report.events[0]
    assert row.event_id == -100
    assert row.calendar_entry_kind == "assignment_due"
    assert row.event_category == "fbf"
    assert row.canvas_assignment_id == 100
    assert row.link_status == "linked"
    assert row.html_url == "https://canvas.wisc.edu/courses/12345/assignments/100"


@pytest.mark.asyncio
async def test_preview_includes_appointment_groups(patterns):
    client = MagicMock()
    client.base_url = "https://canvas.wisc.edu"
    client.get_course = AsyncMock(return_value=Course(id=1, name="Test Course"))
    client.list_calendar_events = AsyncMock(return_value=[])
    client.list_assignment_calendar_events = AsyncMock(return_value=[])
    client.list_appointment_groups = AsyncMock(
        return_value=[
            AppointmentGroup.from_canvas(load_fixture("appointment_group_office_hours.json"))
        ]
    )
    client.list_course_assignments = AsyncMock(return_value=[])
    client.list_course_external_tools = AsyncMock(return_value=[])

    report = await preview_purge(client, 1, patterns)
    assert report.user_count == 1
    group = report.events[0]
    assert group.title == "Office Hours Sign-up"
    assert group.appointment_group_id == 9653
    assert group.html_url == "https://canvas.wisc.edu/appointment_groups/9653"
    assert group.user_event_kind == "appointment_group"


@pytest.mark.asyncio
async def test_preview_purge_includes_human_events(patterns):
    client = MagicMock()
    client.base_url = "https://canvas.example.edu"
    client.get_course = AsyncMock(return_value=Course(id=1, name="Test Course"))
    client.list_calendar_events = AsyncMock(
        return_value=[
            _event_from_fixture("fbf_give_feedback.json"),
            _event_from_fixture("non_fbf_office_hours.json"),
        ]
    )
    client.list_assignment_calendar_events = AsyncMock(return_value=[])
    client.list_appointment_groups = AsyncMock(return_value=[])
    client.list_course_assignments = AsyncMock(return_value=[])
    client.list_course_external_tools = AsyncMock(return_value=[])

    report = await preview_purge(client, 1, patterns)
    assert report.matched_count == 1
    assert report.user_count == 1
    assert len(report.events) == 2
    user = next(e for e in report.events if e.event_category == "user")
    assert user.title == "Office Hours"
    assert user.html_url == "https://canvas.example.edu/calendar?event_id=99001&include_contexts=course_1"
    assert user.link_status == "unknown"


@pytest.mark.asyncio
async def test_preview_skips_hidden_events(patterns):
    hidden = load_fixture("non_fbf_office_hours.json")
    hidden["hidden"] = True
    client = MagicMock()
    client.base_url = "https://canvas.example.edu"
    client.get_course = AsyncMock(return_value=Course(id=1, name="Test Course"))
    client.list_calendar_events = AsyncMock(
        return_value=[CalendarEvent.from_canvas(hidden)]
    )
    client.list_assignment_calendar_events = AsyncMock(return_value=[])
    client.list_appointment_groups = AsyncMock(return_value=[])
    client.list_course_assignments = AsyncMock(return_value=[])
    client.list_course_external_tools = AsyncMock(return_value=[])

    report = await preview_purge(client, 1, patterns)
    assert report.user_count == 0
    assert len(report.events) == 0


@pytest.mark.asyncio
async def test_preview_purge_matched_only(patterns):
    client = MagicMock()
    client.base_url = "https://canvas.example.edu"
    client.get_course = AsyncMock(return_value=Course(id=1, name="Test Course"))
    client.list_calendar_events = AsyncMock(
        return_value=[
            _event_from_fixture("fbf_give_feedback.json"),
            _event_from_fixture("non_fbf_office_hours.json"),
        ]
    )
    client.list_assignment_calendar_events = AsyncMock(return_value=[])
    client.list_appointment_groups = AsyncMock(return_value=[])
    client.list_course_assignments = AsyncMock(return_value=[])
    client.list_course_external_tools = AsyncMock(return_value=[])

    report = await preview_purge(client, 1, patterns)
    assert report.dry_run is True
    assert report.matched_count == 1
    assert report.user_count == 1
    assert report.deleted_count == 0
    assert len(report.events) == 2
    fbf = next(e for e in report.events if e.event_category == "fbf")
    user = next(e for e in report.events if e.event_category == "user")
    assert fbf.status == "matched"
    assert user.title == "Office Hours"


@pytest.mark.asyncio
async def test_execute_purge_deletes_user_appointment_group(patterns):
    group = AppointmentGroup.from_canvas(load_fixture("appointment_group_office_hours.json"))
    client = MagicMock()
    client.base_url = "https://canvas.wisc.edu"
    client.get_course = AsyncMock(return_value=Course(id=1, name="Test Course"))
    client.list_calendar_events = AsyncMock(return_value=[])
    client.list_assignment_calendar_events = AsyncMock(return_value=[])
    client.list_appointment_groups = AsyncMock(return_value=[group])
    client.list_course_assignments = AsyncMock(return_value=[])
    client.list_course_external_tools = AsyncMock(return_value=[])
    client.delete_appointment_group = AsyncMock(return_value={})

    report = await execute_purge(client, 1, patterns, event_ids=[-9653])
    assert report.deleted_count == 1
    client.delete_appointment_group.assert_called_once_with(9653)


@pytest.mark.asyncio
async def test_execute_purge_deletes_user_calendar_event(patterns):
    user_event = _event_from_fixture("non_fbf_office_hours.json")
    client = MagicMock()
    client.base_url = "https://canvas.example.edu"
    client.get_course = AsyncMock(return_value=Course(id=1, name="Test Course"))
    client.list_calendar_events = AsyncMock(return_value=[user_event])
    client.list_appointment_groups = AsyncMock(return_value=[])
    client.list_course_assignments = AsyncMock(return_value=[])
    client.list_course_external_tools = AsyncMock(return_value=[])
    client.delete_calendar_event = AsyncMock(return_value={})

    report = await execute_purge(client, 1, patterns, event_ids=[user_event.id])
    assert report.deleted_count == 1
    assert report.events[0].event_category == "user"
    client.delete_calendar_event.assert_called_once_with(user_event.id)


@pytest.mark.asyncio
async def test_execute_purge_deletes_selected_only(patterns):
    fbf1 = _event_from_fixture("fbf_give_feedback.json")
    fbf2 = _event_from_fixture("fbf_read_feedback.json")
    client = MagicMock()
    client.base_url = "https://canvas.example.edu"
    client.get_course = AsyncMock(return_value=Course(id=1, name="Test Course"))
    client.list_calendar_events = AsyncMock(return_value=[fbf1, fbf2])
    client.list_appointment_groups = AsyncMock(return_value=[])
    client.list_course_assignments = AsyncMock(return_value=[])
    client.list_course_external_tools = AsyncMock(return_value=[])
    client.delete_calendar_event = AsyncMock(return_value={})

    report = await execute_purge(client, 1, patterns, event_ids=[fbf1.id])
    assert report.deleted_count == 1
    client.delete_calendar_event.assert_called_once_with(fbf1.id)


@pytest.mark.asyncio
async def test_preview_marks_orphan_assignment_due_calendar_entry(patterns):
    client = MagicMock()
    client.base_url = "https://canvas.example.edu"
    client.get_course = AsyncMock(return_value=Course(id=1, name="Test Course"))
    client.list_calendar_events = AsyncMock(return_value=[])
    client.list_assignment_calendar_events = AsyncMock(
        return_value=[CalendarEvent.from_canvas(load_fixture("canvas_assignment_due.json"))]
    )
    client.list_appointment_groups = AsyncMock(return_value=[])
    client.list_course_assignments = AsyncMock(return_value=[])
    client.list_course_external_tools = AsyncMock(return_value=[])

    report = await preview_purge(client, 1, patterns)
    assert len(report.events) == 1
    row = report.events[0]
    assert row.calendar_entry_kind == "assignment_due"
    assert row.canvas_assignment_id == 55001
    assert row.link_status == "orphan"
    assert "no longer exists" in (row.link_reason or "")


@pytest.mark.asyncio
async def test_preview_skips_undated_calendar_event(patterns):
    undated = {
        "id": 88499,
        "title": "Give Feedback - Ghost Activity",
        "description": "<a href=\"https://app.feedbackfruits.com/activities/xyz\">Open</a>",
        "html_url": "https://canvas.wisc.edu/calendar?event_id=88499",
        "context_code": "course_12345",
        "workflow_state": "active",
    }
    client = MagicMock()
    client.base_url = "https://canvas.wisc.edu"
    client.get_course = AsyncMock(return_value=Course(id=1, name="Test Course"))
    client.list_calendar_events = AsyncMock(
        return_value=[CalendarEvent.from_canvas(undated)]
    )
    client.list_assignment_calendar_events = AsyncMock(return_value=[])
    client.list_appointment_groups = AsyncMock(return_value=[])
    client.list_course_assignments = AsyncMock(return_value=[])
    client.list_course_external_tools = AsyncMock(return_value=[])

    report = await preview_purge(client, 1, patterns)
    assert report.matched_count == 0
    assert len(report.events) == 0


@pytest.mark.asyncio
async def test_preview_skips_assignment_due_when_calendar_event_exists(patterns):
    client = MagicMock()
    client.base_url = "https://canvas.wisc.edu"
    client.get_course = AsyncMock(return_value=Course(id=1, name="Test Course"))
    client.list_calendar_events = AsyncMock(
        return_value=[_event_from_fixture("fbf_linked_assignment.json")]
    )
    client.list_assignment_calendar_events = AsyncMock(
        return_value=[CalendarEvent.from_canvas(load_fixture("fbf_assignment_due_calendar.json"))]
    )
    client.list_appointment_groups = AsyncMock(return_value=[])
    client.list_course_assignments = AsyncMock(
        return_value=[load_fixture("fbf_external_tool_assignment.json")]
    )
    client.list_course_external_tools = AsyncMock(return_value=[])

    report = await preview_purge(client, 1, patterns)
    assert report.matched_count == 1
    assert len(report.events) == 1
    row = report.events[0]
    assert row.calendar_entry_kind == "calendar_event"
    assert row.canvas_assignment_id == 100


@pytest.mark.asyncio
async def test_preview_classifies_linkless_fbf_via_assignment_metadata(patterns):
    client = MagicMock()
    client.base_url = "https://canvas.wisc.edu"
    client.get_course = AsyncMock(return_value=Course(id=1, name="Test Course"))
    client.list_calendar_events = AsyncMock(
        return_value=[_event_from_fixture("fbf_unlinked_calendar_event.json")]
    )
    client.list_assignment_calendar_events = AsyncMock(return_value=[])
    client.list_appointment_groups = AsyncMock(return_value=[])
    client.list_course_assignments = AsyncMock(
        return_value=[load_fixture("fbf_external_tool_assignment.json")]
    )
    client.list_course_external_tools = AsyncMock(return_value=[])

    report = await preview_purge(client, 1, patterns)
    assert report.matched_count == 1
    assert report.user_count == 0
    fbf = report.events[0]
    assert fbf.event_category == "fbf"
    assert fbf.link_status == "unlinked"
    assert fbf.assignment_due_at == "2025-09-10T23:59:00-04:00"
    assert fbf.canvas_assignment_id == 100


@pytest.mark.asyncio
async def test_execute_purge_deletes_fbf_only(patterns):
    fbf = _event_from_fixture("fbf_give_feedback.json")
    client = MagicMock()
    client.base_url = "https://canvas.example.edu"
    client.get_course = AsyncMock(return_value=Course(id=1, name="Test Course"))
    client.list_calendar_events = AsyncMock(return_value=[fbf])
    client.list_appointment_groups = AsyncMock(return_value=[])
    client.list_course_assignments = AsyncMock(return_value=[])
    client.list_course_external_tools = AsyncMock(return_value=[])
    client.delete_calendar_event = AsyncMock(return_value={})

    report = await execute_purge(client, 1, patterns)
    assert report.dry_run is False
    assert report.deleted_count == 1
    client.delete_calendar_event.assert_called_once_with(fbf.id)
