# Output Formats

All files listed are absolute paths under `deep-plan-{run_id}/`. Coordinator reads structured blocks only; all free-text is advisory.

## Planner Output: `iterations/iter-{N}/plan.md`

```markdown
# Plan: {task-summary}
**Iteration:** {N}
**Mode:** short | deliberate
**Date:** {date}

## Requirements Summary
[One paragraph restating the task in the Planner's own words.]

## RALPLAN-DR Summary

### Principles (3-5)
1. {Principle statement — a foundational constraint, not a slogan}
2. ...

### Decision Drivers (top 3)
1. {Driver — what actually decided this plan}
2. ...

### Viable Options (≥2)
#### Option A: {name}
- **Pros:** {bounded — 2-4 items}
- **Cons:** {bounded — 2-4 items}
- **Viable:** yes | no

#### Option B: {name}
[same structure]

### Invalidation Rationale (only if <2 viable)
- {Alternative} — invalidated because {concrete reason}

## Chosen Option
{Option ID} — {rationale referencing specific Drivers}

## Acceptance Criteria
| ID | Criterion | Verification Command | Expected Output Pattern |
|---|---|---|---|
| AC-001 | {one-sentence testable criterion} | `{executable command}` | `{regex or literal}` |
| AC-002 | ... | ... | ... |

## Implementation Steps
1. {Step with file reference — `src/auth/login.ts:42`}
2. ...

## Risks and Mitigations
| Risk | Mitigation |
|---|---|
| {risk description} | {concrete mitigation — not "monitor closely"} |

## Verification Steps
- {Step — reference real test names and commands, not prose}

## Pre-Mortem (deliberate mode only)
### Scenario 1: {title}
{6 months from now, this fails because ...}

### Scenario 2: {title}
[same structure — must be distinct, not a rephrasing]

### Scenario 3: {title}
[same structure]

## Expanded Test Plan (deliberate mode only)
### Unit
- {test coverage area}

### Integration
- {test coverage area}

### E2E
- {test coverage area}

### Observability
- {metric / log / trace / alert specifically added}

STRUCTURED_OUTPUT_START
ACCEPTANCE_CRITERION|AC-001|{criterion}|{verification_command}|{expected_output_pattern}
ACCEPTANCE_CRITERION|AC-002|...
PRINCIPLE|P-1|{statement}
PRINCIPLE|P-2|...
DRIVER|D-1|{statement}
DRIVER|D-2|...
DRIVER|D-3|...
OPTION|O-A|{name}|viable|{brief}
OPTION|O-B|{name}|viable|{brief}
OPTION|O-C|{name}|invalidated|{reason}
PREMORTEM|PM-1|{scenario}
PREMORTEM|PM-2|{scenario}
PREMORTEM|PM-3|{scenario}
STRUCTURED_OUTPUT_END
```

**Parser rules:**
- Pipe-separated fields, split on first `|` per field.
- Coordinator reads only the `STRUCTURED_OUTPUT` block for state mutation.
- `ACCEPTANCE_CRITERION` lines must have all 4 trailing fields; missing verification_command or expected_output_pattern fails the iteration.
- `PREMORTEM` required only in deliberate mode; required count = 3.
- Missing `STRUCTURED_OUTPUT_START/END` markers = file treated as failed; re-spawn once.

---

## Architect Output: `iterations/iter-{N}/architect-verdict.md`

```markdown
# Architect Verdict — Iteration {N}
**Date:** {date}
**Architect mode:** claude | codex | degraded
**Plan reviewed:** {plan_file_path}

## Steelman Antithesis (against favored option)
[The strongest argument against the chosen option — not a strawman. Include the counter-option it implies.]

## Tradeoff Tensions
1. **{decision name}:** The plan trades {A} for {B}. Losing {A} is non-trivial because {scenario}.

## Synthesis Path (if any)
[Variant of the plan that preserves {A} while retaining most of {B}. If not possible, state explicitly: "No synthesis available — tradeoff is fundamental."]

## Principle Violations (deliberate mode only)
- **Principle {P-N}:** {violation description}

## Verdict Rationale
[Honest assessment. Why ARCHITECT_OK or ARCHITECT_CONCERNS.]

STRUCTURED_OUTPUT_START
VERDICT|ARCHITECT_OK|{architect_mode_tag}
CONCERN|C-1|{description}|major
CONCERN|C-2|{description}|minor
TRADEOFF|{description}
SYNTHESIS|{description}
PRINCIPLE_VIOLATION|P-2|{description}
STRUCTURED_OUTPUT_END
```

**Parser rules:**
- Exactly one `VERDICT` line per file: value is `ARCHITECT_OK` or `ARCHITECT_CONCERNS`; trailing field is the architect mode tag (`claude`, `codex`, `degraded`).
- `CONCERN` severity ∈ {`critical`, `major`, `minor`}; critical concerns block advance to Critic.
- `SYNTHESIS` is optional; `PRINCIPLE_VIOLATION` is deliberate-mode only.

---

## Critic Output: `iterations/iter-{N}/critic-verdict.md`

```markdown
# Critic Verdict — Iteration {N}
**Date:** {date}
**Critic mode:** claude | codex | gemini | degraded
**Plan reviewed:** {plan_file_path}
**Architect verdict read:** {architect_verdict_path}

## Dimension Checks

### 1. Principle-Option Consistency
{PASS | FAIL + reason}

### 2. Fair Alternative Exploration
{PASS | FAIL + reason}

### 3. Risk Mitigation Clarity
{PASS | FAIL + reason}

### 4. Testable Acceptance Criteria
{PASS | FAIL + reason — cite specific criteria missing verification_command or expected_output_pattern}

### 5. Concrete Verification Steps
{PASS | FAIL + reason}

### 6. Pre-Mortem Quality (deliberate only)
{PASS | FAIL + reason}

### 7. Expanded Test Plan (deliberate only)
{PASS | FAIL + reason}

## Rejections (with falsifiability evidence)
Each rejection must include a concrete failure scenario AND an executable verification command. Rejections without both will be DROPPED by the coordinator.

### Rejection R-1: {title}
- **Dimension:** {principle_consistency | fair_alternatives | risk_mitigation | testable_criteria | verification_steps | premortem | test_plan}
- **Failure scenario:** When {actor} does {action}, {observable failure} occurs because {root cause}.
- **Verification command:** `{executable command}` — expected to show the failure.

## Approval Evidence (when APPROVE)
### AE-1: {criterion_id}
- **Why it passes:** {specific citation in plan}

STRUCTURED_OUTPUT_START
VERDICT|APPROVE|{critic_mode_tag}
REJECTION|R-1|{dimension}|{failure_scenario}|{verification_command}
APPROVAL_EVIDENCE|AE-1|{criterion_id}|{why_it_passes}
STRUCTURED_OUTPUT_END
```

**Parser rules:**
- Exactly one `VERDICT` line; value is `APPROVE`, `ITERATE`, or `REJECT`; trailing field is critic mode tag.
- `REJECTION` lines: 4 trailing fields — `dimension | failure_scenario | verification_command`. Coordinator applies the **falsifiability gate** (see SKILL.md Step 4):
  - `failure_scenario` length ≥ 20 chars; must not match rubber-stamp regex (e.g., `/^\s*(needs? more detail|should be clearer|add context|be more specific)\s*\.?$/i`).
  - `verification_command` non-empty AND contains at least one of: `$`, `npm`, `pytest`, `make`, `./`, `cargo`, `go test`, `bun`, `curl`, `docker`, `grep`, `test`, or a CLI token preceded by executable path/glob.
- Surviving rejections feed the next iteration's feedback bundle.
- Dropped rejections are written to `iter-{N}/dropped-rejections.md` with reason.
- If all rejections drop and no `APPROVE` verdict: verdict is promoted to `APPROVE_AFTER_RUBBER_STAMP_FILTER` with an explicit tag in state. This is consensus BUT labeled honestly in the final output.

---

## Feedback Bundle: `iterations/iter-{N}/feedback-bundle.md`

Assembled by the coordinator between iterations. Handed to the Planner for iteration N+1. Coordinator does NOT paraphrase.

```markdown
# Feedback Bundle — Iteration {N+1}
**Prior iteration:** {N}
**Source files:**
- Plan: {iter-N plan.md path}
- Architect verdict: {iter-N architect-verdict.md path}
- Critic verdict: {iter-N critic-verdict.md path}

## Architect Concerns (verbatim from structured output)
- CONCERN|C-1|{description}|major
- CONCERN|C-2|{description}|minor

## Surviving Critic Rejections (verbatim, post-falsifiability gate)
- REJECTION|R-1|{dimension}|{failure_scenario}|{verification_command}

## Dropped Rubber-Stamp Rejections (informational, not requirements)
- R-3: dropped — rubber-stamp phrase "needs more detail"
- R-7: dropped — verification_command empty

## User Feedback (interactive mode only)
[User-provided text verbatim if any]
```

---

## Final Plan: `plan.md`

The final plan is the last iteration's `plan.md` copied verbatim to the run root, with an appended header:

```markdown
<!--
CONSENSUS PLAN METADATA
run_id: {run_id}
termination: consensus_reached_at_iter_N | max_iter_no_consensus | user_stopped | user_rejected
iterations: {N}
architect_mode: claude | codex | degraded
critic_mode: claude | codex | gemini | degraded
dropped_rubber_stamp_rejections: {count}
mode: short | deliberate
-->

{unchanged plan content}
```

No coordinator editing of plan body. If edits are required, go back to Planner via a new iteration.

---

## ADR: `adr.md`

Written by the ADR Scribe. Coordinator copies to run root.

```markdown
# ADR — {task-summary}
**Run:** {run_id}
**Termination:** {label}

## Decision
{Chosen option ID + name from final plan's RALPLAN-DR}

## Drivers
1. {Driver D-1 verbatim from final plan}
2. {Driver D-2 verbatim}
3. {Driver D-3 verbatim}

## Alternatives Considered
### Option {O-A}: {name}
- **Pros:** {verbatim from plan}
- **Cons:** {verbatim from plan}
- **Status:** chosen | invalidated — {reason}

### Option {O-B}: {name}
[same structure]

## Why Chosen
{Rationale referencing specific Drivers. Cite Architect tradeoffs verbatim from verdict files — do not paraphrase.}

## Consequences
- {Accepted tradeoff from Architect verdict, cited}
- {Surviving non-blocking Critic concern, cited}

## Follow-ups
- {Open question from Critic}
- {Monitoring item}

## Consensus Status (only if termination == max_iter_no_consensus)
Max iterations reached without Critic APPROVE. The following rejections were unresolved at termination:
- REJECTION|R-X|{dimension}|{scenario}|{verification_command}   (from iter-{N} critic verdict verbatim)
```

---

## Audit Log: `logs/decisions.jsonl`

One JSON line per decision event. Coordinator-written. Never used by agents, used by humans / `/autopilot` for audit.

```jsonl
{"ts": "2026-04-16T15:31:02Z", "event": "iteration_started", "iteration": 1, "generation": 3}
{"ts": "...", "event": "planner_spawned", "iteration": 1, "spawn_time_iso": "..."}
{"ts": "...", "event": "planner_complete", "iteration": 1, "output_path": "..."}
{"ts": "...", "event": "architect_spawned", "iteration": 1, "architect_mode": "claude"}
{"ts": "...", "event": "architect_complete", "iteration": 1, "verdict": "ARCHITECT_CONCERNS", "concern_count": 2}
{"ts": "...", "event": "critic_spawned", "iteration": 1, "critic_mode": "claude"}
{"ts": "...", "event": "critic_complete", "iteration": 1, "verdict": "ITERATE", "rejection_count": 3, "dropped_count": 1}
{"ts": "...", "event": "falsifiability_gate_applied", "iteration": 1, "dropped": ["R-2"], "reason": "rubber_stamp_phrase"}
{"ts": "...", "event": "feedback_bundle_written", "iteration": 2, "surviving_rejections": 2}
{"ts": "...", "event": "termination", "label": "consensus_reached_at_iter_3", "final_plan_path": "plan.md", "adr_path": "adr.md"}
```
