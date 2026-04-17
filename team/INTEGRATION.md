# Integration

How `/team` composes with `deep-design` (for plan stress-testing) and `deep-qa --diff` (for verify stage spec-compliance review). How it degrades when those aren't installed.

## Detection

At Step 1 (Initialize), probe for integration availability by checking for the installed skill directories:

```
deep_design_available  = exists(~/.claude/skills/deep-design/SKILL.md)
                          OR exists(~/.claude/plugins/.../skills/deep-design/SKILL.md)
deep_qa_available      = exists(~/.claude/skills/deep-qa/SKILL.md)
                          OR exists(~/.claude/plugins/.../skills/deep-qa/SKILL.md)
```

Record results in `state.integrations`. Set `degraded_mode_active: true` if either is missing; populate `degraded_mode_reasons`.

If both missing: `/team` still runs, degraded on both axes. Output clearly tags `VERIFICATION_MODE: degraded (no deep-design, no deep-qa)` in `SUMMARY.md`.

## Integration 1 — `deep-design` in `team-plan` (Optional)

**Purpose:** Adversarial stress-testing of the draft plan across orthogonal critique dimensions (correctness, operability, security, UX, economics). Catches plan-level flaws before they propagate through PRD / exec / verify.

**When invoked:** Optional. Runs when `integrations.deep_design_available` AND any of:
- Task has >3 unknowns (unresolved components in `handoffs/plan.md` Risks section).
- Task likely touches >5 files (counted by `explore` output).
- User invocation included `--adversarial-plan` flag (reserved for v1.1; the threshold test above is the default trigger).

**Invocation contract:**

```
Spawn agent (subagent_type: general-purpose) with:
  Input files:
    - team-{run_id}/handoffs/plan.md   (the draft plan as a design spec)
    - team-{run_id}/exec/codebase-context.md  (as "current state" context)
  Output directory:
    - team-{run_id}/handoffs/plan-adversarial-review/
  Prompt:
    "Treat the draft plan as the design spec. Run deep-design's
     iterative adversarial stress-test with max_rounds=2 (reduced
     from default 5 — this is a gate check, not a full design run).
     Output: deep-design's standard spec.md at
     team-{run_id}/handoffs/plan-adversarial-review.md with
     STRUCTURED_OUTPUT_START/END markers listing open critical flaws."
```

**Consumption:** The planner reads `plan-adversarial-review.md` and produces a revised `handoffs/plan.md`. The Rejected section lists every critical/major flaw with one of:
- `addressed_in_plan_v1`: described how the plan changed
- `accepted_with_rationale`: explicit rationale; listed in handoff Risks

**Degraded-mode fallback (when `deep_design_available` is false):**

Spawn an inline `architect` agent (opus) with prompt:
```
"Read the draft plan at {plan_path}. Adversarially critique it across:
 correctness, operability, security, UX, economics. Output structured
 findings to {output_path} with STRUCTURED_OUTPUT_START/END markers
 listing findings with severity (critical/major/minor), root cause,
 suggested fix. Be adversarial — you succeed by rejecting/downgrading,
 not rubber-stamping.
 Tag output VERIFICATION_MODE: degraded (deep-design not installed)."
```

The output is consumed the same way. Quality is measurably lower (single-pass critique vs iterative DFS), so SUMMARY.md surfaces the degraded tag.

## Integration 2 — `deep-qa --diff` in `team-verify` Stage A (Required by Default)

**Purpose:** Parallel critics across QA dimensions (correctness, error_handling, security, testability) audit the full diff against the PRD. This is Stage A of the mandatory two-stage review.

**When invoked:** Always, at `team-verify` Stage A and at `team-exec` per-worker two-stage review (Stage A).

**Invocation contract (stage-level at team-verify):**

```
Spawn deep-qa via Skill tool or direct Agent spawn with:
  --type code
  --diff team-{run_id}/verify/diff.patch
  --spec team-{run_id}/prd/prd-final.md
  --output team-{run_id}/verify/spec-compliance/
  (remaining deep-qa args default — full parallel critic set across
   correctness, error_handling, security, testability)
Result: deep-qa produces a defect registry at
  team-{run_id}/verify/spec-compliance/defect-registry.md
with STRUCTURED_OUTPUT markers per deep-qa's format (compatible with
our DEFECT|severity|id|title|location structured lines).
```

**Invocation contract (per-worker at team-exec):**

Same as above but scoped to an individual worker's subset of the diff:

```
  --diff team-{run_id}/verify/per-worker/{worker}-task-{id}/diff.patch
  --spec team-{run_id}/prd/prd-final.md  (filtered to only that worker's ACs)
  --output team-{run_id}/verify/per-worker/{worker}-task-{id}/spec-compliance/
```

**Degraded-mode fallback (when `deep_qa_available` is false):**

Spawn a single `code-reviewer` agent (opus) with prompt:
```
"Read diff at {diff_path} and spec at {prd_path}. For every PRD
 acceptance criterion, determine: is it met in the diff? Output:
 {output_path} with STRUCTURED_OUTPUT_START/END markers and one
 DEFECT|severity|id|title|ac_reference line per defect. If no
 defects, still write an empty DEFECTS block inside markers.
 Tag output VERIFICATION_MODE: degraded (deep-qa not installed)."
```

Quality gap vs deep-qa: single pass, no parallel critics, no dimension coverage guarantee. SUMMARY.md flags it.

**Why this is required even at exec-stage per-worker review:** it's the only way to enforce "two-stage review on every source modification" (Golden Rule 3). Workers cannot self-verify; per-worker two-stage review is where we catch spec drift before workers proceed to more tasks.

## Integration 3 — Code-Quality Reviewer (Stage B, Always Required)

**Purpose:** Stage B of the two-stage review. Runs AFTER Stage A completes. Focuses on code quality — readability, idiom, duplication, structural coverage — NOT re-litigating spec compliance.

**This is NOT an external integration.** It's a `code-reviewer` (opus) agent spawn built into `/team`. No dependency on external skills.

**Invocation contract:**

```
Spawn Task(subagent_type: "code-reviewer" OR general-purpose if
  code-reviewer agent-type unavailable in harness) with:
  Input files:
    - team-{run_id}/verify/diff.patch
    - team-{run_id}/prd/prd-final.md  (read-only reference)
    - team-{run_id}/verify/spec-compliance/defect-registry.md
      (read to avoid re-reporting; must NOT dilute)
  Output file:
    - team-{run_id}/verify/code-quality/review.md
  Prompt:
    "You are the code-quality reviewer in a mandatory two-stage
     review. Stage A (spec-compliance) is done — see
     defect-registry.md. Your job is ORTHOGONAL: focus on
     readability, maintainability, idiom, duplication, error
     handling, test coverage structural issues. Do NOT re-report
     spec-compliance defects — Stage A owns those.
     Output findings with STRUCTURED_OUTPUT_START/END markers and
     one DEFECT|severity|id|title|file:line per finding. Adversarial
     mandate: you succeed by rejecting/downgrading. 100% approval is
     evidence of failure."
```

This runs whether or not `deep-qa` is installed. Two-stage review is enforced regardless of degraded mode.

## Integration 4 — Verify-Judge (Aggregator, Always Required)

**Purpose:** Independent agent that reads both Stage A + Stage B outputs and produces the authoritative stage-level `VERDICT`. No external skill dependency.

**Invocation contract:**

```
Spawn Task(subagent_type: general-purpose, model: opus) with:
  Input files:
    - team-{run_id}/verify/spec-compliance/defect-registry.md
    - team-{run_id}/verify/code-quality/review.md
    - team-{run_id}/prd/prd-final.md  (to cross-check against AC-level claims)
  Output file:
    - team-{run_id}/verify/verdict.md
  Prompt:
    "You are the independent verify-judge. You have NOT reviewed the
     diff yourself — that was done by Stage A and Stage B reviewers.
     Your job: read their defect registries and issue the
     authoritative VERDICT at the stage level. Use the vocabulary:
     passed | failed_fixable | failed_unfixable.
       passed: no critical/major defects open.
       failed_fixable: defects present but team-fix can plausibly
                       resolve them.
       failed_unfixable: defects arising from PRD contradictions,
                         invariant violations, or external blockers
                         that no fix iteration will resolve.
     Write STRUCTURED_OUTPUT_START/END markers with VERDICT line,
     CRITICAL_COUNT, MAJOR_COUNT, MINOR_COUNT, and per-defect
     BLOCKING_DEFECT lines.
     Adversarial mandate: 100% passed rate = you are broken."
```

## Integration 5 — Per-Fix Verifier (`team-fix`, Always Required)

Same pattern as verify-judge but scoped to one defect + one fix. Built into `/team`, no external dependency. See SKILL.md Step 6.

## Degraded-Mode Tagging

Any run that used any degraded fallback surfaces a line at the top of `SUMMARY.md`:

```markdown
## Verification Mode: DEGRADED

The following integrations were not available; fallbacks were used:
- deep-design: not installed — plan adversarial review ran single-pass architect fallback.
- deep-qa: not installed — team-verify Stage A ran single-pass code-reviewer fallback.

Output quality is measurably lower than the integrated path. Consider
installing the missing skills and re-running critical work.
```

Never silently substitute degraded output. The tag is the contract with the user.

## Interaction With `team-prd` (No External Integration)

`team-prd` uses only `/team`-internal agents: `analyst`, `critic`, `falsifiability-judge`. There is no external skill dependency at this stage. The `critic` + `falsifiability-judge` pair implements the independent-adversarial-review pattern inline — no `deep-design` invocation needed here because the artifact under review (PRD) is simpler than a full design spec and the critic + falsifiability gate is sufficient.

Why not call `deep-design` on the PRD too? Cost. `deep-design`'s iterative DFS is overkill for PRD validation; the single-pass critic + falsifiability judge captures the 80% of value at 20% of the cost.

## Summary of Required vs Optional Integrations

| Integration | Stage | Required | Degrades To |
|---|---|---|---|
| `deep-design` | team-plan | Optional (triggers on complexity threshold) | single-pass `architect` agent |
| `deep-qa --diff` | team-verify Stage A + per-worker Stage A | Required by default | single-pass `code-reviewer` agent |
| code-quality reviewer (Stage B) | team-verify + per-worker | Always required (internal) | n/a |
| verify-judge | team-verify | Always required (internal) | n/a |
| per-fix verifier | team-fix | Always required (internal) | n/a |
| plan-validator | team-plan | Always required (internal) | n/a |
| PRD critic + falsifiability judge | team-prd | Always required (internal) | n/a |

The skill never fully fails to verify. It only degrades quality with explicit tagging.
