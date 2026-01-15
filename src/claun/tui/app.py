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
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Select,
    Static,
    Switch,
)

from claun.core.config import ScheduleConfig, MinuteInterval, HourConfig, ALL_DAYS
from claun.core.executor import Executor
from claun.core.scheduler import Scheduler
from claun.logging.manager import LogManager
from claun.tui.screens.save_config import SaveConfigModal


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


class HourButton(Button):
    """A button for hour selection."""

    def __init__(self, hour: int, is_start: bool = True, **kwargs) -> None:
        label = f"{hour:02d}:00"
        prefix = "start" if is_start else "end"
        super().__init__(label, id=f"{prefix}-hour-{hour}", **kwargs)
        self.hour = hour
        self.is_start = is_start
        self.selected = False

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        if selected:
            self.add_class("selected")
        else:
            self.remove_class("selected")


class RetroCountdown(Static):
    """A retro ASCII art countdown display with Mets colors."""

    # Extra chunky ASCII art digits (5 lines tall, wider)
    DIGITS = {
        "0": ["██████", "██  ██", "██  ██", "██  ██", "██████"],
        "1": ["  ██  ", " ███  ", "  ██  ", "  ██  ", "██████"],
        "2": ["██████", "    ██", "██████", "██    ", "██████"],
        "3": ["██████", "    ██", "██████", "    ██", "██████"],
        "4": ["██  ██", "██  ██", "██████", "    ██", "    ██"],
        "5": ["██████", "██    ", "██████", "    ██", "██████"],
        "6": ["██████", "██    ", "██████", "██  ██", "██████"],
        "7": ["██████", "    ██", "   ██ ", "  ██  ", "  ██  "],
        "8": ["██████", "██  ██", "██████", "██  ██", "██████"],
        "9": ["██████", "██  ██", "██████", "    ██", "██████"],
        ":": ["  ", "██", "  ", "██", "  "],
    }

    METS_ORANGE = "#FF5910"

    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)
        self._time = "00:00:00"
        self._compact = False

    def set_compact(self, compact: bool) -> None:
        """Switch between ASCII art and compact text mode."""
        if self._compact != compact:
            self._compact = compact
            self._render_time()

    def set_time(self, time_str: str) -> None:
        """Update the displayed time."""
        self._time = time_str
        self._render_time()

    def _render_time(self) -> None:
        """Render the time as Mets orange ASCII art or compact text."""
        if self._compact:
            # Compact mode: simple large text
            self.update(f"[bold {self.METS_ORANGE}]{self._time}[/]")
            return

        # Full ASCII art mode
        lines = ["", "", "", "", ""]

        for char in self._time:
            digit_art = self.DIGITS.get(char, ["  ", "  ", "  ", "  ", "  "])

            for line_idx in range(5):
                lines[line_idx] += f"[bold {self.METS_ORANGE}]{digit_art[line_idx]}[/] "

        self.update("\n".join(lines))


class ClaunApp(App):
    """Main claun TUI application."""

    TITLE = "CLAUN"

    # Mets colors
    METS_BLUE = "#002D72"
    METS_ORANGE = "#FF5910"
    METS_LIGHT_BLUE = "#003087"
    METS_DARK_ORANGE = "#D94E1F"

    CSS = """
    Screen {
        layout: vertical;
        background: #0a0a12;
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
        border: solid #002D72;
    }

    #command-input:focus {
        border: solid #FF5910;
    }

    #flags-section {
        height: auto;
        margin-bottom: 1;
    }

    #flags-input {
        width: 100%;
        border: solid #002D72;
    }

    #flags-input:focus {
        border: solid #FF5910;
    }

    #schedule-row {
        height: auto;
        margin-bottom: 1;
        layout: horizontal;
    }

    #timer-section {
        width: 3fr;
        min-width: 45;
        height: auto;
        padding: 1;
        border: solid #002D72;
        background: #0d0d18;
    }

    #day-selector {
        height: 3;
        margin-bottom: 1;
    }

    .day-button {
        width: 5;
        min-width: 5;
        margin-right: 1;
        background: #002D72;
        color: white;
    }

    .day-button:hover {
        background: #003087;
    }

    .day-button.selected {
        background: #FF5910;
        color: white;
    }

    #hour-section {
        height: auto;
        margin-bottom: 1;
    }

    .hour-select {
        width: 18;
        border: solid #002D72;
    }

    #all-hours-label {
        margin-right: 1;
        color: #FF5910;
    }

    #all-hours-label.dimmed {
        color: #666666;
    }

    #minute-section {
        height: auto;
    }

    .minute-button {
        width: 6;
        min-width: 6;
        margin-right: 1;
        background: #002D72;
        color: white;
    }

    .minute-button:hover {
        background: #003087;
    }

    .minute-button.selected {
        background: #FF5910;
        color: white;
    }

    #countdown-section {
        width: 2fr;
        min-width: 28;
        height: auto;
        align: center middle;
        margin-left: 1;
        padding: 1 2;
        border: heavy #FF5910;
        background: #0d0d18;
    }

    #countdown-section.compact {
        width: auto;
        min-width: 12;
    }

    #countdown-display {
        width: 100%;
        height: auto;
        content-align: center middle;
        text-align: center;
    }

    #pause-button {
        margin-top: 1;
        width: 20;
        background: #002D72;
        color: white;
    }

    #pause-button:hover {
        background: #003087;
    }

    #pause-button.paused {
        background: #FF5910;
        color: white;
    }

    #output-section {
        height: 1fr;
        border: solid #002D72;
        background: #0d0d18;
    }

    #log-path-label {
        height: 1;
        padding: 0 1;
        background: #002D72;
        color: #FF5910;
    }

    #output-log {
        height: 1fr;
        color: #BF40FF;
    }

    .section-label {
        height: 1;
        margin-bottom: 0;
        color: #FF5910;
    }

    Header {
        background: #002D72;
        color: #FF5910;
    }

    Footer {
        background: #002D72;
        color: white;
    }

    Footer > .footer--key {
        background: #FF5910;
        color: white;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("p", "toggle_pause", "Pause/Resume"),
        Binding("r", "run_now", "Run Now"),
        Binding("c", "clear_log", "Clear Log"),
        Binding("s", "save_config", "Save Config"),
    ]

    def __init__(
        self,
        config: Optional[ScheduleConfig] = None,
        start_paused: bool = False,
    ) -> None:
        super().__init__()
        self.config = config or ScheduleConfig(command="")
        self.scheduler = Scheduler(self.config)
        self.log_manager = LogManager(
            Path(self.config.log_path),
            log_id=self.config.log_id,
        )
        self._running = False
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

            # Claude flags input
            with Vertical(id="flags-section"):
                yield Label("Claude Flags (optional):", classes="section-label")
                yield Input(
                    placeholder="e.g., --resume abc123 or --model sonnet",
                    value=self.config.claude_flags,
                    id="flags-input",
                )

            # Schedule controls and countdown side by side (stacks on narrow screens)
            with Horizontal(id="schedule-row"):
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

                    # Hour range selector
                    # Switch LEFT (off) = All Day, Switch RIGHT (on) = Hour Range
                    with Horizontal(id="hour-section"):
                        yield Label("Hours: ", classes="section-label")
                        all_day_label = Label("All day ", id="all-hours-label")
                        use_hour_range = not self.config.hours.run_every_hour
                        if use_hour_range:
                            all_day_label.add_class("dimmed")
                        yield all_day_label
                        yield Switch(
                            value=use_hour_range,
                            id="hour-range-switch",
                        )

                        # Hour range selectors (enabled when switch is RIGHT/on)
                        hour_options = [(f"{h:02d}:00", h) for h in range(24)]
                        yield Select(
                            hour_options,
                            value=self.config.hours.start_hour,
                            id="start-hour-select",
                            classes="hour-select",
                            disabled=not use_hour_range,
                        )
                        yield Label(" to ", id="hour-to-label")
                        yield Select(
                            hour_options,
                            value=self.config.hours.end_hour,
                            id="end-hour-select",
                            classes="hour-select",
                            disabled=not use_hour_range,
                        )

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
                    yield RetroCountdown(id="countdown-display")
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
        self._update_layout_for_width()
        self.run_worker(self._scheduler_loop())

    def on_resize(self) -> None:
        """Handle terminal resize."""
        self._update_layout_for_width()

    def _update_layout_for_width(self) -> None:
        """Update layout based on terminal width."""
        countdown = self.query_one("#countdown-display", RetroCountdown)
        countdown_section = self.query_one("#countdown-section")
        # Switch to compact text mode when narrow instead of stacking
        if self.size.width < 100:
            countdown.set_compact(True)
            countdown_section.add_class("compact")
        else:
            countdown.set_compact(False)
            countdown_section.remove_class("compact")

    def _start_countdown(self) -> None:
        """Start the countdown timer."""
        self.scheduler.get_next_run()
        self._update_countdown()
        self.set_interval(1.0, self._update_countdown)

    def _update_countdown(self) -> None:
        """Update the countdown display."""
        countdown = self.scheduler.get_countdown_formatted()
        display = self.query_one("#countdown-display", RetroCountdown)
        display.set_time(countdown)

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

            flags_input = self.query_one("#flags-input", Input)
            claude_flags = flags_input.value.strip()
            if claude_flags:
                self._log_message(f"[dim]Flags: {claude_flags}[/dim]")

            executor = Executor(claude_flags=claude_flags, passthrough=False)

            result = await executor.run(
                command,
                log_file=log_file,
            )

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

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle switch changes."""
        if event.switch.id == "hour-range-switch":
            # Switch RIGHT (on/true) = use hour range
            # Switch LEFT (off/false) = all day
            use_hour_range = event.value

            start_select = self.query_one("#start-hour-select", Select)
            end_select = self.query_one("#end-hour-select", Select)
            all_day_label = self.query_one("#all-hours-label", Label)

            # Enable hour selects when using hour range
            start_select.disabled = not use_hour_range
            end_select.disabled = not use_hour_range

            # Dim the "All day" label when using hour range
            if use_hour_range:
                all_day_label.add_class("dimmed")
            else:
                all_day_label.remove_class("dimmed")

            self._update_schedule()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changes."""
        if event.select.id in ("start-hour-select", "end-hour-select"):
            self._update_schedule()

    def _update_schedule(self) -> None:
        """Update schedule from UI state."""
        # Get selected days
        days = set()
        for btn in self.query(".day-button"):
            if isinstance(btn, DayButton) and btn.selected:
                days.add(btn.day_num)

        # Get hour configuration
        # Switch RIGHT (on) = use hour range, Switch LEFT (off) = all day
        hour_range_switch = self.query_one("#hour-range-switch", Switch)
        start_select = self.query_one("#start-hour-select", Select)
        end_select = self.query_one("#end-hour-select", Select)

        # Handle Select.BLANK value
        start_hour = start_select.value if start_select.value != Select.BLANK else 0
        end_hour = end_select.value if end_select.value != Select.BLANK else 23

        hours = HourConfig(
            run_every_hour=not hour_range_switch.value,  # Inverted: switch ON = use range
            start_hour=start_hour,
            end_hour=end_hour,
        )

        # Get selected minute interval
        interval = MinuteInterval.EVERY_15
        for btn in self.query(".minute-button"):
            if isinstance(btn, MinuteButton) and btn.selected:
                interval = MinuteInterval(btn.interval)
                break

        # Update config and scheduler
        self.config.days_of_week = days
        self.config.hours = hours
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

    def action_save_config(self) -> None:
        """Open the save config modal."""
        # Sync current UI state to config
        self._update_schedule()
        command_input = self.query_one("#command-input", Input)
        flags_input = self.query_one("#flags-input", Input)
        self.config.command = command_input.value
        self.config.claude_flags = flags_input.value

        def on_save_result(path: str | None) -> None:
            if path:
                self._log_message(f"[green]Config saved to {path}[/green]")

        self.push_screen(SaveConfigModal(self.config), callback=on_save_result)

    def action_quit(self) -> None:
        """Quit the application."""
        self._running = False
        self.exit()
