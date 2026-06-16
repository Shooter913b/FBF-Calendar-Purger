from fbf_purge.canvas.dates import event_has_calendar_date, resolve_assignment_calendar_dates
from fbf_purge.canvas.models import CalendarEvent
from tests.conftest import load_fixture


def test_event_has_calendar_date():
    event = CalendarEvent.from_canvas(load_fixture("fbf_give_feedback.json"))
    assert event_has_calendar_date(event) is True

    undated = CalendarEvent.from_canvas(
        {
            "id": 1,
            "title": "Ghost event",
            "workflow_state": "active",
            "type": "event",
        }
    )
    assert event_has_calendar_date(undated) is False


def test_resolve_assignment_calendar_dates_from_all_day_date():
    event = CalendarEvent.from_canvas(load_fixture("fbf_assignment_due_all_day.json"))
    start_at, due_at = resolve_assignment_calendar_dates(event)
    assert start_at == "2025-09-10T23:59:00"
    assert due_at == "2025-09-10T23:59:00"


def test_resolve_assignment_calendar_dates_prefers_course_due_at():
    event = CalendarEvent.from_canvas(load_fixture("fbf_assignment_due_all_day.json"))
    start_at, due_at = resolve_assignment_calendar_dates(
        event,
        assignment_due_from_course="2025-09-12T23:59:00-04:00",
    )
    assert due_at == "2025-09-12T23:59:00-04:00"
    assert start_at == "2025-09-12T23:59:00-04:00"


def test_resolve_assignment_calendar_dates_from_nested_assignment():
    data = load_fixture("fbf_assignment_due_all_day.json")
    data["assignment"] = {"id": 100, "due_at": "2025-09-11T23:59:00-04:00"}
    event = CalendarEvent.from_canvas(data)
    start_at, due_at = resolve_assignment_calendar_dates(event)
    assert due_at == "2025-09-11T23:59:00-04:00"
    assert start_at == "2025-09-11T23:59:00-04:00"
