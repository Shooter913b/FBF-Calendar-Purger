from __future__ import annotations

from fbf_purge.canvas.models import CalendarEvent


def event_has_calendar_date(event: CalendarEvent) -> bool:
    """True when Canvas can place this row on the calendar grid."""
    return bool(event.start_at or event.end_at or event.all_day_date)


def resolve_assignment_calendar_dates(
    event: CalendarEvent,
    assignment_due_from_course: str | None = None,
    assignment_due_from_fbf: str | None = None,
) -> tuple[str | None, str | None]:
    """Resolve display/filter dates for type=assignment calendar rows."""
    due = (
        assignment_due_from_course
        or assignment_due_from_fbf
        or event.assignment_due_at
        or event.start_at
        or event.end_at
    )
    if due is None and event.all_day_date:
        due = f"{event.all_day_date}T23:59:00"

    start = event.start_at or event.end_at or due
    assignment_due = due or start
    return start, assignment_due
