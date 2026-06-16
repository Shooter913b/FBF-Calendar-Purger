from __future__ import annotations

import re

_DASH_CHARS = ("\u2013", "\u2014", "\u2212", "\u2010", "\u2011")


def normalize_title(title: str | None, separator: str) -> str:
    value = (title or "").strip()
    for dash in _DASH_CHARS:
        value = value.replace(dash, "-")
    sep = separator.strip() or "-"
    if sep != "-":
        value = re.sub(r"\s*-\s*", sep, value)
    value = re.sub(r"\s+", " ", value)
    return value.casefold()
