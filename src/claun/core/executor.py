"""Claude Code process management."""

import asyncio
import shlex
from dataclasses import dataclass
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
    duration_seconds: float = 0.0
    error_output: str = ""


class Executor:
    """Manages Claude Code process execution."""

    def __init__(
        self,
        claude_flags: str = "",
        passthrough: bool = False,
    ) -> None:
        """Initialize executor.

        Args:
            claude_flags: Extra flags to pass to claude (e.g., "--resume abc123").
            passthrough: If True, stream output directly instead of capturing.
        """
        self.claude_flags = claude_flags
        self.passthrough = passthrough

    async def run(
        self,
        prompt: str,
        log_file: Optional[Path] = None,
        on_output: Optional[Callable[[str], None]] = None,
    ) -> ExecutionResult:
        """Execute a prompt in Claude Code.

        Args:
            prompt: The prompt to send to Claude Code.
            log_file: Optional path to write output to.
            on_output: Optional callback for each line of output (for passthrough).

        Returns:
            ExecutionResult with output and exit code.
        """
        import time

        start_time = time.time()

        # Build command arguments
        args = self._build_args(prompt)

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

        return ExecutionResult(
            output=output,
            exit_code=process.returncode or 0,
            duration_seconds=duration,
            error_output=error_output,
        )

    def _build_args(self, prompt: str) -> list[str]:
        """Build command line arguments for claude."""
        # Start with claude and --print for non-interactive output
        args = ["claude", "--print"]

        # Add any extra flags the user specified (before the prompt)
        if self.claude_flags:
            extra_flags = shlex.split(self.claude_flags)
            args.extend(extra_flags)

        # Prompt is the last positional argument
        args.append(prompt)

        return args
