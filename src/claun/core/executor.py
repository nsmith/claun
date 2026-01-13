"""Claude Code process management."""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


class ExecutionError(Exception):
    """Raised when Claude Code execution fails."""

    pass


@dataclass
class ExecutionResult:
    """Result of a command execution."""

    output: str
    exit_code: int
    session_id: Optional[str] = None
    duration_seconds: float = 0.0
    error_output: str = ""


class Executor:
    """Manages Claude Code process execution."""

    def __init__(
        self,
        session_name: Optional[str] = None,
        passthrough: bool = False,
    ) -> None:
        """Initialize executor.

        Args:
            session_name: Optional session name for persistence.
            passthrough: If True, stream output directly instead of capturing.
        """
        self.session_name = session_name
        self.passthrough = passthrough
        self._session_id: Optional[str] = None

    async def run(
        self,
        command: str,
        first_run: bool = False,
        resume: bool = False,
        log_file: Optional[Path] = None,
        on_output: Optional[Callable[[str], None]] = None,
    ) -> ExecutionResult:
        """Execute a command in Claude Code.

        Args:
            command: The command/prompt to send to Claude Code.
            first_run: If True, use --print-session-id for session management.
            resume: If True, resume the previous session.
            log_file: Optional path to write output to.
            on_output: Optional callback for each line of output (for passthrough).

        Returns:
            ExecutionResult with output and exit code.
        """
        import time

        start_time = time.time()

        # Build command arguments
        args = self._build_args(command, first_run, resume)

        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            raise ExecutionError(
                "Claude Code not found. Please ensure 'claude' is installed and in PATH."
            )
        except PermissionError:
            raise ExecutionError("Permission denied when running Claude Code.")

        # Collect output
        output_lines: list[str] = []
        error_lines: list[str] = []

        # Open log file if specified
        log_handle = None
        if log_file:
            log_handle = open(log_file, "w")

        try:
            # Read stdout
            while True:
                assert process.stdout is not None
                line_bytes = await process.stdout.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8", errors="replace")
                output_lines.append(line)

                if self.passthrough and on_output:
                    on_output(line.rstrip("\n"))

                if log_handle:
                    log_handle.write(line)
                    log_handle.flush()

            # Read stderr
            while True:
                assert process.stderr is not None
                line_bytes = await process.stderr.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8", errors="replace")
                error_lines.append(line)

                if log_handle:
                    log_handle.write(f"[stderr] {line}")
                    log_handle.flush()

            await process.wait()

        finally:
            if log_handle:
                log_handle.close()

        duration = time.time() - start_time
        output = "".join(output_lines)
        error_output = "".join(error_lines)

        # Extract session ID if this was a first run
        session_id = None
        if first_run and self.session_name:
            session_id = self._extract_session_id(output)
            if session_id:
                self._session_id = session_id

        return ExecutionResult(
            output=output,
            exit_code=process.returncode or 0,
            session_id=session_id,
            duration_seconds=duration,
            error_output=error_output,
        )

    def _build_args(
        self, command: str, first_run: bool, resume: bool
    ) -> list[str]:
        """Build command line arguments for claude."""
        args = ["claude", "--print", command]

        if self.session_name:
            if first_run:
                # First run: get session ID for later resume
                args.append("--print-session-id")
            elif resume and self._session_id:
                # Resume: use saved session ID
                args.extend(["--session", self._session_id])

        return args

    def _extract_session_id(self, output: str) -> Optional[str]:
        """Extract session ID from claude output."""
        # Session ID is typically printed as a UUID or similar identifier
        # Look for lines that look like session IDs
        for line in output.split("\n"):
            line = line.strip()
            # Session IDs are typically UUIDs or alphanumeric strings
            if len(line) > 10 and len(line) < 100 and line.replace("-", "").isalnum():
                return line
        return None
