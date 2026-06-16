from fbf_purge.canvas.client import CanvasClient
from fbf_purge.canvas.models import Course
from fbf_purge.classifier.patterns import Patterns
from fbf_purge.classifier.rules import classify_event, resolve_assignment_id_for_event
from fbf_purge.services.purge import _build_fbf_assignment_index


async def list_teacher_courses(client: CanvasClient) -> list[Course]:
    return await client.list_courses_for_user()


async def inspect_course(
    client: CanvasClient,
    course_id: int,
    patterns: Patterns,
    sample_limit: int = 10,
) -> dict:
    events = await client.list_calendar_events(course_id)
    fbf_assignments = await _build_fbf_assignment_index(client, course_id, patterns)
    sample = events[:sample_limit]
    classified = []
    for event in events:
        is_fbf, reason = classify_event(event, patterns, fbf_assignments)
        assignment_id = resolve_assignment_id_for_event(
            event,
            patterns,
            fbf_assignments,
            is_fbf,
        )
        classified.append(
            {
                "id": event.id,
                "title": event.title,
                "is_fbf": is_fbf,
                "match_reason": reason,
                "canvas_assignment_id": assignment_id,
            }
        )
    return {
        "course_id": course_id,
        "total_events": len(events),
        "sample_events": [e.model_dump() for e in sample],
        "classified": classified,
    }
