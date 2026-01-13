"""Integration tests for the CLI."""

import pytest
from typer.testing import CliRunner

from claun.cli import app

runner = CliRunner()


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_version_flag(self) -> None:
        """--version shows version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "claun" in result.stdout.lower()
        assert "0.1.0" in result.stdout

    def test_help_flag(self) -> None:
        """--help shows help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "claude code" in result.stdout.lower()


class TestDryRun:
    """Test dry run mode."""

    def test_dry_run_shows_config(self) -> None:
        """--dry-run shows schedule configuration."""
        result = runner.invoke(app, ["--dry-run", "-c", "test command"])
        assert result.exit_code == 0
        assert "test command" in result.stdout
        assert "15 minutes" in result.stdout.lower()

    def test_dry_run_with_weekdays(self) -> None:
        """--dry-run with --weekdays shows weekday schedule."""
        result = runner.invoke(app, ["--dry-run", "-c", "test", "--weekdays"])
        assert result.exit_code == 0
        assert "Mon" in result.stdout
        assert "Fri" in result.stdout
        # Should not include weekend
        output_lines = [l for l in result.stdout.split("\n") if "Days:" in l]
        assert output_lines
        assert "Sat" not in output_lines[0]
        assert "Sun" not in output_lines[0]

    def test_dry_run_with_hour_range(self) -> None:
        """--dry-run with --hours shows hour range."""
        result = runner.invoke(app, ["--dry-run", "-c", "test", "--hours", "9-17"])
        assert result.exit_code == 0
        assert "9:00" in result.stdout or "9-17" in result.stdout

    def test_dry_run_with_minute_interval(self) -> None:
        """--dry-run with --minutes shows interval."""
        result = runner.invoke(app, ["--dry-run", "-c", "test", "-m", "5"])
        assert result.exit_code == 0
        assert "5 minutes" in result.stdout.lower()


class TestHeadlessValidation:
    """Test headless mode validation."""

    def test_headless_requires_command(self) -> None:
        """--headless without --command shows error."""
        result = runner.invoke(app, ["--headless"])
        assert result.exit_code == 1
        # Error goes to stderr, which is combined in output
        assert "command" in result.output.lower()


class TestLogsCommand:
    """Test logs command."""

    def test_logs_no_logs(self, tmp_path) -> None:
        """logs command with empty directory."""
        result = runner.invoke(app, ["logs", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "no logs" in result.stdout.lower()


class TestDayParsing:
    """Test day option parsing."""

    def test_parse_single_day(self) -> None:
        """Single day is parsed correctly."""
        result = runner.invoke(app, ["--dry-run", "-c", "test", "-d", "mon"])
        assert result.exit_code == 0
        assert "Mon" in result.stdout

    def test_parse_multiple_days(self) -> None:
        """Multiple days are parsed correctly."""
        result = runner.invoke(app, ["--dry-run", "-c", "test", "-d", "mon,wed,fri"])
        assert result.exit_code == 0
        output_lines = [l for l in result.stdout.split("\n") if "Days:" in l]
        assert output_lines
        assert "Mon" in output_lines[0]
        assert "Wed" in output_lines[0]
        assert "Fri" in output_lines[0]


class TestHourParsing:
    """Test hour option parsing."""

    def test_parse_24h_format(self) -> None:
        """24-hour format is parsed correctly."""
        result = runner.invoke(app, ["--dry-run", "-c", "test", "--hours", "9-17"])
        assert result.exit_code == 0
        # Should show hour range
        assert "9" in result.stdout and "17" in result.stdout

    def test_parse_12h_format(self) -> None:
        """12-hour format is parsed correctly."""
        result = runner.invoke(app, ["--dry-run", "-c", "test", "--hours", "9am-5pm"])
        assert result.exit_code == 0
        # Should convert to 24-hour
        assert "9" in result.stdout and "17" in result.stdout
