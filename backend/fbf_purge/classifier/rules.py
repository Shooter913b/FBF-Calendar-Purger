import re

from fbf_purge.canvas.models import CalendarEvent
from fbf_purge.classifier.assignments import FbfAssignmentIndex
from fbf_purge.classifier.links import classify_assignment_link
from fbf_purge.classifier.patterns import Patterns
from fbf_purge.classifier.text import normalize_title


def classify_event(
    event: CalendarEvent,
    patterns: Patterns,
    fbf_assignments: FbfAssignmentIndex | None = None,
) -> tuple[bool, str | None]:
    if event.workflow_state == "deleted":
        return False, None

    title = event.title or ""

    for pattern in patterns.exclude_title_regex:
        if re.search(pattern, title, re.IGNORECASE):
            return False, "excluded by title regex"

    haystacks = [
        (event.description or "").lower(),
        (event.html_url or "").lower(),
    ]

    for domain in patterns.domains:
        domain_lower = domain.lower()
        for hay in haystacks:
            if domain_lower in hay:
                return True, f"domain match: {domain}"

    for sub in patterns.description_substrings:
        sub_lower = sub.lower()
        if sub_lower in (event.description or "").lower():
            return True, f"description substring: {sub}"

    sep = patterns.title_suffix_separator
    normalized_title = normalize_title(title, sep)
    sep_norm = sep.strip().casefold()
    for prefix in patterns.title_step_prefixes:
        prefix_norm = prefix.casefold()
        if normalized_title.startswith(prefix_norm) and sep_norm in normalized_title:
            return True, f"title step prefix: {prefix}"

    if fbf_assignments is not None:
        matched = fbf_assignments.match_event(event, patterns)
        if matched:
            assignment_id, reason = matched
            return True, f"{reason} (assignment {assignment_id})"

    return False, None


def resolve_assignment_id_for_event(
    event: CalendarEvent,
    patterns: Patterns,
    fbf_assignments: FbfAssignmentIndex | None,
    is_fbf: bool,
) -> int | None:
    from fbf_purge.classifier.links import parse_canvas_assignment_id

    assignment_id = parse_canvas_assignment_id(event)
    if assignment_id is not None:
        return assignment_id
    if is_fbf and fbf_assignments is not None:
        matched = fbf_assignments.match_event(event, patterns)
        if matched:
            return matched[0]
    return None


def is_active_calendar_item(event: CalendarEvent) -> bool:
    if event.workflow_state == "deleted":
        return False
    if event.hidden:
        return False
    if event.is_assignment_calendar or event.canvas_item_type != "event":
        return False
    return True


def is_active_assignment_calendar_item(event: CalendarEvent) -> bool:
    if event.workflow_state == "deleted":
        return False
    if event.hidden:
        return False
    if not event.is_assignment_calendar:
        return False
    return abs(event.id) > 0


def classify_assignment_calendar_entry(
    event: CalendarEvent,
    fbf_assignment_ids: set[int],
    active_assignment_ids: set[int],
) -> tuple[str, str, int]:
    assignment_id = abs(event.id)
    link_status, link_reason, _ = classify_assignment_link(
        assignment_id,
        active_assignment_ids,
    )
    if link_status == "orphan":
        return (
            "user",
            link_reason
            or f"Orphan assignment due on calendar (assignment {assignment_id})",
            assignment_id,
        )
    if assignment_id in fbf_assignment_ids:
        return (
            "fbf",
            f"FBF assignment due on calendar (assignment {assignment_id})",
            assignment_id,
        )
    return (
        "user",
        f"Assignment due on calendar (assignment {assignment_id})",
        assignment_id,
    )


def is_user_calendar_event(
    event: CalendarEvent,
    patterns: Patterns,
    fbf_assignments: FbfAssignmentIndex | None = None,
) -> bool:
    """User-created custom calendar events (type=event, not FBF)."""
    if not is_active_calendar_item(event):
        return False
    if event.appointment_group_id:
        return False
    is_fbf, _ = classify_event(event, patterns, fbf_assignments)
    return not is_fbf


def is_instructor_calendar_event(
    event: CalendarEvent,
    patterns: Patterns,
    fbf_assignments: FbfAssignmentIndex | None = None,
) -> bool:
    """Deprecated alias for is_user_calendar_event."""
    return is_user_calendar_event(event, patterns, fbf_assignments)


def classify_events(
    events: list[CalendarEvent],
    patterns: Patterns,
    fbf_assignments: FbfAssignmentIndex | None = None,
) -> tuple[list[CalendarEvent], list[CalendarEvent]]:
    fbf_events: list[CalendarEvent] = []
    other_events: list[CalendarEvent] = []
    for event in events:
        is_fbf, _ = classify_event(event, patterns, fbf_assignments)
        if is_fbf:
            fbf_events.append(event)
        else:
            other_events.append(event)
    return fbf_events, other_events
