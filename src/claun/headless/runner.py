"""Headless mode runner for claun."""

import asyncio
from datetime import datetime
from pathlib import Path

from claun.core.config import ScheduleConfig
from claun.core.executor import Executor
from claun.core.scheduler import Scheduler
from claun.logging.manager import LogManager


class HeadlessRunner:
    """Runs scheduled jobs in headless mode with direct terminal output."""

    def __init__(
        self,
        config: ScheduleConfig,
        start_paused: bool = False,
    ) -> None:
        """Initialize headless runner.

        Args:
            config: Schedule configuration.
            start_paused: Whether to start in paused state.
        """
        self.config = config
        self.scheduler = Scheduler(config)
        self.log_manager = LogManager(
            Path(config.log_path),
            log_id=config.log_id,
        )
        self._running = False

        if start_paused:
            self.scheduler.pause()

    async def run(self) -> None:
        """Run the scheduler loop."""
        self._running = True
        self._print_startup()

        while self._running:
            # Calculate next run
            next_run = self.scheduler.get_next_run()
            self._print_next_run(next_run)

            # Wait until next run
            await self._wait_until(next_run)

            if not self._running:
                break

            # Check if paused
            if self.scheduler.is_paused:
                self._print_paused(next_run)
                self.log_manager.create_paused_entry(next_run)
                continue

            # Execute the job
            await self._execute_job()

    def stop(self) -> None:
        """Stop the runner."""
        self._running = False

    async def _wait_until(self, target_time: datetime) -> None:
        """Wait until the target time."""
        while self._running:
            now = datetime.now()
            if now >= target_time:
                break

            # Calculate wait time (max 1 second to allow for interrupts)
            delta = (target_time - now).total_seconds()
            wait_time = min(delta, 1.0)

            if wait_time > 0:
                await asyncio.sleep(wait_time)

    async def _execute_job(self) -> None:
        """Execute a scheduled job."""
        self._print_job_start()

        log_file = self.log_manager.create_log()
        executor = Executor(claude_flags=self.config.claude_flags, passthrough=True)

        def on_output(line: str) -> None:
            print(line)

        try:
            result = await executor.run(
                self.config.command,
                log_file=log_file,
                on_output=on_output,
            )
            self._print_job_end(result.exit_code, result.duration_seconds, log_file)

        except Exception as e:
            self._print_error(str(e))

    def _print_startup(self) -> None:
        """Print startup message."""
        print("=" * 60)
        print("Claun - Claude Code Job Scheduler (Headless Mode)")
        print("=" * 60)
        print(f"Command: {self.config.command}")
        if self.config.claude_flags:
            print(f"Claude flags: {self.config.claude_flags}")
        print(f"Interval: Every {self.config.minute_interval.value} minutes")
        print(f"Log path: {self.config.log_path}")
        if self.scheduler.is_paused:
            print("Status: PAUSED")
        print("-" * 60)

    def _print_next_run(self, next_run: datetime) -> None:
        """Print next run time."""
        countdown = self.scheduler.get_countdown_formatted()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S')} (in {countdown})")

    def _print_paused(self, scheduled_time: datetime) -> None:
        """Print paused message."""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] SKIPPED - Scheduler is paused")

    def _print_job_start(self) -> None:
        """Print job start message."""
        print("-" * 60)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting job...")
        print("-" * 60)

    def _print_job_end(self, exit_code: int, duration: float, log_file: Path) -> None:
        """Print job end message."""
        print("-" * 60)
        status = "SUCCESS" if exit_code == 0 else f"FAILED (exit code {exit_code})"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Job {status} ({duration:.1f}s)")
        print(f"Log: {log_file}")
        print("-" * 60)

    def _print_error(self, error: str) -> None:
        """Print error message."""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: {error}")
