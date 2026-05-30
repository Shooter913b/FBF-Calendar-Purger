import hashlib
import json
import time
from dataclasses import dataclass

from itsdangerous import BadSignature, URLSafeTimedSerializer


@dataclass
class PreviewState:
    course_id: int
    matched_count: int
    event_ids: list[int]
    preview_hash: str
    created_at: float


class PreviewStore:
    """Signed preview tokens (stateless, 15 min TTL)."""

    def __init__(self, secret: str, max_age_seconds: int = 900):
        self._serializer = URLSafeTimedSerializer(secret, salt="fbf-purge-preview")
        self._max_age = max_age_seconds

    @staticmethod
    def compute_hash(event_ids: list[int], matched_count: int) -> str:
        payload = json.dumps(
            {"event_ids": sorted(event_ids), "matched_count": matched_count},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def create_token(self, course_id: int, matched_count: int, event_ids: list[int]) -> str:
        preview_hash = self.compute_hash(event_ids, matched_count)
        data = {
            "course_id": course_id,
            "matched_count": matched_count,
            "event_ids": event_ids,
            "preview_hash": preview_hash,
            "created_at": time.time(),
        }
        return self._serializer.dumps(data)

    def load_token(self, token: str, course_id: int) -> PreviewState:
        try:
            data = self._serializer.loads(token, max_age=self._max_age)
        except BadSignature as exc:
            raise ValueError("Preview token expired or invalid") from exc
        if int(data["course_id"]) != course_id:
            raise ValueError("Preview token does not match course")
        return PreviewState(
            course_id=int(data["course_id"]),
            matched_count=int(data["matched_count"]),
            event_ids=[int(x) for x in data["event_ids"]],
            preview_hash=str(data["preview_hash"]),
            created_at=float(data.get("created_at", 0)),
        )

    def validate_selection(
        self,
        token: str,
        course_id: int,
        selected_event_ids: list[int],
        current_event_ids: list[int],
    ) -> None:
        state = self.load_token(token, course_id)
        current_hash = self.compute_hash(current_event_ids, len(current_event_ids))
        if state.preview_hash != current_hash:
            raise ValueError("Preview is stale; calendar changed since last review")
        if not selected_event_ids:
            raise ValueError("No events selected")
        unknown = set(selected_event_ids) - set(current_event_ids)
        if unknown:
            raise ValueError("Selected events are not in the current preview")
