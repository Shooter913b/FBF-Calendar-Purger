import logging
import secrets
import urllib.parse
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from api.schemas import TokenLoginRequest
from api.deps import get_app_settings
from fbf_purge.config import Settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

CANVAS_SCOPES = " ".join(
    [
        "url:GET|/api/v1/courses",
        "url:GET|/api/v1/courses/:course_id/assignments",
        "url:GET|/api/v1/courses/:course_id/external_tools",
        "url:GET|/api/v1/calendar_events",
        "url:DELETE|/api/v1/calendar_events/:id",
        "url:GET|/api/v1/appointment_groups",
        "url:DELETE|/api/v1/appointment_groups/:id",
        "url:GET|/api/v1/users/self/profile",
    ]
)


def oauth_configured(settings: Settings) -> bool:
    return bool(settings.canvas_client_id and settings.canvas_client_secret)


def auth_error_redirect(settings: Settings, message: str) -> RedirectResponse:
    query = urllib.parse.urlencode({"auth_error": message})
    return RedirectResponse(url=f"{settings.frontend_url}/?{query}")


async def validate_canvas_token(base_url: str, access_token: str) -> str:
    url = f"{base_url.rstrip('/')}/api/v1/users/self/profile"
    try:
        async with httpx.AsyncClient(timeout=15.0) as http:
            response = await http.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach Canvas: {exc}") from exc

    if response.status_code == 401:
        raise HTTPException(
            status_code=401,
            detail="Invalid access token. Create a new one in Canvas → Account → Settings → New Access Token.",
        )
    if response.status_code == 404:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Canvas API returned 404 for {url}. "
                "Check CANVAS_BASE_URL in .env — it should be your institution's Canvas URL "
                "(e.g. https://canvas.wisc.edu), not the placeholder."
            ),
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Canvas rejected the token (HTTP {response.status_code}).",
        )
    data = response.json()
    return data.get("name") or data.get("short_name") or "Canvas User"


async def fetch_canvas_user_name(base_url: str, access_token: str) -> str:
    try:
        return await validate_canvas_token(base_url, access_token)
    except HTTPException:
        return "Canvas User"


@router.get("/config")
async def auth_config(settings: Annotated[Settings, Depends(get_app_settings)]) -> dict:
    """Public info about which sign-in method is active (no secrets)."""
    return {
        "oauth_enabled": oauth_configured(settings),
        "token_login_enabled": True,
        "dev_fallback": settings.dev_mode and bool(settings.canvas_access_token),
        "canvas_base_url": settings.canvas_base_url.rstrip("/"),
    }


@router.get("/login")
async def login(
    request: Request,
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> RedirectResponse:
    if oauth_configured(settings):
        state = secrets.token_urlsafe(32)
        request.session["oauth_state"] = state
        params = {
            "client_id": settings.canvas_client_id,
            "response_type": "code",
            "redirect_uri": settings.canvas_oauth_redirect_uri,
            "state": state,
            "scope": CANVAS_SCOPES,
        }
        url = f"{settings.canvas_base_url.rstrip('/')}/login/oauth2/auth?{urllib.parse.urlencode(params)}"
        return RedirectResponse(url=url)

    if settings.dev_mode and settings.canvas_access_token:
        request.session["canvas_access_token"] = settings.canvas_access_token
        request.session["user_name"] = await fetch_canvas_user_name(
            settings.canvas_base_url,
            settings.canvas_access_token,
        )
        return RedirectResponse(url=f"{settings.frontend_url}/")

    raise HTTPException(
        status_code=501,
        detail=(
            "OAuth is not configured. Sign in with a personal Canvas access token instead, "
            "or set CANVAS_CLIENT_ID and CANVAS_CLIENT_SECRET in .env."
        ),
    )


@router.post("/token")
async def login_with_token(
    request: Request,
    body: TokenLoginRequest,
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> dict:
    token = body.access_token.strip()
    user_name = await validate_canvas_token(settings.canvas_base_url, token)
    request.session["canvas_access_token"] = token
    request.session["user_name"] = user_name
    logger.info("User signed in with personal access token")
    return {"authenticated": True, "user_name": user_name}


@router.get("/callback")
async def callback(
    request: Request,
    settings: Annotated[Settings, Depends(get_app_settings)],
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> RedirectResponse:
    if error:
        message = error_description or error
        return auth_error_redirect(settings, f"Canvas sign-in denied: {message}")

    if not code or not state:
        return auth_error_redirect(settings, "Missing OAuth code or state from Canvas.")

    expected_state = request.session.pop("oauth_state", None)
    if not expected_state or state != expected_state:
        return auth_error_redirect(settings, "Invalid OAuth state. Please try signing in again.")

    token_url = f"{settings.canvas_base_url.rstrip('/')}/login/oauth2/token"
    try:
        async with httpx.AsyncClient(timeout=15.0) as http:
            response = await http.post(
                token_url,
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.canvas_client_id,
                    "client_secret": settings.canvas_client_secret,
                    "redirect_uri": settings.canvas_oauth_redirect_uri,
                    "code": code,
                },
            )
    except httpx.HTTPError as exc:
        logger.exception("OAuth token exchange failed")
        return auth_error_redirect(settings, f"Could not reach Canvas: {exc}")

    if response.status_code >= 400:
        logger.warning("OAuth token exchange error: %s", response.text[:500])
        return auth_error_redirect(settings, "Canvas rejected the sign-in request. Check developer key settings.")

    data = response.json()
    access_token = data.get("access_token")
    if not access_token:
        return auth_error_redirect(settings, "Canvas did not return an access token.")

    user_name = (
        data.get("user", {}).get("name")
        if isinstance(data.get("user"), dict)
        else None
    )
    if not user_name:
        user_name = await fetch_canvas_user_name(settings.canvas_base_url, access_token)

    request.session["canvas_access_token"] = access_token
    request.session["user_name"] = user_name
    return RedirectResponse(url=f"{settings.frontend_url}/")


@router.get("/me")
async def me(request: Request) -> dict:
    if not request.session.get("canvas_access_token"):
        return {"authenticated": False}
    return {
        "authenticated": True,
        "user_name": request.session.get("user_name", "Canvas User"),
    }


@router.post("/logout")
async def logout(request: Request) -> dict:
    request.session.clear()
    return {"ok": True}
