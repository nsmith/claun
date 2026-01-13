"""Pytest configuration and fixtures."""

import pytest
from datetime import datetime
from pathlib import Path


@pytest.fixture
def fixed_now() -> datetime:
    """A fixed datetime for deterministic tests."""
    return datetime(2026, 1, 12, 10, 0, 0)


@pytest.fixture
def temp_log_dir(tmp_path: Path) -> Path:
    """A temporary directory for log files."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir
