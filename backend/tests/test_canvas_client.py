import httpx
import pytest
import respx

from fbf_purge.canvas.client import CanvasClient
from fbf_purge.exceptions import CanvasAPIError


@pytest.mark.asyncio
@respx.mock
async def test_pagination_two_pages():
    base = "https://canvas.test"
    page1 = httpx.Response(
        200,
        json=[{"id": 1, "title": "A"}],
        headers={
            "Link": '<https://canvas.test/api/v1/courses?page=2>; rel="next"',
        },
    )
    page2 = httpx.Response(200, json=[{"id": 2, "title": "B"}])
    respx.get(url__regex=rf"{base}/api/v1/courses.*").mock(side_effect=[page1, page2])

    client = CanvasClient(base, "token", rate_limit_rps=1000)
    items = []
    async for item in client.paginate("/courses"):
        items.append(item)
    await client.aclose()
    assert len(items) == 2
    assert items[0]["id"] == 1
    assert items[1]["id"] == 2


@pytest.mark.asyncio
@respx.mock
async def test_api_error_on_400():
    base = "https://canvas.test"
    respx.get(f"{base}/api/v1/courses/999").mock(
        return_value=httpx.Response(400, text="bad request")
    )
    client = CanvasClient(base, "token", rate_limit_rps=1000)
    with pytest.raises(CanvasAPIError) as exc:
        await client.get_course(999)
    assert exc.value.status_code == 400
    await client.aclose()
