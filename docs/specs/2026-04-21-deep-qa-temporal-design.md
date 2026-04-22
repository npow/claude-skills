# skillflow + deep-qa-temporal: Temporal-backed workflow framework (pilot)

**Status:** design, pending user review
**Author:** npow + Claude (brainstorming session 2026-04-21)
**Type:** framework + first pilot skill
**Supersedes:** `2026-04-18-flux-temporal-orchestration-design.md` (flux hook adapter approach)
**Companion:** `2026-04-18-custom-harness-evaluation-design.md` (P4 eval)
**Target repo:** new standalone project on personal GitHub (provider-agnostic; no Netflix coupling required)

## Context

Ten coordination skills in `~/.claude/skills/` share a file-based state machine that orchestrates parallel subagents: `deep-qa`, `deep-debug`, `deep-research`, `deep-design`, `deep-plan`, `proposal-reviewer`, `team`, `autopilot`, `loop-until-done`, `flaky-test-diagnoser`. Each has an Opus coordinator reading SKILL.md that spawns Haiku/Sonnet subagents via `Agent(run_in_background=true)` and synchronises via `state.json` + `STRUCTURED_OUTPUT_START/END` markers.

The file-based model has known weaknesses:

1. **No cross-session durability.** Claude Code dies mid-run → orchestration state is fragmented across state.json, runtime task tables, and conversation context. Resume is prompt-dependent and imperfect.
2. **PID-liveness ≠ progress.** `TaskOutput status: "running"` says nothing about whether the subagent is making progress. The 2026-04-17 bug: an 18-hour silent death before the user noticed. The mtime-watchdog in `_shared/subagent-watchdog.md` closes this with file-system heuristics but it's a workaround, not a guarantee.
3. **Retries are coordinator-authored prose.** Each skill has ad-hoc retry logic in SKILL.md. Inconsistent between skills; brittle under LLM drift.
4. **No visibility.** No cross-skill ledger; each skill's state.json lives in a run directory. Want to know "what's in flight right now?" → shell grep.

The **flux design (2026-04-18)** addressed #2 and #3 via Claude Code hooks that register Agent spawns as Temporal activities. It explicitly punted on #1 ("not goal: cross-session workflow durability") and kept the Opus coordinator in SKILL.md markdown. Flux is a state/retry shim, not a workflow rewrite.

**This spec proposes superseding flux.** The Opus-in-markdown coordinator is the root cause of #1, and every per-skill retry/convergence pattern is a workaround for having no formal workflow definition. Moving coordination into Python Temporal workflows — with subagents as activities, not Agent tool calls — gives all four properties as by-products of the Temporal model.

## Goal

Ship **skillflow**, a small Temporal-backed framework for Claude Code skills, with **deep-qa-temporal** as the first skill built on it. The framework is open-source-ready (provider-agnostic, no Netflix internal APIs required); the pilot skill proves the framework's shape is correct before additional coordination skills migrate onto it.

**Success = a user types `/deep-qa-temporal ./some-artifact.md`, does unrelated work, and 20 minutes later sees findings surfaced in their conversation — even if Claude Code was restarted mid-run. The plumbing is in `skillflow` and is reusable for the remaining 9 coordination skills.**

## Non-goals (for the pilot)

1. **Migrating the other 9 skills.** Pilot proves the framework plus one skill; later specs migrate each remaining skill.
2. **Rich primitive library (FanoutRound, JudgePanel, etc.).** skillflow ships with: CLI dispatcher, auto-spawning worker, Anthropic-SDK transport, structured-output parser, INBOX mirror, SessionStart-hook auto-installer. That's the minimum surface to make any Temporal-backed skill work. Higher-level primitives wait for skill #2 to reveal which are real.
3. **Child workflows for long-lived specialists.** Swarm has them (PatternDetector, LLMCritic, ResourceMonitor); deep-qa's background judges/summaries are one-shots. No child workflows in the pilot.
4. **Replay determinism of LLM outputs.** Activities use idempotency keys — same input → Temporal returns cached result. LLM outputs themselves aren't bit-identical across retries; we rely on structured-output verdicts being stable enough for consistent downstream decisions.
5. **Migration of existing state.json format.** Temporal is the new source of truth; the disk mirror uses its own layout. No import of historical runs.

## Key decisions

### D1. Full workflow rewrite, not an adapter

Coordinator logic (phases, frontier, dedup, coverage, termination) moves from SKILL.md prose into Python workflow methods. The deep-qa-temporal skill directory holds a thin launcher (~100 lines) that wraps `skillflow launch deep-qa` CLI invocation in a non-blocking bash task. User sees the same prompts/outputs they see today; the orchestration is Python underneath.

This supersedes flux's hook-adapter approach. Flux kept Claude-as-coordinator, which meant every resume re-prompted an LLM to reconstruct context — not durable in the strong sense we want.

### D2. Subagent transport: Anthropic SDK by default, model gateway optional, `claude -p` where tools needed

Default transport is the stock `anthropic` Python SDK hitting `api.anthropic.com` with the user's `ANTHROPIC_API_KEY`. Provider-agnostic, zero Netflix dependency, works for any Anthropic user.

Optional overrides via env vars (no code change):
- `ANTHROPIC_BASE_URL=http://mgp.local.dev.netflix.net:9123/proxy/npowws` + `ANTHROPIC_API_KEY=sk-dummy` — routes through Netflix model gateway (verified reachable 2026-04-21: localhost-bound, `sbn-dev-agent` injects Metatron auth; any Temporal worker running as the same user has identical access).
- Future: OpenAI-compatible endpoint, Bedrock, etc. — all via base_url.

Activities that need Claude Code's toolbelt (Bash/Grep/Read for live code exploration — relevant for deep-qa's `--type code` critics and `--type research` fact-verifier) fall back to spawning a `claude -p` subprocess. The activity abstraction hides the transport choice behind `spawn_subagent(role, inputs, tools_needed)`.

**Preflight on worker startup:** probe the configured transport (`/v1/messages` cheap call) and abort with a clear install-hint message if unreachable. Don't silently fail activities.

Per-activity-kind routing in deep-qa-temporal:

| Activity | Transport | Rationale |
|---|---|---|
| Dimension discovery | anthropic-sdk (Sonnet) | Reads artifact, emits angles. No tool use. |
| Critic (doc / research / skill types) | anthropic-sdk (Haiku) | Reads artifact, emits defects. No tool use. |
| Critic (code type) | `claude -p` (Haiku) | Needs Grep/Read for caller analysis. |
| Severity judge (pass-1 blind, pass-2 informed) | anthropic-sdk (Haiku) | Reads defect data, emits verdict. No tool use. |
| Coordinator summary | anthropic-sdk (Haiku) | Reads state snapshot, emits prose. No tool use. |
| Rationalization auditor | anthropic-sdk (Sonnet) | Reads draft report + judge verdicts, emits fidelity score. No tool use. |
| Fact verifier (research type) | `claude -p` (Haiku) | Needs WebFetch for URL spot-checks. |

### D3. Headless daemon with auto-spawn

The skillflow worker runs as a long-lived user daemon. **On first `skillflow launch`, the CLI checks if a worker is polling the task queue (Temporal `describe_task_queue`); if no pollers, it forks `skillflow worker --detach` silently and proceeds.** No manual `worker &` step required. Worker survives Claude Code death and subsequent CLI invocations reuse the same process.

Explicit control also available:
- `skillflow worker` — foreground, for debugging
- `skillflow worker --detach` — background-daemonised (what auto-spawn uses)
- `skillflow worker --stop` — graceful shutdown

Auto-spawned workers log to `~/.skillflow/worker-{pid}.log` so users can debug if things hang.

### D4. Non-blocking default UX with automatic surfacing

User invokes `/deep-qa-temporal <artifact>`; SKILL.md runs `Bash(run_in_background=true, command="skillflow launch deep-qa --await <artifact>")`. Claude Code's turn ends immediately with workflow ID + reassurance. User does other work.

When the workflow completes (seconds or hours later), the `--await` CLI exits → Claude Code fires a `<task-notification>` → Claude reads the final report file and posts findings as a new turn.

No polling. No hook. The bash-task completion mechanism already exists.

### D5. Four-layer result-surfacing safety net

Rationale: "durable compute that never surfaces results" is the failure mode we must prevent. Layered defences:

1. **In-session notification** (D4) — the happy path.
2. **`~/.skillflow/INBOX.md`** — append-only inbox file. One line per terminal transition (completed, failed, worker_killed, etc.). User can `cat ~/.skillflow/INBOX.md` anytime.
3. **SessionStart hook (auto-installed)** — every new Claude Code session prepends unread INBOX entries to context. Catches crash-recovery case where in-session notification was lost with the session.
4. **Desktop notification** (default-on, flag `--no-notify` to disable) — workflow's on-terminate activity shells platform-appropriate notifier (`osascript` on macOS, `notify-send` on Linux). Ping independent of Claude Code.

Every terminal label — success or failure — writes its own INBOX line. "Silent waste" is only possible if the user rm's `~/.skillflow/` and ignores the desktop notification.

### D6. Auto-install hook on first launch

The SessionStart hook entry in `~/.claude/settings.json` is idempotently installed by the CLI on **first** `skillflow launch` — no separate `install-hook` step. CLI reads settings.json, checks for the `skillflow-session-start` hook entry, appends if missing, writes back. Idempotent: subsequent launches are no-ops.

The hook script (`skillflow hook session-start`) reads `~/.skillflow/INBOX.md`, formats unread entries as a context preamble, prints to stdout. On failure it prints nothing and exits 0 — never blocks session start.

Uninstall via `skillflow hook uninstall` (removes the entry from settings.json). INBOX file is independent of hook presence.

### D7. Workspace-drift warning, not tamper-kill

Swarm kills the mission if locked files mutate mid-run. deep-qa is routinely used on work-in-progress, so kill-on-edit is too strict. Instead: record `git rev-parse HEAD` + `git status --porcelain` at launch; re-check before each round; if diverged, emit a `workspace_drift` finding in the QA report and continue. User sees the warning in the final report. Flag `--strict-lock` flips to abort-on-drift for users who want swarm-style paranoia.

### D8. Artifact snapshot, not live-read

`skillflow launch deep-qa` copies the target artifact to `~/.skillflow/runs/{run_id}/artifact.md` at launch. All critics read the snapshot, not the live path. Matches today's `deep-qa` phase 2 behaviour.

## Architecture

### Repo structure (new personal GitHub project: `skillflow`)

```
skillflow/                                 # personal GitHub, MIT license
├── pyproject.toml                         # installable as `pip install skillflow`
├── README.md
├── LICENSE
├── .github/workflows/ci.yml               # pytest on push
├── skillflow/                             # framework
│  ├── __init__.py
│  ├── cli.py                              # main entry: skillflow <subcommand>
│  ├── worker.py                           # auto-spawnable worker daemon
│  ├── registry.py                         # skill discovery + registration
│  ├── transport/
│  │  ├── __init__.py
│  │  ├── anthropic_sdk.py                 # default provider
│  │  ├── claude_cli.py                    # claude -p subprocess helper
│  │  └── structured_output.py             # STRUCTURED_OUTPUT_START/END parser
│  ├── durable/
│  │  ├── activities.py                    # shared base activities: spawn_subagent, write_artifact, emit_finding
│  │  ├── retry_policies.py                # shared retry policies (Haiku/Sonnet/subprocess tiers)
│  │  └── state.py                         # base WorkflowState dataclass
│  ├── inbox.py                            # INBOX.md read/write
│  ├── hook.py                             # hook installer + session-start reader
│  └── notify.py                           # desktop notification (macOS/Linux)
├── skills/
│  └── deep_qa/                            # first skill lives here as a sub-package
│     ├── __init__.py
│     ├── workflow.py                      # DeepQaWorkflow
│     ├── state.py                         # DeepQaState, Angle, Defect, JudgeBatch
│     ├── activities.py                    # deep-qa-specific: spawn_critic, spawn_judge, etc.
│     ├── dimensions.py                    # dimension catalog (ported from DIMENSIONS.md)
│     └── prompts/                         # jinja templates for subagent prompts
│        ├── critic_doc.md
│        ├── critic_code.md
│        ├── critic_research.md
│        ├── critic_skill.md
│        ├── judge_blind.md
│        ├── judge_informed.md
│        ├── summary.md
│        └── auditor.md
└── tests/
   ├── test_cli.py
   ├── test_transport.py
   ├── test_inbox.py
   ├── test_hook.py
   └── skills/test_deep_qa_workflow.py
```

### Claude Code skill directory (consumer side)

```
~/.claude/skills/deep-qa-temporal/
├── SKILL.md    (launcher, ~100 lines — invokes `skillflow launch deep-qa`)
└── DIMENSIONS.md (copy from deep-qa, for parity reference during transition)
```

The Claude Code skill is a thin shim that shells out to the installed `skillflow` CLI. User installs skillflow via `pip install skillflow` (or `pipx install skillflow`); the skill directory references it.

### Runtime

```
User types /deep-qa-temporal ./spec.md
        │
        ▼
SKILL.md runs:
  Bash(run_in_background=true,
       command="skillflow launch deep-qa --await ./spec.md")
        │
        ▼
skillflow CLI:
  1. Preflight: Temporal reachable? Transport reachable?
  2. Check/install SessionStart hook (idempotent)
  3. Check worker polling task queue; if none, fork `skillflow worker --detach`
  4. Snapshot artifact → ~/.skillflow/runs/{run_id}/artifact.md
  5. git snapshot (drift detection seed)
  6. client.start_workflow(DeepQaWorkflow, QaRequest, id=run_id)
  7. Block on workflow.result() (--await flag)
        │
        ▼
Temporal dev server (localhost:7233)
        │
        ▼
skillflow worker daemon
        │
        └── DeepQaWorkflow (phases 0-6, same shape as existing deep-qa)
                │
                └── activities: spawn_subagent, write_artifact, emit_finding, …
                      (each uses skillflow.transport dispatcher internally)
        │
        ▼
Workflow returns FinalReport → emit_finding appends to ~/.skillflow/INBOX.md
        │
        ▼
CLI --await exits with report path on stdout
        │
        ▼
Background bash task completes → <task-notification> fires
        │
        ▼
Claude Code turn resumes → posts findings to user
```

### State schema (deep-qa-specific, extends skillflow base)

`DeepQaState` extends skillflow's base `WorkflowState` (generation counter, activity ledger, cost tracking). Mirrored to `~/.skillflow/runs/{run_id}/state.json` after each mutation.

```python
@dataclass
class DeepQaState(WorkflowState):         # base adds: generation, activity_outcomes, cost_running_total
    run_id: str                           # inherited shape; deep-qa just binds values
    artifact_path: str
    artifact_type: Literal["doc", "code", "research", "skill"]
    max_rounds: int
    hard_stop: int
    current_round: int
    current_phase: str
    workspace_snapshot: WorkspaceSnapshot
    drift_events: list[DriftEvent]
    frontier: list[Angle]
    explored_angles: list[Angle]
    defects: list[Defect]
    judge_batches: list[JudgeBatch]
    summaries: list[SummaryRef]
    required_categories_covered: dict[str, bool]
    rounds_without_new_dimensions: int
    termination_label: Optional[str]
```

### Activity contracts

Shared invariants enforced by skillflow.durable.activities decorator:

1. **Idempotency key:** `f"{run_id}:{phase}:{role}:{iteration}:{item_id}"`. Temporal caches results per key; retries return cached output.
2. **Input via file path, not inline.** Each activity reads its file at body time.
3. **Output via structured markers.** `STRUCTURED_OUTPUT_START/END` from `_shared/execution-model-contracts.md` §3. Parser in `skillflow.transport.structured_output`.
4. **Heartbeat on every stream chunk / stdout line.** Temporal's heartbeat-timeout catches stalls.
5. **Timeouts:**
   - `start_to_close_timeout`: 180s Haiku, 300s Sonnet, 600s subprocess
   - `heartbeat_timeout`: 60s
   - `schedule_to_close_timeout`: 30min
6. **Retry policy:** 2 attempts, exponential backoff (5s → 10s → 20s). No retry on `InvalidInputError` / `MalformedResponseError`.

### Phase mapping (deep-qa's 6 phases → workflow methods)

| Phase | Workflow method | Activities used |
|---|---|---|
| 0. Input validation | `_phase_0_validate()` | `write_artifact` |
| 1. Dimension discovery | `_phase_1_dimensions()` | `spawn_dim_discover` |
| 2. Initialize state | `_phase_2_init()` | `write_artifact`, `snapshot_workspace` |
| 3. QA rounds | `_phase_3_rounds()` | `spawn_critic`, `spawn_judge`, `spawn_summary` |
| 4. Fact verification | `_phase_4_verify()` | `spawn_verifier` |
| 5. Termination check | `_phase_5_terminate()` | (none) |
| 5.5. Pass-2 judges + auditor | `_phase_5_5_pass2()` | `spawn_judge`, `spawn_auditor` |
| 6. Synthesis | `_phase_6_synthesize()` | `write_artifact`, `emit_finding` |

### Failure handling

| Failure | Detection | Response |
|---|---|---|
| Transport 5xx | raised exception | Retry per policy |
| Transport 400 (malformed prompt) | `InvalidInputError` | No retry; workflow emits `spawn_failed`; degrades frontier |
| Subagent produces no structured block | `MalformedResponseError` | Fail-safe to WORST legal value (e.g., `SEVERITY critical`); log |
| `claude -p` dies | heartbeat lapse | Retry per policy |
| Worker daemon dies mid-run | Temporal records activity timeout | On next worker start (manually or auto-spawn), workflow resumes from last completed activity |
| User restarts Claude Code | bash task dies (losing `--await` notification hook) | SessionStart hook surfaces INBOX entries on next start |
| Workspace drift | `snapshot_workspace` between rounds | Emit `workspace_drift` finding; continue (unless `--strict-lock`) |
| Hard stop reached | Workflow check at top of `_phase_3_rounds()` | Immediate termination; label `"Hard stop at round {N}"` |

### CLI reference

```
skillflow launch <skill> <args...> [--await] [--no-notify] [--strict-lock]
skillflow list [--running | --completed | --failed]
skillflow show <run_id>                 # dump final report
skillflow logs <run_id>                 # activity logs for debugging
skillflow watch <run_id>                # stream findings live
skillflow inbox                         # show unread INBOX.md entries
skillflow dismiss <run_id>              # clear from INBOX
skillflow abort <run_id> [--reason R]
skillflow worker [--detach | --stop]    # daemon lifecycle
skillflow hook install | uninstall      # hook management (install is idempotent + automatic)
skillflow doctor                        # preflight check: Temporal, transport, worker, hook
```

Skill-specific flags pass through positionally: `skillflow launch deep-qa --type code --diff HEAD~1 ./src/`

### Migration & coexistence

- `deep-qa-temporal/` Claude Code skill directory sits next to existing `deep-qa/`; both work.
- Two CLIs: today's `deep-qa` (file-based) runs via the old skill. `/deep-qa-temporal` shells to `skillflow`.
- `~/.skillflow/` is the shared state root. Independent from any prior `deep-qa-{run_id}/` scratch directories.
- After the pilot stabilises, each subsequent skill migration adds a new package under `skills/` and a thin Claude Code launcher under `~/.claude/skills/{skill-name}-temporal/`.

### Flux relationship

This spec **supersedes** `2026-04-18-flux-temporal-orchestration-design.md` (already marked as such). The flux adapter approach was scoped to symptoms #2–3 only. skillflow targets all four symptoms by making Temporal the orchestrator, not an observer. No flux code to delete — no implementation PRs landed.

## UX

### Launch (happy path)

```
user: /deep-qa-temporal ./spec.md

Claude:
  [calls Bash(run_in_background=true,
              command="skillflow launch deep-qa --await ./spec.md")]

  Launched deep-qa-20260421-143322. Running in the background on the
  skillflow worker. I'll automatically surface findings when it completes.
  You can do other work; the workflow survives session crashes.
```

### Auto-surface on completion

```
[20 minutes later, user chatting about something unrelated]

<task-notification: skillflow launch completed>

Claude:
  deep-qa-20260421-143322 completed: 2 critical, 4 major, 7 minor defects
  across 4 QA dimensions. Full report at ~/.skillflow/runs/.../qa-report.md.

  Top findings:
  1. [critical] …
  2. [critical] …
  …
```

### Crash recovery via SessionStart hook

```
user: [opens new Claude Code session after yesterday's crash]

<session-start-hook context:
 Unread skillflow runs:
 - deep-qa-20260421-143322 COMPLETED  spec.md  2 crit, 4 maj  skillflow show 143322
 - deep-qa-20260421-190001 FAILED   auth.py  worker_killed  skillflow logs 190001
>

Claude (on first user message):
  Two skillflow runs finished since we last talked — one succeeded, one
  failed. Want the successful report now, or fix the failure first?
```

## Test strategy

1. **Unit (pytest, sub-second):** framework state machine; INBOX read/write; hook install idempotence; transport parsers; drift-detection logic; auto-spawn race protection.
2. **Workflow tests (Temporal `testing.WorkflowEnvironment`, time-skipped):** phase transitions; retry behaviour under activity failure; resume-after-crash scenarios.
3. **Activity tests (mocked transports):** `spawn_critic` parses structured output; `write_artifact` produces expected JSON.
4. **End-to-end (real Temporal dev server, real Anthropic API):** deep-qa-temporal on a fabricated doc artifact; verify INBOX entry; verify session-restart picks up in-progress run.
5. **Failure injection:**
   - Kill worker mid-round → restart (auto-spawn should detect on next CLI call) → verify resume
   - Kill Temporal server → verify CLI preflight error path
   - Edit artifact during run → verify `workspace_drift` finding + `--strict-lock` abort
   - Transport unreachable → verify retry exhaustion + `spawn_failed` labels
   - Malformed structured output → verify fail-safe-to-worst severity
6. **Parity vs file-based deep-qa:** same 3 artifacts through both; top-3 critical findings semantically equivalent.
7. **Framework-surface test:** scaffold a trivial second skill (`hello-world`) on skillflow to prove the registry + activity dispatcher don't have deep-qa-specific leakage.

## Rollout plan

**Phase A: framework scaffold (day 1-2)**
1. Create `skillflow` GitHub repo with MIT license, pyproject.toml, CI
2. Implement CLI skeleton (launch/list/show/worker/hook subcommands)
3. Implement worker with auto-spawn + preflight
4. Implement transport dispatcher + anthropic-sdk + claude-cli backends
5. Implement INBOX, notify, hook installer
6. Preflight/doctor command

**Phase B: framework-smoke pilot skill (day 2)**
1. Tiny `hello-world` skill: one activity, one workflow, asserts framework plumbing end-to-end
2. Verify: launch → worker auto-spawn → activity → INBOX entry → SessionStart hook surfaces it → desktop notification fires
3. This gates Phase C; if hello-world doesn't cycle cleanly, the framework isn't ready

**Phase C: deep-qa workflow skeleton (day 3-4)**
1. `DeepQaState` + activity signatures (dummy bodies)
2. `DeepQaWorkflow` with phase methods + dummy activities
3. Time-skipped workflow tests for phase transitions
4. `skillflow launch deep-qa` end-to-end with dummies

**Phase D: deep-qa activities (day 4-6)**
1. `spawn_dim_discover` (simplest)
2. `spawn_critic` (anthropic-sdk, then claude-cli)
3. `spawn_judge` (blind pass-1, informed pass-2)
4. `spawn_summary`, `spawn_auditor`, `spawn_verifier`
5. Heartbeat + retry policies applied

**Phase E: UX + safety net (day 6-7)**
1. SKILL.md launcher at `~/.claude/skills/deep-qa-temporal/SKILL.md`
2. End-to-end on 3 golden artifacts (doc, code, research)
3. 5 failure-injection scenarios
4. Parity comparison vs file-based deep-qa

**Phase F: polish + publish (day 7-8)**
1. `skillflow/README.md` (public-facing)
2. `skills/deep_qa/README.md` (skill-specific)
3. Skill migration template for skills #2–10
4. GitHub release; `pip install skillflow` works

## Open decisions — CLOSED

| # | Decision | Chosen |
|---|---|---|
| 1 | Repo location | New standalone repo on personal GitHub (`skillflow`) |
| 2 | Temporal task queue name | `skillflow` (shared across all future skills) |
| 3 | CLI binary name | `skillflow` with subcommand dispatch (`skillflow launch deep-qa …`) |
| 4 | Worker daemon lifecycle | Auto-spawn-on-demand by CLI; explicit `worker --detach`/`--stop` also available |
| 5 | SessionStart hook install | Auto-install on first launch, idempotent |
| 6 | LLM SDK | Anthropic SDK with configurable `base_url` (less Netflix coupling); model gateway becomes an env-var override |
| 7 | `claude -p` fallback scope | Include; pilot covers all four artifact types |

## Success criteria (verifiable)

1. **Durability:** kill worker mid-round; next CLI invocation auto-spawns a new one; workflow resumes and produces identical final report as an uninterrupted run on the same input. (E2E test.)
2. **Latency:** per-activity p95 latency ≤ 20% over equivalent Haiku calls outside the workflow. (Microbenchmark.)
3. **Surfacing:** in 100 simulated completions across three Claude-Code states (idle / mid-turn / closed), findings reach the user within one of immediate notification (idle), deferred notification (mid-turn), or SessionStart prepend (closed). Zero drops. (Integration test.)
4. **Parity:** run same 3 artifacts through file-based deep-qa and deep-qa-temporal; top-3 critical findings semantically equivalent.
5. **Graceful failure:** with Temporal server stopped, `skillflow launch` surfaces a clear preflight error (not a hang) and hints at `temporal server start-dev`.
6. **Framework-neutrality:** the `hello-world` smoke skill in Phase B exercises every skillflow surface without importing anything from `skills/deep_qa/`. Guards against deep-qa-shaped leakage in the framework.
7. **Test coverage:** framework hits ≥90% line coverage; deep-qa workflow hits ≥85%.
8. **Docs:** a user who has never seen skillflow can, from only the public README, install and run a successful deep-qa on a fresh doc within 10 minutes.

---

## Post-spec-review workflow

After user approves this spec:
1. Invoke `superpowers:writing-plans` to produce an implementation plan with verification gates per phase
2. Implementation proceeds per plan; user review at each phase boundary
3. After deep-qa-temporal ships and stabilises (one week of real-world use), open migration specs for skills #2–10 using the framework and the template produced in Phase F
