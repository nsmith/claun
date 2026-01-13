"""CLI interface for claun using Typer."""

from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer

from claun import __version__
from claun.core.config import (
    ScheduleConfig,
    HourConfig,
    MinuteInterval,
    WEEKDAYS,
    WEEKENDS,
    ALL_DAYS,
)

# Main app - no subcommands for core functionality
app = typer.Typer(
    name="claun",
    help="Schedule Claude Code jobs with a beautiful TUI or headless mode.",
    add_completion=False,
)


class MinuteOption(str, Enum):
    """Minute interval options."""

    one = "1"
    five = "5"
    fifteen = "15"
    sixty = "60"


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        typer.echo(f"claun version {__version__}")
        raise typer.Exit()


def parse_days(days_str: Optional[list[str]], weekdays: bool, weekends: bool) -> set[int]:
    """Parse day options into a set of day numbers."""
    if weekdays:
        return set(WEEKDAYS)
    if weekends:
        return set(WEEKENDS)
    if days_str:
        day_map = {
            "mon": 0, "monday": 0,
            "tue": 1, "tuesday": 1,
            "wed": 2, "wednesday": 2,
            "thu": 3, "thursday": 3,
            "fri": 4, "friday": 4,
            "sat": 5, "saturday": 5,
            "sun": 6, "sunday": 6,
        }
        days = set()
        for day in days_str:
            for d in day.lower().split(","):
                d = d.strip()
                if d in day_map:
                    days.add(day_map[d])
        return days if days else set(ALL_DAYS)
    return set(ALL_DAYS)


def parse_hours(hours_str: Optional[str]) -> HourConfig:
    """Parse hour range string into HourConfig."""
    if not hours_str:
        return HourConfig(run_every_hour=True)

    # Handle formats like "9-17", "9am-5pm", "09:00-17:00"
    hours_str = hours_str.lower().replace(" ", "")

    # Try to split on hyphen
    if "-" in hours_str:
        parts = hours_str.split("-")
        if len(parts) == 2:
            start = parse_single_hour(parts[0])
            end = parse_single_hour(parts[1])
            if start is not None and end is not None:
                return HourConfig(run_every_hour=False, start_hour=start, end_hour=end)

    return HourConfig(run_every_hour=True)


def parse_single_hour(hour_str: str) -> Optional[int]:
    """Parse a single hour string like '9', '9am', '17', '5pm'."""
    hour_str = hour_str.strip()

    # Handle am/pm
    is_pm = "pm" in hour_str
    is_am = "am" in hour_str
    hour_str = hour_str.replace("am", "").replace("pm", "").replace(":", "")

    try:
        hour = int(hour_str)
        if is_pm and hour < 12:
            hour += 12
        elif is_am and hour == 12:
            hour = 0
        return hour if 0 <= hour <= 23 else None
    except ValueError:
        return None


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    # Core options
    command: Annotated[
        Optional[str],
        typer.Option("--command", "-c", help="Claude Code command to run"),
    ] = None,
    session: Annotated[
        Optional[str],
        typer.Option("--session", "-s", help="Session name for persistence"),
    ] = None,
    # Mode selection
    headless: Annotated[
        bool,
        typer.Option("--headless", "-H", help="Run in headless mode (no TUI)"),
    ] = False,
    # Day options
    days: Annotated[
        Optional[list[str]],
        typer.Option("--days", "-d", help="Days to run (mon,tue,wed,thu,fri,sat,sun)"),
    ] = None,
    weekdays_only: Annotated[
        bool,
        typer.Option("--weekdays", help="Run only on weekdays (mon-fri)"),
    ] = False,
    weekends_only: Annotated[
        bool,
        typer.Option("--weekends", help="Run only on weekends (sat-sun)"),
    ] = False,
    # Hour options
    hours: Annotated[
        Optional[str],
        typer.Option("--hours", help="Hour range (e.g., '9-17' or '9am-5pm')"),
    ] = None,
    # Minute options
    minutes: Annotated[
        MinuteOption,
        typer.Option("--minutes", "-m", help="Minute interval (1, 5, 15, or 60)"),
    ] = MinuteOption.fifteen,
    # Logging options
    log_path: Annotated[
        Optional[Path],
        typer.Option("--log-path", "-l", help="Directory for log files"),
    ] = None,
    log_id: Annotated[
        Optional[str],
        typer.Option("--log-id", help="Optional ID prefix for log filenames"),
    ] = None,
    # Control options
    paused: Annotated[
        bool,
        typer.Option("--paused", "-P", help="Start in paused state"),
    ] = False,
    run_once: Annotated[
        bool,
        typer.Option("--once", help="Run once immediately and exit"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show schedule without executing"),
    ] = False,
    # Version
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-v", callback=version_callback, is_eager=True, help="Show version"),
    ] = None,
) -> None:
    """
    Schedule Claude Code jobs with a friendly TUI or headless mode.

    Examples:

        claun                              # Launch TUI with defaults

        claun -c "Review PR #123"          # TUI with pre-filled command

        claun -H -c "Run tests" -m 15      # Headless, every 15 minutes

        claun --weekdays --hours 9am-5pm   # Work hours only
    """
    # If a subcommand is invoked, don't run main logic
    if ctx.invoked_subcommand is not None:
        return

    # Validate headless mode requires a command
    if headless and not command and not dry_run:
        typer.echo("Error: --headless mode requires --command", err=True)
        raise typer.Exit(1)

    # Build configuration
    config = ScheduleConfig(
        command=command or "",
        session_name=session,
        days_of_week=parse_days(days, weekdays_only, weekends_only),
        hours=parse_hours(hours),
        minute_interval=MinuteInterval(int(minutes.value)),
        log_path=str(log_path) if log_path else ".",
        log_id=log_id,
    )

    # Handle dry run
    if dry_run:
        show_dry_run(config)
        raise typer.Exit(0)

    # Handle run once
    if run_once:
        if not command:
            typer.echo("Error: --once requires --command", err=True)
            raise typer.Exit(1)
        run_once_mode(config)
        raise typer.Exit(0)

    # Run in appropriate mode
    if headless:
        run_headless_mode(config, paused)
    else:
        run_tui_mode(config, paused)


def show_dry_run(config: ScheduleConfig) -> None:
    """Display schedule configuration without running."""
    from claun.scheduling.calculator import ScheduleCalculator

    typer.echo("\n[Dry Run] Schedule Configuration:")
    typer.echo(f"  Command: {config.command or '(not set)'}")
    typer.echo(f"  Session: {config.session_name or '(none)'}")

    # Days
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    active_days = [day_names[d] for d in sorted(config.days_of_week)]
    typer.echo(f"  Days: {', '.join(active_days)}")

    # Hours
    if config.hours.run_every_hour:
        typer.echo("  Hours: Every hour")
    else:
        typer.echo(f"  Hours: {config.hours.start_hour}:00 - {config.hours.end_hour}:00")

    # Minutes
    typer.echo(f"  Interval: Every {config.minute_interval.value} minutes")

    # Log path
    typer.echo(f"  Log path: {config.log_path}")

    # Show cron expression
    if config.command:
        calc = ScheduleCalculator(config)
        typer.echo(f"\n  Cron expression: {calc.to_cron_expression()}")

        result = calc.get_next_run()
        typer.echo(f"  Next run: {result.next_run.strftime('%Y-%m-%d %H:%M:%S')}")


def run_once_mode(config: ScheduleConfig) -> None:
    """Run the command once and exit."""
    import asyncio
    from claun.core.executor import Executor
    from claun.logging.manager import LogManager

    typer.echo(f"Running once: {config.command}")

    log_manager = LogManager(Path(config.log_path), log_id=config.log_id)
    log_file = log_manager.create_log()

    executor = Executor(session_name=config.session_name, passthrough=True)

    def on_output(line: str) -> None:
        typer.echo(line)

    async def run() -> int:
        result = await executor.run(
            config.command,
            first_run=True,
            log_file=log_file,
            on_output=on_output,
        )
        return result.exit_code

    exit_code = asyncio.run(run())
    typer.echo(f"\nLog written to: {log_file}")
    raise typer.Exit(exit_code)


def run_headless_mode(config: ScheduleConfig, paused: bool) -> None:
    """Run in headless mode."""
    import asyncio
    from claun.headless.runner import HeadlessRunner

    runner = HeadlessRunner(config, start_paused=paused)

    try:
        asyncio.run(runner.run())
    except KeyboardInterrupt:
        typer.echo("\nStopped by user")
        raise typer.Exit(0)


def run_tui_mode(config: ScheduleConfig, paused: bool) -> None:
    """Run in TUI mode."""
    from claun.tui.app import ClaunApp

    tui_app = ClaunApp(config=config, start_paused=paused)
    tui_app.run()


@app.command()
def logs(
    path: Annotated[
        Optional[Path],
        typer.Option("--path", "-p", help="Log directory to browse"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum logs to show"),
    ] = 20,
    log_id: Annotated[
        Optional[str],
        typer.Option("--id", help="Filter by log ID"),
    ] = None,
) -> None:
    """Browse and manage log files."""
    from claun.logging.manager import LogManager

    log_path = path or Path(".")
    manager = LogManager(log_path, log_id=log_id)

    entries = manager.list_logs(limit=limit)

    if not entries:
        typer.echo("No logs found.")
        raise typer.Exit(0)

    typer.echo(f"\nFound {len(entries)} log(s) in {log_path}:\n")

    for entry in entries:
        status = "[PAUSED]" if entry.is_paused else ""
        timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S") if entry.timestamp else "unknown"
        id_str = f"[{entry.log_id}] " if entry.log_id else ""
        typer.echo(f"  {timestamp}  {id_str}{status}  {entry.path.name}")


if __name__ == "__main__":
    app()
