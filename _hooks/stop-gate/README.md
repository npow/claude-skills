# stop-gate

A Claude Code [Stop hook](https://docs.anthropic.com/en/docs/claude-code/hooks) that prevents Claude from stalling — asking unnecessary permission, presenting false option menus, or declaring work "done" while deferring achievable tasks.

When Claude ends a turn, the hook sends the last few messages to a fast Claude model which classifies the stop as either **legitimate** (task done, or needs human input for an irreversible action) or a **stall** (permission-seeking, procrastination, false dilemma). Stalls are blocked with feedback telling Claude what to do instead.

Fails open: any internal error (network, parse, missing API key) exits 0 so a broken hook never bricks the session.

## Files

| File | Purpose |
|---|---|
| `stop-gate.py` | The hook script (reads stdin, calls Claude API, exits 0 or 2) |
| `autonomy-rules.md` | Source of truth for what counts as a stall vs. legitimate stop |
| `test_stop_gate.py` | pytest suite (~40 tests) |

## Install

1. Copy (or symlink) the files into `~/.claude/hooks/`:

```bash
mkdir -p ~/.claude/hooks
ln -sfn "$(pwd)/stop-gate.py" ~/.claude/hooks/stop-gate.py
ln -sfn "$(pwd)/autonomy-rules.md" ~/.claude/autonomy-rules.md
```

2. Add the hook to your `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "command": "~/.claude/hooks/stop-gate.py",
            "type": "command"
          }
        ],
        "matcher": ""
      }
    ]
  }
}
```

3. Set your API key (if not already configured for Claude Code):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Configuration

All config is via environment variables with sensible defaults:

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Your Anthropic API key (required unless using a proxy) |
| `ANTHROPIC_BASE_URL` | `https://api.anthropic.com` | API base URL (set this for proxies) |
| `CLAUDE_STOP_GATE_API_URL` | derived from `ANTHROPIC_BASE_URL` | Full messages endpoint URL (override) |
| `CLAUDE_STOP_GATE_API_KEY` | derived from `ANTHROPIC_API_KEY` | API key (override) |
| `CLAUDE_STOP_GATE_MODEL` | `claude-sonnet-4-6` | Classifier model |
| `CLAUDE_STOP_GATE_DISABLE` | — | Set to `1` to disable the hook |

## Customizing rules

Edit `autonomy-rules.md` to change what the classifier considers a stall. The hook reads it fresh on every invocation, so changes take effect immediately. The file documents categories A-D (situations where asking the user is required) and an extensive list of stall patterns to block.

## Tests

```bash
python3 -m pytest _hooks/stop-gate/test_stop_gate.py -v
```
