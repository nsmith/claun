# Claun Development Guide

## Project Overview

Claun is a Python CLI tool for scheduling Claude Code jobs with a beautiful TUI.
The name is a portmanteau of "Claude" and "cron".

## Core Principles

1. **User simplicity first**: A user should go from install to running job in under 2 minutes
2. **Sensible defaults**: All days enabled, 15-minute intervals, no configuration required
3. **Single page interface**: No menu diving, most common functions front and center
4. **Tests first**: Write tests before implementation
5. **Modular architecture**: Business logic must work in both TUI and headless mode

## Architecture Rules

- **Never bake business logic into presentation code**
- All scheduling, timing, and execution logic lives in `src/claun/core/`
- TUI is just a view layer that calls into core modules
- Headless mode uses the exact same core modules

## Project Structure

```
src/claun/
├── __init__.py           # Package version, exports
├── __main__.py           # Entry point: python -m claun
├── cli.py                # Typer CLI definition
├── app.py                # Main application orchestrator
├── core/                 # Business logic (presentation-agnostic)
│   ├── scheduler.py      # Schedule calculation engine
│   ├── executor.py       # Claude Code process management
│   ├── session.py        # Session persistence (/rename, /resume)
│   ├── timer.py          # Countdown timer logic
│   └── config.py         # Configuration dataclasses
├── scheduling/           # Scheduling abstractions
│   ├── models.py         # Schedule, TimeSpec dataclasses
│   ├── builder.py        # Build schedules from UI inputs
│   └── calculator.py     # Next-run calculations
├── logging/              # Log management
│   ├── manager.py        # Log file creation
│   ├── writer.py         # Async log writing
│   └── browser.py        # Log browsing/querying
├── tui/                  # Textual TUI components
│   ├── app.py            # Main Textual App class
│   ├── screens/          # Screen definitions
│   └── widgets/          # Custom widgets
└── headless/
    └── runner.py         # Direct terminal output mode
```

## Testing Requirements

- Write tests BEFORE implementing features
- Target 90%+ coverage for core modules
- Use pytest with pytest-asyncio for async code
- TUI widgets get snapshot tests via textual-dev

## Code Style

- Use type hints everywhere
- Format with ruff
- Check types with mypy --strict
- Keep functions small and focused

## Key Commands

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=src/claun --cov-report=term-missing

# Type check
mypy src/claun

# Lint and format
ruff check src tests
ruff format src tests

# Run TUI in dev mode
textual run --dev src/claun/tui/app.py

# Build package
python -m build

# Install locally for testing
pip install -e .
```

## Previewing the TUI (for Claude Code)

Since Claude Code cannot run interactive TUIs directly, use the preview script to inspect the TUI state:

```bash
# Get text description of TUI state (quick check)
python scripts/preview_tui.py --text

# Generate SVG screenshot (visual inspection)
python scripts/preview_tui.py

# Preview with specific command pre-filled
python scripts/preview_tui.py -c "My test command"

# Save to specific file
python scripts/preview_tui.py --svg my_screenshot.svg
```

The preview script outputs:
- Current command input value
- Session name value
- Selected days (Mon-Sun)
- Selected minute interval
- Countdown timer value
- Pause state and button label

The SVG screenshot can be read directly to see the visual layout. Use this workflow when:
- Testing TUI changes
- Debugging widget behavior
- Verifying layout and styling
- Documenting the interface

## Session Handling

When a session name is provided:
1. First run: Use `/rename <session-name>` to name the session
2. Subsequent runs: Use `/resume <session-name>` to continue

## Log File Naming

Format: `[optional_id]_claun_[YYYYMMDD]_[HHMMSS].txt`

Examples:
- `claun_20260112_143022.txt` (no id)
- `myproject_claun_20260112_143022.txt` (with id)

Rules:
- Parse these filenames to infer last run time
- Create "paused" log entries when jobs are skipped due to pause state

## Platform Considerations

- Use `pathlib.Path` for all file operations
- Test on macOS, Linux, and Windows
- Default log path: current working directory (for simplicity)

## Defaults (Sensible by Design)

| Setting | Default |
|---------|---------|
| Days of week | All enabled (Mon-Sun) |
| Hours | Run every hour |
| Minute interval | Every 15 minutes |
| Log path | Current directory |
| Mode | TUI |
| Paused | False |
