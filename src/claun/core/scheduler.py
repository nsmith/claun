"""Schedule calculation engine for claun."""

from datetime import datetime, timedelta
from typing import Optional

from claun.core.config import ScheduleConfig, MinuteInterval


class Scheduler:
    """Manages scheduling logic for Claude Code jobs."""

    def __init__(self, config: ScheduleConfig) -> None:
        """Initialize scheduler with configuration.

        Args:
            config: Schedule configuration defining when to run.
        """
        self.config = config
        self._is_paused = False
        self._next_run: Optional[datetime] = None

    @property
    def is_paused(self) -> bool:
        """Whether the scheduler is currently paused."""
        return self._is_paused

    def pause(self) -> None:
        """Pause the scheduler, preventing job execution."""
        self._is_paused = True

    def resume(self) -> None:
        """Resume the scheduler, allowing job execution."""
        self._is_paused = False

    def get_next_run(self, from_time: Optional[datetime] = None) -> datetime:
        """Calculate the next run time based on configuration.

        Args:
            from_time: Calculate from this time. Defaults to now.

        Returns:
            The next datetime when a job should run.
        """
        if from_time is None:
            from_time = datetime.now()

        next_run = self._calculate_next_run(from_time)
        self._next_run = next_run
        return next_run

    def _calculate_next_run(self, from_time: datetime) -> datetime:
        """Internal calculation of next run time."""
        interval = self.config.minute_interval.value
        current = from_time

        # Start from the next interval boundary
        if interval == 60:
            # For hourly, go to next hour
            candidate = current.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        else:
            # For other intervals, find next interval boundary
            current_minute = current.minute
            next_interval_minute = ((current_minute // interval) + 1) * interval

            if next_interval_minute >= 60:
                # Roll over to next hour
                candidate = current.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            else:
                candidate = current.replace(
                    minute=next_interval_minute, second=0, microsecond=0
                )

        # Now check if candidate satisfies day and hour constraints
        candidate = self._adjust_for_constraints(candidate)
        return candidate

    def _adjust_for_constraints(self, candidate: datetime) -> datetime:
        """Adjust candidate time to satisfy day and hour constraints."""
        max_iterations = 366 * 24  # Prevent infinite loops

        for _ in range(max_iterations):
            # Check day of week
            if candidate.weekday() not in self.config.days_of_week:
                # Skip to next day at start of valid hours
                candidate = self._next_valid_day(candidate)
                continue

            # Check hour constraints
            if not self.config.hours.run_every_hour:
                start = self.config.hours.start_hour
                end = self.config.hours.end_hour

                if candidate.hour < start:
                    # Before start hour, move to start hour
                    candidate = candidate.replace(
                        hour=start, minute=0, second=0, microsecond=0
                    )
                    continue
                elif candidate.hour > end:
                    # After end hour, move to next day
                    candidate = self._next_valid_day(candidate)
                    continue

            # Candidate satisfies all constraints
            return candidate

        # Should never reach here with valid config
        return candidate

    def _next_valid_day(self, current: datetime) -> datetime:
        """Find the next valid day that satisfies constraints."""
        # Move to next day at start hour (or midnight if run_every_hour)
        next_day = current.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)

        if not self.config.hours.run_every_hour:
            next_day = next_day.replace(hour=self.config.hours.start_hour)

        return next_day

    def should_run_now(self, current_time: Optional[datetime] = None) -> bool:
        """Check if a job should run at the current time.

        Args:
            current_time: The current time to check. Defaults to now.

        Returns:
            True if a job should run now, False otherwise.
        """
        if self._is_paused:
            return False

        if self._next_run is None:
            return False

        if current_time is None:
            current_time = datetime.now()

        return current_time >= self._next_run

    def get_countdown(self, current_time: Optional[datetime] = None) -> int:
        """Get seconds until next run.

        Args:
            current_time: The current time. Defaults to now.

        Returns:
            Seconds until next run, or 0 if already due.
        """
        if self._next_run is None:
            return 0

        if current_time is None:
            current_time = datetime.now()

        delta = self._next_run - current_time
        seconds = int(delta.total_seconds())
        return max(0, seconds)

    def get_countdown_formatted(self, current_time: Optional[datetime] = None) -> str:
        """Get countdown formatted as HH:MM:SS.

        Args:
            current_time: The current time. Defaults to now.

        Returns:
            Countdown string in HH:MM:SS format.
        """
        total_seconds = self.get_countdown(current_time)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
