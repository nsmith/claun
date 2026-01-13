"""Tests for the executor module."""

import pytest
from unittest.mock import AsyncMock, patch
from pathlib import Path

from claun.core.executor import Executor, ExecutionResult, ExecutionError


class TestExecutorBasics:
    """Test basic executor functionality."""

    def test_create_executor(self) -> None:
        """Executor can be created."""
        executor = Executor()
        assert executor is not None

    def test_executor_with_flags(self) -> None:
        """Executor can be created with claude flags."""
        executor = Executor(claude_flags="--resume abc123")
        assert executor.claude_flags == "--resume abc123"


class TestCommandExecution:
    """Test command execution."""

    @pytest.mark.asyncio
    async def test_runs_claude_command(self) -> None:
        """Executor runs claude with the prompt."""
        executor = Executor()

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(side_effect=[b"output\n", b""])
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(side_effect=[b""])
            mock_process.wait = AsyncMock(return_value=0)
            mock_exec.return_value = mock_process

            result = await executor.run("test command")

            # Verify claude was called
            mock_exec.assert_called_once()
            call_args = mock_exec.call_args
            assert "claude" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_captures_stdout(self) -> None:
        """Executor captures stdout from command."""
        executor = Executor()

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(
                side_effect=[b"line 1\n", b"line 2\n", b""]
            )
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(side_effect=[b""])
            mock_process.wait = AsyncMock(return_value=0)
            mock_exec.return_value = mock_process

            result = await executor.run("test")

            assert "line 1" in result.output
            assert "line 2" in result.output

    @pytest.mark.asyncio
    async def test_returns_exit_code(self) -> None:
        """Executor returns the exit code."""
        executor = Executor()

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 1
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(side_effect=[b""])
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(side_effect=[b"error\n", b""])
            mock_process.wait = AsyncMock(return_value=1)
            mock_exec.return_value = mock_process

            result = await executor.run("failing command")

            assert result.exit_code == 1


class TestClaudeFlagsHandling:
    """Test claude flags handling."""

    @pytest.mark.asyncio
    async def test_passes_extra_flags_to_claude(self) -> None:
        """Extra flags are passed to claude command."""
        executor = Executor(claude_flags="--resume abc123 --model opus")

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(side_effect=[b"output\n", b""])
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(side_effect=[b""])
            mock_process.wait = AsyncMock(return_value=0)
            mock_exec.return_value = mock_process

            await executor.run("test prompt")

            call_args = mock_exec.call_args
            args = list(call_args[0])
            assert "--resume" in args
            assert "abc123" in args
            assert "--model" in args
            assert "opus" in args

    @pytest.mark.asyncio
    async def test_uses_print_flag(self) -> None:
        """Executor uses --print flag for non-interactive output."""
        executor = Executor()

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(side_effect=[b""])
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(side_effect=[b""])
            mock_process.wait = AsyncMock(return_value=0)
            mock_exec.return_value = mock_process

            await executor.run("my prompt")

            call_args = mock_exec.call_args
            args = list(call_args[0])
            assert "--print" in args
            assert "my prompt" in args


class TestPassthroughMode:
    """Test passthrough mode for headless operation."""

    @pytest.mark.asyncio
    async def test_passthrough_streams_to_callback(self) -> None:
        """Passthrough mode streams output to callback."""
        executor = Executor(passthrough=True)
        lines_received: list[str] = []

        def on_output(line: str) -> None:
            lines_received.append(line)

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(
                side_effect=[b"hello\n", b"world\n", b""]
            )
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(side_effect=[b""])
            mock_process.wait = AsyncMock(return_value=0)
            mock_exec.return_value = mock_process

            await executor.run("test", on_output=on_output)

            assert "hello" in lines_received[0]
            assert "world" in lines_received[1]


class TestLogFileHandling:
    """Test log file writing during execution."""

    @pytest.mark.asyncio
    async def test_writes_to_log_file(self, temp_log_dir: Path) -> None:
        """Executor writes output to log file."""
        log_file = temp_log_dir / "test.txt"
        executor = Executor()

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(
                side_effect=[b"logged output\n", b""]
            )
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(side_effect=[b""])
            mock_process.wait = AsyncMock(return_value=0)
            mock_exec.return_value = mock_process

            await executor.run("test", log_file=log_file)

            assert log_file.exists()
            content = log_file.read_text()
            assert "logged output" in content
