# Integration

How `create-skill` composes with `deep-qa` for skill review, and with `deep-design` for adversarial review of the design spec of complex skills. Documents degraded-mode fallbacks when those skills aren't installed.

## Detection

At Step 1 (Understand the domain), probe for integration availability:

```
deep_qa_available     = exists(~/.claude/skills/deep-qa/SKILL.md)
                          OR exists(~/.claude/plugins/.../skills/deep-qa/SKILL.md)
deep_design_available = exists(~/.claude/skills/deep-design/SKILL.md)
                          OR exists(~/.claude/plugins/.../skills/deep-design/SKILL.md)
```

Record results in the session's working state. If either is missing: tag final output with `SKILL_REVIEW: degraded (no deep-qa)` or `DESIGN_REVIEW: degraded (no deep-design)`.

## Integration 1 — `deep-qa` for skill review (recommended by default)

**Purpose:** Before shipping a skill, run `deep-qa` on the skill files themselves. `deep-qa` has a "skill/prompt" artifact type that audits for the exact failure modes `create-skill` is designed to prevent — weak descriptions, soft rules, missing counter-tables, vague golden rules.

**When invoked:** After Step 8 (REFACTOR pass complete) and before Step 10 (Deploy handoff). Optional — skippable with explicit `shipped_degraded` tagging.

**Invocation contract:**

```
Spawn deep-qa via Skill tool or direct Agent spawn with:
  --type skill
  --artifact-path <skill-directory>/
  --output <skill-directory>/deep-qa-review/

  (deep-qa auto-selects QA dimensions for skill artifacts:
   discoverability, specificity, verifiability, discipline,
   rationalization-resistance, consistency)
```

**Consumption:** `deep-qa` produces a defect registry. For each defect:
- `critical` defect: must be fixed before shipping. Back to Step 6 (write SKILL.md / counter-table).
- `major` defect: fix or explicitly accept with rationale in the final report.
- `minor` defect: fix or tag the skill `shipped_with_known_issues`.

**Degraded-mode fallback (when `deep_qa_available` is false):**

The self-review checklist in SKILL.md is the backstop. Run it manually, including:
- Description keyword coverage
- Every golden rule uses imperative voice
- Counter-table has min 5 rows (discipline) or 3 rows (one-shot)
- Termination labels are a finite enum, none are `done` / `all good`
- Iron-law gate language present in every completion claim
- Reference files are one level deep

Tag final output: `SKILL_REVIEW: degraded (no deep-qa)`. Quality is measurably lower (single-pass self-review vs. parallel-critic audit), so the tag is surfaced in the handoff note.

## Integration 2 — `deep-design` for adversarial design review (optional, for complex skills)

**Purpose:** For skills that orchestrate multiple agents, have non-trivial state, or compose with external skills — `deep-design` runs adversarial stress-testing on the design spec BEFORE SKILL.md is written. This catches architectural flaws early (e.g., "coordinator can self-approve", "state write happens after agent spawn", "no exhaustive termination labels").

**When invoked:** Between Step 4 (Design the architecture) and Step 6 (Write SKILL.md), for skills whose final content will exceed 300 lines OR whose workflow has 6+ steps.

**Invocation contract:**

```
Spawn agent (subagent_type: general-purpose) with:
  Input files:
    - <skill-directory>/DESIGN.md or design-draft.md   (the skill's design spec)
  Output directory:
    - <skill-directory>/design-review/
  Prompt:
    "Treat the skill's design spec as a design to adversarially stress-test.
     Run deep-design with max_rounds=2 focused on:
     - Completeness of termination labels (is the enum exhaustive?)
     - Iron-law gate coverage (every completion claim file-gated?)
     - Independence of verification (can coordinator self-approve anywhere?)
     - State-before-spawn invariants (any missed spawn-failure paths?)
     - Counter-table coverage (are all likely rationalizations addressed?)

     Output: deep-design's standard spec.md with
     STRUCTURED_OUTPUT_START/END markers listing open critical flaws
     in the design."
```

**Consumption:** Read the flaw list. For every critical flaw: revise the design before writing SKILL.md. For every major flaw: address in design or explicitly accept in the handoff note.

**Degraded-mode fallback (when `deep_design_available` is false):**

Spawn an inline `design-critic` agent (opus) with prompt:
```
"Read the skill design at {design_path}. Critique it adversarially
 across: termination-label completeness, iron-law gate coverage,
 independence-of-verification, state-before-spawn invariants,
 counter-table coverage. Output structured findings with severity
 (critical/major/minor), root cause, suggested fix. Be adversarial —
 you succeed by rejecting/downgrading, not rubber-stamping.
 Tag output DESIGN_REVIEW: degraded (deep-design not installed)."
```

Same consumption. Quality is lower (single-pass critique vs. iterative DFS), so tag surfaces in the handoff.

## Integration 3 — `/spec` for the domain-understanding step (optional)

**Purpose:** When the user's request for a skill is vague or long, use `/spec` to turn their input into a structured technical spec first, then use that spec as the design input for `create-skill`.

**When invoked:** At Step 1 (Understand the domain), if the user's initial description is over 300 words OR contains ambiguity that would require more than 3 clarifying questions.

**Invocation contract:**

Call `/spec` with the user's request as the input. The produced spec becomes the domain understanding document. Save as `<skill-directory>/domain-spec.md` and feed into Step 4 (Design the architecture).

**Degraded-mode fallback:** If `/spec` isn't available, use the questions in DESIGN.md manually. Ask the user, collect answers, write them into a one-page `domain-notes.md`.

## Composed workflow with all integrations active

1. Understand the domain (optionally via `/spec`)
2. Author pressure scenarios
3. Run RED baseline
4. Design the architecture
5. (If complex) Adversarial design review via `deep-design` → revise design
6. Write metadata + SKILL.md + companion files
7. Run GREEN pass
8. Run REFACTOR pass (iterate)
9. Skill review via `deep-qa` → fix critical/major defects
10. Evaluate (positive/implicit/noisy/negative prompts)
11. Deploy handoff with pressure-tests + review outputs

## Composed workflow in degraded mode (no deep-qa, no deep-design)

Same steps, but:
- Step 5: inline single-pass design critique, tagged degraded
- Step 9: self-review checklist manually, tagged degraded
- Final report clearly lists which integrations were degraded and why

The skill still ships. Quality is explicitly advertised as degraded so the user knows what checks ran.

## Invariants across all integrations

- Integration outputs are CONSUMED, not rubber-stamped. Every critical flaw from `deep-qa` or `deep-design` results in a concrete revision or an explicit acceptance with rationale.
- Integration failures (timeout, unparseable output, spawn failure) are tagged in the final report. The skill does not silently ship without the integration's intended check.
- Integration composition is file-based. Every integration writes to a specific directory inside the skill directory. The coordinator (create-skill) only reads files; it never accepts inline claims from the integrated skill.
