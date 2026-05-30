from datetime import datetime

from pydantic import BaseModel, Field

from fbf_purge.canvas.models import PurgeEventResult, PurgeReport


class CourseOut(BaseModel):
    id: int
    name: str
    course_code: str | None = None


class CoursesResponse(BaseModel):
    courses: list[CourseOut]


class PurgeReportOut(BaseModel):
    course_id: int
    course_name: str
    dry_run: bool
    matched_count: int
    deleted_count: int
    failed_count: int
    events: list[PurgeEventResult]
    started_at: datetime
    finished_at: datetime | None = None
    preview_token: str | None = None

    @classmethod
    def from_report(cls, report: PurgeReport) -> "PurgeReportOut":
        return cls(
            course_id=report.course_id,
            course_name=report.course_name,
            dry_run=report.dry_run,
            matched_count=report.matched_count,
            deleted_count=report.deleted_count,
            failed_count=report.failed_count,
            events=report.events,
            started_at=report.started_at,
            finished_at=report.finished_at,
            preview_token=report.preview_token,
        )


class PurgeRequest(BaseModel):
    confirm: bool = Field(..., description="Must be true to execute purge")
    preview_token: str
    event_ids: list[int] = Field(..., min_length=1, description="Calendar event IDs to delete")


class TokenLoginRequest(BaseModel):
    access_token: str = Field(..., min_length=10)


class ErrorResponse(BaseModel):
    detail: str
    code: str


class HealthResponse(BaseModel):
    status: str
