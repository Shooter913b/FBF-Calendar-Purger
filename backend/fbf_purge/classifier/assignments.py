from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fbf_purge.canvas.models import CalendarEvent
from fbf_purge.classifier.patterns import Patterns

_DASH_CHARS = ("\u2013", "\u2014", "\u2212", "\u2010", "\u2011")
_EXTERNAL_TOOL_ID_RE = re.compile(r"/external_tools/(\d+)", re.IGNORECASE)


def _normalize(text: str | None) -> str:
    return (text or "").strip().casefold()


def _normalize_title(title: str | None, separator: str) -> str:
    value = (title or "").strip()
    for dash in _DASH_CHARS:
        value = value.replace(dash, "-")
    sep = separator.strip() or "-"
    if sep != "-":
        value = re.sub(r"\s*-\s*", sep, value)
    value = re.sub(r"\s+", " ", value)
    return value.casefold()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _same_instant(left: datetime, right: datetime) -> bool:
    if left.tzinfo is None:
        left = left.replace(tzinfo=timezone.utc)
    if right.tzinfo is None:
        right = right.replace(tzinfo=timezone.utc)
    return left.astimezone(timezone.utc) == right.astimezone(timezone.utc)


def _pattern_haystacks(*values: str | None) -> list[str]:
    return [(value or "").lower() for value in values if value]


def _matches_patterns(values: list[str], patterns: Patterns) -> bool:
    for domain in patterns.domains:
        domain_lower = domain.lower()
        if any(domain_lower in hay for hay in values):
            return True
    for sub in patterns.description_substrings + patterns.external_tool_name_substrings:
        sub_lower = sub.lower()
        if any(sub_lower in hay for hay in values):
            return True
    return False


@dataclass
class FbfToolCatalog:
    tool_ids: set[int] = field(default_factory=set)
    url_fragments: list[str] = field(default_factory=list)

    @classmethod
    def from_external_tools(
        cls,
        tools: list[dict],
        patterns: Patterns,
    ) -> FbfToolCatalog:
        tool_ids: set[int] = set()
        url_fragments: list[str] = []
        for tool in tools:
            haystacks = _pattern_haystacks(
                tool.get("name"),
                tool.get("url"),
                tool.get("domain"),
            )
            if not _matches_patterns(haystacks, patterns):
                continue
            tool_ids.add(int(tool["id"]))
            for value in (tool.get("url"), tool.get("domain")):
                fragment = (value or "").strip().lower()
                if fragment and fragment not in url_fragments:
                    url_fragments.append(fragment)
        return cls(tool_ids=tool_ids, url_fragments=url_fragments)

    @property
    def has_fbf_tools(self) -> bool:
        return bool(self.tool_ids or self.url_fragments)

    def matches_launch_url(self, url: str | None) -> bool:
        hay = (url or "").lower()
        if not hay:
            return False
        match = _EXTERNAL_TOOL_ID_RE.search(hay)
        if match and int(match.group(1)) in self.tool_ids:
            return True
        return any(fragment in hay for fragment in self.url_fragments)


def is_fbf_assignment(
    assignment: dict,
    patterns: Patterns,
    tool_catalog: FbfToolCatalog | None = None,
) -> bool:
    submission_types = assignment.get("submission_types") or []
    if "external_tool" not in submission_types:
        return False

    tool = assignment.get("external_tool_tag_attributes") or {}
    haystacks = _pattern_haystacks(
        tool.get("url"),
        assignment.get("description"),
        assignment.get("name"),
    )
    if _matches_patterns(haystacks, patterns):
        return True

    if tool_catalog is not None:
        if tool_catalog.matches_launch_url(tool.get("url")):
            return True
        content_id = tool.get("content_id")
        if content_id is not None and int(content_id) in tool_catalog.tool_ids:
            return True

    return False


@dataclass(frozen=True)
class FbfAssignmentRecord:
    assignment_id: int
    name: str
    due_at: str | None = None


@dataclass
class FbfAssignmentIndex:
    assignments: list[FbfAssignmentRecord]

    @classmethod
    def from_course_assignments(
        cls,
        assignments: list[dict],
        patterns: Patterns,
        external_tools: list[dict] | None = None,
    ) -> FbfAssignmentIndex:
        tool_catalog = (
            FbfToolCatalog.from_external_tools(external_tools, patterns)
            if external_tools is not None
            else FbfToolCatalog()
        )
        records: list[FbfAssignmentRecord] = []
        for item in assignments:
            if not is_fbf_assignment(item, patterns, tool_catalog):
                continue
            records.append(
                FbfAssignmentRecord(
                    assignment_id=int(item["id"]),
                    name=item.get("name") or f"Assignment {item['id']}",
                    due_at=item.get("due_at"),
                )
            )
        return cls(assignments=records)

    @property
    def fbf_assignment_ids(self) -> set[int]:
        return {record.assignment_id for record in self.assignments}

    def due_at_for(self, assignment_id: int) -> str | None:
        for record in self.assignments:
            if record.assignment_id == assignment_id:
                return record.due_at
        return None

    def _title_variants(self, event: CalendarEvent, patterns: Patterns) -> list[str]:
        raw_title = event.title or ""
        sep = patterns.title_suffix_separator
        variants = {
            _normalize(raw_title),
            _normalize_title(raw_title, sep),
        }
        norm_title = _normalize_title(raw_title, sep)
        sep_norm = _normalize(sep)
        for prefix in patterns.title_step_prefixes:
            prefix_norm = _normalize(prefix)
            prefix_with_sep = f"{prefix_norm}{sep_norm}"
            if norm_title.startswith(prefix_with_sep):
                variants.add(norm_title[len(prefix_with_sep) :].strip())
        return [variant for variant in variants if variant]

    def _event_times(self, event: CalendarEvent) -> list[datetime]:
        times: list[datetime] = []
        for value in (event.start_at, event.end_at):
            parsed = _parse_iso(value)
            if parsed is not None:
                times.append(parsed)
        return times

    def match_event(self, event: CalendarEvent, patterns: Patterns) -> tuple[int, str] | None:
        if not self.assignments:
            return None

        title_variants = self._title_variants(event, patterns)
        if not title_variants:
            return None

        event_times = self._event_times(event)
        sep = patterns.title_suffix_separator
        sep_norm = _normalize(sep)

        for record in self.assignments:
            name = _normalize(record.name)
            name_variants = {
                name,
                _normalize_title(record.name, sep),
            }
            if not name or not any(title_variants):
                continue

            for title in title_variants:
                if title in name_variants:
                    return record.assignment_id, f"title matches FBF assignment: {record.name}"

                for prefix in patterns.title_step_prefixes:
                    prefix_norm = _normalize(prefix)
                    candidate = _normalize_title(f"{prefix}{sep}{record.name}", sep)
                    if title == candidate:
                        return (
                            record.assignment_id,
                            f"title matches FBF step for assignment: {record.name}",
                        )
                    if sep_norm and title.endswith(f"{sep_norm}{name}"):
                        return (
                            record.assignment_id,
                            f"title suffix matches FBF assignment: {record.name}",
                        )

                if len(name) >= 4 and (name in title or title in name):
                    return (
                        record.assignment_id,
                        f"title overlaps FBF assignment name: {record.name}",
                    )

            due = _parse_iso(record.due_at)
            if due is not None and event_times:
                for event_time in event_times:
                    if not _same_instant(event_time, due):
                        continue
                    for title in title_variants:
                        if title in name_variants or (
                            len(name) >= 4 and (name in title or title in name)
                        ):
                            return (
                                record.assignment_id,
                                f"due date and title match FBF assignment: {record.name}",
                            )

        return None
