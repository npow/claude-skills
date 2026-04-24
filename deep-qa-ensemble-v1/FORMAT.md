# Output Formats

## Per-Angle Critique File

Each QA critic writes to `deep-qa-{run_id}/critiques/{angle_id}.md`:

```markdown
# {angle_id}: {critique question}
**Artifact Type:** {artifact_type}
**QA Dimension:** {dimension}
**Depth:** {depth}
**Parent:** {parent_id or "seed"}
**Date:** {date}

## Defects Found

### Defect: {title}
**Severity:** critical | major | minor

**Scenario:**
[A concrete, specific scenario demonstrating the defect. Not abstract — describe a real consumer
of this artifact encountering the problem step by step. Who encounters it? What do they do?
What goes wrong? What is the consequence?]

**Root Cause:**
[WHY this is broken. The underlying gap, assumption, or omission — not just the symptom.]

**Suggested Remediation Direction (optional):**
[How to address the root cause. Brief — the artifact owner decides how to fix it.
Do NOT prescribe a specific solution. Identify the category of fix needed.]

---

### Defect: {title}
[same structure, repeat for each defect found]

---

## New QA Angles Discovered

1. **{question}** — Dimension: {existing_dim | NEW: new_dim_name} — Priority: {high/medium/low}
   Why: {1 sentence on why this angle matters}

[List 1-3 genuinely novel angles. NOT rephrased versions of already-explored angles.]
[If no new angles: "None — this dimension is thoroughly covered."]

## New Dimensions Discovered

[List any entirely new QA axes not in the original dimension map.]
[If none: "None — all findings fit within existing dimensions."]

## Mini-Synthesis

[REQUIRED. ≥3 sentences covering:]
[1. What defect patterns this angle revealed about the artifact]
[2. How these findings connect to or differ from other explored angles (if known)]
[3. What this changes about your understanding of the artifact's overall quality risks]

[This section is what the coordinator reads for final synthesis — make it count.]

## Exhaustion Assessment

**Score: {1-5}**
- 1 = barely scratched the surface of this angle
- 2 = found obvious issues but deeper problems likely exist
- 3 = covered the main defect patterns, some depth
- 4 = thorough QA, only minor gaps remain
- 5 = this angle is fully QA'd, nothing significant left

**What's missing (if score < 4):**
[Specific gaps a follow-up QA pass should target]
```

---

## Severity Guide by Artifact Type

### `doc` (document/spec)
- **critical**: A referenced component is entirely unspecified; the spec cannot be implemented; a fundamental requirement is missing; two sections directly contradict on a load-bearing claim
- **major**: Significant ambiguity — two reasonable implementations would differ materially; a required error path is unspecified; an assumption is unstated but load-bearing
- **minor**: Wording could be clearer; example doesn't perfectly match the rule; minor inconsistency unlikely to cause misimplementation

### `code`
- **critical**: Data loss, security vulnerability, incorrect output for valid inputs on the happy path, panic/crash on valid inputs
- **major**: Error path entirely unhandled; significant performance regression; untestable code structure; missing auth check
- **minor**: Style/readability issue; minor inefficiency; naming inconsistency

### `research`
- **critical**: Key claim in the conclusion not supported by any cited evidence; citation is fabricated or points to a source that says the opposite; fundamental logical error in the argument
- **major**: Logical leap from evidence to conclusion; significant counter-evidence not acknowledged; major coverage gap on a central topic; numerical claim misattributed
- **minor**: Minor imprecision; claim could be better sourced; wording could be more precise

### `skill`
- **critical**: Skill can be made to violate its core safety rules via injection; runaway loop possible without hard stop; fundamental instruction conflict that makes the skill's core behavior undefined
- **major**: Significant instruction conflict on a common path; important edge case unhandled; structured output format has no fail-safe; cost circuit breaker missing
- **minor**: Minor ambiguity; cosmetic inconsistency; one-off edge case not covered

---

## Final QA Report: `deep-qa-{run_id}/qa-report.md`

```markdown
# QA Report: {artifact_name}
**Artifact Type:** {artifact_type}
**Generated:** {date}
**Rounds completed:** {N}
**Termination:** {see Phase 5 label table — never leave blank}
**Invocation:** {interactive | automated (--auto)}
**Files examined:** {list of files included in artifact.md}
**Angles explored:** {count} ({timed_out} timed out, {spawn_exhausted} spawn-exhausted)
**Dimensions covered:** {count}/{total}
**Defects found:** {total} ({critical} critical, {major} major, {minor} minor)
**Disputed:** {count}
**Open defects:** {count}

> ⚠️ [Show whenever ANY required category is uncovered, regardless of termination label]:
> Coverage incomplete. Uncovered required categories: {list}. See Known Gaps section.

---

## Executive Summary

[3-5 paragraphs. The overall quality assessment, key defects, and what matters most.
Written for someone who will NOT read the full report.
Include: highest-severity defects, systemic patterns (if any), and the most important gap to address first.]

---

## Critical Defects

[Only present if critical defects exist. If none: "No critical defects found."]

### {defect_id}: {title}
**Dimension:** {dimension}
**Severity:** critical

**Scenario:** [concrete scenario]

**Root Cause:** [underlying gap or omission]

**Suggested Remediation:** [direction — brief]

**Status:** open | accepted: {rationale} | disputed: {rationale}

---

[Repeat for each critical defect]

---

## Major Defects

[Same structure as Critical Defects. If none: "No major defects found."]

---

## Minor Defects

| ID | Title | Dimension | Scenario Summary |
|----|-------|-----------|-----------------|
| defect_xxx | {title} | {dim} | {1 line} |

---

## Defect Patterns

[Cross-cutting themes in the defects found.]
["N defects share the same root cause: X"]
["The {dimension} dimension produced {N} defects — suggesting a systemic issue with {pattern}"]
["Dimensions with zero defects: {list} — note: absence of defects may reflect shallow coverage, not quality"]

---

## Disputed Defects

[Defects that failed validation checks. NOT suppressed — documented here with rationale.]

| ID | Original Severity | Title | Dispute Rationale |
|----|------------------|-------|------------------|
| defect_xxx | major | {title} | {why disputed — which validation check it failed} |

[If none: "No disputed defects."]

---

## Verification Results (research artifacts only)

Checked: {X} of {Y} claims ({X/Y}%)
Sampling strategy: risk-stratified (single-source primary + numerical/statistical + contested)

Results:
- Citations accessible and matching: {N}
- Citations inaccessible (paywalled/404): {N}
- Citation mismatches flagged:
  - {claim}: {mismatch description}

⚠️ IMPORTANT LIMITATIONS:
- LLM number verification is unreliable — all numerical/statistical claims require manual verification against cited source
- This is a spot-check, not a comprehensive audit. {Y - X} claims were not checked.
- For high-stakes decisions, independently verify all primary claims.

---

## Coverage Assessment

| Dimension | Angles Explored | Defects Found | Coverage | Notes |
|-----------|----------------|---------------|----------|-------|
| {dim} | {count} | {count} | full/partial/minimal | {timed_out / shallow} |

### Required Category Coverage

| Category | Covered | Notes |
|----------|---------|-------|
| {cat} | ✓ / ✗ | {if ✗: what gap exists} |

### Known Gaps

[What aspects were NOT adequately QA'd? What would a follow-up pass focus on?]
[exhaustion score < 3 dimensions should be listed explicitly]

---

## Open Defects Register

| ID | Title | Severity | Dimension | Scenario Summary |
|----|-------|----------|-----------|-----------------|
| defect_001 | {title} | critical | {dim} | {1 line} |

[If no open defects: "All defects have been triaged (accepted, disputed, or won't-fix)."]

---

## Methodology

- Artifact: {artifact_name}
- Type: {artifact_type}
- Rounds: {N} of {max_rounds}
- Angles explored: {count} ({timed_out} timed out, {spawn_failed} spawn failed)
- Model tiers: Sonnet (depth 0-1 high), Haiku (depth 1 medium, depth 2+, severity judges, coordinator summaries)
- Termination: {label from Phase 5 table} — {M} frontier directions unexplored (if applicable)

⚠️ Honest coverage caveats:
- Dimensions are self-enumerated from artifact content — an unknown dimension cannot be covered
- Critics share the same model blind spots; systematic failures may not surface
- "Conditions Met" means coverage criteria were satisfied, not that the artifact has zero defects
- {N} angles timed out and were not re-explored; those areas may have uncovered defects
```
