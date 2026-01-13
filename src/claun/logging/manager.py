"""Log file management for claun."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
import re


@dataclass
class LogEntry:
    """Represents a log file entry."""

    path: Path
    timestamp: Optional[datetime] = None
    log_id: Optional[str] = None
    is_paused: bool = False


class LogManager:
    """Manages log files for claun runs."""

    # Pattern: [id_]claun_YYYYMMDD_HHMMSS[_microseconds].txt
    LOG_PATTERN = re.compile(
        r"(?:(?P<log_id>.+?)_)?claun_(?P<date>\d{8})_(?P<time>\d{6})(?:_(?P<micro>\d+))?\.txt$"
    )

    def __init__(
        self,
        base_path: Path,
        log_id: Optional[str] = None,
    ) -> None:
        """Initialize log manager.

        Args:
            base_path: Directory to store log files.
            log_id: Optional ID prefix for log filenames.
        """
        self.base_path = Path(base_path)
        self.log_id = log_id

    def create_log(self, timestamp: Optional[datetime] = None) -> Path:
        """Create a new log file.

        Args:
            timestamp: Timestamp for the log. Defaults to now.

        Returns:
            Path to the created log file.
        """
        if timestamp is None:
            timestamp = datetime.now()

        self.base_path.mkdir(parents=True, exist_ok=True)

        filename = self._build_filename(timestamp)
        log_path = self.base_path / filename

        # Create empty file
        log_path.touch()

        return log_path

    def create_paused_entry(self, scheduled_time: datetime) -> Path:
        """Create a log entry for a paused/skipped run.

        Args:
            scheduled_time: When the run was scheduled to happen.

        Returns:
            Path to the created log file.
        """
        log_path = self.create_log(timestamp=scheduled_time)

        content = (
            f"# Claun Run Skipped\n"
            f"Status: PAUSED\n"
            f"Scheduled time: {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"\n"
            f"This job was paused when it was scheduled to run.\n"
        )
        log_path.write_text(content)

        return log_path

    def list_logs(self, limit: int = 50) -> list[LogEntry]:
        """List log files, newest first.

        Args:
            limit: Maximum number of logs to return.

        Returns:
            List of LogEntry objects, sorted by timestamp descending.
        """
        if not self.base_path.exists():
            return []

        entries: list[LogEntry] = []

        for path in self.base_path.glob("*claun_*.txt"):
            entry = self._parse_log_file(path)
            if entry:
                entries.append(entry)

        # Sort by timestamp (newest first), then by path (as tiebreaker for same second)
        entries.sort(key=lambda e: (e.timestamp or datetime.min, e.path.name), reverse=True)

        return entries[:limit]

    def get_last_run_time(self) -> Optional[datetime]:
        """Get the timestamp of the most recent run.

        Returns:
            Datetime of last run, or None if no logs exist.
        """
        logs = self.list_logs(limit=1)
        if logs:
            return logs[0].timestamp
        return None

    def _build_filename(self, timestamp: datetime) -> str:
        """Build log filename from timestamp."""
        date_str = timestamp.strftime("%Y%m%d")
        time_str = timestamp.strftime("%H%M%S")
        micro_str = str(timestamp.microsecond)

        if self.log_id:
            return f"{self.log_id}_claun_{date_str}_{time_str}_{micro_str}.txt"
        return f"claun_{date_str}_{time_str}_{micro_str}.txt"

    def _parse_log_file(self, path: Path) -> Optional[LogEntry]:
        """Parse metadata from log filename."""
        match = self.LOG_PATTERN.match(path.name)
        if not match:
            return None

        log_id = match.group("log_id")
        date_str = match.group("date")
        time_str = match.group("time")

        try:
            timestamp = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
        except ValueError:
            timestamp = None

        # Check if it's a paused entry
        is_paused = False
        try:
            content = path.read_text()
            is_paused = "Status: PAUSED" in content
        except Exception:
            pass

        return LogEntry(
            path=path,
            timestamp=timestamp,
            log_id=log_id,
            is_paused=is_paused,
        )
