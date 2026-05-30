from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from api.deps import get_canvas_client, get_patterns
from api.main import app
from api.preview_store import PreviewStore
from fbf_purge.canvas.models import Course, PurgeEventResult, PurgeReport
from fbf_purge.classifier.patterns import load_patterns
from tests.conftest import PATTERNS_PATH


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.aclose = AsyncMock()
    client.get_course = AsyncMock(return_value=Course(id=1, name="Test Course", course_code="TST-101"))
    client.list_calendar_events = AsyncMock(return_value=[])
    client.list_courses_for_user = AsyncMock(
        return_value=[Course(id=1, name="Test Course", course_code="TST-101")]
    )
    client.delete_calendar_event = AsyncMock(return_value={})
    return client


@pytest.fixture
async def api_client(mock_client):
    app.dependency_overrides[get_canvas_client] = lambda: mock_client
    app.dependency_overrides[get_patterns] = lambda: load_patterns(PATTERNS_PATH)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health(api_client):
    r = await api_client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_list_courses(api_client):
    r = await api_client.get("/api/courses")
    assert r.status_code == 200
    assert len(r.json()["courses"]) == 1


@pytest.mark.asyncio
async def test_preview_returns_token(api_client, mock_client):
    from fbf_purge.canvas.models import CalendarEvent
    from tests.conftest import load_fixture

    mock_client.list_calendar_events = AsyncMock(
        return_value=[CalendarEvent.from_canvas(load_fixture("fbf_give_feedback.json"))]
    )
    r = await api_client.get("/api/courses/1/purge/preview")
    assert r.status_code == 200
    data = r.json()
    assert data["dry_run"] is True
    assert data["matched_count"] == 1
    assert data["preview_token"]


@pytest.mark.asyncio
async def test_purge_409_on_stale_token(api_client, mock_client):
    from fbf_purge.canvas.models import CalendarEvent
    from tests.conftest import load_fixture

    event = CalendarEvent.from_canvas(load_fixture("fbf_give_feedback.json"))
    mock_client.list_calendar_events = AsyncMock(return_value=[event])

    preview = await api_client.get("/api/courses/1/purge/preview")
    token = preview.json()["preview_token"]
    event_id = event.id

    mock_client.list_calendar_events = AsyncMock(return_value=[])
    r = await api_client.post(
        "/api/courses/1/purge",
        json={"confirm": True, "preview_token": token, "event_ids": [event_id]},
        headers={"X-Confirm-Course-Id": "1"},
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_login_with_token(api_client, respx_mock):
    import httpx
    import respx

    respx.get(url__regex=r".*/api/v1/users/self/profile").mock(
        return_value=httpx.Response(200, json={"name": "Test Instructor"})
    )

    r = await api_client.post(
        "/api/auth/token",
        json={"access_token": "test-token-1234567890"},
    )
    assert r.status_code == 200
    assert r.json()["authenticated"] is True
    assert r.json()["user_name"] == "Test Instructor"

    me = await api_client.get("/api/auth/me")
    assert me.json()["authenticated"] is True


@pytest.mark.asyncio
async def test_purge_deletes_selected_only(api_client, mock_client):
    from fbf_purge.canvas.models import CalendarEvent
    from tests.conftest import load_fixture

    fbf1 = CalendarEvent.from_canvas(load_fixture("fbf_give_feedback.json"))
    fbf2 = CalendarEvent.from_canvas(load_fixture("fbf_read_feedback.json"))
    mock_client.list_calendar_events = AsyncMock(return_value=[fbf1, fbf2])

    preview = await api_client.get("/api/courses/1/purge/preview")
    token = preview.json()["preview_token"]

    mock_client.delete_calendar_event = AsyncMock(return_value={})
    r = await api_client.post(
        "/api/courses/1/purge",
        json={"confirm": True, "preview_token": token, "event_ids": [fbf1.id]},
        headers={"X-Confirm-Course-Id": "1"},
    )
    assert r.status_code == 200
    assert r.json()["deleted_count"] == 1
    mock_client.delete_calendar_event.assert_called_once_with(fbf1.id)
