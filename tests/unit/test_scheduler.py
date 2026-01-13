"""Tests for the scheduler module."""

import pytest
from datetime import datetime, timedelta

from claun.core.config import (
    ScheduleConfig,
    HourConfig,
    MinuteInterval,
    ALL_DAYS,
    WEEKDAYS,
)
from claun.core.scheduler import Scheduler


class TestSchedulerBasics:
    """Test basic scheduler functionality."""

    def test_create_scheduler_with_config(self) -> None:
        """Scheduler can be created with a config."""
        config = ScheduleConfig(command="test")
        scheduler = Scheduler(config)
        assert scheduler.config == config

    def test_scheduler_starts_unpaused(self) -> None:
        """Scheduler starts in unpaused state."""
        config = ScheduleConfig(command="test")
        scheduler = Scheduler(config)
        assert not scheduler.is_paused

    def test_pause_and_resume(self) -> None:
        """Scheduler can be paused and resumed."""
        config = ScheduleConfig(command="test")
        scheduler = Scheduler(config)

        scheduler.pause()
        assert scheduler.is_paused

        scheduler.resume()
        assert not scheduler.is_paused


class TestNextRunCalculation:
    """Test next run time calculation."""

    def test_default_config_runs_every_15_minutes(self, fixed_now: datetime) -> None:
        """Default config runs every 15 minutes."""
        config = ScheduleConfig(command="test")
        scheduler = Scheduler(config)

        next_run = scheduler.get_next_run(from_time=fixed_now)

        # At 10:00, next run should be 10:15
        expected = fixed_now.replace(minute=15)
        assert next_run == expected

    def test_every_5_minutes(self, fixed_now: datetime) -> None:
        """5-minute interval works correctly."""
        config = ScheduleConfig(
            command="test",
            minute_interval=MinuteInterval.EVERY_5,
        )
        scheduler = Scheduler(config)

        next_run = scheduler.get_next_run(from_time=fixed_now)

        # At 10:00, next run should be 10:05
        expected = fixed_now.replace(minute=5)
        assert next_run == expected

    def test_every_hour(self, fixed_now: datetime) -> None:
        """60-minute interval (hourly) works correctly."""
        config = ScheduleConfig(
            command="test",
            minute_interval=MinuteInterval.EVERY_60,
        )
        scheduler = Scheduler(config)

        next_run = scheduler.get_next_run(from_time=fixed_now)

        # At 10:00, next run should be 11:00
        expected = fixed_now.replace(hour=11, minute=0)
        assert next_run == expected

    def test_mid_interval_calculation(self) -> None:
        """Next run calculated correctly from mid-interval."""
        config = ScheduleConfig(
            command="test",
            minute_interval=MinuteInterval.EVERY_15,
        )
        scheduler = Scheduler(config)

        # At 10:07, next run should be 10:15
        now = datetime(2026, 1, 12, 10, 7, 0)
        next_run = scheduler.get_next_run(from_time=now)

        expected = datetime(2026, 1, 12, 10, 15, 0)
        assert next_run == expected


class TestDayOfWeekFiltering:
    """Test day-of-week restrictions."""

    def test_respects_day_of_week_restrictions(self) -> None:
        """Scheduler respects day-of-week settings."""
        config = ScheduleConfig(
            command="test",
            days_of_week=set(WEEKDAYS),  # Monday-Friday only
        )
        scheduler = Scheduler(config)

        # Saturday at noon (2026-01-17 is a Saturday)
        saturday = datetime(2026, 1, 17, 12, 0, 0)
        next_run = scheduler.get_next_run(from_time=saturday)

        # Should skip to Monday (2026-01-19)
        assert next_run.weekday() == 0  # Monday
        assert next_run.date() == datetime(2026, 1, 19).date()

    def test_single_day_restriction(self) -> None:
        """Scheduler works with single day restriction."""
        config = ScheduleConfig(
            command="test",
            days_of_week={0},  # Monday only
            minute_interval=MinuteInterval.EVERY_60,
        )
        scheduler = Scheduler(config)

        # Tuesday (2026-01-13)
        tuesday = datetime(2026, 1, 13, 10, 0, 0)
        next_run = scheduler.get_next_run(from_time=tuesday)

        # Should skip to next Monday (2026-01-19)
        assert next_run.weekday() == 0
        assert next_run.date() == datetime(2026, 1, 19).date()


class TestHourFiltering:
    """Test hour range restrictions."""

    def test_between_hours_restriction(self) -> None:
        """Scheduler respects hour range settings."""
        config = ScheduleConfig(
            command="test",
            hours=HourConfig(run_every_hour=False, start_hour=9, end_hour=17),
            minute_interval=MinuteInterval.EVERY_60,
        )
        scheduler = Scheduler(config)

        # At 6am
        early = datetime(2026, 1, 12, 6, 0, 0)
        next_run = scheduler.get_next_run(from_time=early)

        # Should start at 9am
        assert next_run.hour == 9

    def test_after_hours_skips_to_next_day(self) -> None:
        """After work hours, scheduler skips to next day."""
        config = ScheduleConfig(
            command="test",
            hours=HourConfig(run_every_hour=False, start_hour=9, end_hour=17),
            minute_interval=MinuteInterval.EVERY_60,
        )
        scheduler = Scheduler(config)

        # At 8pm (after 5pm end)
        evening = datetime(2026, 1, 12, 20, 0, 0)
        next_run = scheduler.get_next_run(from_time=evening)

        # Should be 9am next day
        assert next_run.hour == 9
        assert next_run.date() == datetime(2026, 1, 13).date()


class TestPauseBehavior:
    """Test pause state behavior."""

    def test_paused_scheduler_should_not_run(self) -> None:
        """Paused scheduler should not execute."""
        config = ScheduleConfig(command="test")
        scheduler = Scheduler(config)
        scheduler.pause()

        assert not scheduler.should_run_now()

    def test_unpaused_scheduler_can_run(self, fixed_now: datetime) -> None:
        """Unpaused scheduler can execute when due."""
        config = ScheduleConfig(command="test")
        scheduler = Scheduler(config)

        # Set next run to now
        scheduler._next_run = fixed_now
        assert scheduler.should_run_now(current_time=fixed_now)


class TestCountdown:
    """Test countdown calculation."""

    def test_countdown_to_next_run(self, fixed_now: datetime) -> None:
        """Countdown returns seconds until next run."""
        config = ScheduleConfig(
            command="test",
            minute_interval=MinuteInterval.EVERY_15,
        )
        scheduler = Scheduler(config)

        # Force next run to 10:15
        scheduler._next_run = fixed_now.replace(minute=15)

        countdown = scheduler.get_countdown(current_time=fixed_now)

        # Should be 15 minutes = 900 seconds
        assert countdown == 900

    def test_countdown_format(self, fixed_now: datetime) -> None:
        """Countdown can be formatted as HH:MM:SS."""
        config = ScheduleConfig(command="test")
        scheduler = Scheduler(config)

        # Force next run to 1 hour, 23 minutes, 45 seconds from now
        scheduler._next_run = fixed_now + timedelta(hours=1, minutes=23, seconds=45)

        formatted = scheduler.get_countdown_formatted(current_time=fixed_now)

        assert formatted == "01:23:45"
