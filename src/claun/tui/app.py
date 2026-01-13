"""Main Textual TUI application for claun."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Button,
    Digits,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Static,
    Switch,
)

from claun.core.config import ScheduleConfig, MinuteInterval, ALL_DAYS
from claun.core.executor import Executor
from claun.core.scheduler import Scheduler
from claun.logging.manager import LogManager


class DayButton(Button):
    """A toggle button for a day of the week."""

    def __init__(self, day_name: str, day_num: int, **kwargs) -> None:
        super().__init__(day_name, id=f"day-{day_num}", **kwargs)
        self.day_num = day_num
        self.selected = True
        self.add_class("selected")

    def toggle(self) -> bool:
        """Toggle selection state."""
        self.selected = not self.selected
        if self.selected:
            self.add_class("selected")
        else:
            self.remove_class("selected")
        return self.selected


class MinuteButton(Button):
    """A button for minute interval selection."""

    def __init__(self, interval: int, **kwargs) -> None:
        label = f"{interval}m" if interval < 60 else "1h"
        super().__init__(label, id=f"min-{interval}", **kwargs)
        self.interval = interval
        self.selected = interval == 15  # Default

        if self.selected:
            self.add_class("selected")


class ClaunApp(App):
    """Main claun TUI application."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-container {
        height: 100%;
        padding: 1;
    }

    #command-section {
        height: auto;
        margin-bottom: 1;
    }

    #command-input {
        width: 100%;
    }

    #session-section {
        height: auto;
        margin-bottom: 1;
    }

    #session-input {
        width: 100%;
    }

    #timer-section {
        height: auto;
        margin-bottom: 1;
        padding: 1;
        border: solid $primary;
    }

    #day-selector {
        height: 3;
        margin-bottom: 1;
    }

    .day-button {
        width: 5;
        min-width: 5;
        margin-right: 1;
    }

    .day-button.selected {
        background: $success;
    }

    #hour-section {
        height: auto;
        margin-bottom: 1;
    }

    #minute-section {
        height: auto;
    }

    .minute-button {
        width: 6;
        min-width: 6;
        margin-right: 1;
    }

    .minute-button.selected {
        background: $success;
    }

    #countdown-section {
        height: 12;
        align: center middle;
        margin: 1;
        padding: 1;
        border: heavy $primary;
        background: $surface;
    }

    #countdown-digits {
        width: auto;
        text-style: bold;
    }

    #pause-button {
        margin-top: 1;
        width: 20;
    }

    #pause-button.paused {
        background: $warning;
    }

    #output-section {
        height: 1fr;
        border: solid $primary;
    }

    #log-path-label {
        height: 1;
        padding: 0 1;
        background: $surface;
    }

    #output-log {
        height: 1fr;
    }

    .section-label {
        height: 1;
        margin-bottom: 0;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("p", "toggle_pause", "Pause/Resume"),
        Binding("r", "run_now", "Run Now"),
        Binding("c", "clear_log", "Clear Log"),
    ]

    def __init__(
        self,
        config: Optional[ScheduleConfig] = None,
        start_paused: bool = False,
    ) -> None:
        super().__init__()
        self.config = config or ScheduleConfig(command="")
        self.scheduler = Scheduler(self.config)
        self.executor = Executor(
            session_name=self.config.session_name,
            passthrough=False,
        )
        self.log_manager = LogManager(
            Path(self.config.log_path),
            log_id=self.config.log_id,
        )
        self._running = False
        self._first_run = True
        self._countdown_task: Optional[asyncio.Task] = None
        self._schedule_changed = False  # Signal to recalculate next run

        if start_paused:
            self.scheduler.pause()

    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header(show_clock=True)

        with Container(id="main-container"):
            # Command input
            with Vertical(id="command-section"):
                yield Label("Command:", classes="section-label")
                yield Input(
                    placeholder="Enter your Claude Code command...",
                    value=self.config.command,
                    id="command-input",
                )

            # Session input
            with Vertical(id="session-section"):
                yield Label("Session Name (optional):", classes="section-label")
                yield Input(
                    placeholder="Leave empty for no session persistence",
                    value=self.config.session_name or "",
                    id="session-input",
                )

            # Timer controls
            with Vertical(id="timer-section"):
                yield Label("Schedule:", classes="section-label")

                # Day selector
                with Horizontal(id="day-selector"):
                    for i, name in enumerate(["M", "T", "W", "T", "F", "S", "S"]):
                        btn = DayButton(name, i, classes="day-button")
                        if i not in self.config.days_of_week:
                            btn.selected = False
                            btn.remove_class("selected")
                        yield btn

                # Minute interval selector
                with Horizontal(id="minute-section"):
                    yield Label("Interval: ", classes="section-label")
                    for interval in [1, 5, 15, 60]:
                        btn = MinuteButton(interval, classes="minute-button")
                        if interval == self.config.minute_interval.value:
                            btn.selected = True
                            btn.add_class("selected")
                        else:
                            btn.selected = False
                            btn.remove_class("selected")
                        yield btn

            # Countdown display
            with Container(id="countdown-section"):
                yield Digits("00:00:00", id="countdown-digits")
                yield Button(
                    "Start" if self.scheduler.is_paused else "Pause",
                    id="pause-button",
                    variant="primary",
                )

            # Output section
            with Vertical(id="output-section"):
                yield Label(f"Logs: {self.config.log_path}", id="log-path-label")
                yield RichLog(id="output-log", highlight=True, markup=True)

        yield Footer()

    def on_mount(self) -> None:
        """Called when app is mounted."""
        self._start_countdown()
        self._running = True
        self.run_worker(self._scheduler_loop())

    def _start_countdown(self) -> None:
        """Start the countdown timer."""
        self.scheduler.get_next_run()
        self._update_countdown()
        self.set_interval(1.0, self._update_countdown)

    def _update_countdown(self) -> None:
        """Update the countdown display."""
        countdown = self.scheduler.get_countdown_formatted()
        digits = self.query_one("#countdown-digits", Digits)
        digits.update(countdown)

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        self._log_message("[dim]Scheduler started[/dim]")

        try:
            while self._running:
                self._schedule_changed = False
                next_run = self.scheduler.get_next_run()
                self._log_message(f"[dim]Next run scheduled: {next_run.strftime('%H:%M:%S')}[/dim]")

                # Wait until next run (or schedule changes)
                while self._running and not self._schedule_changed:
                    now = datetime.now()
                    if now >= next_run:
                        break
                    await asyncio.sleep(0.5)

                # If schedule changed, recalculate without firing
                if self._schedule_changed:
                    self._log_message("[dim]Schedule changed, recalculating...[/dim]")
                    continue

                if not self._running:
                    break

                self._log_message("[cyan]Timer fired![/cyan]")

                # Check if paused
                if self.scheduler.is_paused:
                    self._log_message("[yellow]Skipped - Scheduler is paused[/yellow]")
                    self.log_manager.create_paused_entry(next_run)
                    continue

                # Get current command from input
                command_input = self.query_one("#command-input", Input)
                command = command_input.value.strip()

                if not command:
                    self._log_message("[red]No command configured - enter a command above[/red]")
                    continue

                # Execute
                await self._execute_job(command)
        except Exception as e:
            self._log_message(f"[red bold]Scheduler loop error: {e}[/red bold]")
            import traceback
            self._log_message(f"[red]{traceback.format_exc()}[/red]")

    async def _execute_job(self, command: str) -> None:
        """Execute a scheduled job."""
        self._log_message(f"[cyan]Starting job: {command}[/cyan]")

        try:
            log_file = self.log_manager.create_log()
            self._log_message(f"[dim]Log file: {log_file}[/dim]")

            session_input = self.query_one("#session-input", Input)
            session_name = session_input.value.strip() or None
            self._log_message(f"[dim]Session: {session_name or '(none)'}[/dim]")

            executor = Executor(session_name=session_name, passthrough=False)
            self._log_message(f"[dim]Running claude with first_run={self._first_run}[/dim]")

            result = await executor.run(
                command,
                first_run=self._first_run,
                resume=not self._first_run and session_name is not None,
                log_file=log_file,
            )
            self._first_run = False

            # Log output
            for line in result.output.split("\n"):
                if line.strip():
                    self._log_message(line)

            status = "[green]SUCCESS[/green]" if result.exit_code == 0 else f"[red]FAILED (exit {result.exit_code})[/red]"
            self._log_message(f"{status} ({result.duration_seconds:.1f}s) - Log: {log_file.name}")

        except Exception as e:
            import traceback
            self._log_message(f"[red bold]Execution error: {e}[/red bold]")
            self._log_message(f"[red]{traceback.format_exc()}[/red]")

    def _log_message(self, message: str) -> None:
        """Add a message to the log."""
        log = self.query_one("#output-log", RichLog)
        timestamp = datetime.now().strftime("%H:%M:%S")
        log.write(f"[dim]{timestamp}[/dim] {message}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button = event.button

        if isinstance(button, DayButton):
            button.toggle()
            self._update_schedule()

        elif isinstance(button, MinuteButton):
            # Deselect all other minute buttons
            for btn in self.query(".minute-button"):
                if isinstance(btn, MinuteButton):
                    btn.selected = False
                    btn.remove_class("selected")
            button.selected = True
            button.add_class("selected")
            self._update_schedule()

        elif button.id == "pause-button":
            self.action_toggle_pause()

    def _update_schedule(self) -> None:
        """Update schedule from UI state."""
        # Get selected days
        days = set()
        for btn in self.query(".day-button"):
            if isinstance(btn, DayButton) and btn.selected:
                days.add(btn.day_num)

        # Get selected minute interval
        interval = MinuteInterval.EVERY_15
        for btn in self.query(".minute-button"):
            if isinstance(btn, MinuteButton) and btn.selected:
                interval = MinuteInterval(btn.interval)
                break

        # Update config and scheduler
        self.config.days_of_week = days
        self.config.minute_interval = interval
        self.scheduler = Scheduler(self.config)
        self.scheduler.get_next_run()

        # Signal the scheduler loop to recalculate
        self._schedule_changed = True

    def action_toggle_pause(self) -> None:
        """Toggle pause state."""
        pause_btn = self.query_one("#pause-button", Button)

        if self.scheduler.is_paused:
            self.scheduler.resume()
            pause_btn.label = "Pause"
            pause_btn.remove_class("paused")
            self._log_message("[green]Resumed[/green]")
        else:
            self.scheduler.pause()
            pause_btn.label = "Resume"
            pause_btn.add_class("paused")
            self._log_message("[yellow]Paused[/yellow]")

    def action_run_now(self) -> None:
        """Run the job immediately."""
        command_input = self.query_one("#command-input", Input)
        command = command_input.value.strip()

        if command:
            self.run_worker(self._execute_job(command))
        else:
            self._log_message("[red]No command to run[/red]")

    def action_clear_log(self) -> None:
        """Clear the output log."""
        log = self.query_one("#output-log", RichLog)
        log.clear()

    def action_quit(self) -> None:
        """Quit the application."""
        self._running = False
        self.exit()
