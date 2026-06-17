import json
import logging
import threading
from pathlib import Path
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)

VISIT_COUNT_REDIS_KEY = "fbf:visit_count"


class VisitCounterBackend(Protocol):
    def record_visit(self) -> int:
        """Increment and return total visit count."""


class FileVisitCounter:
    """JSON file on a persistent filesystem (e.g. Render attached disk)."""

    def __init__(self, path: Path):
        self._path = path
        self._lock = threading.Lock()

    def _load_count(self) -> int:
        if not self._path.is_file():
            return 0
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return 0
        raw = data.get("visit_count", 0)
        if isinstance(raw, int) and raw >= 0:
            return raw
        if isinstance(raw, float) and raw >= 0:
            return int(raw)
        return 0

    def _save_count(self, visit_count: int) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"visit_count": visit_count}
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(self._path)

    def record_visit(self) -> int:
        with self._lock:
            visit_count = self._load_count() + 1
            self._save_count(visit_count)
            return visit_count


class UpstashVisitCounter:
    """Redis counter over Upstash REST (survives Render sleep on the free tier)."""

    def __init__(self, rest_url: str, rest_token: str, counter_key: str = VISIT_COUNT_REDIS_KEY):
        self._rest_url = rest_url.rstrip("/")
        self._rest_token = rest_token
        self._counter_key = counter_key
        self._lock = threading.Lock()

    def _run(self, command: list[str | int]) -> object:
        response = httpx.post(
            self._rest_url,
            headers={"Authorization": f"Bearer {self._rest_token}"},
            json=command,
            timeout=10.0,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("error"):
            raise RuntimeError(str(payload["error"]))
        return payload["result"]

    def record_visit(self) -> int:
        with self._lock:
            return int(self._run(["INCR", self._counter_key]))


def create_visit_counter(
    *,
    store_path: Path,
    upstash_redis_rest_url: str = "",
    upstash_redis_rest_token: str = "",
) -> VisitCounterBackend:
    if upstash_redis_rest_url.strip() and upstash_redis_rest_token.strip():
        logger.info("Visit stats: using Upstash Redis")
        return UpstashVisitCounter(
            rest_url=upstash_redis_rest_url.strip(),
            rest_token=upstash_redis_rest_token.strip(),
        )

    logger.info("Visit stats: using file store at %s", store_path)
    return FileVisitCounter(store_path)


# Backwards-compatible aliases for tests and app state attribute name.
VisitorStore = FileVisitCounter
create_visitor_store = create_visit_counter
