from fbf_purge.canvas.models import CalendarEvent


def _absolute_url(base_url: str, url: str) -> str:
    if url.startswith("/"):
        return f"{base_url.rstrip('/')}{url}"
    return url


def resolve_appointment_group_html_url(base_url: str, group_id: int, existing: str | None) -> str:
    url = (existing or "").strip()
    if url:
        return _absolute_url(base_url, url)
    return f"{base_url.rstrip('/')}/appointment_groups/{group_id}"


def resolve_assignment_html_url(
    base_url: str,
    course_id: int,
    event: CalendarEvent,
) -> str | None:
    """User-facing Canvas assignment URL for a type=assignment calendar entry."""
    if not event.is_assignment_calendar:
        return None

    url = (event.html_url or "").strip()
    if url:
        return _absolute_url(base_url, url)

    assignment_id = abs(event.id)
    return f"{base_url.rstrip('/')}/courses/{course_id}/assignments/{assignment_id}"


def resolve_calendar_html_url(
    base_url: str,
    course_id: int,
    event: CalendarEvent,
) -> str | None:
    """User-facing Canvas calendar URL for a custom calendar event (type=event)."""
    if event.is_assignment_calendar or event.id <= 0:
        return None

    url = (event.html_url or "").strip()
    if url:
        if url.startswith("/"):
            return _absolute_url(base_url, url)
        if "/api/v1/" not in url:
            return url

    context = event.context_code or f"course_{course_id}"
    return (
        f"{base_url.rstrip('/')}/calendar?event_id={event.id}"
        f"&include_contexts={context}"
    )
