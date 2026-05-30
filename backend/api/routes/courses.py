from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_app_settings, get_canvas_client, get_patterns
from api.schemas import CourseOut, CoursesResponse
from fbf_purge.canvas.client import CanvasClient
from fbf_purge.classifier.patterns import Patterns
from fbf_purge.config import Settings
from fbf_purge.exceptions import CanvasAuthError, CanvasNotFoundError
from fbf_purge.services.courses import inspect_course, list_teacher_courses

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.get("", response_model=CoursesResponse)
async def list_courses(
    client: Annotated[CanvasClient, Depends(get_canvas_client)],
) -> CoursesResponse:
    try:
        courses = await list_teacher_courses(client)
    except CanvasAuthError as exc:
        raise HTTPException(status_code=401, detail="Please sign in with Canvas again.") from exc
    finally:
        await client.aclose()

    return CoursesResponse(
        courses=[
            CourseOut(id=c.id, name=c.name, course_code=c.course_code) for c in courses
        ]
    )


@router.get("/{course_id}/inspect")
async def inspect(
    course_id: int,
    client: Annotated[CanvasClient, Depends(get_canvas_client)],
    patterns: Annotated[Patterns, Depends(get_patterns)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> dict:
    if not settings.enable_inspect:
        raise HTTPException(status_code=404, detail="Inspect endpoint is disabled")
    try:
        return await inspect_course(client, course_id, patterns)
    except CanvasNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Course not found") from exc
    except CanvasAuthError as exc:
        raise HTTPException(status_code=403, detail="You don't have permission for this course.") from exc
    finally:
        await client.aclose()
