from fastapi import APIRouter, Request

from api.schemas import VisitStatsResponse
from api.visitor_store import VisitCounterBackend

router = APIRouter(prefix="/api/stats", tags=["stats"])


def _get_counter(request: Request) -> VisitCounterBackend:
    counter = getattr(request.app.state, "visitor_store", None)
    if counter is None:
        raise RuntimeError("Visit counter not initialized")
    return counter


@router.get("/visits", response_model=VisitStatsResponse)
async def record_visit(request: Request) -> VisitStatsResponse:
    lifetime_visits = _get_counter(request).record_visit()
    return VisitStatsResponse(lifetime_visits=lifetime_visits)
