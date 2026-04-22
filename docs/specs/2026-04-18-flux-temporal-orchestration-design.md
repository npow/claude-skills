# Flux: Temporal-backed orchestration for Claude Code skills

**Status:** SUPERSEDED 2026-04-21 by [`2026-04-21-deep-qa-temporal-design.md`](2026-04-21-deep-qa-temporal-design.md). The user re-scoped the work from a hook-adapter (keep SKILL.md coordinator, add Temporal guarantees via hooks) to a full workflow rewrite (coordinator logic moves into Python Temporal workflows). Flux's non-goal #1 (cross-session workflow durability) became an in-scope goal; the hook approach can't deliver it. Do NOT implement this spec.
**Author:** npow + Claude (brainstorming session 2026-04-18)
**Type:** superseded
**Companion:** `2026-04-18-custom-harness-evaluation-design.md` (P4 eval)

## Context

Coordinator skills (deep-research, deep-design, deep-qa, deep-idea, deep-debug, consensus-plan, autopilot, ship-it) spawn long-running background agents via `Agent(run_in_background=true)` and poll with `TaskOutput(block=true)`. A bug surfaced 2026-04-17 where a deep-research agent silently died mid-run; the coordinator blocked indefinitely because `TaskOutput status: "running"` only signals "PID in the runtime's task table" — not "process making progress." 18 hours passed before the user noticed.

Root cause analysis (see brainstorming session transcript): the Claude Code runtime tracks process liveness (PID alive), not progress liveness (output growing). No heartbeat, no mtime check, no CPU sanity check, no timeout on `Agent` spawns. Silent death is undetectable from the coordinator's vantage point.

This affects every skill using `run_in_background=true` — at minimum 7 skills today, plus every future coordinator. The symptom is "all my skills that use coordination are vulnerable" (user, verbatim).

**Goal:** introduce Temporal-grade guarantees — enforced start-to-close timeouts, heartbeat-based death detection, automatic retries with backoff, idempotent activity IDs, durable activity state — to all coordinator skills with a thin adapter layer that keeps the Claude Code skill format unchanged.

**Non-goal:** cross-session workflow durability, deterministic LLM replay, or moving off Claude Code. Those are the P4 eval's territory (see companion spec).

## Design decisions

### Architecture (one diagram)

```
┌──────────────────────── Claude Code session ──────────────────────┐
│                                                                     │
│  Claude (coordinator reading SKILL.md)                              │
│    │                                                                │
│    ├── Agent(run_in_background=true, prompt=...)                    │
│    │     ↓                                                          │
│    │  [PreToolUse hook: flux-pretool-agent]                         │
│    │     ↓                                                          │
│    │  ┌─────────────────────────────────────┐                       │
│    │  │  Temporal server (dev mode, SQLite) │◄───┐                  │
│    │  │  - StartActivity registered         │    │                  │
│    │  │  - start_to_close, heartbeat_timeout│    │                  │
│    │  │  - retry policy stored              │    │                  │
│    │  └─────────────────────────────────────┘    │                  │
│    │                                              │                 │
│    │     Agent tool actually spawns (PID X)       │                 │
│    │     ↓                                        │                 │
│    │  [PostToolUse hook: flux-posttool-agent]    │                  │
│    │     ↓ links task_id ↔ activity_id           │                  │
│    │                                              │                 │
│    │                                              │                 │
│    ├── (meanwhile, spawned at session start:)    │                  │
│    │  Bash(run_in_background=true):              │                  │
│    │  flux-heartbeat-daemon.py                   │                  │
│    │    - polls all output files' mtimes         │                  │
│    │    - reports heartbeats to Temporal ────────┘                  │
│    │                                                                │
│    ├── TaskOutput(task_id, block=true, timeout=300)                 │
│    │     ↓                                                          │
│    │  [PreToolUse hook: flux-pretool-taskoutput]                    │
│    │     ↓ queries Temporal for activity status                     │
│    │     ↓ if timed_out: runtime calls TaskStop, returns synthetic  │
│    │     ↓   failure to coordinator                                 │
│    │     ↓ else: proceeds to raw TaskOutput                         │
│    │                                                                │
│  Coordinator receives: completed | timed_out_start_to_close         │
│                      | timed_out_heartbeat | failed_terminal        │
│                      | retrying                                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Temporal's role:** durable source of truth for activity lifecycle. Owns the state machine, retry policy, heartbeat timeout enforcement, visibility.

**Flux's role:** adapter. Translates Claude Code tool calls into Temporal SDK calls. Translates Temporal verdicts back into tool-call outcomes.

**Skills' role:** emit declarative metadata (timeouts, retry policy) via annotations in state.json. No workflow code. Behavior unchanged for happy-path operation.

### Components

**1. Temporal dev server**
- Binary: `temporal server start-dev` (Temporal CLI, ~30MB download, self-contained)
- Backed by SQLite; no external DB required
- Runs on localhost, default ports (7233 gRPC, 8233 UI)
- Started lazily by first hook invocation; shared across Claude Code sessions on same host
- User-space process; no daemon/service setup required
- User installs via `brew install temporal` (macOS) or equivalent; flux hooks detect absence and surface install instructions

**2. Hooks (bash wrappers invoking Python)**
Located in `~/.claude/skills/.shared/flux/hooks/`:

| Hook | Trigger | Purpose | Rough size |
|---|---|---|---|
| `flux-pretool-agent.sh` | PreToolUse on `Agent` with `run_in_background=true` | Register activity in Temporal before spawn; read skill annotations for timeouts | ~50 lines |
| `flux-posttool-agent.sh` | PostToolUse on same | Link Claude's task_id to Temporal's activity_id in state | ~30 lines |
| `flux-pretool-taskoutput.sh` | PreToolUse on `TaskOutput` with `block=true` | Query Temporal for activity status; if timed_out, short-circuit with TaskStop + synthetic failure response | ~60 lines |
| `flux-posttool-taskoutput.sh` | PostToolUse on same | Record activity completion / failure in Temporal | ~30 lines |

Hooks call a shared Python CLI (`flux` command) so logic lives in Python, not bash. Bash wrappers exist only because Claude Code hooks invoke shell.

**3. Flux CLI (Python, installed as editable package)**
- `flux activity start --id --prompt-file --start-to-close --heartbeat-timeout --retry-max --retry-backoff --idempotency-key` — registers activity with Temporal, returns activity_id
- `flux activity link --task-id --activity-id` — records mapping after Agent spawns
- `flux activity status --id` — returns structured status
- `flux activity cancel --id` — triggers graceful cancellation via Temporal
- `flux activity wait --id --timeout` — blocks until activity reaches terminal state or timeout
- `flux heartbeat --id --last-write-mtime` — reports heartbeat to Temporal
- `flux status --run-id` — dumps all activities for a run

Implementation: `~/.claude/skills/.shared/flux/src/flux/` — Python package with `temporalio` SDK dependency.

**4. Heartbeat daemon (Python)**
Spawned once per Claude Code session via `Bash(run_in_background=true)` from a `SessionStart` hook. Role:
- Tails the state.json `activities` registry every 5s
- For each active activity, checks mtime of its output file
- If mtime hasn't advanced in ≥ heartbeat_interval, reports it to Temporal as heartbeat failure
- Temporal then fires `HeartbeatTimeoutError` → triggers retry policy

Lives in `~/.claude/skills/.shared/flux/src/flux_daemon.py`. Runs until session ends. Auto-respawned if it dies (detected by next hook invocation).

**5. Skill annotations (minimal)**
Each coordinator skill gains optional per-activity-type metadata in its STATE.md schema. Example addition to deep-qa STATE.md:

```json
"activities": {
  "hyp_angle_agent": {
    "flux_timeouts": {
      "start_to_close_s": 180,
      "heartbeat_timeout_s": 45,
      "schedule_to_close_s": 900
    },
    "flux_retry_policy": {
      "initial_interval_s": 5,
      "backoff_coefficient": 2.0,
      "max_interval_s": 60,
      "max_attempts": 2,
      "non_retryable_errors": ["InvalidInputError"]
    }
  }
}
```

Skills that don't add annotations get defaults (120s start_to_close, 60s heartbeat, 1 retry). No breaking changes.

### What is guaranteed (and what is not)

**Guaranteed:**
1. **Bounded `TaskOutput` wait** — hook short-circuits if Temporal has already declared the activity timed_out; `timeout` parameter on `TaskOutput` is lower bound.
2. **Bounded activity runtime** — Temporal fires timeout → hook runs `TaskStop` → Claude's task exits. No agent runs longer than `start_to_close`.
3. **Silent-death detection within `heartbeat_timeout` + 1 poll interval** — typically 45-60s. Was 18 hours.
4. **Automatic retry for transient failures** — Temporal re-fires activity per retry policy; coordinator sees retries transparently until terminal success/failure.
5. **Idempotent activity IDs** — same `idempotency-key` on resume → Temporal returns prior result; no double-spawn.
6. **Durable activity state across coordinator session** — Temporal persists to SQLite; if Claude Code session dies, next session reads Temporal for activity history.

**Not guaranteed (out of scope):**
1. **Deterministic workflow replay** — Claude itself (the coordinator) is non-deterministic. If coordinator Claude crashes, resumption re-reads state.json + Temporal activity history, but the coordinator's LLM may make different decisions on resume. Mitigated by storing coordinator decisions in state.json so resume is as close to idempotent as possible.
2. **Cross-session workflows** — activities run within one Claude Code session; they don't span sessions (that's a P4 concern).
3. **Signals / queries from external clients** — Temporal supports these, but no hook path currently injects them into Claude; out of scope.
4. **Protection against the heartbeat daemon itself dying** — if daemon crashes mid-run, heartbeats stop flowing; Temporal will eventually time out activities as `heartbeat_timeout`. Self-healing: next hook invocation detects daemon absence and respawns it.

### Graceful degradation

When Temporal server is unreachable (not installed, crashed, network issue):

1. Hook detects Temporal connection failure
2. Hook logs warning to `~/.claude/skills/.shared/flux/log/degraded-{session_id}.log`
3. Hook falls through to raw tool call (Claude proceeds as if flux wasn't there)
4. Synthesizes a "flux disabled" banner in the coordinator's tool-result output so Claude knows guarantees aren't active

Coordinator skills DO NOT hard-depend on flux. Every skill works without Temporal running, just without Temporal-grade guarantees — same failure mode as today, with a log entry.

### Rollout plan

**Phase A: infrastructure (day 1-2)**
1. Install Temporal CLI, confirm `temporal server start-dev` works locally
2. Scaffold `~/.claude/skills/.shared/flux/` — Python package, bash hooks, daemon
3. Write unit tests for flux CLI commands against a local Temporal dev server
4. Configure hooks in `~/.claude/settings.json` (`PreToolUse` / `PostToolUse` / `SessionStart`)

**Phase B: first skill migration (day 2)**
1. Pick deep-debug (newest, smallest, well-specified)
2. Add activity annotations to its STATE.md schema
3. Update SKILL.md Phase 3b (judge spawn) and Phase 5.5 (drain) to reference flux invocations in prose
4. Integration test: full deep-debug run on a fabricated bug; verify Temporal UI shows activity history with retries/heartbeats correctly

**Phase C: remaining skills (day 3-4)**
Migrate in order: deep-qa, deep-research, deep-design, deep-idea, consensus-plan. Each migration is ~30-60 min.

**Phase D: failure-injection tests (day 4)**
1. Kill Temporal mid-run → verify graceful degradation
2. Kill spawned agent → verify heartbeat detection + retry
3. Kill heartbeat daemon → verify auto-respawn
4. Kill coordinator Claude session → verify Temporal retains activity state
5. Run 20-cycle longevity test to surface rare bugs

**Phase E: documentation (day 4-5)**
1. `~/.claude/skills/.shared/flux/README.md` — user-facing
2. Update relevant skills' SKILL.md to reference flux briefly
3. Write migration template for future coordinator skills

### Files to be created / modified

**New:**
- `~/.claude/skills/.shared/flux/pyproject.toml`
- `~/.claude/skills/.shared/flux/src/flux/__init__.py`
- `~/.claude/skills/.shared/flux/src/flux/cli.py`
- `~/.claude/skills/.shared/flux/src/flux/activity.py`
- `~/.claude/skills/.shared/flux/src/flux/heartbeat_daemon.py`
- `~/.claude/skills/.shared/flux/src/flux/config.py`
- `~/.claude/skills/.shared/flux/hooks/flux-pretool-agent.sh`
- `~/.claude/skills/.shared/flux/hooks/flux-posttool-agent.sh`
- `~/.claude/skills/.shared/flux/hooks/flux-pretool-taskoutput.sh`
- `~/.claude/skills/.shared/flux/hooks/flux-posttool-taskoutput.sh`
- `~/.claude/skills/.shared/flux/hooks/flux-session-start.sh`
- `~/.claude/skills/.shared/flux/README.md`
- `~/.claude/skills/.shared/flux/tests/*` (pytest suite)
- `~/.claude/skills/docs/specs/2026-04-18-flux-skill-migration-template.md` — reusable template

**Modified:**
- `~/.claude/settings.json` — hook configuration entries
- `~/.claude/skills/deep-debug/STATE.md` — add `activities` metadata section
- `~/.claude/skills/deep-debug/SKILL.md` — annotate spawn sections with flux timeouts
- Same for deep-qa, deep-research, deep-design, deep-idea, consensus-plan

**Not modified:**
- Any existing SKILL.md workflow text (hooks are transparent)
- Any existing FORMAT.md, DIMENSIONS.md, etc.
- Any skill that doesn't use `run_in_background=true`

### Test strategy

1. **Unit tests** (pytest): flux CLI commands against a local Temporal dev server
2. **Hook integration tests**: exercise each hook with fabricated tool-call events (test harness provided by Temporal SDK)
3. **Skill end-to-end tests**: run deep-debug on a seeded bug, verify full cycle succeeds; run deep-qa on a seeded doc, verify batched judge + heartbeat detection
4. **Failure injection**: the 5 scenarios in Phase D above
5. **Longevity**: 20-run batch on varied skill invocations; scan logs for warnings
6. **Migration-blast-radius test**: run each migrated skill end-to-end; measure runtime overhead vs. pre-migration baseline (expect <5% overhead)

### Dependencies / risks

**Dependencies:**
- `temporalio` Python SDK (Temporal Technologies; Apache 2.0; mature)
- Temporal CLI binary (same source)
- Python 3.10+ (already required by other skills)

**Risks:**
- **Hook latency** — each tool call adds 50-200ms. Measured risk: flux-pretool-taskoutput is invoked before every Agent spawn and every TaskOutput poll. For skills that loop frequently (autopilot?), this adds up. Mitigation: benchmark on deep-debug during Phase D; if intolerable, batch queries or move to daemon-based cache.
- **Temporal server startup** — first hook invocation must ensure server is running. Cold start is 1-3s. Mitigation: `flux-session-start.sh` checks + starts server once per session.
- **Dependency injection via hooks** — hooks are configured globally in settings.json. If hooks break, ALL tool calls are affected. Mitigation: every hook script has a top-level try/except that logs to stderr and exits 0 (non-blocking) on any failure; graceful degradation fully tested in Phase D.
- **SQLite concurrent access** — Temporal dev-mode uses SQLite, which has limited concurrent-writer support. Two concurrent Claude Code sessions may conflict. Mitigation: document "one session at a time for now" in README; if needed later, move Temporal to Postgres dev mode.
- **Schema changes** — if Temporal SDK upgrades break API, flux breaks. Mitigation: pin `temporalio` version in pyproject.toml; test upgrades before bumping.

### Success criteria

1. **Functional:** A deliberately-hung agent (e.g. `sleep 99999` in a spawn prompt) is detected within 60s and retried per policy
2. **Functional:** A coordinator Claude session killed mid-run can be resumed in a new session with no activity loss (Temporal retains state)
3. **Performance:** Per-tool-call overhead < 200ms p95 on a modern dev machine
4. **Graceful:** Running any migrated skill with `temporal server` stopped produces a `degraded-...log` entry AND the skill completes normally (without guarantees)
5. **Coverage:** All 6 coordinator skills migrated; each has a test run verifying no regressions vs. pre-migration behavior
6. **Documentation:** flux/README.md is sufficient for a new coordinator skill author to migrate without asking questions

## Open decisions (for user review)

1. **Hook installation location** — global (`~/.claude/settings.json`) vs per-project. Proposed: global. Reversal cost: remove hook block + restart Claude Code.
2. **Temporal version** — pin at latest stable at build time. Proposed: pin `temporalio==1.8.x` series. Easy to bump.
3. **Is Python 3.10+ acceptable?** — existing skills already use it; confirming.
4. **Heartbeat daemon respawn policy** — detect-and-respawn on every hook invocation, or run a separate supervisor? Proposed: detect-and-respawn (simpler, good-enough).
5. **Default timeouts for skills that don't annotate** — Proposed: 120s start_to_close, 60s heartbeat_timeout, 1 retry. Conservative enough to not cause regressions; loose enough to catch real hangs.

## Migration template (attach to each skill)

Every migrated skill needs these three changes; anything beyond is skill-specific:

1. **STATE.md** — add `activities: {}` section with per-activity-type flux annotations
2. **SKILL.md** — prepend a short note to the Execution Model section: "Background spawns are managed by flux; see STATE.md `activities` for timeouts/retry policy."
3. **No code changes** — hooks intercept spawn/poll transparently. Unless the skill has custom polling logic that bypasses TaskOutput (rare), no SKILL.md workflow edits required.

---

## Post-spec-review workflow

After user approves this spec:
1. Invoke `superpowers:writing-plans` to create implementation plan
2. Plan gates Phase A/B/C/D/E with independent verification per phase
3. Implementation proceeds per plan, with user review at phase boundaries
