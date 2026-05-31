import re
from typing import Literal

from fbf_purge.canvas.models import CalendarEvent

LinkStatus = Literal["orphan", "linked", "unknown"]

CANVAS_ASSIGNMENT_RE = re.compile(
    r"/courses/\d+/assignments/(\d+)",
    re.IGNORECASE,
)


def parse_canvas_assignment_id(event: CalendarEvent) -> int | None:
    for hay in (event.description or "", event.html_url or ""):
        match = CANVAS_ASSIGNMENT_RE.search(hay)
        if match:
            return int(match.group(1))
    return None


def classify_event_link(
    event: CalendarEvent,
    active_assignment_ids: set[int],
) -> tuple[LinkStatus, str | None, int | None]:
    assignment_id = parse_canvas_assignment_id(event)
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
