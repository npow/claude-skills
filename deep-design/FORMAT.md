# Output Formats

## Per-Angle Critique File

Each critic writes to `deep-design-critiques/{angle_id}.md`:

```markdown
# {angle_id}: {critique question}
**Dimension:** {dimension}
**Depth:** {depth}
**Parent:** {parent_id or "seed"}
**Spec Version Reviewed:** {version}
**Date:** {date}

## Flaws Found

### Flaw: {title}
**Severity:** critical | major | minor
**Scenario:**
[A concrete, specific scenario demonstrating the flaw. Not abstract — describe actual user/player behavior step by step.]

**Root Cause:**
[WHY this is broken. The underlying design assumption that fails.]

**Suggested Fix Direction:**
[How to address the root cause. Not a band-aid — a structural fix.]

**Cascading Risks:**
[Could this fix introduce new problems? What should be checked?]

---

### Flaw: {title}
[same structure, repeat for each flaw found]

---

## GAP_REPORT (optional — use when a previously closed flaw was insufficiently fixed)

If a prior fix addressed the symptoms but not the root cause, file a GAP_REPORT rather than a new flaw:

```
GAP_REPORT: {"references_flaw_id": "flaw_007", "gap_description": "Fix scoped only to the named component; same invariant violation occurs in the orchestrator path which was not updated"}
```

Rules:
- `references_flaw_id` must be a known flaw ID (from the Known Flaws file)
- This bypasses the dedup list — you may file it even if the flaw title appears in known flaws
- Does NOT consume a challenge token
- The coordinator will re-open the referenced flaw for redesign

---

## New Critique Angles Discovered

1. **{question}** — Dimension: {existing_dim|NEW: new_dim_name} — Priority: {high/medium/low}
   Why: {1 sentence on why this angle matters}

[List only the single highest-value new angle. Cap is 1 per round for spec-derived critics. If truly no new angles exist, write: "None — this dimension is thoroughly covered."]

## New Dimensions Discovered

[List any entirely new axes of critique not in the original dimension map.]
[If none: "None — all findings fit within existing dimensions."]

## Mini-Synthesis

[REQUIRED. ≥3 sentences covering:]
[1. What failure modes this angle revealed about the design]
[2. How these findings connect to or differ from other explored angles (if known)]
[3. What this changes about your understanding of the design's core risks]

[This section is what the coordinator reads for final synthesis — make it count.]

## Exhaustion Assessment

**Score: {1-5}**
- 1 = barely scratched the surface of this angle
- 2 = found obvious issues but deeper problems likely exist
- 3 = covered the main failure modes
- 4 = thorough critique, only minor gaps
- 5 = this angle is fully explored, nothing significant left

**What's missing (if score < 4):**
[Specific gaps a follow-up critique should target]

SEVERITY_CLAIMS_START
SEVERITY|{flaw_id_placeholder}|{title}|critical|major|minor
SEVERITY|{flaw_id_placeholder}|{title}|major
SEVERITY_CLAIMS_END

STRUCTURED_OUTPUT_START
FLAW|{system_assigned_id}|{title}|{one_line_scenario}
FLAW|{system_assigned_id}|{title}|{one_line_scenario}
GAP_REPORT|{references_flaw_id}|{gap_description}
NEW_ANGLE|{dimension}|{question}
STRUCTURED_OUTPUT_END
```

Key rules for the structured section:
- SEVERITY_CLAIMS block is STRIPPED by coordinator before creating judge input. The original file is immutable.
- Flaw IDs in STRUCTURED_OUTPUT are assigned by coordinator after parsing (not critic-chosen). Critics use a placeholder title; coordinator assigns `flaw_{N}` IDs.
- Pipe characters in field values: parser splits on first pipe only per field. No escaping needed.
- Files without STRUCTURED_OUTPUT_START/END markers are treated as failed (not partially consumed).
- New critique angles: cap is **1 per round** for spec-derived critics. List only the single highest-value new angle. (Outside-frame critics may file up to 2.)

---

## Outside-Frame Critic Output Format

Outside-frame critics are seeded from the original concept description only (not the current spec). Their output uses the following format:

```markdown
# outside-frame: {run_id} round {N}
**Seeded from:** Original concept description only (not current spec)
**Date:** {date}

## What's Missing

### Missing Component: {title}
**Scenario:** A working implementation of {concept} would require [X] but the spec never mentions it.
**Root Cause:** [Why this omission matters]
**Suggested Addition:** [What should be specified]

[repeat for each missing component found]

## New Critique Angles Discovered
1. {question} — Dimension: {dim} — Priority: {priority}
   Why: {reason}
2. {question} (outside-frame critics may file up to 2)

SEVERITY_CLAIMS_START
SEVERITY|{placeholder}|{title}|major
SEVERITY_CLAIMS_END

STRUCTURED_OUTPUT_START
FLAW|{placeholder}|{title}|{scenario}
NEW_ANGLE|{dimension}|{question}
STRUCTURED_OUTPUT_END
```

---

## Design Spec Version Format

Each spec version is written to `deep-design-specs/v{N}-{label}.md`:

```markdown
# Design Spec: {concept}
**Version:** {version}
**Date:** {date}
**Changes from previous:** {summary of what changed and why}

## Core Concept
[Elevator pitch — 2-3 sentences]

## Design Goals
- [What this design is trying to achieve]
- [What experience/feeling/outcome it optimizes for]
- [What it explicitly does NOT try to do]

## Detailed Design

### {Section 1: e.g., Game Flow}
[Detailed description of this aspect]

### {Section 2: e.g., Mechanics}
[Detailed description]

### {Section 3: e.g., Technical Architecture}
[Detailed description]

[...as many sections as needed]

## Design Decisions Log
| Decision | Rationale | Flaw Addressed | Version Introduced |
|----------|-----------|----------------|-------------------|
| {what} | {why} | {flaw_id or "initial"} | {version} |

## Known Tradeoffs
- **{tradeoff}**: We chose X over Y because {reason}. The cost is {downside}.

## Open Questions
- {questions that need external input or testing to resolve}
```

## Final Spec: `deep-design-spec.md`

```markdown
# Deep Design Spec: {concept}
**Generated:** {date}
**Critique Rounds:** {N}
**Angles Explored:** {count}
**Dimensions Covered:** {count}/{total}
**Flaws Found:** {total} ({critical} critical, {major} major, {minor} minor)
**Flaws Resolved:** {fixed_count} fixed, {accepted_count} accepted
**Convergence:** {yes | no — hit max_rounds}

## Executive Summary
[3-5 paragraphs. The design, its key innovations, and why it works. Written for someone who will NOT read the full spec.]

## Core Concept
[The elevator pitch. What is this? Why does it matter? What's the core insight?]

## Design Goals & Non-Goals
### Goals
- [What this design optimizes for]

### Non-Goals
- [What this design explicitly does NOT try to do]

## Detailed Design

### {Section 1}
[Full design description]

### {Section 2}
[Full design description]

[...all sections]

## How It Plays / How It Works
[A complete walkthrough of the user/player experience from start to finish. Concrete, not abstract.]

## Design Decisions & Rationale

### {Decision 1: e.g., "Open-ended questions only, no trivia"}
**Flaw addressed:** {flaw title and ID}
**What we considered:** {alternatives explored}
**What we chose:** {the decision}
**Why:** {rationale — connect to root cause}
**Tradeoff:** {what we gave up}

### {Decision 2}
[same structure]

## Battle-Tested Properties
[What aspects of the design have been thoroughly stress-tested? What can you be confident about?]

## Accepted Tradeoffs
| Tradeoff | Rationale | Flaw ID |
|----------|-----------|---------|
| {what we sacrificed} | {why it's acceptable} | {flaw_id} |

## Remaining Risks
[Honest assessment of what could still go wrong. These are minor flaws or risks that don't warrant redesign but should be monitored.]

## Open Questions
[Things that can't be resolved through design critique alone — need user testing, prototyping, or domain expertise.]

## Implementation Notes
[Key technical considerations, suggested architecture, gotchas for the implementer.]

## Appendix: Full Flaw Registry
| ID | Title | Severity | Status | Resolution |
|----|-------|----------|--------|------------|
| flaw_001 | {title} | critical | fixed | {brief fix description} |

## Appendix: Critique Coverage
| Dimension | Angles Explored | Key Flaws | Coverage |
|-----------|----------------|-----------|----------|
| {dim} | {count} | {flaw titles} | full/partial/minimal |

## Methodology
- Concept: {concept}
- Rounds: {N}
- Angles explored: {count}
- Critics per round: {max_agents_per_round}
- Duplication budget: 2
- Max depth: {max_depth}
- Termination reason: {convergence | max_rounds}
```
