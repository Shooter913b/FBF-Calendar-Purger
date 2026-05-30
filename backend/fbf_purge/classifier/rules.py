import re

from fbf_purge.canvas.models import CalendarEvent
from fbf_purge.classifier.patterns import Patterns


def classify_event(event: CalendarEvent, patterns: Patterns) -> tuple[bool, str | None]:
    if event.workflow_state == "deleted":
        return False, None

    title = event.title or ""

    for pattern in patterns.exclude_title_regex:
        if re.search(pattern, title, re.IGNORECASE):
            return False, "excluded by title regex"

    haystacks = [
        (event.description or "").lower(),
        (event.html_url or "").lower(),
    ]

    for domain in patterns.domains:
        domain_lower = domain.lower()
        for hay in haystacks:
            if domain_lower in hay:
                return True, f"domain match: {domain}"

    for sub in patterns.description_substrings:
        sub_lower = sub.lower()
        if sub_lower in (event.description or "").lower():
            return True, f"description substring: {sub}"

    sep = patterns.title_suffix_separator
    for prefix in patterns.title_step_prefixes:
        if title.startswith(prefix) and sep in title:
            return True, f"title step prefix: {prefix}"

    return False, None


def classify_events(
    events: list[CalendarEvent],
    patterns: Patterns,
) -> tuple[list[CalendarEvent], list[CalendarEvent]]:
    fbf_events: list[CalendarEvent] = []
    other_events: list[CalendarEvent] = []
    for event in events:
        is_fbf, _ = classify_event(event, patterns)
        if is_fbf:
            fbf_events.append(event)
        else:
            other_events.append(event)
    return fbf_events, other_events
