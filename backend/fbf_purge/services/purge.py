from datetime import datetime, timezone

from fbf_purge.canvas.client import CanvasClient
from fbf_purge.canvas.models import PurgeEventResult, PurgeReport
from fbf_purge.classifier.patterns import Patterns
from fbf_purge.classifier.rules import classify_event
from fbf_purge.exceptions import CanvasAPIError, FBFError


async def preview_purge(
    client: CanvasClient,
    course_id: int,
    patterns: Patterns,
) -> PurgeReport:
    started = datetime.now(timezone.utc)
    course = await client.get_course(course_id)
    all_events = await client.list_calendar_events(course_id)

    results: list[PurgeEventResult] = []
    for event in all_events:
        is_fbf, reason = classify_event(event, patterns)
        if is_fbf:
            results.append(
                PurgeEventResult(
                    event_id=event.id,
                    title=event.title,
                    start_at=event.start_at,
                    status="matched",
                    match_reason=reason,
                )
            )

    finished = datetime.now(timezone.utc)
    return PurgeReport(
        course_id=course_id,
        course_name=course.name,
        dry_run=True,
        matched_count=len(results),
        deleted_count=0,
        failed_count=0,
        events=results,
        started_at=started,
        finished_at=finished,
    )


async def execute_purge(
    client: CanvasClient,
    course_id: int,
    patterns: Patterns,
    event_ids: list[int] | None = None,
) -> PurgeReport:
    started = datetime.now(timezone.utc)
    course = await client.get_course(course_id)
    all_events = await client.list_calendar_events(course_id)

    selected = set(event_ids) if event_ids is not None else None
    results: list[PurgeEventResult] = []
    deleted_count = 0
    failed_count = 0

    for event in all_events:
        is_fbf, reason = classify_event(event, patterns)
        if not is_fbf:
            continue
        if selected is not None and event.id not in selected:
            continue
        try:
            await client.delete_calendar_event(event.id)
            deleted_count += 1
            results.append(
                PurgeEventResult(
                    event_id=event.id,
                    title=event.title,
                    start_at=event.start_at,
                    status="deleted",
                    match_reason=reason,
                )
            )
        except FBFError as exc:
            failed_count += 1
            results.append(
                PurgeEventResult(
                    event_id=event.id,
                    title=event.title,
                    start_at=event.start_at,
                    status="failed",
                    match_reason=reason,
                    error_message=str(exc),
                )
            )
        except Exception as exc:
            failed_count += 1
            results.append(
                PurgeEventResult(
                    event_id=event.id,
                    title=event.title,
                    start_at=event.start_at,
                    status="failed",
                    match_reason=reason,
                    error_message=str(exc),
                )
            )

    finished = datetime.now(timezone.utc)
    return PurgeReport(
        course_id=course_id,
        course_name=course.name,
        dry_run=False,
        matched_count=len(results),
        deleted_count=deleted_count,
        failed_count=failed_count,
        events=results,
        started_at=started,
        finished_at=finished,
    )
