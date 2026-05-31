import asyncio
import re
import time
from collections.abc import AsyncIterator
from typing import Any
import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from fbf_purge.canvas.models import CalendarEvent, Course
from fbf_purge.exceptions import CanvasAPIError, CanvasAuthError, CanvasNotFoundError


def _parse_link_header(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip()
        if 'rel="next"' in section or "rel=next" in section:
            match = re.search(r"<([^>]+)>", section)
            if match:
                return match.group(1)
    return None


def _should_retry(exc: BaseException) -> bool:
    if isinstance(exc, CanvasAPIError):
        return exc.status_code == 429 or exc.status_code >= 500
    return False


class CanvasClient:
    def __init__(self, base_url: str, access_token: str, rate_limit_rps: float = 8.0):
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self._min_interval = 1.0 / rate_limit_rps if rate_limit_rps > 0 else 0
        self._last_request_at = 0.0
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30.0,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _throttle(self) -> None:
        if self._min_interval <= 0:
            return
        now = time.monotonic()
        elapsed = now - self._last_request_at
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_request_at = time.monotonic()

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code in (401, 403):
            raise CanvasAuthError(f"Canvas auth failed ({response.status_code})")
        if response.status_code == 404:
            raise CanvasNotFoundError(f"Canvas resource not found: {response.request.url}")
        if response.status_code >= 400:
            body = response.text[:500]
            raise CanvasAPIError(response.status_code, f"Canvas API error {response.status_code}: {body}")

    @retry(
        retry=retry_if_exception(_should_retry),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=16),
        reraise=True,
    )
    async def get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        await self._throttle()
        if not path.startswith("/"):
            path = f"/{path}"
        if not path.startswith("/api/v1"):
            path = f"/api/v1{path}"
        response = await self._client.get(path, params=params)
        self._raise_for_status(response)
        return response

    @retry(
        retry=retry_if_exception(_should_retry),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=16),
        reraise=True,
    )
    async def delete(self, path: str) -> httpx.Response:
        await self._throttle()
        if not path.startswith("/"):
            path = f"/{path}"
        if not path.startswith("/api/v1"):
            path = f"/api/v1{path}"
        response = await self._client.delete(path)
        self._raise_for_status(response)
        return response

    async def paginate(self, path: str, params: dict[str, Any] | None = None) -> AsyncIterator[dict]:
        next_url: str | None = None
        first = True
        while first or next_url:
            first = False
            if next_url:
                await self._throttle()
                response = await self._client.get(next_url)
                self._raise_for_status(response)
            else:
                response = await self.get(path, params=params)
            data = response.json()
            if isinstance(data, list):
                for item in data:
                    yield item
            else:
                yield data
            next_url = _parse_link_header(response.headers.get("Link"))

    async def list_calendar_events(self, course_id: int) -> list[CalendarEvent]:
        events: list[CalendarEvent] = []
        params = {
            "type": "event",
            "context_codes[]": f"course_{course_id}",
            "all_events": "true",
            "per_page": 100,
        }
        async for item in self.paginate("/calendar_events", params=params):
            events.append(CalendarEvent.from_canvas(item))
        return events

    async def list_active_assignment_ids(self, course_id: int) -> set[int]:
        ids: set[int] = set()
        params = {"per_page": 100}
        async for item in self.paginate(f"/courses/{course_id}/assignments", params=params):
            if item.get("workflow_state") == "deleted":
                continue
            ids.add(int(item["id"]))
        return ids

    async def delete_calendar_event(self, event_id: int) -> dict:
        response = await self.delete(f"/calendar_events/{event_id}")
        return response.json()

    async def get_course(self, course_id: int) -> Course:
        response = await self.get(f"/courses/{course_id}")
        return Course.from_canvas(response.json())

    async def list_courses_for_user(self) -> list[Course]:
        courses: list[Course] = []
        params = {
            "enrollment_type": "teacher",
            "enrollment_state": "active",
            "per_page": 100,
        }
        async for item in self.paginate("/courses", params=params):
            courses.append(Course.from_canvas(item))
        return sorted(courses, key=lambda c: c.name.lower())
