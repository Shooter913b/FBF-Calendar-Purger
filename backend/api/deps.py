from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request

from fbf_purge.canvas.client import CanvasClient
from fbf_purge.classifier.patterns import Patterns
from fbf_purge.config import Settings, get_settings
from fbf_purge.exceptions import CanvasAuthError


def get_app_settings() -> Settings:
    return get_settings()


def get_patterns(request: Request) -> Patterns:
    patterns = getattr(request.app.state, "patterns", None)
    if patterns is None:
        raise HTTPException(
            status_code=500,
            detail="Server misconfigured: FBF patterns not loaded at startup.",
        )
    return patterns


async def get_canvas_client(
    request: Request,
    settings: Annotated[Settings, Depends(get_app_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> CanvasClient:
    token: str | None = None

    # Session token from OAuth or dev login
    if hasattr(request, "session"):
        token = request.session.get("canvas_access_token")

    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if not token and settings.dev_mode and settings.canvas_access_token:
        token = settings.canvas_access_token

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Please sign in with Canvas again.",
            headers={"X-Error-Code": "auth_required"},
        )

    return CanvasClient(
        settings.canvas_base_url,
        token,
        settings.rate_limit_requests_per_second,
    )
