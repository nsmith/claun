"""Configuration dataclasses for claun."""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class MinuteInterval(Enum):
    """Predefined minute intervals for scheduling."""

    EVERY_1 = 1
    EVERY_5 = 5
    EVERY_15 = 15
    EVERY_60 = 60


class DayOfWeek(Enum):
    """Days of the week (Monday=0, Sunday=6)."""

    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


ALL_DAYS: frozenset[int] = frozenset({0, 1, 2, 3, 4, 5, 6})
WEEKDAYS: frozenset[int] = frozenset({0, 1, 2, 3, 4})
WEEKENDS: frozenset[int] = frozenset({5, 6})


@dataclass
class HourConfig:
    """Configuration for which hours to run."""

    run_every_hour: bool = True
    start_hour: int = 0  # 0-23, only used if run_every_hour=False
    end_hour: int = 23  # 0-23, only used if run_every_hour=False

    def __post_init__(self) -> None:
        if not 0 <= self.start_hour <= 23:
            raise ValueError(f"start_hour must be 0-23, got {self.start_hour}")
        if not 0 <= self.end_hour <= 23:
            raise ValueError(f"end_hour must be 0-23, got {self.end_hour}")


@dataclass
class AdvancedConfig:
    """Advanced timing configuration for power users."""

    # Specific dates to run (YYYY-MM-DD format)
    specific_dates: list[str] = field(default_factory=list)

    # Specific days of month (1-31)
    days_of_month: set[int] = field(default_factory=set)

    # Specific hours to run (0-23, overrides HourConfig)
    specific_hours: set[int] = field(default_factory=set)

    # Custom minute interval (overrides MinuteInterval)
    custom_minute_interval: Optional[int] = None

    def __post_init__(self) -> None:
        for day in self.days_of_month:
            if not 1 <= day <= 31:
                raise ValueError(f"day_of_month must be 1-31, got {day}")
        for hour in self.specific_hours:
            if not 0 <= hour <= 23:
                raise ValueError(f"hour must be 0-23, got {hour}")


@dataclass
class ScheduleConfig:
    """Complete schedule configuration."""

    # Required: the prompt to run
    command: str

    # Optional extra flags for claude (e.g., "--resume abc123")
    claude_flags: str = ""

    # Days of week to run (0=Monday, 6=Sunday)
    days_of_week: set[int] = field(default_factory=lambda: set(ALL_DAYS))

    # Hour configuration
    hours: HourConfig = field(default_factory=HourConfig)

    # Minute interval
    minute_interval: MinuteInterval = MinuteInterval.EVERY_15

    # Advanced configuration (optional)
    advanced: Optional[AdvancedConfig] = None

    # Logging configuration
    log_path: str = "."
    log_id: Optional[str] = None

    def __post_init__(self) -> None:
        # Command can be empty for TUI mode where user enters it interactively
        for day in self.days_of_week:
            if not 0 <= day <= 6:
                raise ValueError(f"day_of_week must be 0-6, got {day}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        result: dict[str, Any] = {
            "command": self.command,
            "claude_flags": self.claude_flags,
            "days_of_week": sorted(self.days_of_week),
            "hours": {
                "run_every_hour": self.hours.run_every_hour,
                "start_hour": self.hours.start_hour,
                "end_hour": self.hours.end_hour,
            },
            "minute_interval": self.minute_interval.value,
            "log_path": self.log_path,
        }
        if self.log_id:
            result["log_id"] = self.log_id
        if self.advanced:
            result["advanced"] = {
                "specific_dates": self.advanced.specific_dates,
                "days_of_month": sorted(self.advanced.days_of_month),
                "specific_hours": sorted(self.advanced.specific_hours),
                "custom_minute_interval": self.advanced.custom_minute_interval,
            }
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScheduleConfig":
        """Load from dict."""
        hours_data = data.get("hours", {})
        hours = HourConfig(
            run_every_hour=hours_data.get("run_every_hour", True),
            start_hour=hours_data.get("start_hour", 0),
            end_hour=hours_data.get("end_hour", 23),
        )

        advanced = None
        if "advanced" in data:
            adv_data = data["advanced"]
            advanced = AdvancedConfig(
                specific_dates=adv_data.get("specific_dates", []),
                days_of_month=set(adv_data.get("days_of_month", [])),
                specific_hours=set(adv_data.get("specific_hours", [])),
                custom_minute_interval=adv_data.get("custom_minute_interval"),
            )

        return cls(
            command=data.get("command", ""),
            claude_flags=data.get("claude_flags", ""),
            days_of_week=set(data.get("days_of_week", ALL_DAYS)),
            hours=hours,
            minute_interval=MinuteInterval(data.get("minute_interval", 15)),
            advanced=advanced,
            log_path=data.get("log_path", "."),
            log_id=data.get("log_id"),
        )

    def save_to_file(self, path: Path) -> None:
        """Save config to JSON file."""
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n")

    @classmethod
    def load_from_file(cls, path: Path) -> "ScheduleConfig":
        """Load config from JSON file."""
        data = json.loads(path.read_text())
        return cls.from_dict(data)


@dataclass
class AppState:
    """Runtime application state."""

    config: ScheduleConfig
    is_paused: bool = False
    is_running: bool = False
    last_run_time: Optional[str] = None
    next_run_time: Optional[str] = None
    current_log_file: Optional[str] = None
