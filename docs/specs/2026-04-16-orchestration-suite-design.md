# Orchestration Suite — Design Spec

**Date:** 2026-04-16
**Status:** Design approved; ready for implementation planning
**Scope:** Add 5 new orchestration skills to npow/claude-skills that are strictly better than OMC's equivalents on every dimension

## Problem Statement

npow/claude-skills excels at adversarial knowledge-artifact work (deep-design, deep-qa) and lean templated artifacts (spec, research-brief). It lacks the orchestration-runtime layer that OMC provides — multi-agent coordination, persistence loops, parallel fanout, consensus planning, and end-to-end autonomous pipelines.

Users currently must either (a) install OMC alongside npow, accepting OMC's heavy machinery and MCP dependencies, or (b) manually compose npow + superpowers skills to replicate orchestration. Neither is ideal: OMC brings failure modes and portability cost; manual composition loses the packaged runtime.

The goal is to add orchestration skills to npow that absorb the good mechanisms from OMC, the discipline patterns from superpowers, and the adversarial rigor already present in npow — producing skills that are strictly better than OMC's originals on every dimension a reasonable person would care about.

## Goals

- Produce 5 new orchestration skills that each beat OMC's equivalent on: correctness/reliability, output quality, discipline (honesty, anti-rationalization), portability (no OMC MCP deps), discoverability (descriptive naming), and maintainability (npow file layout).
- Deep integration with existing npow skills: new orchestration skills delegate to `deep-design` for adversarial design stress-testing and `deep-qa` for defect audits.
- Pure file-based state — no MCP state tools required. Works in plain Claude Code.
- Use Claude Code's native team tools (`TeamCreate`, `TaskList`, `SendMessage`, `TaskUpdate`, `TaskGet`, `TaskList`, `TeamDelete`) — these are built-in, not OMC-specific.

## Non-Goals

- Porting OMC's CLI worker integration (codex/gemini tmux panes). Out of scope for v1; can be added later as optional capability.
- Porting OMC's MCP state tools. File-based state is sufficient and portable.
- Replacing OMC's existing skills in-place. These are parallel, descriptively-named alternatives.
- Cross-session session resume via OMC's `state_read`. File-based state supports resume within a CWD; that's enough for v1.
- Rewriting npow's existing Research & Design skills. Those were the subject of the prior analysis but are out of scope for this upgrade.

## The Five Skills

| Name | Replaces | Job |
|---|---|---|
| `/team` | OMC `team` | N coordinated agents on a staged pipeline (plan → prd → exec → verify → fix) |
| `/parallel-exec` | OMC `ultrawork` | Fire independent agents in parallel with tier routing and verification |
| `/loop-until-done` | OMC `ralph` | PRD-driven persistence loop until all stories pass and reviewer approves |
| `/consensus-plan` | OMC `ralplan` | Planner → Architect → Critic loop producing an ADR-backed plan |
| `/autopilot` | OMC `autopilot` | Full lifecycle from vague idea to working verified code |

## Architecture

### File layout — every skill

```
{skill-name}/
├── SKILL.md           # main workflow + golden rules + self-review checklist
├── FORMAT.md          # output formats per stage/artifact (per deep-design convention)
├── STATE.md           # state.json schema and resume protocol
├── GOLDEN-RULES.md    # consolidated rules + rationalization counter-table
└── INTEGRATION.md     # composition with deep-design, deep-qa, degraded-mode fallbacks
```

This matches the existing companion-file pattern used by `deep-design/` and `deep-qa/` in npow. Strictly better than OMC's monolithic single SKILL.md on maintainability and discoverability.

### Runtime state — every skill

Each invocation creates `{skill-name}-{run_id}/` in the current working directory (matches npow's existing pattern from `deep-design-{run_id}/`). Contents vary per skill but always include:

- `state.json` — authoritative state; written before every agent spawn, `generation` counter incremented on every write
- `handoffs/` or `stages/` — per-stage or per-iteration artifacts with structured fields
- `critiques/` or `reviews/` or `verify/` — independent agent outputs with `STRUCTURED_OUTPUT_START`/`STRUCTURED_OUTPUT_END` markers
- `logs/` — frontier_pop_log.jsonl (where applicable), decision audit trail

Resume protocol: each skill's STATE.md documents how to replay from the last completed stage by reading `state.json` on next invocation. No in-memory reconstruction.

### Eight cross-cutting golden rules

Applied in every skill's GOLDEN-RULES.md. Absorbed from npow/deep-design + superpowers/verification-before-completion + superpowers/subagent-driven-development:

1. **Independence invariant.** Coordinator orchestrates; never evaluates. Severity, completeness, approval are delegated to independent judge agents with no stake in the outcome.
2. **Iron-law verification gate.** No completion claims without fresh evidence. Each stage must produce an evidence file (test output, lint exit code, judge verdict) before transition.
3. **Two-stage review on source modifications.** Every stage that modifies source files gets spec-compliance review (matches the plan?) then code-quality review (built well?). Separate independent agents. Applies to team-exec, team-fix, loop-until-done story completion, autopilot Phase 2.
4. **Honest termination labels.** Explicit per-skill vocabulary. Never use "no issues remain" or "all complete" as a label. Each skill's SKILL.md defines the exhaustive label table.
5. **State written before agent spawn.** `spawn_time_iso` recorded before Agent call; spawn failure recorded as `spawn_failed`, not "spawned but silent." Resume retries spawn; does not wait.
6. **Structured output is the contract.** Judges, critics, reviewers produce machine-parseable lines between `STRUCTURED_OUTPUT_START`/`STRUCTURED_OUTPUT_END` markers. Free-text is ignored by coordinator. Unparseable → fail-safe critical.
7. **All data passed via files.** Spec content, dedup lists, judge inputs all written to disk before agent call. Inline data is silently truncated.
8. **No coordinator self-approval.** Same context cannot author and approve. Every approval is by a fresh independent agent reading from files.

### Anti-rationalization counter-table — every skill

Tailored per skill. Common entries:

| Excuse | Reality |
|---|---|
| "Tests probably pass" | RUN them. Probably ≠ evidence. |
| "Verifier already ran earlier" | Fresh stage = fresh verification. |
| "I read the output in a previous round" | Previous output is stale state. Read current. |
| "Coordinator can call this one" | No. Independent agent. Always. |
| "Two-stage review is overkill here" | No exceptions. Separate agents, every modification. |

### Deep integration with existing npow skills

| Where | Calls | Why strictly better than OMC |
|---|---|---|
| `/team` team-verify stage | `deep-qa --diff` | OMC uses single verifier; `deep-qa` runs parallel critics across QA dimensions (correctness, error_handling, security, testability for code). |
| `/team` team-plan stage (optional) | `deep-design` | OMC uses planner agent only; `deep-design` adversarially stress-tests the design across orthogonal critique dimensions. |
| `/loop-until-done` story verification | `deep-qa` | OMC uses architect verification; `deep-qa` is more rigorous and produces a structured defect registry. |
| `/autopilot` Phase 0 (Expand) | `/spec` or `deep-design` based on ambiguity | OMC uses analyst+architect pass; npow's `/spec` is template-enforced, `deep-design` is adversarial. |
| `/autopilot` Phase 1 (Plan) | `/consensus-plan` | Reuses the independent-agent pattern instead of duplicating the architect+critic logic inline. |
| `/autopilot` Phase 2 (Exec) | `/team` | Reuses the staged pipeline instead of duplicating it. |
| `/autopilot` Phase 3 (QA) | `deep-qa --diff` | OMC uses ultraqa (test→fix loop) which is different in purpose. Our Phase 3 is defect audit; fixing is delegated to `/loop-until-done`. |
| `/autopilot` Phase 4 (Validate) | 3 independent judges reading from files | OMC uses 3 reviewer agents with coordinator orchestration; ours are fully independent. |
| `/consensus-plan` | 3 independent agents (Planner, Architect, Critic) | OMC's are Task subagents invoked by coordinator; ours are fully independent, reading/writing via files. |

### Degraded mode (when deep-design or deep-qa aren't installed)

Each INTEGRATION.md documents fallback behavior:
- Missing `deep-design` → `/team` and `/autopilot` Phase 0 fall back to inline architect review with explicit "degraded mode" tag in output.
- Missing `deep-qa` → `/team` team-verify and `/loop-until-done` story verification fall back to a single code-reviewer agent. Stage output tags `VERIFICATION_MODE: degraded`.

Skills still work without the integrations; quality is lower but advertised explicitly.

## Skill Details

### `/team` — strict-better deltas vs OMC team

| Dimension | OMC team | npow `/team` |
|---|---|---|
| team-plan agent | explore + planner | explore + planner + optional deep-design pass for adversarial plan review |
| team-prd agent | analyst (critic optional) | analyst + mandatory independent critic with falsifiability gate |
| team-exec worker | executor (no TDD enforcement) | executor with TDD preamble in every worker prompt |
| team-verify | single verifier agent | deep-qa --diff (parallel critics across QA dimensions) + independent code-quality reviewer (two-stage) |
| team-fix | executor loop | bounded by fix_budget; each fix verified independently before merge |
| Handoff docs | freeform markdown at `.omc/handoffs/` | structured schema (`decided`, `rejected`, `risks`, `files`, `remaining`) at `team-{run_id}/handoffs/` with required fields |
| State | OMC MCP `state_write` | file-based at `team-{run_id}/state.json` (portable) |
| Termination labels | complete / failed / cancelled | complete / partial_with_accepted_unfixed / blocked_unresolved / budget_exhausted / cancelled |
| Self-approval | coordinator can mark stage complete | forbidden — every stage gate requires fresh independent verification |
| Shutdown protocol | 30s wait, retry once | same (OMC's is good) |

### `/parallel-exec` — strict-better deltas vs OMC ultrawork

| Dimension | OMC ultrawork | npow `/parallel-exec` |
|---|---|---|
| Dispatch spec | prompt + model tier | prompt + model tier + mandatory verification_command for each task |
| Tier guidance | references external doc | inline table with concrete examples per tier — self-contained |
| Post-execution check | "lightweight verify — build/tests pass" | independent convergence-checker agent reads all task outputs, reports conflicts + flaky tasks |
| Per-task reporting | completed / failed | passed_with_evidence / failed_with_error / conflicted_with_sibling / unverified |
| Iron-law gate | none — "all tasks completed" | no aggregate claim until convergence check produces structured output |
| Dependency handling | prose ("sequential if dependent") | explicit `depends_on` field in task spec; enforcement by coordinator |
| Background execution | `run_in_background=true` for long ops | same (OMC's is good) |

### `/loop-until-done` — strict-better deltas vs OMC ralph

| Dimension | OMC ralph | npow `/loop-until-done` |
|---|---|---|
| PRD validation | coordinator refines scaffold criteria | independent judge agent validates each criterion is falsifiable |
| Story verification | architect agent checks criteria | deep-qa + two-stage review (spec compliance → code quality) per story |
| Acceptance criteria format | prose | structured: `criterion, verification_command, expected_output` |
| Deslop pass | mandatory (good) | preserved |
| Reviewer selection | `--critic=architect\|critic\|codex` | same + add `--critic=deep-qa` for full audit |
| Termination labels | complete / failed | all_stories_passed / blocked_on_story_{id} / budget_exhausted / reviewer_rejected_{count}_times |
| Progress tracking | `progress.txt` freeform | structured `progress.jsonl` — one line per iteration with structured fields |
| Resume | state file | same (OMC's pattern is good) |

### `/consensus-plan` — strict-better deltas vs OMC ralplan

| Dimension | OMC ralplan | npow `/consensus-plan` |
|---|---|---|
| Role independence | Task subagents invoked by coordinator | fully independent agents reading/writing via files only; coordinator never evaluates |
| Critic rejection | "ITERATE" or "REJECT" verdict | falsifiability gate — rejection requires concrete scenario + verification command |
| Plan output | ADR + RALPLAN-DR summary | same + verification_commands[] for each acceptance criterion |
| Alternative providers | `--architect codex`, `--critic codex` | same (OMC's is good) |
| Max iterations | 5 | 5, with honest termination label per iteration |
| Iteration label | "approved" | consensus_reached_at_iter_N / max_iter_no_consensus / user_stopped |
| Interactive gates | `--interactive` flag | same (OMC's is good) |

### `/autopilot` — strict-better deltas vs OMC autopilot

| Phase | OMC autopilot | npow `/autopilot` |
|---|---|---|
| Phase 0 (Expand) | analyst + architect | auto-detect ambiguity → high ambiguity runs `deep-interview` (if available) or `/spec` template, low ambiguity runs `deep-design` for adversarial stress |
| Phase 1 (Plan) | architect + critic inline | delegates to `/consensus-plan` |
| Phase 2 (Exec) | ralph + ultrawork | delegates to `/team` with deep integration |
| Phase 3 (QA) | ultraqa cycle | `deep-qa --diff` for defect audit + `/loop-until-done` for fixing discovered defects |
| Phase 4 (Validate) | coordinator orchestrates 3 reviewer agents | 3 fully independent judge agents (correctness, security, quality) reading from files |
| Phase 5 (Cleanup) | delete state files | honest completion report listing passed/unverified/accepted-tradeoffs — then cleanup |
| Phase gates | each phase must complete | iron-law — each phase must produce an evidence file before transition |
| Termination labels | complete / failed | complete / partial_with_accepted_tradeoffs / blocked_at_phase_N / budget_exhausted |

## Data Model

### Common state.json shape (variant per skill)

```json
{
  "run_id": "20260416-153022",
  "skill": "team | parallel-exec | loop-until-done | consensus-plan | autopilot",
  "created_at": "2026-04-16T15:30:22Z",
  "current_phase": "plan | prd | exec | verify | fix | complete | ...",
  "generation": 42,
  "budget": {
    "max_iterations": 5,
    "current_iteration": 2,
    "token_spent_estimate_usd": 3.42
  },
  "stages": [
    {
      "name": "plan",
      "status": "complete | in_progress | failed | blocked",
      "started_at": "...",
      "completed_at": "...",
      "evidence_files": ["plan.md", "adversarial-review.md"]
    }
  ],
  "invariants": {
    "coordinator_never_evaluated": true,
    "all_evidence_fresh_this_session": true
  },
  "termination": null
}
```

Each skill extends with skill-specific fields (documented in its STATE.md).

### Stage handoff schema (used in `team-{run_id}/handoffs/*.md`)

```markdown
## Handoff: {from-stage} → {to-stage}

**Decided:**
- [decision with one-line rationale]

**Rejected:**
- [alternative] | [reason for rejection]

**Risks carried forward:**
- [risk] | [mitigation if any, or "accepted"]

**Files modified:**
- `path/to/file.ts` — what changed

**Remaining for next stage:**
- [concrete item]

**Evidence:**
- `{run_id}/handoffs/plan-verification.md` — [what was verified, verdict]
```

Required fields: Decided, Rejected, Risks, Files, Remaining, Evidence. No freeform prose.

### Acceptance criterion schema (used in `/loop-until-done` prd.json)

```json
{
  "story_id": "US-001",
  "subject": "Add flag detection helpers",
  "acceptance_criteria": [
    {
      "id": "AC-001-1",
      "criterion": "detectNoPrdFlag('ralph --no-prd fix') returns true",
      "verification_command": "npm test -- --testPathPattern=flag-detection.test.ts",
      "expected_output_pattern": "tests: 4 passed",
      "passes": false,
      "last_verified_at": null
    }
  ],
  "status": "pending | in_progress | passed | blocked"
}
```

Structured; every criterion has an executable verification command.

## Failure Modes

| Failure | Probability | Impact | Mitigation |
|---|---|---|---|
| Coordinator claims stage complete without running verification | Low (iron-law in golden rules) | Critical — false completion | Pre-transition gate reads `state.json`; if `evidence_files` empty for the closing stage, refuses to advance. |
| Agent spawn silently fails | Low | Medium — pipeline stalls | `spawn_time_iso` written before call; missing = retry on resume. |
| Independent judge rubber-stamps | Medium | High — rationalization creeps in | Judge prompt includes adversarial mandate (from deep-design pattern); ≥90% approval rate flags the judge as broken. |
| File-based state corrupted mid-write | Low | Medium — resume confused | Atomic writes via tempfile + rename; `generation` counter validates ordering. |
| `deep-qa` or `deep-design` not installed | Medium | Medium — degraded verification | Degraded mode documented in INTEGRATION.md; each skill tags output `VERIFICATION_MODE: degraded`. |
| Worker claim race in `/team` | Low (inherited from OMC mitigation) | Medium — duplicate work | Lead pre-assigns owners via `TaskUpdate(owner=...)` before spawning workers. |
| Long-running stage exceeds budget | Medium | Low — partial completion | Hard budget cap per skill; exceeds → label `budget_exhausted` with honest coverage report. |
| User cancels mid-run | High | Low — recoverable | Resume protocol reads `state.json` + stage evidence files; replays from last complete stage. |

## Success Metrics

- **Strict-better on all 8 golden rules** vs OMC equivalents, verified by side-by-side skill-file diff review.
- **Portability:** `/team`, `/parallel-exec`, `/loop-until-done`, `/consensus-plan`, `/autopilot` all execute in plain Claude Code without OMC plugin installed.
- **Integration:** each skill's INTEGRATION.md documents and tests the call into `deep-design` and `deep-qa`.
- **Discoverability:** skill names are self-documenting; description fields start with "Use when…" (superpowers CSO pattern).
- **Adversarial robustness:** randomized baseline tests (superpowers writing-skills pattern) — spawn a subagent without the skill, observe failure mode; add skill, confirm compliance.

## Open Questions

- Should `/autopilot` offer `deep-interview` as the Phase 0 option (it's an OMC skill)? For v1: detect availability at runtime; if present, offer as an option. If not present, fall back to `/spec` or `deep-design`. Documented in INTEGRATION.md.
- Should we add a `/team-cancel` companion skill to mirror OMC's `/cancel`? For v1: cancel is a `CTRL-C` + `state.json` inspection flow, documented in each skill's SKILL.md. No separate skill.
- Should the skills publish themselves to the npow README "Orchestration" section? Yes — but README updates are part of implementation, not this design doc.

## Implementation Plan

Handed off to `superpowers:writing-plans` as the next step. The plan will decompose this design into bite-sized TDD-shaped tasks per skill, with one wave of parallel subagent-driven development per skill (shared architecture + foundation first, then each skill in turn).
