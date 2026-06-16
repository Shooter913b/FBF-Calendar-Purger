import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from api.schemas import VisitorStatsResponse
from api.visitor_store import VisitorStore, is_valid_visitor_id

router = APIRouter(prefix="/api/stats", tags=["stats"])

VISITOR_COOKIE = "fbf_visitor_id"
VISITOR_COOKIE_MAX_AGE = 365 * 24 * 60 * 60


def _get_store(request: Request) -> VisitorStore:
    store = getattr(request.app.state, "visitor_store", None)
    if store is None:
        raise RuntimeError("Visitor store not initialized")
    return store


@router.get("/visitors", response_model=VisitorStatsResponse)
async def register_visitor(request: Request) -> JSONResponse:
    store = _get_store(request)
    visitor_id = request.cookies.get(VISITOR_COOKIE)
    set_cookie = False

    if not is_valid_visitor_id(visitor_id):
        visitor_id = str(uuid.uuid4())
        set_cookie = True

    lifetime_users, _is_new = store.register(visitor_id)

    response = JSONResponse(
        VisitorStatsResponse(lifetime_users=lifetime_users).model_dump()
    )
    if set_cookie:
        response.set_cookie(
            key=VISITOR_COOKIE,
            value=visitor_id,
            max_age=VISITOR_COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            path="/",
        )
    return response
