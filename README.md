# claun

Schedule Claude Code jobs with a beautiful TUI or headless mode. Sometimes systemd is just overkill.

## Installation

```bash
pip install claun
```

## Quick Start

```bash
# Launch TUI (default)
claun

# Launch TUI with pre-filled command
claun -c "Review the latest PR"

# Run in headless mode
claun -H -c "Run daily standup summary" -m 60

# See what would run without executing
claun --dry-run -c "test command"
```

## Features

- **Beautiful TUI**: Single-page interface with all controls visible
- **Headless mode**: Run as a background service with terminal output
- **Flexible scheduling**: Days of week, hour ranges, minute intervals
- **Session persistence**: Optionally resume Claude Code sessions
- **Simple logging**: Automatic log files with browseable history

## TUI Mode

Launch with `claun` to get an interactive interface with:

- Command input field
- Optional session name for persistence
- Day-of-week toggles (M T W T F S S)
- Minute interval selector (1, 5, 15, or 60 minutes)
- Big countdown clock to next run
- Pause/Resume control
- Live output log

**Keyboard shortcuts:**
- `q` - Quit
- `p` - Pause/Resume
- `r` - Run now
- `c` - Clear log

## Headless Mode

Run without TUI for background/automated use:

```bash
# Every 15 minutes (default)
claun -H -c "Check for issues"

# Hourly during work hours
claun -H -c "Status update" --hours "9am-5pm" -m 60

# Weekdays only
claun -H -c "Daily standup" --weekdays -m 60
```

## CLI Options

```
Options:
  -c, --command TEXT      Claude Code command to run
  -s, --session TEXT      Session name for persistence
  -H, --headless          Run in headless mode (no TUI)
  -d, --days TEXT         Days to run (mon,tue,wed,thu,fri,sat,sun)
  --weekdays              Run only on weekdays (mon-fri)
  --weekends              Run only on weekends (sat-sun)
  --hours TEXT            Hour range (e.g., '9-17' or '9am-5pm')
  -m, --minutes [1|5|15|60]  Minute interval
  -l, --log-path PATH     Directory for log files
  --log-id TEXT           Optional ID prefix for log filenames
  -P, --paused            Start in paused state
  --once                  Run once immediately and exit
  --dry-run               Show schedule without executing
  -v, --version           Show version
```

## Subcommands

### Browse Logs

```bash
# List recent logs in current directory
claun logs

# List logs from specific path
claun logs --path /var/log/claun

# Limit to 10 most recent
claun logs -n 10
```

## Log Files

Logs are saved as: `[log_id_]claun_YYYYMMDD_HHMMSS_microseconds.txt`

Examples:
- `claun_20260112_143022_123456.txt`
- `myproject_claun_20260112_143022_789012.txt` (with --log-id)

## License

GPL-3.0
