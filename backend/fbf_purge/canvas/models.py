from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


LinkStatus = Literal["orphan", "linked", "unlinked", "unknown"]
EventCategory = Literal["fbf", "user"]
UserEventKind = Literal["calendar_event", "appointment_group"]
CalendarEntryKind = Literal["calendar_event", "assignment_due"]


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
    canvas_item_type: str = "event"
    is_assignment_calendar: bool = False
    hidden: bool = False
    appointment_group_id: int | None = None
    all_day: bool = False
    all_day_date: str | None = None
    assignment_due_at: str | None = None

    @classmethod
    def from_canvas(cls, data: dict) -> "CalendarEvent":
        raw_id = data["id"]
        canvas_item_type = data.get("type") or "event"
        is_assignment = canvas_item_type == "assignment" or (
            isinstance(raw_id, str) and str(raw_id).startswith("assignment_")
        )
        if isinstance(raw_id, str) and raw_id.startswith("assignment_"):
            numeric_id = int(raw_id.removeprefix("assignment_"))
            event_id = -numeric_id
        else:
            event_id = int(raw_id)

        assignment = data.get("assignment") or {}
        assignment_due_at = assignment.get("due_at") if isinstance(assignment, dict) else None

        return cls(
            id=event_id,
            title=data.get("title"),
            start_at=data.get("start_at"),
            end_at=data.get("end_at"),
            description=data.get("description"),
            html_url=data.get("html_url"),
            context_code=data.get("context_code"),
            workflow_state=data.get("workflow_state"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            canvas_item_type=canvas_item_type,
            is_assignment_calendar=is_assignment,
            hidden=bool(data.get("hidden")),
            appointment_group_id=data.get("appointment_group_id"),
            all_day=bool(data.get("all_day")),
            all_day_date=data.get("all_day_date"),
            assignment_due_at=assignment_due_at,
        )


class AppointmentGroup(BaseModel):
    id: int
    title: str | None = None
    start_at: str | None = None
    end_at: str | None = None
    description: str | None = None
    html_url: str | None = None
    workflow_state: str | None = None

    @classmethod
    def from_canvas(cls, data: dict) -> "AppointmentGroup":
        return cls(
            id=int(data["id"]),
            title=data.get("title"),
            start_at=data.get("start_at"),
            end_at=data.get("end_at"),
            description=data.get("description"),
            html_url=data.get("html_url"),
            workflow_state=data.get("workflow_state"),
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
    html_url: str | None = None
    status: PurgeEventStatus
    event_category: EventCategory = "fbf"
    user_event_kind: UserEventKind | None = None
    calendar_entry_kind: CalendarEntryKind = "calendar_event"
    match_reason: str | None = None
    error_message: str | None = None
    link_status: LinkStatus | None = None
    link_reason: str | None = None
    canvas_assignment_id: int | None = None
    assignment_due_at: str | None = None
    appointment_group_id: int | None = None


class PurgeReport(BaseModel):
    course_id: int
    course_name: str
    dry_run: bool
    matched_count: int
    orphan_count: int = 0
    user_count: int = 0
    deleted_count: int
    failed_count: int
    events: list[PurgeEventResult] = Field(default_factory=list)
    started_at: datetime
    finished_at: datetime | None = None
    preview_token: str | None = None
