from fbf_purge.canvas.models import CalendarEvent
from fbf_purge.classifier.assignments import (
    FbfAssignmentIndex,
    FbfToolCatalog,
    is_fbf_assignment,
)
from fbf_purge.classifier.rules import classify_event, is_instructor_calendar_event
from tests.conftest import load_fixture


def test_is_fbf_external_tool_assignment(patterns):
    assignment = load_fixture("fbf_external_tool_assignment.json")
    assert is_fbf_assignment(assignment, patterns) is True


def test_institution_external_tool_assignment_matches_tool_catalog(patterns):
    assignment = load_fixture("fbf_institution_external_tool_assignment.json")
    tool = load_fixture("fbf_external_tool.json")
    catalog = FbfToolCatalog.from_external_tools([tool], patterns)
    assert catalog.has_fbf_tools is True
    assert is_fbf_assignment(assignment, patterns, catalog) is True


def test_non_fbf_assignment_not_matched(patterns):
    assignment = {
        "id": 1,
        "name": "Essay 1",
        "submission_types": ["online_upload"],
    }
    assert is_fbf_assignment(assignment, patterns) is False


def test_unlinked_calendar_event_matches_fbf_assignment_metadata(patterns):
    event = CalendarEvent.from_canvas(load_fixture("fbf_unlinked_calendar_event.json"))
    assignment = load_fixture("fbf_external_tool_assignment.json")
    index = FbfAssignmentIndex.from_course_assignments([assignment], patterns)

    is_fbf, reason = classify_event(event, patterns, index)
    assert is_fbf is True
    assert reason is not None
    assert "assignment 100" in reason
    assert is_instructor_calendar_event(event, patterns, index) is False


def test_unlinked_calendar_event_matches_via_institution_tool_url(patterns):
    event = CalendarEvent.from_canvas(load_fixture("fbf_unlinked_calendar_event.json"))
    assignment = load_fixture("fbf_institution_external_tool_assignment.json")
    tool = load_fixture("fbf_external_tool.json")
    index = FbfAssignmentIndex.from_course_assignments([assignment], patterns, [tool])

    is_fbf, reason = classify_event(event, patterns, index)
    assert is_fbf is True
    assert "assignment 101" in reason


def test_unlinked_calendar_event_not_fbf_without_assignment_index(patterns):
    event = CalendarEvent.from_canvas(load_fixture("fbf_unlinked_calendar_event.json"))
    is_fbf, _ = classify_event(event, patterns)
    assert is_fbf is False
    assert is_instructor_calendar_event(event, patterns) is True


def test_step_title_matches_fbf_assignment(patterns):
    data = load_fixture("fbf_unlinked_calendar_event.json")
    data["title"] = "Give Feedback - Peer Review Essay 1"
    event = CalendarEvent.from_canvas(data)
    assignment = load_fixture("fbf_external_tool_assignment.json")
    index = FbfAssignmentIndex.from_course_assignments([assignment], patterns)

    matched = index.match_event(event, patterns)
    assert matched is not None
    assert matched[0] == 100


def test_en_dash_step_title_classifies_as_fbf(patterns):
    data = load_fixture("fbf_unlinked_calendar_event.json")
    data["title"] = "Give Feedback \u2013 Peer Review Essay 1"
    event = CalendarEvent.from_canvas(data)
    is_fbf, reason = classify_event(event, patterns)
    assert is_fbf is True
    assert reason is not None
