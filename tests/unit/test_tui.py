"""Tests for the TUI application."""

import pytest
from unittest.mock import patch, AsyncMock

from pathlib import Path

from claun.core.config import ScheduleConfig, HourConfig, MinuteInterval
from claun.tui.app import ClaunApp, DayButton, MinuteButton, RetroCountdown
from claun.tui.screens.save_config import SaveConfigModal


class TestTUIInitialization:
    """Test TUI app initialization."""

    def test_creates_app_with_default_config(self) -> None:
        """App can be created with default config."""
        app = ClaunApp()
        assert app.config.command == ""
        assert app.config.hours.run_every_hour is True

    def test_creates_app_with_custom_config(self) -> None:
        """App can be created with custom config."""
        config = ScheduleConfig(
            command="test command",
            hours=HourConfig(run_every_hour=False, start_hour=9, end_hour=17),
        )
        app = ClaunApp(config=config)
        assert app.config.command == "test command"
        assert app.config.hours.run_every_hour is False
        assert app.config.hours.start_hour == 9
        assert app.config.hours.end_hour == 17

    def test_app_starts_unpaused_by_default(self) -> None:
        """App starts unpaused by default."""
        app = ClaunApp()
        assert not app.scheduler.is_paused

    def test_app_can_start_paused(self) -> None:
        """App can be started in paused state."""
        app = ClaunApp(start_paused=True)
        assert app.scheduler.is_paused


class TestDayButton:
    """Test day button widget."""

    def test_day_button_starts_selected(self) -> None:
        """Day button starts selected by default."""
        btn = DayButton("M", 0)
        assert btn.selected is True
        assert "selected" in btn.classes

    def test_day_button_toggle(self) -> None:
        """Day button can be toggled."""
        btn = DayButton("M", 0)

        btn.toggle()
        assert btn.selected is False
        assert "selected" not in btn.classes

        btn.toggle()
        assert btn.selected is True
        assert "selected" in btn.classes


class TestMinuteButton:
    """Test minute button widget."""

    def test_minute_button_15_selected_by_default(self) -> None:
        """15-minute button is selected by default."""
        btn = MinuteButton(15)
        assert btn.selected is True
        assert "selected" in btn.classes

    def test_minute_button_other_not_selected(self) -> None:
        """Non-15-minute buttons are not selected by default."""
        btn = MinuteButton(5)
        assert btn.selected is False

    def test_minute_button_label_format(self) -> None:
        """Minute buttons have correct labels."""
        assert MinuteButton(1).label == "1m"
        assert MinuteButton(5).label == "5m"
        assert MinuteButton(15).label == "15m"
        assert MinuteButton(60).label == "1h"


class TestTUIHourControls:
    """Test hour range controls in TUI."""

    @pytest.mark.asyncio
    async def test_hour_controls_present(self) -> None:
        """Hour controls are present in the UI."""
        app = ClaunApp()
        async with app.run_test() as pilot:
            # Check all hour-related widgets exist
            switch = app.query_one("#hour-range-switch")
            start_select = app.query_one("#start-hour-select")
            end_select = app.query_one("#end-hour-select")

            assert switch is not None
            assert start_select is not None
            assert end_select is not None

    @pytest.mark.asyncio
    async def test_hour_selects_disabled_when_all_hours(self) -> None:
        """Hour selects are disabled when 'all hours' is on."""
        config = ScheduleConfig(
            command="test",
            hours=HourConfig(run_every_hour=True),
        )
        app = ClaunApp(config=config)
        async with app.run_test() as pilot:
            start_select = app.query_one("#start-hour-select")
            end_select = app.query_one("#end-hour-select")

            assert start_select.disabled is True
            assert end_select.disabled is True

    @pytest.mark.asyncio
    async def test_hour_selects_enabled_when_range(self) -> None:
        """Hour selects are enabled when using hour range."""
        config = ScheduleConfig(
            command="test",
            hours=HourConfig(run_every_hour=False, start_hour=9, end_hour=17),
        )
        app = ClaunApp(config=config)
        async with app.run_test() as pilot:
            start_select = app.query_one("#start-hour-select")
            end_select = app.query_one("#end-hour-select")

            assert start_select.disabled is False
            assert end_select.disabled is False

    @pytest.mark.asyncio
    async def test_hour_values_from_config(self) -> None:
        """Hour selects show values from config."""
        config = ScheduleConfig(
            command="test",
            hours=HourConfig(run_every_hour=False, start_hour=9, end_hour=17),
        )
        app = ClaunApp(config=config)
        async with app.run_test() as pilot:
            start_select = app.query_one("#start-hour-select")
            end_select = app.query_one("#end-hour-select")

            assert start_select.value == 9
            assert end_select.value == 17


class TestTUIScheduleUpdate:
    """Test schedule updates from UI changes."""

    @pytest.mark.asyncio
    async def test_day_button_updates_schedule(self) -> None:
        """Clicking day button updates the schedule."""
        app = ClaunApp()
        async with app.run_test() as pilot:
            # All days selected by default
            assert len(app.config.days_of_week) == 7

            # Click Monday button to deselect
            monday_btn = app.query_one("#day-0", DayButton)
            monday_btn.toggle()
            app._update_schedule()

            # Monday should be removed
            assert 0 not in app.config.days_of_week
            assert len(app.config.days_of_week) == 6

    @pytest.mark.asyncio
    async def test_minute_button_updates_schedule(self) -> None:
        """Clicking minute button updates the schedule."""
        app = ClaunApp()
        async with app.run_test() as pilot:
            # Default is 15 minutes
            assert app.config.minute_interval == MinuteInterval.EVERY_15

            # Select 5-minute interval
            for btn in app.query(".minute-button"):
                if isinstance(btn, MinuteButton):
                    btn.selected = btn.interval == 5
                    if btn.interval == 5:
                        btn.add_class("selected")
                    else:
                        btn.remove_class("selected")

            app._update_schedule()

            assert app.config.minute_interval == MinuteInterval.EVERY_5


class TestTUIResponsiveLayout:
    """Test responsive layout behavior."""

    @pytest.mark.asyncio
    async def test_compact_countdown_when_narrow(self) -> None:
        """Countdown switches to compact mode when width is below 135."""
        app = ClaunApp()
        async with app.run_test(size=(120, 40)) as pilot:
            countdown_section = app.query_one("#countdown-section")
            countdown = app.query_one("#countdown-display", RetroCountdown)
            assert "compact" in countdown_section.classes
            assert countdown._compact is True

    @pytest.mark.asyncio
    async def test_full_countdown_when_wide(self) -> None:
        """Countdown uses full ASCII art when width is 135 or more."""
        app = ClaunApp()
        async with app.run_test(size=(150, 40)) as pilot:
            countdown_section = app.query_one("#countdown-section")
            countdown = app.query_one("#countdown-display", RetroCountdown)
            assert "compact" not in countdown_section.classes
            assert countdown._compact is False


class TestSaveConfigModal:
    """Test save config modal."""

    @pytest.mark.asyncio
    async def test_save_config_action_opens_modal(self) -> None:
        """Save config action opens the modal."""
        app = ClaunApp()
        async with app.run_test() as pilot:
            # Trigger save action
            app.action_save_config()
            await pilot.pause()

            # Modal should be on the screen stack
            assert len(app.screen_stack) == 2
            assert isinstance(app.screen_stack[-1], SaveConfigModal)

    @pytest.mark.asyncio
    async def test_save_config_modal_has_default_path(self) -> None:
        """Modal shows default path in input."""
        config = ScheduleConfig(command="test")
        modal = SaveConfigModal(config)

        app = ClaunApp()
        async with app.run_test() as pilot:
            app.push_screen(modal)
            await pilot.pause()

            from textual.widgets import Input
            path_input = app.screen.query_one("#path-input", Input)
            assert path_input.value == ".claun.json"

    @pytest.mark.asyncio
    async def test_save_config_modal_saves_file(self, tmp_path: Path) -> None:
        """Modal saves config to specified file."""
        config = ScheduleConfig(
            command="save me",
            minute_interval=MinuteInterval.EVERY_5,
        )
        save_path = tmp_path / "saved.json"
        modal = SaveConfigModal(config, default_path=str(save_path))

        app = ClaunApp()
        async with app.run_test() as pilot:
            app.push_screen(modal)
            await pilot.pause()

            # Click save button
            await pilot.click("#save-btn")
            await pilot.pause()

            # File should exist
            assert save_path.exists()

            # Load and verify
            loaded = ScheduleConfig.load_from_file(save_path)
            assert loaded.command == "save me"
            assert loaded.minute_interval == MinuteInterval.EVERY_5

    @pytest.mark.asyncio
    async def test_save_config_modal_cancel_closes(self) -> None:
        """Cancel button closes modal without saving."""
        config = ScheduleConfig(command="test")
        modal = SaveConfigModal(config)

        app = ClaunApp()
        async with app.run_test() as pilot:
            app.push_screen(modal)
            await pilot.pause()

            # Modal should be visible
            assert len(app.screen_stack) == 2

            # Click cancel
            await pilot.click("#cancel-btn")
            await pilot.pause()

            # Modal should be closed
            assert len(app.screen_stack) == 1

    @pytest.mark.asyncio
    async def test_save_config_modal_escape_closes(self) -> None:
        """Escape key closes modal."""
        config = ScheduleConfig(command="test")
        modal = SaveConfigModal(config)

        app = ClaunApp()
        async with app.run_test() as pilot:
            app.push_screen(modal)
            await pilot.pause()

            assert len(app.screen_stack) == 2

            # Press escape
            await pilot.press("escape")
            await pilot.pause()

            assert len(app.screen_stack) == 1
