from pathlib import Path

import pytest

from fbf_purge.config import Settings


def test_resolved_patterns_path_with_backend_prefix():
    backend_root = Path(__file__).resolve().parent.parent
    settings = Settings(fbf_patterns_path="backend/config/fbf_patterns.yaml")
    resolved = settings.resolved_patterns_path()
    assert resolved == backend_root / "config" / "fbf_patterns.yaml"
    assert resolved.is_file()


def test_resolved_patterns_path_default():
    backend_root = Path(__file__).resolve().parent.parent
    settings = Settings(fbf_patterns_path="config/fbf_patterns.yaml")
    resolved = settings.resolved_patterns_path()
    assert resolved == backend_root / "config" / "fbf_patterns.yaml"
