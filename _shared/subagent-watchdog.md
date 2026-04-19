# Subagent Watchdog (Shared)

Every background-spawned subagent is paired with a staleness monitor that treats **output-file growth** as ground truth. The Task/Agent runtime reports PID liveness, not progress — a process that is deadlocked, spinning, or stuck in an infinite retry loop stays `status: "running"` forever and the completion notification never fires. Without a watchdog the coordinator blocks on `TaskOutput(block=true)` indefinitely.

**Used by:** deep-qa, deep-debug, deep-research, deep-design, deep-plan, proposal-reviewer, team, autopilot, loop-until-done, flaky-test-diagnoser.

---

## The gap this closes

The Task/Agent runtime exposes three signals, and only one of them is reliable:

| Signal | What it actually means | Trust level |
|---|---|---|
| `status: "running"` | PID is still in the runtime's task table | **Weak** — unchanged for hangs, deadlocks, stuck retries |
| `<task-notification>` on completion | Process exited cleanly | Authoritative — but never fires for a hung process |
| Output file mtime / size growth | Subagent is producing output | **Ground truth** — a stalled jsonl is a stalled agent |

Any coordinator that decides "is this subagent healthy?" from `status` alone will miss hangs. The watchdog pattern below replaces that decision with a mtime-plus-threshold check.

---

## The contract

**For every `run_in_background=true` spawn**, the coordinator does three things in order:

1. **Record `output_path` to state.json before the spawn** (already required by the state-before-spawn contract). The watchdog needs to know which file is ground truth.
2. **Start the spawn.** Capture the `task_id` returned by the Agent tool.
3. **Arm a watchdog.** Either a Monitor tail that fires a STALE event when mtime age exceeds threshold, or a periodic staleness poll every time the coordinator is about to block on `TaskOutput`.

When the watchdog fires STALE:
- Coordinator records `status: "stalled_watchdog"` and `stalled_at_iso` to state.
- Coordinator grades: `healthy | stalled | hung | dead` using the grading table below.
- Coordinator calls `TaskStop` on the subagent and treats the lane as `timed_out_heartbeat` in its termination vocabulary. Never silently continue waiting.

---

## Grading ground-truth state

Compute these four values any time you're about to trust a subagent's liveness:

| Metric | How to get it |
|---|---|
| `now` | `date +%s` (UTC epoch seconds) |
| `last_write_age_seconds` | `now - stat -f %m <output_path>` on macOS; `now - stat -c %Y <output_path>` on Linux |
| `bytes_since_last_check` | current size minus size at previous check |
| `runtime_status` | `TaskOutput(block=false)` → `status` field |

Grading:

| Grade | Condition | Action |
|---|---|---|
| `healthy` | `runtime_status == "running"` AND `bytes_since_last_check > 0` | continue waiting |
| `stalled` | `runtime_status == "running"` AND `last_write_age_seconds > STALE_THRESHOLD` | escalate — send diagnostic signal, keep watching briefly |
| `hung` | `runtime_status == "running"` AND `last_write_age_seconds > HUNG_THRESHOLD` | `TaskStop` + terminate lane as `timed_out_heartbeat` |
| `dead` | `runtime_status != "running"` AND no `<task-notification>` received | runtime lost the task — read output file, treat final line as best-effort result |

**Default thresholds (per skill, override if domain-specific):**

| Constant | Default | Rationale |
|---|---|---|
| `STALE_THRESHOLD` | 10 min | First whisper. A research agent fetching a dozen sources can legitimately sit quiet for ~5 min. |
| `HUNG_THRESHOLD` | 30 min | Hard kill threshold. Anything quiet this long is not making progress. |
| `WATCHDOG_POLL_INTERVAL` | 60 s | How often the Monitor tail sends stat back. |

Skills that spawn fast Haiku work (judges, summaries) tighten these — e.g. deep-qa judges: STALE=3 min, HUNG=10 min. Skills that spawn long researchers (deep-research depth≥1 direction) can loosen them but never above HUNG=60 min.

---

## Implementation pattern

Two flavors. Pick the one that fits the skill's spawn shape.

### Flavor A: Monitor tail per spawn (pushes events)

For skills that fan out N subagents in parallel and want push notifications when any one stalls. Best for deep-qa, deep-debug, deep-research.

Canonical invocation (uses the helper at [`_shared/watchdog-monitor.sh`](watchdog-monitor.sh) so every adopter runs the same code path):

```
Monitor(
  description="watchdog {skill}-{run_id}/{agent_role}",
  timeout_ms=(hung_seconds + 60) * 1000,    # small buffer above HUNG
  persistent=false,
  command="bash ~/.claude/skills/_shared/watchdog-monitor.sh \
           {output_path} {stale_seconds} {hung_seconds} {lane_label}"
)
```

The helper emits one of three line prefixes: `STALE ...`, `HUNG ...`, or `ERROR ...`. Coordinator parser:

- `STALE` → soft warning: log + update `state.agents[id].status = "stalled_watchdog"` + keep watching.
- `HUNG` → hard fail: `TaskStop` the lane + mark `hung_killed` + emit `timed_out_heartbeat` in termination.
- `ERROR` → treat as HUNG fail-safe: the watchdog itself couldn't determine age, so don't trust the lane.

**Critical:** include the full alphabet of failure signatures, not just the happy path. The helper already covers STALE, HUNG, missing file (falls back to spawn-epoch age), and stat-failure ERROR. If you inline a variant, keep all four.

### Flavor B: In-line poll before TaskOutput block (pulls state)

For skills that have a single wait-point (judge batch, summary). Simpler to reason about; no separate Monitor to clean up. Best for deep-plan, deep-design.

```bash
# Before calling TaskOutput(block=true), first check age explicitly:
age=$(( $(date +%s) - $(stat -f %m {output_path} 2>/dev/null || stat -c %Y {output_path}) ))
if [ "$age" -gt {HUNG_THRESHOLD} ]; then
  # TaskStop + mark hung; do not call block=true on a dead task
else
  # age is acceptable; safe to block
fi
```

The coordinator must run this check each time it's about to wait. **"TaskOutput status is running" is never sufficient justification to enter an unbounded wait.**

---

## Fail-safe semantics

**When the watchdog can't determine age** (output file doesn't exist yet, stat fails, Monitor crashed) → fail-safe to `stalled`, escalate to `hung` after HUNG_THRESHOLD from spawn time. Do not fail-safe to `healthy`; that reintroduces the original bug.

**When the grading is ambiguous** (runtime says `running` but output is fresh — legitimate; runtime says not-`running` but output is still growing — impossible, but treat as runtime lying → trust the file) → prefer the file-system signal. It has no retry buffer, no stale cache, no PID-table lag.

**When the subagent legitimately needs long quiet periods** (e.g. a web-fetching researcher that holds for 8 minutes on a slow source) → raise STALE_THRESHOLD for that spawn, but never above HUNG_THRESHOLD, and document the override in the skill's SKILL.md.

---

## State schema additions

Skills adopting this contract add to their `state.agents[id]` record (or the skill-specific equivalent — `directions.{id}` in deep-research, `hypotheses.{id}` in deep-debug, `angles.{id}` in deep-qa, `workers.{id}` in team / loop-until-done, etc.):

```json
{
  "status": "pending | in_progress | stalled_watchdog | hung_killed | spawn_failed | completed",
  "spawn_time_iso": "...",
  "output_path": "...",
  "last_mtime_check_iso": "...",
  "last_mtime_age_seconds": 42,
  "watchdog_monitor_id": "monitor-12345",    // null for Flavor B
  "stalled_at_iso": "...",                   // set on STALE
  "hung_killed_at_iso": "..."                // set on HUNG + TaskStop
}
```

The grading transitions are monotonic: `in_progress → stalled_watchdog → hung_killed` (or jump directly to `completed`). Never downgrade from `hung_killed` back to `in_progress` — a killed agent stays killed.

## Termination-label addition

Every adopting skill's termination vocabulary gains one label when a watchdog fires:

| Label | When |
|---|---|
| `timed_out_heartbeat` | At least one lane hit its HUNG threshold and was killed by the watchdog; no alternative lanes recovered the work cleanly |

Skills that already have their own per-lane outcome vocabulary (e.g. deep-debug's `cancelled` / `timed_out_heartbeat`, deep-research's per-direction status) apply the label at the lane level AND bubble it up to the run-level termination if a watchdog-kill blocked the whole run from completing cleanly. Skills with a single top-level termination label treat `timed_out_heartbeat` as a peer of their existing failure labels — never as a synonym for "complete."

Honest-language guard: a watchdog-killed lane never terminates as `completed`, `partial_with_accepted_unfixed`, or any label that implies the subagent's work was assessed. The hung subagent's output was never read; that distinction matters. If other lanes recovered enough to produce a useful run, the run label is the skill's existing "partial" variant — `timed_out_heartbeat` remains on the killed lane.

---

## Common failure modes this prevents

- **The 18-hour silent death:** coordinator calls `TaskOutput(block=true)` on a spinning subagent. Runtime never fires the completion notification. Coordinator waits forever. Watchdog's HUNG threshold kills it in 30 min and surfaces `timed_out_heartbeat`.
- **Status-field trust:** `status: "running"` is not evidence. File mtime is evidence. "last write 18 minutes ago" is a fact; "it's still running" is a hope.
- **Vague waiting verbs:** the coordinator that says "subagent is still in progress" without computing age is rationalizing. The watchdog forces the coordinator to emit a concrete age every time it waits.
- **Cascade hangs:** a skill spawning 8 parallel agents where one hangs — without the watchdog, the coordinator blocks on the first unfinished `TaskOutput`, masking whether any of the 8 is stuck. With the watchdog, every stuck lane surfaces independently.

---

## Anti-rationalizations

| Excuse | Reality |
|---|---|
| "The runtime will fire the notification eventually" | It won't if the process never exits. A hung process doesn't complete; it hangs. |
| "Status is running, so it's making progress" | Status is PID liveness, not progress. See the table above. |
| "My subagents always complete quickly" | Until the day one doesn't. The whole point of a watchdog is the long-tail failure, not the median case. |
| "I'll notice if it hangs" | You won't. You context-switch. The user asks a different question. Hours pass. The session compacts. The orphan survives the summary. |
| "Adding a watchdog is overkill for a Haiku judge" | A hung Haiku judge is indistinguishable from a hung Sonnet researcher to the coordinator. Cost of watchdog: ~5 lines of bash. Cost of skipped watchdog: the bug we just fixed. |
| "I can tail -f the jsonl myself to check" | Manual tailing is not a contract. A future coordinator (or a future version of you after a context compaction) will not remember to tail. Encode it. |

---

## Integration checklist for a skill importing this reference

- [ ] SKILL.md has a one-line cross-reference near the Execution Model section: `See [_shared/subagent-watchdog.md](../_shared/subagent-watchdog.md) for staleness monitoring on every background spawn.`
- [ ] Every `run_in_background=true` call-site in SKILL.md (and workflow phases that describe spawning) explicitly names the watchdog Flavor (A or B) and the thresholds used.
- [ ] State schema (STATE.md or equivalent) adds the fields from "State schema additions" above.
- [ ] Termination vocabulary includes `timed_out_heartbeat` / `hung_killed` labels so the coordinator has an honest outcome to emit when a watchdog fires.
- [ ] Self-Review Checklist adds: "Every background spawn has a watchdog armed with thresholds appropriate to the agent tier."
- [ ] Golden Rules adds: "TaskOutput status is not evidence of progress. Output-file mtime is. Watchdog fires on mtime age, not on status."
- [ ] Skills that override default thresholds document the override and the rationale inline.

---

## Divergence policy

Skills that legitimately need a different liveness signal (e.g. a skill whose subagents don't write to a file — rare) must document the override explicitly, specifying what the ground-truth signal actually is for that skill. Silent divergence back to "trust status" is the failure mode this file exists to prevent.
