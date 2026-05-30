from fbf_purge.canvas.models import CalendarEvent
from fbf_purge.classifier.rules import classify_event
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


def test_deleted_event_not_matched(patterns):
    data = load_fixture("fbf_give_feedback.json")
    data["workflow_state"] = "deleted"
    event = CalendarEvent.from_canvas(data)
    is_fbf, _ = classify_event(event, patterns)
    assert is_fbf is False
