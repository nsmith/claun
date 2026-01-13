"""Configuration dataclasses for claun."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


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

    # Required: the command to run
    command: str

    # Optional session name for persistence
    session_name: Optional[str] = None

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


@dataclass
class AppState:
    """Runtime application state."""

    config: ScheduleConfig
    is_paused: bool = False
    is_running: bool = False
    last_run_time: Optional[str] = None
    next_run_time: Optional[str] = None
    current_log_file: Optional[str] = None
