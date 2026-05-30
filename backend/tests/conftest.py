import json
from pathlib import Path

import pytest

from fbf_purge.classifier.patterns import load_patterns

FIXTURES = Path(__file__).parent / "fixtures"
PATTERNS_PATH = Path(__file__).resolve().parent.parent / "config" / "fbf_patterns.yaml"


@pytest.fixture
def patterns():
    return load_patterns(PATTERNS_PATH)


def load_fixture(name: str) -> dict:
    with (FIXTURES / name).open(encoding="utf-8") as f:
        return json.load(f)
