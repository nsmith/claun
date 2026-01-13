"""Tests for the log manager module."""

import pytest
from datetime import datetime
from pathlib import Path

from claun.logging.manager import LogManager, LogEntry


class TestLogManagerBasics:
    """Test basic log manager functionality."""

    def test_create_manager(self, temp_log_dir: Path) -> None:
        """LogManager can be created."""
        manager = LogManager(temp_log_dir)
        assert manager.base_path == temp_log_dir

    def test_create_manager_with_id(self, temp_log_dir: Path) -> None:
        """LogManager can be created with log ID."""
        manager = LogManager(temp_log_dir, log_id="myproject")
        assert manager.log_id == "myproject"


class TestLogFileCreation:
    """Test log file creation."""

    def test_creates_log_file(self, temp_log_dir: Path) -> None:
        """LogManager creates log files."""
        manager = LogManager(temp_log_dir)
        log_path = manager.create_log()

        assert log_path.exists()
        assert log_path.suffix == ".txt"

    def test_log_filename_format(self, temp_log_dir: Path) -> None:
        """Log filename follows expected format."""
        manager = LogManager(temp_log_dir)
        log_path = manager.create_log()

        # Format: claun_YYYYMMDD_HHMMSS.txt
        assert "claun_" in log_path.name

    def test_log_filename_with_id(self, temp_log_dir: Path) -> None:
        """Log filename includes ID prefix."""
        manager = LogManager(temp_log_dir, log_id="myproject")
        log_path = manager.create_log()

        # Format: myproject_claun_YYYYMMDD_HHMMSS.txt
        assert log_path.name.startswith("myproject_claun_")

    def test_creates_directory_if_missing(self, tmp_path: Path) -> None:
        """LogManager creates log directory if it doesn't exist."""
        log_dir = tmp_path / "new_logs"
        manager = LogManager(log_dir)
        log_path = manager.create_log()

        assert log_dir.exists()
        assert log_path.exists()


class TestPausedLogEntry:
    """Test paused log entries."""

    def test_creates_paused_entry(self, temp_log_dir: Path) -> None:
        """LogManager creates paused log entry."""
        manager = LogManager(temp_log_dir)
        scheduled_time = datetime(2026, 1, 12, 10, 15, 0)

        log_path = manager.create_paused_entry(scheduled_time)

        assert log_path.exists()
        content = log_path.read_text()
        assert "paused" in content.lower()
        assert "10:15" in content


class TestLogListing:
    """Test log file listing."""

    def test_lists_logs(self, temp_log_dir: Path) -> None:
        """LogManager lists existing logs."""
        manager = LogManager(temp_log_dir)

        # Create some logs
        manager.create_log()
        manager.create_log()

        logs = manager.list_logs()

        assert len(logs) == 2

    def test_lists_logs_newest_first(self, temp_log_dir: Path) -> None:
        """Logs are listed newest first."""
        manager = LogManager(temp_log_dir)

        # Create logs
        first = manager.create_log()
        import time
        time.sleep(0.01)  # Ensure different timestamps
        second = manager.create_log()

        logs = manager.list_logs()

        # Newest first
        assert logs[0].path == second
        assert logs[1].path == first

    def test_respects_limit(self, temp_log_dir: Path) -> None:
        """list_logs respects limit parameter."""
        manager = LogManager(temp_log_dir)

        # Create 5 logs
        for _ in range(5):
            manager.create_log()

        logs = manager.list_logs(limit=3)

        assert len(logs) == 3


class TestLogParsing:
    """Test log metadata parsing."""

    def test_parses_timestamp_from_filename(self, temp_log_dir: Path) -> None:
        """LogManager parses timestamp from filename."""
        manager = LogManager(temp_log_dir)
        log_path = manager.create_log()

        logs = manager.list_logs()

        assert logs[0].timestamp is not None
        assert logs[0].timestamp.year == datetime.now().year

    def test_parses_log_id_from_filename(self, temp_log_dir: Path) -> None:
        """LogManager parses log ID from filename."""
        manager = LogManager(temp_log_dir, log_id="myproject")
        manager.create_log()

        logs = manager.list_logs()

        assert logs[0].log_id == "myproject"


class TestLastRunInference:
    """Test last run time inference from logs."""

    def test_infers_last_run(self, temp_log_dir: Path) -> None:
        """LogManager infers last run from logs."""
        manager = LogManager(temp_log_dir)
        manager.create_log()

        last_run = manager.get_last_run_time()

        assert last_run is not None
        assert last_run.year == datetime.now().year

    def test_no_logs_returns_none(self, temp_log_dir: Path) -> None:
        """No logs means no last run time."""
        manager = LogManager(temp_log_dir)

        last_run = manager.get_last_run_time()

        assert last_run is None
