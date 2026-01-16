# claun

![Claun TUI](docs/screenshot.png)

Schedule Claude Code jobs with a TUI or headless mode. Sometimes systemd is just overkill. Pronounced "Klon" like the guitar pedal.

In all seriousness, the purpose of this tool is to quickly prototype workflows, or for something that is going to run on your dev desktop (like pulling/fixing bugs and submitting PRs). Please don't use it for a production pipeline! If you want to do something that you rely on for real work use systemd or Kinesis/Glue/Lambda (or I guess cron if you are old school like that). I am not responsible for any 3am pages when this falls over ;) 

## Installation

```bash
pip install claun-tui
```

## Quick Start

```bash
# Launch TUI (default)
claun

# Launch TUI with pre-filled command
claun -c "Review our metrics from the past hour for anomalies"

# Run in headless mode
claun -H -c "Update bug list from Linear MCP and fix" -m 60

# See what would run without executing
claun --dry-run -c "test command"
```

## Features

- **Simple TUI**: Single-page interface with all controls visible - no menu diving
- **Headless mode**: Run as a background service with terminal output
- **Flexible scheduling**: Days of week, hour ranges, minute intervals
- **Claude flags**: Pass any flags to claude (like `--resume` for session persistence)
- **Simple logging**: Automatic log files with browseable history

## TUI Mode

Launch with `claun` to get an interactive interface with:

- Command input field
- Optional Claude flags (e.g., `--resume <session-id>` or `--model sonnet`)
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

## Session Persistence

To resume a previous Claude Code session, use the `--flags` option to pass `--resume`:

```bash
# First, note your session ID from a previous run
# Then resume it:
claun -c "Continue working on the feature" -f "--resume abc123-def456"

# In the TUI, enter in the "Claude Flags" field:
# --resume abc123-def456
```

You can also pass other claude flags:

```bash
# Use a specific model
claun -c "Pull and fix bugs from the Linear MCP, run /code-simplifier and push PRs" -f "--model opus"

# Enable web search
claun -c "What is the score of the Niners/Seahawks game?" -f "--allowedTools WebSearch"

# Combine multiple flags
claun -c "Fix the next bug on the bug list" -f "--resume abc123 --model sonnet"
```

## CLI Options

```
Options:
  -c, --command TEXT      Claude Code command to run
  -f, --flags TEXT        Extra flags for claude (e.g., '--resume abc123')
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
