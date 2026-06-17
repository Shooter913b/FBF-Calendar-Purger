import json
import logging
import os
import threading
from pathlib import Path
from typing import Protocol
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)

VISITOR_REDIS_SET_KEY = "fbf:visitor_ids"


class VisitorStoreBackend(Protocol):
    def register(self, visitor_id: str) -> tuple[int, bool]:
        """Return (lifetime_users, is_new_visitor)."""


class FileVisitorStore:
    """JSON file on a persistent filesystem (e.g. Render attached disk)."""

    def __init__(self, path: Path):
        self._path = path
        self._lock = threading.Lock()

    def _load_ids(self) -> set[str]:
        if not self._path.is_file():
            return set()
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return set()
        raw = data.get("visitor_ids", [])
        if not isinstance(raw, list):
            return set()
        return {item for item in raw if isinstance(item, str) and is_valid_visitor_id(item)}

    def _save_ids(self, visitor_ids: set[str]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"visitor_ids": sorted(visitor_ids)}
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(self._path)

    def register(self, visitor_id: str) -> tuple[int, bool]:
        if not is_valid_visitor_id(visitor_id):
            raise ValueError("Invalid visitor id")

        with self._lock:
            visitor_ids = self._load_ids()
            is_new = visitor_id not in visitor_ids
            if is_new:
                visitor_ids.add(visitor_id)
                self._save_ids(visitor_ids)
            return len(visitor_ids), is_new


class UpstashVisitorStore:
    """Redis set over Upstash REST (survives Render sleep on the free tier)."""

    def __init__(self, rest_url: str, rest_token: str, set_key: str = VISITOR_REDIS_SET_KEY):
        self._rest_url = rest_url.rstrip("/")
        self._rest_token = rest_token
        self._set_key = set_key
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

    def register(self, visitor_id: str) -> tuple[int, bool]:
        if not is_valid_visitor_id(visitor_id):
            raise ValueError("Invalid visitor id")

        with self._lock:
            added = int(self._run(["SADD", self._set_key, visitor_id]))
            count = int(self._run(["SCARD", self._set_key]))
            return count, added == 1


def is_valid_visitor_id(value: str | None) -> bool:
    if not value:
        return False
    try:
        parsed = UUID(value)
    except (TypeError, ValueError, AttributeError):
        return False
    return str(parsed) == value.lower()


def create_visitor_store(
    *,
    store_path: Path,
    upstash_redis_rest_url: str = "",
    upstash_redis_rest_token: str = "",
) -> VisitorStoreBackend:
    if upstash_redis_rest_url.strip() and upstash_redis_rest_token.strip():
        logger.info("Visitor stats: using Upstash Redis")
        return UpstashVisitorStore(
            rest_url=upstash_redis_rest_url.strip(),
            rest_token=upstash_redis_rest_token.strip(),
        )

    logger.info("Visitor stats: using file store at %s", store_path)
    return FileVisitorStore(store_path)


# Backwards-compatible alias for tests and imports.
VisitorStore = FileVisitorStore
