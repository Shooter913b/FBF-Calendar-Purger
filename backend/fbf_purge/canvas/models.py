from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


LinkStatus = Literal["orphan", "linked", "unknown"]


class CalendarEvent(BaseModel):
    id: int
    title: str | None = None
    start_at: str | None = None
    end_at: str | None = None
    description: str | None = None
    html_url: str | None = None
    context_code: str | None = None
    workflow_state: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_canvas(cls, data: dict) -> "CalendarEvent":
        return cls(
            id=int(data["id"]),
            title=data.get("title"),
            start_at=data.get("start_at"),
            end_at=data.get("end_at"),
            description=data.get("description"),
            html_url=data.get("html_url"),
            context_code=data.get("context_code"),
            workflow_state=data.get("workflow_state"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


class Course(BaseModel):
    id: int
    name: str
    course_code: str | None = None
    time_zone: str | None = None

    @classmethod
    def from_canvas(cls, data: dict) -> "Course":
        return cls(
            id=int(data["id"]),
            name=data.get("name") or f"Course {data['id']}",
            course_code=data.get("course_code"),
            time_zone=data.get("time_zone"),
        )


PurgeEventStatus = Literal["matched", "deleted", "failed", "skipped"]


class PurgeEventResult(BaseModel):
    event_id: int
    title: str | None = None
    start_at: str | None = None
    status: PurgeEventStatus
    match_reason: str | None = None
    error_message: str | None = None
    link_status: LinkStatus | None = None
    link_reason: str | None = None
    canvas_assignment_id: int | None = None


class PurgeReport(BaseModel):
    course_id: int
    course_name: str
    dry_run: bool
    matched_count: int
    orphan_count: int = 0
    deleted_count: int
    failed_count: int
    events: list[PurgeEventResult] = Field(default_factory=list)
    started_at: datetime
    finished_at: datetime | None = None
    preview_token: str | None = None
