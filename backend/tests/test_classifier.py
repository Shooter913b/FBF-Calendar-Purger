from fbf_purge.canvas.models import CalendarEvent
from fbf_purge.classifier.rules import classify_event, is_instructor_calendar_event
from tests.conftest import load_fixture


def test_fbf_give_feedback_matches(patterns):
    event = CalendarEvent.from_canvas(load_fixture("fbf_give_feedback.json"))
    is_fbf, reason = classify_event(event, patterns)
    assert is_fbf is True
    assert reason is not None


def test_fbf_read_feedback_matches(patterns):
    event = CalendarEvent.from_canvas(load_fixture("fbf_read_feedback.json"))
    is_fbf, reason = classify_event(event, patterns)
    assert is_fbf is True


def test_office_hours_not_fbf(patterns):
    event = CalendarEvent.from_canvas(load_fixture("non_fbf_office_hours.json"))
    is_fbf, _ = classify_event(event, patterns)
    assert is_fbf is False


def test_office_hours_is_instructor_event(patterns):
    event = CalendarEvent.from_canvas(load_fixture("non_fbf_office_hours.json"))
    assert is_instructor_calendar_event(event, patterns) is True


def test_assignment_due_is_not_instructor_event(patterns):
    event = CalendarEvent.from_canvas(load_fixture("canvas_assignment_due.json"))
    assert is_instructor_calendar_event(event, patterns) is False


def test_fbf_not_instructor_event(patterns):
    event = CalendarEvent.from_canvas(load_fixture("fbf_give_feedback.json"))
    assert is_instructor_calendar_event(event, patterns) is False


def test_linked_non_fbf_is_instructor_event(patterns):
    linked = CalendarEvent.from_canvas(load_fixture("fbf_linked_assignment.json"))
    assert is_instructor_calendar_event(linked, patterns) is False


def test_deleted_event_not_matched(patterns):
    data = load_fixture("fbf_give_feedback.json")
    data["workflow_state"] = "deleted"
    event = CalendarEvent.from_canvas(data)
    is_fbf, _ = classify_event(event, patterns)
    assert is_fbf is False
