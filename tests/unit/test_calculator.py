"""Tests for the schedule calculator module."""

import pytest
from datetime import datetime

from claun.core.config import (
    ScheduleConfig,
    HourConfig,
    MinuteInterval,
    AdvancedConfig,
    WEEKDAYS,
)
from claun.scheduling.calculator import ScheduleCalculator


class TestBasicCalculation:
    """Test basic schedule calculation."""

    def test_calculate_from_config(self, fixed_now: datetime) -> None:
        """Calculator can compute next run from config."""
        config = ScheduleConfig(command="test")
        calc = ScheduleCalculator(config)

        result = calc.get_next_run(from_time=fixed_now)

        assert result.next_run > fixed_now

    def test_15_minute_interval(self, fixed_now: datetime) -> None:
        """15-minute interval works correctly."""
        config = ScheduleConfig(
            command="test",
            minute_interval=MinuteInterval.EVERY_15,
        )
        calc = ScheduleCalculator(config)

        result = calc.get_next_run(from_time=fixed_now)

        # At 10:00, next run should be 10:15
        assert result.next_run == fixed_now.replace(minute=15)

    def test_5_minute_interval(self, fixed_now: datetime) -> None:
        """5-minute interval works correctly."""
        config = ScheduleConfig(
            command="test",
            minute_interval=MinuteInterval.EVERY_5,
        )
        calc = ScheduleCalculator(config)

        result = calc.get_next_run(from_time=fixed_now)

        assert result.next_run == fixed_now.replace(minute=5)


class TestDayConstraints:
    """Test day-of-week constraints."""

    def test_weekdays_only(self) -> None:
        """Weekdays-only constraint works."""
        config = ScheduleConfig(
            command="test",
            days_of_week=set(WEEKDAYS),
            minute_interval=MinuteInterval.EVERY_60,
        )
        calc = ScheduleCalculator(config)

        # Saturday at noon
        saturday = datetime(2026, 1, 17, 12, 0, 0)
        result = calc.get_next_run(from_time=saturday)

        # Should be Monday
        assert result.next_run.weekday() == 0
        assert result.was_adjusted


class TestHourConstraints:
    """Test hour range constraints."""

    def test_hour_range(self) -> None:
        """Hour range constraint works."""
        config = ScheduleConfig(
            command="test",
            hours=HourConfig(run_every_hour=False, start_hour=9, end_hour=17),
            minute_interval=MinuteInterval.EVERY_60,
        )
        calc = ScheduleCalculator(config)

        # At 6am
        early = datetime(2026, 1, 12, 6, 0, 0)
        result = calc.get_next_run(from_time=early)

        assert result.next_run.hour == 9
        assert result.was_adjusted


class TestAdvancedConfig:
    """Test advanced configuration options."""

    def test_custom_minute_interval(self, fixed_now: datetime) -> None:
        """Custom minute interval from advanced config works."""
        config = ScheduleConfig(
            command="test",
            advanced=AdvancedConfig(custom_minute_interval=7),
        )
        calc = ScheduleCalculator(config)

        result = calc.get_next_run(from_time=fixed_now)

        # At 10:00, next run should be 10:07
        assert result.next_run.minute == 7

    def test_specific_hours(self, fixed_now: datetime) -> None:
        """Specific hours from advanced config works."""
        config = ScheduleConfig(
            command="test",
            advanced=AdvancedConfig(specific_hours={14, 18}),
            minute_interval=MinuteInterval.EVERY_60,
        )
        calc = ScheduleCalculator(config)

        result = calc.get_next_run(from_time=fixed_now)

        # At 10:00, next run should be 14:00
        assert result.next_run.hour == 14


class TestCronExpression:
    """Test cron expression generation."""

    def test_generates_valid_cron(self) -> None:
        """Calculator can generate a cron expression."""
        config = ScheduleConfig(
            command="test",
            minute_interval=MinuteInterval.EVERY_15,
        )
        calc = ScheduleCalculator(config)

        cron = calc.to_cron_expression()

        # Should be a valid cron expression with 5 fields
        assert len(cron.split()) == 5
        assert cron.startswith("*/15")

    def test_hour_range_cron(self) -> None:
        """Hour range generates correct cron expression."""
        config = ScheduleConfig(
            command="test",
            hours=HourConfig(run_every_hour=False, start_hour=9, end_hour=17),
            minute_interval=MinuteInterval.EVERY_60,
        )
        calc = ScheduleCalculator(config)

        cron = calc.to_cron_expression()

        # Should have hour range
        assert "9-17" in cron
