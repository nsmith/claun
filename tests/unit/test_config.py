"""Tests for config serialization."""

import json
import pytest
from pathlib import Path

from claun.core.config import (
    ScheduleConfig,
    HourConfig,
    MinuteInterval,
    AdvancedConfig,
    ALL_DAYS,
)


class TestScheduleConfigSerialization:
    """Tests for ScheduleConfig serialization methods."""

    def test_to_dict_minimal(self) -> None:
        """Test to_dict with minimal config."""
        config = ScheduleConfig(command="test command")
        result = config.to_dict()

        assert result["command"] == "test command"
        assert result["claude_flags"] == ""
        assert result["days_of_week"] == [0, 1, 2, 3, 4, 5, 6]
        assert result["hours"]["run_every_hour"] is True
        assert result["minute_interval"] == 15
        assert result["log_path"] == "."
        assert "log_id" not in result
        assert "advanced" not in result

    def test_to_dict_full(self) -> None:
        """Test to_dict with all fields set."""
        config = ScheduleConfig(
            command="full test",
            claude_flags="--resume abc123",
            days_of_week={0, 2, 4},
            hours=HourConfig(run_every_hour=False, start_hour=9, end_hour=17),
            minute_interval=MinuteInterval.EVERY_5,
            log_path="/var/log",
            log_id="myproject",
        )
        result = config.to_dict()

        assert result["command"] == "full test"
        assert result["claude_flags"] == "--resume abc123"
        assert result["days_of_week"] == [0, 2, 4]
        assert result["hours"]["run_every_hour"] is False
        assert result["hours"]["start_hour"] == 9
        assert result["hours"]["end_hour"] == 17
        assert result["minute_interval"] == 5
        assert result["log_path"] == "/var/log"
        assert result["log_id"] == "myproject"

    def test_to_dict_with_advanced(self) -> None:
        """Test to_dict with advanced config."""
        config = ScheduleConfig(
            command="advanced test",
            advanced=AdvancedConfig(
                specific_dates=["2025-01-15"],
                days_of_month={1, 15},
                specific_hours={9, 12, 17},
                custom_minute_interval=7,
            ),
        )
        result = config.to_dict()

        assert "advanced" in result
        assert result["advanced"]["specific_dates"] == ["2025-01-15"]
        assert result["advanced"]["days_of_month"] == [1, 15]
        assert result["advanced"]["specific_hours"] == [9, 12, 17]
        assert result["advanced"]["custom_minute_interval"] == 7

    def test_from_dict_minimal(self) -> None:
        """Test from_dict with minimal data."""
        data = {"command": "minimal"}
        config = ScheduleConfig.from_dict(data)

        assert config.command == "minimal"
        assert config.claude_flags == ""
        assert config.days_of_week == set(ALL_DAYS)
        assert config.hours.run_every_hour is True
        assert config.minute_interval == MinuteInterval.EVERY_15
        assert config.log_path == "."
        assert config.log_id is None

    def test_from_dict_full(self) -> None:
        """Test from_dict with all fields."""
        data = {
            "command": "full command",
            "claude_flags": "--model opus",
            "days_of_week": [1, 3, 5],
            "hours": {
                "run_every_hour": False,
                "start_hour": 8,
                "end_hour": 20,
            },
            "minute_interval": 60,
            "log_path": "/logs",
            "log_id": "test_id",
        }
        config = ScheduleConfig.from_dict(data)

        assert config.command == "full command"
        assert config.claude_flags == "--model opus"
        assert config.days_of_week == {1, 3, 5}
        assert config.hours.run_every_hour is False
        assert config.hours.start_hour == 8
        assert config.hours.end_hour == 20
        assert config.minute_interval == MinuteInterval.EVERY_60
        assert config.log_path == "/logs"
        assert config.log_id == "test_id"

    def test_from_dict_with_advanced(self) -> None:
        """Test from_dict with advanced config."""
        data = {
            "command": "test",
            "advanced": {
                "specific_dates": ["2025-12-25"],
                "days_of_month": [10, 20],
                "specific_hours": [6, 18],
                "custom_minute_interval": 3,
            },
        }
        config = ScheduleConfig.from_dict(data)

        assert config.advanced is not None
        assert config.advanced.specific_dates == ["2025-12-25"]
        assert config.advanced.days_of_month == {10, 20}
        assert config.advanced.specific_hours == {6, 18}
        assert config.advanced.custom_minute_interval == 3

    def test_round_trip(self) -> None:
        """Test that to_dict and from_dict are inverses."""
        original = ScheduleConfig(
            command="round trip test",
            claude_flags="--verbose",
            days_of_week={0, 1, 2},
            hours=HourConfig(run_every_hour=False, start_hour=10, end_hour=16),
            minute_interval=MinuteInterval.EVERY_1,
            log_path="/tmp/logs",
            log_id="roundtrip",
        )

        data = original.to_dict()
        restored = ScheduleConfig.from_dict(data)

        assert restored.command == original.command
        assert restored.claude_flags == original.claude_flags
        assert restored.days_of_week == original.days_of_week
        assert restored.hours.run_every_hour == original.hours.run_every_hour
        assert restored.hours.start_hour == original.hours.start_hour
        assert restored.hours.end_hour == original.hours.end_hour
        assert restored.minute_interval == original.minute_interval
        assert restored.log_path == original.log_path
        assert restored.log_id == original.log_id


class TestScheduleConfigFileIO:
    """Tests for ScheduleConfig file I/O."""

    def test_save_to_file(self, tmp_path: Path) -> None:
        """Test saving config to file."""
        config = ScheduleConfig(
            command="save test",
            minute_interval=MinuteInterval.EVERY_5,
        )
        file_path = tmp_path / "test.json"

        config.save_to_file(file_path)

        assert file_path.exists()
        data = json.loads(file_path.read_text())
        assert data["command"] == "save test"
        assert data["minute_interval"] == 5

    def test_load_from_file(self, tmp_path: Path) -> None:
        """Test loading config from file."""
        file_path = tmp_path / "load.json"
        file_path.write_text(json.dumps({
            "command": "loaded command",
            "days_of_week": [0, 6],
            "minute_interval": 1,
        }))

        config = ScheduleConfig.load_from_file(file_path)

        assert config.command == "loaded command"
        assert config.days_of_week == {0, 6}
        assert config.minute_interval == MinuteInterval.EVERY_1

    def test_save_and_load_round_trip(self, tmp_path: Path) -> None:
        """Test save and load are inverses."""
        original = ScheduleConfig(
            command="file round trip",
            claude_flags="--quiet",
            days_of_week={1, 2, 3, 4, 5},
            hours=HourConfig(run_every_hour=False, start_hour=9, end_hour=17),
            minute_interval=MinuteInterval.EVERY_15,
            log_path="./logs",
            log_id="filetest",
        )
        file_path = tmp_path / "roundtrip.json"

        original.save_to_file(file_path)
        loaded = ScheduleConfig.load_from_file(file_path)

        assert loaded.command == original.command
        assert loaded.claude_flags == original.claude_flags
        assert loaded.days_of_week == original.days_of_week
        assert loaded.hours.run_every_hour == original.hours.run_every_hour
        assert loaded.minute_interval == original.minute_interval
        assert loaded.log_id == original.log_id
