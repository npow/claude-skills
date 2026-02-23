# Phase 1: Spec

Transform a raw idea into a formal, unambiguous specification.

## Input

The user's idea description — could be one sentence or a full plan document (like gap-finder output).

## Process

1. Read the idea description thoroughly.
2. Identify ambiguities — anything that could be interpreted two ways.
3. Write `SPEC.md` in the project root with the structure below.
4. Present SPEC.md to the user and ask for confirmation before proceeding. Do NOT auto-advance.

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

## Quality gate

The user must approve SPEC.md before Phase 2 begins. If the user requests changes, revise and re-present. No implementation code is written before spec approval.

## What NOT to do

- Do not include implementation details (file names, class names, algorithms) — that's Phase 2.
- Do not pad the spec with obvious requirements ("must be fast", "must be secure") — only project-specific criteria.
- Do not list technologies you haven't verified exist and work (check npm/PyPI if unsure).
