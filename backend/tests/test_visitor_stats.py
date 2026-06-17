from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.visitor_store import (
    FileVisitCounter,
    UpstashVisitCounter,
    VisitorStore,
    create_visit_counter,
)


def test_file_visit_counter_increments(tmp_path):
    store = FileVisitCounter(tmp_path / "visitors.json")
    assert store.record_visit() == 1
    assert store.record_visit() == 2
    assert store.record_visit() == 3


def test_file_visit_counter_ignores_legacy_format(tmp_path):
    path = tmp_path / "visitors.json"
    path.write_text('{"visitor_ids": ["abc"]}\n', encoding="utf-8")
    store = FileVisitCounter(path)
    assert store.record_visit() == 1


@pytest.mark.asyncio
async def test_record_visit_increments_each_request(tmp_path):
    store = FileVisitCounter(tmp_path / "visitors.json")
    app.state.visitor_store = store
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.get("/api/stats/visits")
        assert first.status_code == 200
        assert first.json()["lifetime_visits"] == 1
        assert "fbf_visitor_id" not in first.cookies

        second = await client.get("/api/stats/visits")
        assert second.status_code == 200
        assert second.json()["lifetime_visits"] == 2


def test_create_visit_counter_prefers_upstash():
    store = create_visit_counter(
        store_path=Path("/tmp/visitors.json"),
        upstash_redis_rest_url="https://example.upstash.io",
        upstash_redis_rest_token="secret",
    )
    assert isinstance(store, UpstashVisitCounter)


def test_upstash_visit_counter_increments(respx_mock):
    import httpx
    import respx

    route = respx.post("https://example.upstash.io/").mock(
        side_effect=[
            httpx.Response(200, json={"result": 1}),
            httpx.Response(200, json={"result": 2}),
        ]
    )
    store = UpstashVisitCounter("https://example.upstash.io", "secret")

    assert store.record_visit() == 1
    assert store.record_visit() == 2
    assert route.call_count == 2


# Backwards-compatible alias used in older tests/imports.
def test_visitor_store_alias(tmp_path):
    store = VisitorStore(tmp_path / "visitors.json")
    assert store.record_visit() == 1
