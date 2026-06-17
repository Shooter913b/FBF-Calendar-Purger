import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_env_files() -> tuple[str, ...]:
    """Find .env in cwd, backend/, or repo root."""
    here = Path(__file__).resolve()
    backend_root = here.parent.parent
    repo_root = backend_root.parent
    candidates = [
        Path.cwd() / ".env",
        backend_root / ".env",
        repo_root / ".env",
    ]
    found = [str(p) for p in candidates if p.is_file()]
    return tuple(found) if found else (".env",)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_resolve_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    canvas_base_url: str = "https://canvas.instructure.com"
    canvas_access_token: str = ""
    canvas_client_id: str = ""
    canvas_client_secret: str = ""
    canvas_oauth_redirect_uri: str = "http://localhost:3000/api/auth/callback"

    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    session_secret: str = "dev-secret-change-in-production"
    dev_mode: bool = True

    fbf_patterns_path: str = "config/fbf_patterns.yaml"
    rate_limit_requests_per_second: float = 8.0
    log_level: str = "INFO"
    enable_inspect: bool = False
    visitor_store_path: str = "data/visitors.json"
    upstash_redis_rest_url: str = ""
    upstash_redis_rest_token: str = ""

    def resolved_patterns_path(self) -> Path:
        path = Path(self.fbf_patterns_path)
        if path.is_absolute() and path.is_file():
            return path

        backend_root = Path(__file__).resolve().parent.parent
        repo_root = backend_root.parent
        path_posix = path.as_posix()

        candidates: list[Path] = [
            Path.cwd() / path,
            backend_root / path,
            repo_root / path,
            backend_root / "config" / "fbf_patterns.yaml",
        ]
        if path_posix.startswith("backend/"):
            candidates.append(backend_root / path_posix.removeprefix("backend/"))

        for candidate in candidates:
            if candidate.is_file():
                return candidate

        raise FileNotFoundError(
            f"FBF patterns file not found (tried {self.fbf_patterns_path}). "
            f"Set FBF_PATTERNS_PATH in .env or add {backend_root / 'config' / 'fbf_patterns.yaml'}"
        )

    def resolved_visitor_store_path(self) -> Path:
        explicit = os.environ.get("VISITOR_STORE_PATH", "").strip()
        if explicit:
            return Path(explicit)

        if self.visitor_store_path != "data/visitors.json":
            path = Path(self.visitor_store_path)
            if path.is_absolute():
                return path
            backend_root = Path(__file__).resolve().parent.parent
            return backend_root / path

        if os.environ.get("RENDER") == "true":
            return Path("/app/data/visitors.json")

        backend_root = Path(__file__).resolve().parent.parent
        return backend_root / "data" / "visitors.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
