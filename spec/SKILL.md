---
name: spec
description: |
  DEPRECATED — use `deep-design --spec` instead.
  Turns a conversation, idea, or discussion into an SDD-compatible spec.md.
  Use when the user asks to write a spec, technical spec, design doc, RFC, API design,
  data model, spec this out, turn this into a spec, write up the design, document this,
  implementation spec, spec for this feature.
argument-hint: "[feature or system to specify]"
allowed-tools: Write

category: design
capabilities: [loop-based]
input_types: [artifact-file, task, question]
output_types: [design-spec]
complexity: moderate
cost_profile: low
maturity: deprecated
metadata_source: inferred
---

# Spec

> **DEPRECATED**: This skill is now a thin wrapper around `deep-design --spec`. The standalone `spec` skill is maintained for backwards compatibility but all new development happens in deep-design.

## Routing

When invoked, this skill delegates to `deep-design --spec`:
- If `deep-design` is available: invoke it with `--spec` flag and pass through the argument.
- If not available: fall back to the inline workflow below.

## SDD-Compatible Output

The spec is written as `specs/{NNN-feature-name}/spec.md` following the Spec-Driven Development format:

```
specs/{NNN-feature-name}/
├── spec.md              # Feature specification
└── checklists/
    └── requirements.md  # Spec quality validation
```

### Required Sections

- *User Scenarios & Testing* — prioritized user stories (P1, P2, P3) with Given/When/Then acceptance scenarios. Each story must be independently testable.
- *Functional Requirements* — FR-001, FR-002, etc. Each testable and unambiguous.
- *Success Criteria* — SC-001, SC-002, etc. Technology-agnostic, measurable outcomes.
- *Key Entities* — if data is involved (entity, attributes, relationships).
- *Assumptions* — reasonable defaults documented here.
- *Edge Cases* — boundary conditions and error scenarios.

### Spec Quality Rules

- Focus on WHAT and WHY, never HOW. No implementation details (languages, frameworks, APIs).
- Success criteria must be measurable and technology-agnostic.
- Max 3 `[NEEDS CLARIFICATION]` markers (scope > security > UX priority).
- Every requirement must be testable.

## Fallback Workflow

If `deep-design` is unavailable, use this inline workflow:

> **Pace:** Spec authoring is load-bearing design work — choices made here propagate to implementation. Think carefully and step-by-step.

1. **Extract the core idea** — identify what system, feature, or API is being specified.
2. **Ask clarifying questions if needed (batched, max 3)** — present ALL as a single numbered batch.
3. **Create SDD directory** — scan `specs/` for next sequential prefix, create `specs/{NNN-name}/`.
4. **Draft spec.md** — write all required sections following the SDD format above.
5. **Generate checklists/requirements.md** — validate spec quality (no implementation details, testable requirements, measurable criteria, max 3 clarification markers).
6. **Self-correct** — if validation fails, fix and re-validate (max 3 iterations).
7. **Report** — print SDD_DIR path, spec status, and suggested next step (`deep-plan` or `deep-design --spec` for clarification).

## Golden Rules

1. **Problem before design.** Always define what and why before how.
2. **Non-Goals are valuable.** They define the boundary of the work.
3. **Success Criteria are mandatory.** Without measurable criteria there is no definition of done.
4. **Ask at most 3 clarifying questions, batched in one message.**
5. **Spec serves downstream tools.** The spec.md must be consumable by `deep-plan` for plan generation and by `autopilot` for the full SDD workflow.

## Follow-up Skills

| Next Step | Skill | Purpose |
|-----------|-------|---------|
| Clarify ambiguities | `deep-design --spec` | Adversarial stress-testing of the spec |
| Plan implementation | `deep-plan --spec specs/{NNN}/spec.md` | Produce plan.md + tasks.md |
| Build everything | `autopilot` | Full SDD workflow: specify → plan → tasks → implement |
