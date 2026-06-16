from fbf_purge.canvas.models import CalendarEvent
from fbf_purge.classifier.rules import (
    classify_assignment_calendar_entry,
    is_active_assignment_calendar_item,
)
from tests.conftest import load_fixture


def test_is_active_assignment_calendar_item():
    event = CalendarEvent.from_canvas(load_fixture("fbf_assignment_due_calendar.json"))
    assert event.is_assignment_calendar is True
    assert event.id == -100
    assert is_active_assignment_calendar_item(event) is True


def test_classify_fbf_assignment_calendar_entry():
    event = CalendarEvent.from_canvas(load_fixture("fbf_assignment_due_calendar.json"))
    category, reason, assignment_id = classify_assignment_calendar_entry(
        event,
        {100},
        {100},
    )
    assert category == "fbf"
    assert assignment_id == 100
    assert "FBF assignment due" in reason


def test_classify_non_fbf_assignment_calendar_entry():
    event = CalendarEvent.from_canvas(load_fixture("canvas_assignment_due.json"))
    category, _, assignment_id = classify_assignment_calendar_entry(
        event,
        {100},
        {55001},
    )
    assert category == "user"
    assert assignment_id == 55001


def test_classify_orphan_assignment_calendar_entry():
    event = CalendarEvent.from_canvas(load_fixture("canvas_assignment_due.json"))
    category, reason, assignment_id = classify_assignment_calendar_entry(
        event,
        {100},
        set(),
    )
    assert category == "user"
    assert assignment_id == 55001
    assert "no longer exists" in reason
