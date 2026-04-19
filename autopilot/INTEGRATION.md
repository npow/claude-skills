# Integration

`/autopilot` is a composition operator. It delegates every phase to a specialized skill and never authors or evaluates load-bearing content itself. This file documents the mapping, the detection of available integrations, and the degraded-mode fallbacks when integrations are missing.

## Detection

At Phase 0 initialization, probe for each integration. Write results to `state.integrations`.

```
deep_interview_available = exists(~/.claude/plugins/.../skills/deep-interview/SKILL.md)
                            OR exists(~/.claude/skills/deep-interview/SKILL.md)
spec_available           = exists(~/.claude/skills/spec/SKILL.md)
deep_design_available    = exists(~/.claude/skills/deep-design/SKILL.md)
consensus_plan_available = exists(~/.claude/skills/deep-plan/SKILL.md)
team_available           = exists(~/.claude/skills/team/SKILL.md)
deep_qa_available        = exists(~/.claude/skills/deep-qa/SKILL.md)
loop_until_done_available= exists(~/.claude/skills/loop-until-done/SKILL.md)
```

Record each flag. If any are missing, set `degraded_mode_active: true` and populate `degraded_mode_reasons[]`. Surface the list in the Phase 5 completion report with explicit tags.

## Phase 0 — Expand (routed by ambiguity classifier)

**Routes, in order of preference:**

| Ambiguity | Skill routed to | Output |
|---|---|---|
| high | `deep-interview` (if available) | `autopilot-{run_id}/expand/spec.md` (deep-interview writes to `.omc/specs/`; copy or symlink into phase dir) |
| high | `/spec` template mode (fallback) | same path |
| medium | `/spec` template mode | same path |
| low | `deep-design` (if available) | same path (deep-design's final spec) |
| low | `/spec` template mode (fallback) | same path |

**Invocation contract (representative — `deep-interview` route):**

```
Spawn Skill("deep-interview") via Skill tool with:
  Argument: initial_idea (from autopilot-{run_id}/state.json)
  Working directory: autopilot-{run_id}/expand/
After completion:
  Copy .omc/specs/deep-interview-*.md → autopilot-{run_id}/expand/spec.md
  Parse trailing metadata for final_ambiguity_score
  Reject if final_ambiguity_score > 0.3 (user requested clarity, didn't get it)
```

**Degraded-mode fallback (no `deep-interview`, no `/spec`, no `deep-design`):**

Spawn an `architect` agent (opus) with the prompt:
```
"Read the idea at {initial_idea}. Produce a technical specification
 at {output_path} covering: problem statement, goals, non-goals,
 API/interface, data model, failure modes, success metrics, open
 questions. Be specific — no TBDs. Tag output
 VERIFICATION_MODE: degraded (no spec/deep-design/deep-interview installed)."
```

Output quality is lower (single-pass, no adversarial stress-test, no ambiguity gate). Phase 5 surfaces the degradation tag.

## Phase 1 — Plan (delegated to `/deep-plan`)

**Always required** for autopilot runs. If `/deep-plan` isn't installed, autopilot refuses to run and prompts the user to install it or use `--skip-consensus` (degraded).

**Invocation contract:**

```
Spawn Skill("deep-plan") via Skill tool with:
  Argument: "--direct (spec at autopilot-{run_id}/expand/spec.md)"
  Note: --direct flag skips deep-plan's interview phase because
        Phase 0 already did the requirements gathering.
After completion:
  Copy .omc/plans/ralplan-*.md → autopilot-{run_id}/plan/deep-plan.md
  Parse trailing labels for consensus_reached_at_iter_N | max_iter_no_consensus | user_stopped
  Reject if label != consensus_reached_at_iter_N (Phase 1 gate)
```

**Degraded-mode fallback (no `/deep-plan`):**

Spawn 3 agents sequentially (Planner → Architect → Critic) with fixed prompts modeled on `/deep-plan`'s contract. Accept if the Critic's structured output has `VERDICT|APPROVE`. Reject and halt Phase 1 otherwise. Surface `VERIFICATION_MODE: degraded (deep-plan not installed)` in Phase 5.

## Phase 2 — Exec (delegated to `/team`)

**Always required.** If `/team` isn't installed, autopilot refuses to run.

**Invocation contract:**

```
Spawn Skill("team") via Skill tool with:
  Argument: "auto (plan at autopilot-{run_id}/plan/deep-plan.md)"
After completion:
  Copy team-{run_id}/SUMMARY.md → autopilot-{run_id}/exec/team-summary.md
  Copy team-{run_id}/state.json  → autopilot-{run_id}/exec/team-state.json
  Parse state.json for terminal label:
    complete / partial_with_accepted_unfixed / blocked_unresolved /
    budget_exhausted / cancelled
  Accept Phase 2 only if label == complete OR partial_with_accepted_unfixed
  (the latter requires user to have already accepted the tradeoffs during team-fix gate)
```

**Degraded-mode fallback (no `/team`):**

Refuse to run — `/team` is too complex to substitute inline. The user receives an explicit error:
```
/autopilot requires /team to be installed. Install npow's /team skill or
use /loop-until-done directly if you accept single-agent execution.
```

## Phase 3 — QA (delegated to `deep-qa --diff` + `/loop-until-done`)

**Two-stage phase:**

### Phase 3a — Audit (via `deep-qa --diff`)

**Invocation contract:**

```
Spawn Skill("deep-qa") via Skill tool with:
  Arguments: "--type code --diff autopilot-{run_id}/exec/team-diff.patch --auto"
  (Note: --auto because autopilot is non-interactive end-to-end)
After completion:
  Copy deep-qa-*/qa-report.md → autopilot-{run_id}/qa/defect-registry.md
  Parse defect-registry.md for STRUCTURED_OUTPUT markers
  Extract critical/major defect counts
```

**Gate:** If `critical_count == 0` AND `major_count == 0`: advance directly to Phase 4.
Otherwise: Phase 3b fires.

**Degraded-mode fallback (no `deep-qa`):**

Spawn a single `code-reviewer` agent (opus) to review the diff against the plan's acceptance criteria. Output to the same `defect-registry.md` path with `VERIFICATION_MODE: degraded (deep-qa not installed)` tag. Coverage is measurably lower — no parallel critics, no dimension guarantees.

### Phase 3b — Fix (via `/loop-until-done`, only if defects found)

**Invocation contract:**

```
Generate a PRD at autopilot-{run_id}/qa/fix-prd.json from the defect
registry. Each critical/major defect becomes a user story with:
  - criterion: "defect {id} is resolved"
  - verification_command: the defect's suggested_verification or
    a default "rerun the test that first exposed it"
  - expected_output_pattern: from the defect

Spawn Skill("loop-until-done") via Skill tool with:
  Argument: "--prd autopilot-{run_id}/qa/fix-prd.json"
After completion:
  Parse loop-{run_id}/state.json for terminal label:
    all_stories_passed / blocked_on_story_{id} /
    budget_exhausted / reviewer_rejected_N_times
  Accept Phase 3 only if label == all_stories_passed
  If budget_exhausted: pivot Phase 5 to partial_with_accepted_tradeoffs
    and list unresolved defects
```

**Degraded-mode fallback (no `/loop-until-done`):**

Fall back to `/team` team-fix stage (inline fix loop bounded by max_fix_loops=3). If `/team` also not available: surface critical defects as open issues and mark Phase 3 as `failed_unfixable` — Phase 4 still runs for validation, but Phase 5 terminal label forces `blocked_at_phase_3`.

## Phase 4 — Validate (3 Independent Judges)

**Not delegated to any skill.** This is inline to autopilot — 3 parallel Agent spawns with fixed prompts. The coordinator aggregates verdicts but does not evaluate.

### Judge 1: Correctness

```
Spawn Task(subagent_type: general-purpose, model: opus) with:
  Input files:
    - autopilot-{run_id}/expand/spec.md
    - autopilot-{run_id}/plan/deep-plan.md
    - autopilot-{run_id}/exec/team-diff.patch
  Output file:
    - autopilot-{run_id}/validate/correctness-verdict.md
  Prompt: (see SKILL.md "Phase 4 Judge Prompts" for full text)
  Emits: VERDICT|pass|fail with CRITICAL_GAPS lines
```

### Judge 2: Security

Same pattern, prompt focuses on OWASP Top 10, secrets, unsafe patterns, input validation, authorization boundaries. Output: `autopilot-{run_id}/validate/security-verdict.md`.

### Judge 3: Quality

Same pattern, prompt focuses on idiom, readability, maintainability, test coverage structural issues, over-engineering. Output: `autopilot-{run_id}/validate/quality-verdict.md`.

**Aggregator (not a judge — a pure file reader):**

```
The coordinator reads all three verdict files, parses VERDICT lines,
and writes autopilot-{run_id}/validate/aggregate.md:
  PASS if all 3 == pass
  PARTIAL if 1-2 fail but failures are non-critical
  FAIL if any critical-severity finding in any judge
No subjective aggregation — pure rule-based combination.
```

**Phase 4 gate:**
- `PASS` → advance to Phase 5 with terminal label `complete`
- `PARTIAL` → advance to Phase 5 with terminal label `partial_with_accepted_tradeoffs` and listed tradeoffs
- `FAIL` → loop back to Phase 3b (/loop-until-done fix) with the critical findings as new stories, up to 2 more fix iterations; after that, terminal label becomes `blocked_at_phase_4`

**Degraded-mode fallback:**

None. Phase 4 is inline — no external dependency. Three independent agents are always spawned.

## Phase 5 — Cleanup & Honest Report

**Not delegated.** Coordinator spawns a `report-writer` agent (sonnet) with the full evidence bundle and asks for a structured completion report. Then cleanup runs.

**Invocation contract:**

```
Spawn Task(subagent_type: general-purpose, model: sonnet) with:
  Input files:
    - autopilot-{run_id}/state.json
    - every evidence file listed in state.stages[].evidence_files
  Output file:
    - autopilot-{run_id}/FINAL-REPORT.md
  Prompt: (see SKILL.md "Phase 5 Report-Writer Prompt" for full text)
  Report must include:
    - Terminal label (from state.json, not re-derived)
    - What was built (summary)
    - What was verified (with evidence references)
    - What is unverified (explicitly listed)
    - Accepted tradeoffs (with rationale from team-fix or user-acceptance gates)
    - Blocked items (with reason)
    - Degraded-mode tag if any integrations fell back
After report written:
  Optionally archive autopilot-{run_id}/ to .npow-orch-archive/
  Do NOT delete — the evidence bundle is the audit trail
```

**Important:** Phase 5 never changes the terminal label. Whatever label Phase 4 produced is authoritative. The report writer paraphrases; it does not adjudicate.

## Summary: Required vs Optional Integrations

| Phase | Integration | Required | Degrades To |
|---|---|---|---|
| 0 | `deep-interview` | Optional (routing preference on high ambiguity) | `/spec` or `deep-design` |
| 0 | `/spec` | Optional (fallback on medium ambiguity) | `deep-design` or inline architect agent |
| 0 | `deep-design` | Optional (preferred on low ambiguity) | `/spec` or inline architect agent |
| 1 | `/deep-plan` | Required by default | 3-agent inline sequence (degraded) |
| 2 | `/team` | **Hard required** — refuses to run if missing | n/a (halt with explicit error) |
| 3a | `deep-qa` | Required by default | single-pass `code-reviewer` agent |
| 3b | `/loop-until-done` | Required when defects found | `/team` team-fix or skip-with-blocked-label |
| 4 | 3 judges (inline) | Always required | n/a (never degrades) |
| 5 | report-writer (inline) | Always required | n/a (never degrades) |

## Non-Silent Degradation

Every degraded fallback writes a line to `autopilot-{run_id}/degraded-mode.log` at the moment of fallback. At Phase 5, the FINAL-REPORT.md includes a "Verification Mode" section listing every degradation with reason:

```markdown
## Verification Mode: DEGRADED

The following integrations were unavailable; fallbacks were used:
- deep-interview: not installed — Phase 0 ran `/spec` template mode.
- deep-qa: not installed — Phase 3a ran single-pass code-reviewer fallback.

Output quality is measurably lower than the fully-integrated path. Consider
installing the missing skills and re-running critical work.
```

Never silently substitute. The tag is the contract.

## Interaction with Other Orchestration Skills

`/autopilot` composes the full orchestration suite. Direct dependencies:

- `/deep-plan` — Phase 1 exclusively
- `/team` — Phase 2 exclusively
- `/loop-until-done` — Phase 3b when defects found
- `/parallel-exec` — not directly invoked; `/team` uses it internally for team-exec fanout

The suite is designed to be composable: `/autopilot` dogfoods the whole stack. Bugs in any lower-level skill surface in `/autopilot` output via the Phase 5 report (terminal labels from sub-skills propagate up).

## When NOT to Use Autopilot

- User has a detailed spec and plan already → skip Phase 0+1, invoke `/team` directly
- User wants interactive control → use `/deep-plan --interactive` then `/team`
- Task is a single-file fix → delegate directly to an executor agent
- Task needs human review gates between phases → autopilot is intentionally non-interactive; use `/team ralph` for a gated persistence loop

See the SKILL.md "Do Not Use When" section for the authoritative triggers.
