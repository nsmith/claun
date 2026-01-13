"""Data models for scheduling."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TimeSpec:
    """Specification for a time of day."""

    hour: int  # 0-23
    minute: int  # 0-59

    def __post_init__(self) -> None:
        if not 0 <= self.hour <= 23:
            raise ValueError(f"hour must be 0-23, got {self.hour}")
        if not 0 <= self.minute <= 59:
            raise ValueError(f"minute must be 0-59, got {self.minute}")

    def to_24h_string(self) -> str:
        """Format as 24-hour time string (HH:MM)."""
        return f"{self.hour:02d}:{self.minute:02d}"

    def to_12h_string(self) -> str:
        """Format as 12-hour time string (H:MMam/pm)."""
        period = "am" if self.hour < 12 else "pm"
        hour_12 = self.hour % 12
        if hour_12 == 0:
            hour_12 = 12
        return f"{hour_12}:{self.minute:02d}{period}"


@dataclass
class ScheduleResult:
    """Result of a next-run calculation."""

    next_run: datetime
    was_adjusted: bool = False
    adjustment_reason: Optional[str] = None
