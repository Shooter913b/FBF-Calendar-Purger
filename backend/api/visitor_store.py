import json
import threading
from pathlib import Path
from uuid import UUID


class VisitorStore:
    """Persistent set of anonymous visitor UUIDs (no personal data)."""

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
        self._path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def register(self, visitor_id: str) -> tuple[int, bool]:
        """Return (lifetime_users, is_new_visitor)."""
        if not is_valid_visitor_id(visitor_id):
            raise ValueError("Invalid visitor id")

        with self._lock:
            visitor_ids = self._load_ids()
            is_new = visitor_id not in visitor_ids
            if is_new:
                visitor_ids.add(visitor_id)
                self._save_ids(visitor_ids)
            return len(visitor_ids), is_new


def is_valid_visitor_id(value: str | None) -> bool:
    if not value:
        return False
    try:
        parsed = UUID(value)
    except (TypeError, ValueError, AttributeError):
        return False
    return str(parsed) == value.lower().lower()
