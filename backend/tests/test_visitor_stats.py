import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.visitor_store import (
    UpstashVisitorStore,
    VisitorStore,
    create_visitor_store,
    is_valid_visitor_id,
)


def test_is_valid_visitor_id():
    value = str(uuid.uuid4())
    assert is_valid_visitor_id(value) is True
    assert is_valid_visitor_id(value.upper()) is True
    assert is_valid_visitor_id("not-a-uuid") is False
    assert is_valid_visitor_id(None) is False


def test_visitor_store_register(tmp_path):
    store = VisitorStore(tmp_path / "visitors.json")
    first_id = str(uuid.uuid4())
    second_id = str(uuid.uuid4())

    count, is_new = store.register(first_id)
    assert count == 1
    assert is_new is True

    count, is_new = store.register(first_id)
    assert count == 1
    assert is_new is False

    count, is_new = store.register(second_id)
    assert count == 2
    assert is_new is True


@pytest.mark.asyncio
async def test_register_visitor_sets_cookie_and_counts(tmp_path):
    store = VisitorStore(tmp_path / "visitors.json")
    app.state.visitor_store = store
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.get("/api/stats/visitors")
        assert first.status_code == 200
        assert first.json()["lifetime_users"] == 1
        assert "fbf_visitor_id" in first.cookies
        visitor_id = first.cookies["fbf_visitor_id"]

        second = await client.get(
            "/api/stats/visitors",
            cookies={"fbf_visitor_id": visitor_id},
        )
        assert second.status_code == 200
        assert second.json()["lifetime_users"] == 1

    async with AsyncClient(transport=transport, base_url="http://test") as other_client:
        third = await other_client.get("/api/stats/visitors")
        assert third.status_code == 200
        assert third.json()["lifetime_users"] == 2


def test_create_visitor_store_prefers_upstash():
    store = create_visitor_store(
        store_path=Path("/tmp/visitors.json"),
        upstash_redis_rest_url="https://example.upstash.io",
        upstash_redis_rest_token="secret",
    )
    assert isinstance(store, UpstashVisitorStore)


def test_upstash_visitor_store_register(respx_mock):
    import httpx
    import respx

    visitor_id = str(uuid.uuid4())
    route = respx.post("https://example.upstash.io/").mock(
        side_effect=[
            httpx.Response(200, json={"result": 1}),
            httpx.Response(200, json={"result": 1}),
            httpx.Response(200, json={"result": 0}),
            httpx.Response(200, json={"result": 1}),
        ]
    )
    store = UpstashVisitorStore("https://example.upstash.io", "secret")

    count, is_new = store.register(visitor_id)
    assert count == 1
    assert is_new is True

    count, is_new = store.register(visitor_id)
    assert count == 1
    assert is_new is False

    assert route.call_count == 4
