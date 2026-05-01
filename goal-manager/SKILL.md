---
name: goal-manager
description: Use when the user asks to set a goal, track progress across sessions, check goal drift, review long-term objectives, or says "remember this goal", "what are my goals", "how is X progressing". Tracks multi-session goals and detects drift.
category: agent-infrastructure
capabilities:
  - goal-tracking
  - drift-detection
  - context-injection
best_for: maintaining alignment on objectives that span multiple sessions, hours, or days
input_type: cli-args
output_type: json
maturity: alpha
---

# Goal Manager — Long-Horizon Coherence

Track multi-session objectives, detect goal drift, and inject compact goal summaries into session prompts. Prevents goal amnesia, objective substitution, and silent scope drift across session boundaries.

## When to Use

- A user establishes an objective that will span multiple sessions (e.g., "spec out the 5 Tier 1 items", "build the scenario reliability framework")
- At session start, to inject active goal context into the prompt
- Periodically, to check for drift (stale goals, unmapped work, decision accumulation)
- When completing, abandoning, or pausing long-running work

## Architecture

```
~/.aimee/workspace/
├── GOALS.md                  # Human-readable index (sentinel-managed section)
├── goals/
│   ├── g-<id>.json           # One file per goal (atomic writes)
│   ├── thread_map.json       # Slack thread → goal ID mapping
│   └── .lhc_meta.json        # Schema version, last drift check, alert log
```

Override workspace with `LHC_WORKSPACE` env var.

## CLI Reference

Script: `${SKILLS_ROOT}/goal-manager/scripts/goal_manager.py`

All commands output JSON to stdout.

### Goal Lifecycle

```bash
# Register a new goal
goal_manager.py register \
  --title "Build scenario reliability framework" \
  --intent "Adversarial test coverage for all 10 skills" \
  --criteria "68 scenarios passing" "CI gate wired" \
  --effort weeks \
  --tags reliability testing \
  --thread-id "C04JU1P5ELV/1777303899.777999" \
  --parent g-<parent-id> \
  --triggered-by "antanomy paper review item 1"

# Update progress on a goal
goal_manager.py update-progress \
  --goal-id g-<id> \
  --accomplished "Wrote 12 failure injection primitives" "CLI wrapper done" \
  --remaining "Wire CI gate" "Backfill 56 skills" \
  --decisions "desc|rationale|scope_impact" \
  --confidence 0.7 \
  --session-id <session-id> \
  --run-id <sagaflow-run-id>

# Complete a goal (blocks if active children exist)
goal_manager.py complete \
  --goal-id g-<id> \
  --summary "All 68 scenarios passing, CI gate live" \
  --artifacts spec.md report.html

# Abandon a goal (cascades to children, unlinks threads)
goal_manager.py abandon --goal-id g-<id> --reason "Deprioritized"

# Pause / resume
goal_manager.py pause --goal-id g-<id> --reason "Blocked on dependency"
goal_manager.py resume --goal-id g-<id>
```

### Queries

```bash
# List goals (default: active only)
goal_manager.py list --filter active|paused|completed|abandoned|all

# Show full goal record
goal_manager.py show --goal-id g-<id>

# Generate context block for session prompt (≤2000 tokens)
goal_manager.py context-block --thread-id "C04JU1P5ELV/1234567890.123456"
```

### Drift Detection

```bash
# Run all drift rules against active goals
goal_manager.py drift-check --scope all

# Run drift check for a specific goal
goal_manager.py drift-check --scope g-<id>
```

**Drift rules implemented:**
| Rule | Trigger | Severity |
|------|---------|----------|
| D-01 | No progress for 3+ days | MEDIUM (3d) / HIGH (7d) |
| D-02 | 3+ decisions accumulated | MEDIUM |
| D-03 | Confidence dropped below 0.6 | HIGH |
| D-06 | Active children blocking parent | MEDIUM |
| D-08 | Unmapped work flag set | LOW |

D-05 (scope change via criteria diff) is stubbed. D-07 (priority confusion) surfaces via the unmapped-work flag.

**Anti-noise:** HIGH alerts have a 24-hour cooldown per goal. Max 3 HIGH alerts surfaced per session.

### Thread Mapping

```bash
# Link a Slack thread to a goal
goal_manager.py link-thread --goal-id g-<id> --thread-id "C04JU1P5ELV/1234567890.123456"

# Flag unmapped work on a goal
goal_manager.py set-unmapped-work --goal-id g-<id> --value true
```

### Maintenance

```bash
# Check internal consistency (orphans, broken parent refs, stale thread mappings)
goal_manager.py consistency-check
```

## Integration Points

### Session Start
Call `context-block` to get a compact goal summary (≤2,000 tokens) for injection into the session prompt. Pass `--thread-id` to prioritize thread-relevant goals.

### After Meaningful Work
Call `update-progress` with what was accomplished, what remains, and any decisions made. Include `--confidence` if the goal feels at risk.

### Session End / Idle
Call `drift-check --scope all` to surface stale goals or accumulated drift.

### Goal Completion
Call `complete` when done. The command enforces that all child goals must be completed first.

## GOALS.md Format

The script manages a sentinel block in GOALS.md:

```markdown
<!-- LHC:BEGIN -->
| ID | Title | Status | Progress | Updated |
|----|-------|--------|----------|---------|
| g-xxx | Build reliability framework | active | 3/5 items done | 2026-04-28 |
<!-- LHC:END -->
```

Content outside the sentinel block is preserved. The block is rewritten on every mutation.
