#!/usr/bin/env python3
"""Preview the TUI and generate screenshots for inspection.

Usage:
    python scripts/preview_tui.py                    # Generate SVG screenshot
    python scripts/preview_tui.py --text             # Text description only
    python scripts/preview_tui.py --command "test"   # With pre-filled command
    python scripts/preview_tui.py --svg out.svg      # Save to specific file
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claun.tui.app import ClaunApp
from claun.core.config import ScheduleConfig


async def preview_tui(
    command: str = "Example: Review PR #123",
    output_svg: str | None = None,
    text_only: bool = False,
    width: int = 100,
    height: int = 35,
) -> None:
    """Preview the TUI and output inspection data."""

    config = ScheduleConfig(command=command)
    app = ClaunApp(config=config)

    async with app.run_test(size=(width, height)) as pilot:
        # Collect UI state information
        print("=" * 60)
        print("CLAUN TUI PREVIEW")
        print("=" * 60)

        # Command input
        command_input = app.query_one("#command-input")
        print(f"\nCommand Input: {command_input.value!r}")

        # Claude flags input
        flags_input = app.query_one("#flags-input")
        flags_val = flags_input.value or "(empty)"
        print(f"Claude Flags: {flags_val!r}")

        # Day buttons
        days = []
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, btn in enumerate(app.query(".day-button")):
            if hasattr(btn, "selected") and btn.selected:
                days.append(day_names[i])
        print(f"Selected Days: {', '.join(days)}")

        # Hour settings (switch OFF = all day, switch ON = hour range)
        hour_range_switch = app.query_one("#hour-range-switch")
        if hour_range_switch.value:
            start_select = app.query_one("#start-hour-select")
            end_select = app.query_one("#end-hour-select")
            print(f"Hours: {start_select.value:02d}:00 - {end_select.value:02d}:00")
        else:
            print("Hours: All day")

        # Minute interval
        for btn in app.query(".minute-button"):
            if hasattr(btn, "selected") and btn.selected:
                print(f"Minute Interval: {btn.interval} minutes")
                break

        # Countdown
        countdown = app.query_one("#countdown-digits")
        print(f"Countdown: {countdown.value}")

        # Pause state
        pause_btn = app.query_one("#pause-button")
        is_paused = "paused" in pause_btn.classes
        print(f"Paused: {is_paused}")
        print(f"Pause Button Label: {pause_btn.label}")

        print("\n" + "=" * 60)

        # Generate SVG if requested
        if not text_only:
            svg_path = output_svg or "tui_preview.svg"
            app.save_screenshot(svg_path)
            print(f"\nSVG screenshot saved to: {svg_path}")
            print(f"View in browser or read with: cat {svg_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview the claun TUI")
    parser.add_argument(
        "--command", "-c",
        default="Example: Review PR #123",
        help="Command to pre-fill in the TUI"
    )
    parser.add_argument(
        "--svg", "-o",
        default=None,
        help="Output SVG file path (default: tui_preview.svg)"
    )
    parser.add_argument(
        "--text", "-t",
        action="store_true",
        help="Text description only, no SVG"
    )
    parser.add_argument(
        "--width", "-W",
        type=int,
        default=100,
        help="Terminal width (default: 100)"
    )
    parser.add_argument(
        "--height", "-H",
        type=int,
        default=35,
        help="Terminal height (default: 35)"
    )

    args = parser.parse_args()

    asyncio.run(preview_tui(
        command=args.command,
        output_svg=args.svg,
        text_only=args.text,
        width=args.width,
        height=args.height,
    ))


if __name__ == "__main__":
    main()
