import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from api.routes import auth, courses, health, purge
from fbf_purge.classifier.patterns import load_patterns
from fbf_purge.config import get_settings
from fbf_purge.exceptions import CanvasAPIError, CanvasAuthError, CanvasNotFoundError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings.cache_clear()
    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    patterns_path = settings.resolved_patterns_path()
    logger.info("Loading FBF patterns from %s", patterns_path)
    app.state.settings = settings
    app.state.patterns = load_patterns(patterns_path)
    yield


app = FastAPI(
    title="FBF Calendar Purge API",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="lax",
    https_only=False,
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(purge.router)


@app.exception_handler(CanvasAuthError)
async def canvas_auth_handler(_request: Request, exc: CanvasAuthError) -> None:
    raise HTTPException(status_code=401, detail="Please sign in with Canvas again.") from exc


@app.exception_handler(CanvasNotFoundError)
async def canvas_not_found_handler(_request: Request, exc: CanvasNotFoundError) -> None:
    raise HTTPException(status_code=404, detail="Resource not found") from exc


@app.exception_handler(CanvasAPIError)
async def canvas_api_handler(_request: Request, exc: CanvasAPIError) -> None:
    if exc.status_code == 429:
        raise HTTPException(status_code=429, detail="Canvas is busy. Wait a moment and try again.") from exc
    raise HTTPException(status_code=502, detail="Something went wrong talking to Canvas.") from exc


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        raise exc
    logging.exception("Unhandled error")
    detail = str(exc) if settings.dev_mode else "Internal server error"
    return JSONResponse(status_code=500, content={"detail": detail, "code": "internal_error"})


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    code = "error"
    if exc.headers and "X-Error-Code" in exc.headers:
        code = exc.headers["X-Error-Code"]
    elif exc.status_code == 401:
        code = "auth_required"
    elif exc.status_code == 409:
        code = "preview_stale"
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc.detail), "code": code},
    )
