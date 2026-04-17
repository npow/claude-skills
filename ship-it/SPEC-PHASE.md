# Phase 1: Spec

Transform a raw idea into a formal, unambiguous specification. Phase 1 is the only phase where the coordinator authors the primary artifact directly; the user is the independent judge.

## Input

The user's idea description — one sentence to a full plan document.

## Process

1. Generate `run_id = $(date +%Y%m%d-%H%M%S)`. Create `ship-it-{run_id}/spec/` and write initial `state.json` (see [STATE.md](STATE.md)).
2. Read the idea description thoroughly.
3. Identify ambiguities — anything that could be interpreted two ways.
4. Write `SPEC.md` in the project root with the structure below.
5. Copy to `ship-it-{run_id}/spec/SPEC.md` (canonical evidence copy).
6. Present SPEC.md to the user. Ask for explicit approval. Do NOT auto-advance.
7. Record the user's response verbatim in `ship-it-{run_id}/spec/user-approval.md` per the schema in [FORMAT.md](FORMAT.md).
8. If `USER_APPROVED|false` or `APPROVAL_SCOPE|partial|conditional`: revise SPEC.md in the direction the user indicated, re-save both copies, re-present. Max 3 rounds. If still not approved after 3 rounds, surface as `blocked_on_user_approval` and halt.

## SPEC.md structure

```markdown
# [Product Name]

## Problem
[1-2 sentences: what pain does this solve?]

## Target User
[Specific persona: "SaaS founders with <$50K MRR who check metrics daily"]

## Core Features (MVP)
1. [Feature] — [one-line description of what it does]
2. [Feature] — [one-line description]
3. [Feature] — [one-line description]

## Non-Goals (explicitly out of scope for MVP)
- [Thing we are NOT building]
- [Thing we are NOT building]

## Tech Stack
- Language: [TypeScript/Python/etc]
- Framework: [if any]
- Key dependencies: [list]
- Deployment: [npm package / CLI / web service / etc]

## Success Criteria
- [ ] [Concrete, testable criterion — "MRR calculation matches Stripe dashboard within 1%"]
- [ ] [Another criterion]
- [ ] [Another criterion]

## API / Tool Interface
[For MCP servers: list each tool with name, inputs, outputs]
[For CLIs: list each command with flags and output format]
[For libraries: list each public function with signature]
```

## Iron-law gate (Phase 1 → Phase 2)

A fresh `phase-gate` subagent reads the evidence files and emits the structured verdict documented in [FORMAT.md](FORMAT.md). Required evidence:

- `ship-it-{run_id}/spec/SPEC.md` with all required sections (Problem, Target User, Core Features, Non-Goals, Tech Stack, Success Criteria, API)
- `ship-it-{run_id}/spec/user-approval.md` with `USER_APPROVED|true`
- Absence of any section → `ADVANCE: false`
- `USER_APPROVED|false` → `ADVANCE: false`

`APPROVAL_SCOPE|partial|conditional` with listed conditions → `ADVANCE: true` but the conditions are carried into the Phase 6 completion report as Accepted Tradeoffs.

## What NOT to do

- Do not include implementation details (file names, class names, algorithms) — that's Phase 2.
- Do not pad the spec with obvious requirements ("must be fast", "must be secure") — only project-specific criteria.
- Do not list technologies you haven't verified exist and work (check npm/PyPI if unsure).
- Do not infer user approval from ambiguous responses ("sounds ok", "let's see"). Prompt again for explicit yes.
- Do not advance to Phase 2 before `USER_APPROVED|true`. The gate is load-bearing.
