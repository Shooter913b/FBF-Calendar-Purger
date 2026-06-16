from fbf_purge.canvas.models import CalendarEvent
from fbf_purge.canvas.urls import (
    resolve_appointment_group_html_url,
    resolve_assignment_html_url,
    resolve_calendar_html_url,
)
from tests.conftest import load_fixture


def test_resolve_appointment_group_html_url():
    url = resolve_appointment_group_html_url(
        "https://canvas.wisc.edu",
        9653,
        "https://canvas.wisc.edu/appointment_groups/9653",
    )
    assert url == "https://canvas.wisc.edu/appointment_groups/9653"


def test_resolve_appointment_group_html_url_builds_when_missing():
    url = resolve_appointment_group_html_url("https://canvas.wisc.edu", 9653, None)
    assert url == "https://canvas.wisc.edu/appointment_groups/9653"


def test_resolve_calendar_html_url_from_api():
    event = CalendarEvent.from_canvas(load_fixture("fbf_give_feedback.json"))
    url = resolve_calendar_html_url("https://canvas.example.edu", 12345, event)
    assert url == "https://canvas.example.edu/calendar?event_id=88421"


def test_resolve_calendar_html_url_builds_when_missing():
    event = CalendarEvent.from_canvas(load_fixture("non_fbf_office_hours.json"))
    url = resolve_calendar_html_url("https://canvas.wisc.edu", 12345, event)
    assert url == "https://canvas.wisc.edu/calendar?event_id=99001&include_contexts=course_12345"


def test_resolve_calendar_html_url_none_for_assignment():
    event = CalendarEvent.from_canvas(load_fixture("canvas_assignment_due.json"))
    assert resolve_calendar_html_url("https://canvas.example.edu", 1, event) is None


def test_resolve_assignment_html_url():
    event = CalendarEvent.from_canvas(load_fixture("fbf_assignment_due_calendar.json"))
    url = resolve_assignment_html_url("https://canvas.wisc.edu", 482667, event)
    assert url == "https://canvas.wisc.edu/courses/12345/assignments/100"
