import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from api.deps import get_app_settings, get_canvas_client, get_patterns
from api.preview_store import PreviewStore
from api.schemas import PurgeReportOut, PurgeRequest
from fbf_purge.canvas.client import CanvasClient
from fbf_purge.classifier.patterns import Patterns
from fbf_purge.config import Settings
from fbf_purge.exceptions import CanvasAPIError, CanvasAuthError, CanvasNotFoundError
from fbf_purge.services.purge import execute_purge, preview_purge

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/courses", tags=["purge"])


def _preview_store(settings: Settings) -> PreviewStore:
    return PreviewStore(settings.session_secret)


@router.get("/{course_id}/purge/preview", response_model=PurgeReportOut)
async def purge_preview(
    course_id: int,
    client: Annotated[CanvasClient, Depends(get_canvas_client)],
    patterns: Annotated[Patterns, Depends(get_patterns)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> PurgeReportOut:
    try:
        report = await preview_purge(client, course_id, patterns)
        preview_event_ids = [e.event_id for e in report.events]
        store = _preview_store(settings)
        report.preview_token = store.create_token(
            course_id,
            len(preview_event_ids),
            preview_event_ids,
        )
        logger.info(
            "preview course_id=%s matched_count=%s",
            course_id,
            report.matched_count,
        )
        return PurgeReportOut.from_report(report)
    except CanvasNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Course not found") from exc
    except CanvasAuthError as exc:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to manage this course's calendar.",
        ) from exc
    except CanvasAPIError as exc:
        logger.warning("Canvas API error during preview: %s", exc)
        if exc.status_code == 429:
            raise HTTPException(status_code=429, detail="Canvas is busy. Wait a moment and try again.") from exc
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Preview failed for course_id=%s", course_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        await client.aclose()


@router.post("/{course_id}/purge", response_model=PurgeReportOut)
async def purge_execute(
    course_id: int,
    body: PurgeRequest,
    client: Annotated[CanvasClient, Depends(get_canvas_client)],
    patterns: Annotated[Patterns, Depends(get_patterns)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    x_confirm_course_id: Annotated[str | None, Header()] = None,
) -> PurgeReportOut:
    if not body.confirm:
        raise HTTPException(status_code=400, detail="confirm must be true")
    if x_confirm_course_id and str(course_id) != x_confirm_course_id:
        raise HTTPException(status_code=400, detail="Course ID header mismatch")

    store = _preview_store(settings)
    try:
        # Re-fetch preview to detect stale state
        current = await preview_purge(client, course_id, patterns)
        current_ids = [e.event_id for e in current.events]
        store.validate_selection(
            body.preview_token,
            course_id,
            body.event_ids,
            current_ids,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail="The course calendar changed. Please review the list again.",
        ) from exc
    except CanvasAuthError as exc:
        raise HTTPException(status_code=403, detail="You don't have permission for this course.") from exc

    try:
        report = await execute_purge(client, course_id, patterns, event_ids=body.event_ids)
        logger.info(
            "purge course_id=%s deleted=%s failed=%s",
            course_id,
            report.deleted_count,
            report.failed_count,
        )
        return PurgeReportOut.from_report(report)
    except CanvasAPIError as exc:
        logger.warning("Canvas API error during purge: %s", exc)
        if exc.status_code == 429:
            raise HTTPException(status_code=429, detail="Canvas is busy. Wait a moment and try again.") from exc
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Purge failed for course_id=%s", course_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        await client.aclose()
