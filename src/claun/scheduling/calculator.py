"""Schedule calculator using croniter for complex schedules."""

from datetime import datetime
from typing import Optional

from croniter import croniter

from claun.core.config import ScheduleConfig, ALL_DAYS
from claun.scheduling.models import ScheduleResult


class ScheduleCalculator:
    """Calculates next run times from schedule configuration."""

    def __init__(self, config: ScheduleConfig) -> None:
        """Initialize calculator with configuration.

        Args:
            config: Schedule configuration.
        """
        self.config = config
        self._cron_expr: Optional[str] = None

    def get_next_run(self, from_time: Optional[datetime] = None) -> ScheduleResult:
        """Calculate the next run time.

        Args:
            from_time: Calculate from this time. Defaults to now.

        Returns:
            ScheduleResult with next run time and adjustment info.
        """
        if from_time is None:
            from_time = datetime.now()

        cron_expr = self.to_cron_expression()
        cron = croniter(cron_expr, from_time)
        next_run = cron.get_next(datetime)

        # Determine if we had to adjust (skip days, hours, etc.)
        was_adjusted = False
        adjustment_reason = None

        if next_run.date() != from_time.date():
            was_adjusted = True
            adjustment_reason = "Skipped to valid day"
        elif next_run.hour != from_time.hour and not self.config.hours.run_every_hour:
            was_adjusted = True
            adjustment_reason = "Skipped to valid hour"

        return ScheduleResult(
            next_run=next_run,
            was_adjusted=was_adjusted,
            adjustment_reason=adjustment_reason,
        )

    def to_cron_expression(self) -> str:
        """Generate a cron expression from the configuration.

        Returns:
            A 5-field cron expression string.
        """
        if self._cron_expr is not None:
            return self._cron_expr

        # Build cron expression: minute hour day-of-month month day-of-week

        # Minute field
        minute_interval = self._get_minute_interval()
        if minute_interval == 60:
            minute_field = "0"
        elif minute_interval == 1:
            minute_field = "*"
        else:
            minute_field = f"*/{minute_interval}"

        # Hour field
        hour_field = self._build_hour_field()

        # Day-of-month field
        dom_field = self._build_day_of_month_field()

        # Month field
        month_field = "*"

        # Day-of-week field
        dow_field = self._build_day_of_week_field()

        self._cron_expr = f"{minute_field} {hour_field} {dom_field} {month_field} {dow_field}"
        return self._cron_expr

    def _get_minute_interval(self) -> int:
        """Get the effective minute interval."""
        # Advanced config overrides
        if self.config.advanced and self.config.advanced.custom_minute_interval:
            return self.config.advanced.custom_minute_interval
        return self.config.minute_interval.value

    def _build_hour_field(self) -> str:
        """Build the hour field of the cron expression."""
        # Advanced config specific hours override
        if self.config.advanced and self.config.advanced.specific_hours:
            hours = sorted(self.config.advanced.specific_hours)
            return ",".join(str(h) for h in hours)

        if self.config.hours.run_every_hour:
            return "*"

        start = self.config.hours.start_hour
        end = self.config.hours.end_hour
        return f"{start}-{end}"

    def _build_day_of_month_field(self) -> str:
        """Build the day-of-month field of the cron expression."""
        if self.config.advanced and self.config.advanced.days_of_month:
            days = sorted(self.config.advanced.days_of_month)
            return ",".join(str(d) for d in days)
        return "*"

    def _build_day_of_week_field(self) -> str:
        """Build the day-of-week field of the cron expression."""
        if self.config.days_of_week == set(ALL_DAYS):
            return "*"

        # croniter uses 0=Sunday, but Python's weekday() uses 0=Monday
        # Convert: Python Monday(0) -> cron Monday(1), Python Sunday(6) -> cron Sunday(0)
        cron_days = []
        for day in sorted(self.config.days_of_week):
            cron_day = (day + 1) % 7  # Convert Python weekday to cron weekday
            cron_days.append(str(cron_day))

        return ",".join(cron_days)
