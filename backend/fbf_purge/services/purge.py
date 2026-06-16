from datetime import datetime, timezone
import logging

from fbf_purge.canvas.client import CanvasClient
from fbf_purge.canvas.models import AppointmentGroup, PurgeEventResult, PurgeReport
from fbf_purge.classifier.assignments import FbfAssignmentIndex
from fbf_purge.classifier.patterns import Patterns
from fbf_purge.classifier.links import classify_event_assignment_link, parse_canvas_assignment_id, classify_assignment_link
from fbf_purge.classifier.rules import (
    classify_assignment_calendar_entry,
    classify_event,
    is_active_assignment_calendar_item,
    is_active_calendar_item,
    is_user_calendar_event,
)
from fbf_purge.canvas.dates import event_has_calendar_date, resolve_assignment_calendar_dates
from fbf_purge.canvas.urls import (
    resolve_appointment_group_html_url,
    resolve_assignment_html_url,
    resolve_calendar_html_url,
)
from fbf_purge.exceptions import CanvasAPIError, CanvasAuthError, FBFError

logger = logging.getLogger(__name__)


async def _fetch_appointment_groups(
    client: CanvasClient,
    course_id: int,
) -> list[AppointmentGroup]:
    try:
        return await client.list_appointment_groups(course_id)
    except (CanvasAuthError, CanvasAPIError) as exc:
        logger.warning(
            "Could not fetch appointment groups for course %s: %s",
            course_id,
            exc,
        )
        return []


async def _fetch_course_external_tools(
    client: CanvasClient,
    course_id: int,
) -> list[dict]:
    try:
        return await client.list_course_external_tools(course_id)
    except (CanvasAuthError, CanvasAPIError) as exc:
        logger.warning(
            "Could not fetch external tools for course %s: %s",
            course_id,
            exc,
        )
        return []


async def _build_fbf_assignment_index(
    client: CanvasClient,
    course_id: int,
    patterns: Patterns,
    course_assignments: list[dict] | None = None,
) -> FbfAssignmentIndex:
    assignments = (
        course_assignments
        if course_assignments is not None
        else await client.list_course_assignments(course_id)
    )
    external_tools = await _fetch_course_external_tools(client, course_id)
    return FbfAssignmentIndex.from_course_assignments(
        assignments,
        patterns,
        external_tools,
    )


async def preview_purge(
    client: CanvasClient,
    course_id: int,
    patterns: Patterns,
) -> PurgeReport:
    started = datetime.now(timezone.utc)
    course = await client.get_course(course_id)
    all_events = await client.list_calendar_events(course_id)
    assignment_calendar_events = await client.list_assignment_calendar_events(course_id)
    appointment_groups = await _fetch_appointment_groups(client, course_id)
    course_assignments = await client.list_course_assignments(course_id)
    active_assignment_ids = {int(a["id"]) for a in course_assignments}
    assignment_due_by_id = {int(a["id"]): a.get("due_at") for a in course_assignments}
    fbf_assignments = await _build_fbf_assignment_index(
        client,
        course_id,
        patterns,
        course_assignments,
    )

    results: list[PurgeEventResult] = []
    for event in all_events:
        if not is_active_calendar_item(event):
            continue

        is_fbf, reason = classify_event(event, patterns, fbf_assignments)
        inferred_assignment_id = None
        if is_fbf and parse_canvas_assignment_id(event) is None and fbf_assignments is not None:
            matched = fbf_assignments.match_event(event, patterns)
            if matched:
                inferred_assignment_id = matched[0]
        link_status, link_reason, canvas_assignment_id = classify_event_assignment_link(
            event,
            active_assignment_ids,
            inferred_assignment_id=inferred_assignment_id,
        )
        if is_fbf:
            category = "fbf"
            match_reason = reason
            html_url = resolve_calendar_html_url(client.base_url, course_id, event)
            user_event_kind = None
        elif is_user_calendar_event(event, patterns, fbf_assignments):
            category = "user"
            match_reason = "User calendar event"
            html_url = resolve_calendar_html_url(client.base_url, course_id, event)
            user_event_kind = "calendar_event"
        else:
            continue

        if not event_has_calendar_date(event):
            continue

        assignment_due_at = (
            assignment_due_by_id.get(canvas_assignment_id)
            if canvas_assignment_id is not None
            else None
        )

        results.append(
            PurgeEventResult(
                event_id=event.id,
                title=event.title,
                start_at=event.start_at,
                html_url=html_url,
                status="matched",
                event_category=category,
                user_event_kind=user_event_kind,
                match_reason=match_reason,
                link_status=link_status,
                link_reason=link_reason,
                canvas_assignment_id=canvas_assignment_id,
                assignment_due_at=assignment_due_at,
                calendar_entry_kind="calendar_event",
            )
        )

    calendar_event_assignment_ids = {
        row.canvas_assignment_id
        for row in results
        if row.calendar_entry_kind == "calendar_event" and row.canvas_assignment_id is not None
    }

    for event in assignment_calendar_events:
        if not is_active_assignment_calendar_item(event):
            continue

        category, match_reason, canvas_assignment_id = classify_assignment_calendar_entry(
            event,
            fbf_assignments.fbf_assignment_ids,
            active_assignment_ids,
        )
        if canvas_assignment_id in calendar_event_assignment_ids:
            continue
        link_status, link_reason, canvas_assignment_id = classify_assignment_link(
            canvas_assignment_id,
            active_assignment_ids,
        )
        start_at, assignment_due_at = resolve_assignment_calendar_dates(
            event,
            assignment_due_from_course=assignment_due_by_id.get(canvas_assignment_id)
            if canvas_assignment_id is not None
            else None,
            assignment_due_from_fbf=fbf_assignments.due_at_for(canvas_assignment_id)
            if canvas_assignment_id is not None
            else None,
        )
        if start_at is None and assignment_due_at is None:
            continue

        results.append(
            PurgeEventResult(
                event_id=event.id,
                title=event.title,
                start_at=start_at,
                html_url=resolve_assignment_html_url(client.base_url, course_id, event),
                status="matched",
                event_category=category,
                user_event_kind=None,
                calendar_entry_kind="assignment_due",
                match_reason=match_reason,
                link_status=link_status,
                link_reason=link_reason,
                canvas_assignment_id=canvas_assignment_id,
                assignment_due_at=assignment_due_at,
            )
        )

    for group in appointment_groups:
        if group.workflow_state not in ("active",):
            continue
        results.append(
            PurgeEventResult(
                event_id=-group.id,
                title=group.title,
                start_at=group.start_at,
                html_url=resolve_appointment_group_html_url(
                    client.base_url,
                    group.id,
                    group.html_url,
                ),
                status="matched",
                event_category="user",
                user_event_kind="appointment_group",
                match_reason="Appointment signup (Office Hours)",
                link_status="unknown",
                link_reason="Appointment group — not linked to a Canvas assignment",
                appointment_group_id=group.id,
            )
        )

    fbf_results = [r for r in results if r.event_category == "fbf"]
    user_results = [r for r in results if r.event_category == "user"]
    orphan_count = sum(1 for r in fbf_results if r.link_status == "orphan")
    finished = datetime.now(timezone.utc)
    return PurgeReport(
        course_id=course_id,
        course_name=course.name,
        dry_run=True,
        matched_count=len(fbf_results),
        orphan_count=orphan_count,
        user_count=len(user_results),
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
    appointment_groups = await _fetch_appointment_groups(client, course_id)
    fbf_assignments = await _build_fbf_assignment_index(client, course_id, patterns)

    selected = set(event_ids) if event_ids is not None else None
    group_by_event_id = {
        -group.id: group
        for group in appointment_groups
        if group.workflow_state == "active"
    }
    results: list[PurgeEventResult] = []
    deleted_count = 0
    failed_count = 0

    for event in all_events:
        if not is_active_calendar_item(event):
            continue
        if selected is not None and event.id not in selected:
            continue

        is_fbf, reason = classify_event(event, patterns, fbf_assignments)
        is_user = is_user_calendar_event(event, patterns, fbf_assignments)
        if not is_fbf and not is_user:
            continue

        html_url = resolve_calendar_html_url(client.base_url, course_id, event)
        try:
            await client.delete_calendar_event(event.id)
            deleted_count += 1
            results.append(
                PurgeEventResult(
                    event_id=event.id,
                    title=event.title,
                    start_at=event.start_at,
                    html_url=html_url,
                    status="deleted",
                    event_category="fbf" if is_fbf else "user",
                    user_event_kind=None if is_fbf else "calendar_event",
                    match_reason=reason if is_fbf else "User calendar event",
                )
            )
        except FBFError as exc:
            failed_count += 1
            results.append(
                PurgeEventResult(
                    event_id=event.id,
                    title=event.title,
                    start_at=event.start_at,
                    html_url=html_url,
                    status="failed",
                    event_category="fbf" if is_fbf else "user",
                    match_reason=reason if is_fbf else "User calendar event",
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
                    html_url=html_url,
                    status="failed",
                    event_category="fbf" if is_fbf else "user",
                    match_reason=reason if is_fbf else "User calendar event",
                    error_message=str(exc),
                )
            )

    for event_id, group in group_by_event_id.items():
        if selected is not None and event_id not in selected:
            continue
        html_url = resolve_appointment_group_html_url(
            client.base_url,
            group.id,
            group.html_url,
        )
        try:
            await client.delete_appointment_group(group.id)
            deleted_count += 1
            results.append(
                PurgeEventResult(
                    event_id=event_id,
                    title=group.title,
                    start_at=group.start_at,
                    html_url=html_url,
                    status="deleted",
                    event_category="user",
                    user_event_kind="appointment_group",
                    match_reason="Appointment signup (Office Hours)",
                    appointment_group_id=group.id,
                )
            )
        except FBFError as exc:
            failed_count += 1
            results.append(
                PurgeEventResult(
                    event_id=event_id,
                    title=group.title,
                    start_at=group.start_at,
                    html_url=html_url,
                    status="failed",
                    event_category="user",
                    user_event_kind="appointment_group",
                    match_reason="Appointment signup (Office Hours)",
                    appointment_group_id=group.id,
                    error_message=str(exc),
                )
            )
        except Exception as exc:
            failed_count += 1
            results.append(
                PurgeEventResult(
                    event_id=event_id,
                    title=group.title,
                    start_at=group.start_at,
                    html_url=html_url,
                    status="failed",
                    event_category="user",
                    user_event_kind="appointment_group",
                    match_reason="Appointment signup (Office Hours)",
                    appointment_group_id=group.id,
                    error_message=str(exc),
                )
            )

    finished = datetime.now(timezone.utc)
    return PurgeReport(
        course_id=course_id,
        course_name=course.name,
        dry_run=False,
        matched_count=len(results),
        orphan_count=0,
        user_count=sum(1 for r in results if r.event_category == "user"),
        deleted_count=deleted_count,
        failed_count=failed_count,
        events=results,
        started_at=started,
        finished_at=finished,
    )
