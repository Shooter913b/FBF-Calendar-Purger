from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Patterns:
    domains: list[str] = field(default_factory=lambda: ["feedbackfruits.com"])
    title_step_prefixes: list[str] = field(default_factory=list)
    title_suffix_separator: str = " - "
    description_substrings: list[str] = field(default_factory=lambda: ["feedbackfruits"])
    external_tool_name_substrings: list[str] = field(
        default_factory=lambda: ["feedback fruits", "feedbackfruits"]
    )
    exclude_title_regex: list[str] = field(default_factory=list)


def load_patterns(path: str | Path) -> Patterns:
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return Patterns(
        domains=data.get("domains", ["feedbackfruits.com"]),
        title_step_prefixes=data.get("title_step_prefixes", []),
        title_suffix_separator=data.get("title_suffix_separator", " - "),
        description_substrings=data.get("description_substrings", ["feedbackfruits"]),
        external_tool_name_substrings=data.get(
            "external_tool_name_substrings",
            ["feedback fruits", "feedbackfruits"],
        ),
        exclude_title_regex=data.get("exclude_title_regex", []),
    )
