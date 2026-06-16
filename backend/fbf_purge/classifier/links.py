import re
from typing import Literal

from fbf_purge.canvas.models import CalendarEvent

LinkStatus = Literal["orphan", "linked", "unlinked", "unknown"]

CANVAS_ASSIGNMENT_RE = re.compile(
    r"/courses/\d+/assignments/(\d+)",
    re.IGNORECASE,
)


def parse_canvas_assignment_id(event: CalendarEvent) -> int | None:
    if event.is_assignment_calendar:
        return abs(event.id)
    for hay in (event.description or "", event.html_url or ""):
        match = CANVAS_ASSIGNMENT_RE.search(hay)
        if match:
            return int(match.group(1))
    return None


def classify_assignment_link(
    assignment_id: int | None,
    active_assignment_ids: set[int],
) -> tuple[LinkStatus, str | None, int | None]:
    if assignment_id is None:
        return (
            "unknown",
            "No Canvas assignment link found in event",
            None,
        )
    if assignment_id not in active_assignment_ids:
        return (
            "orphan",
            f"Assignment {assignment_id} no longer exists in this course",
            assignment_id,
        )
    return (
        "linked",
        f"Linked to active assignment {assignment_id}",
        assignment_id,
    )


def classify_inferred_assignment_link(
    assignment_id: int,
    active_assignment_ids: set[int],
) -> tuple[LinkStatus, str | None, int | None]:
    if assignment_id not in active_assignment_ids:
        return (
            "orphan",
            f"Inferred assignment {assignment_id} no longer exists in this course",
            assignment_id,
        )
    return (
        "unlinked",
        f"Matches active assignment {assignment_id} (no link in event)",
        assignment_id,
    )


def classify_event_assignment_link(
    event: CalendarEvent,
    active_assignment_ids: set[int],
    inferred_assignment_id: int | None = None,
) -> tuple[LinkStatus, str | None, int | None]:
    linked_id = parse_canvas_assignment_id(event)
    if linked_id is not None:
        return classify_assignment_link(linked_id, active_assignment_ids)
    if inferred_assignment_id is not None:
        return classify_inferred_assignment_link(inferred_assignment_id, active_assignment_ids)
    return (
        "unknown",
        "No Canvas assignment link found in event",
        None,
    )


def classify_event_link(
    event: CalendarEvent,
    active_assignment_ids: set[int],
) -> tuple[LinkStatus, str | None, int | None]:
    return classify_event_assignment_link(event, active_assignment_ids)
