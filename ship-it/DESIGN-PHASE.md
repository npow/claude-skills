# Phase 2: Design

Architect the project from the approved spec. Produce a design document, then have it reviewed by a critic subagent.

## Process

1. Read SPEC.md.
2. Write DESIGN.md with the structure below.
3. Launch a **critic subagent** (Task tool, subagent_type: general-purpose) with prompt:
   - "You are a senior software architect reviewing a design document. Read SPEC.md and DESIGN.md. Find: (a) missing error handling, (b) API inconsistencies, (c) circular dependencies, (d) unclear module boundaries, (e) missing data validation. Be specific — cite file names and function signatures. If the design is acceptable, say APPROVED. If not, list specific changes needed."
4. If the critic says APPROVED, proceed to Phase 3.
5. If the critic rejects, revise DESIGN.md and re-submit. Max 3 rounds.
6. If still rejected after 3 rounds, present both the design and the critic's concerns to the user for a decision.

## DESIGN.md structure

```markdown
# Design: [Product Name]

## File Tree
```
project-root/
  src/
    index.ts          # Entry point / CLI
    server.ts         # [if MCP: McpServer registration]
    types.ts          # Shared types and interfaces (ALL modules import from here)
    [module]/
      [module].ts     # Implementation
      [module].test.ts # Tests
  package.json
  tsconfig.json
  README.md
```

## Shared Types (types.ts)
[Define every interface, type, and enum that crosses module boundaries. This file is the single source of truth that all modules reference. This prevents divergence during parallel builds.]

## Module: [Name]
**Responsibility**: [One sentence]
**Public API**:
  - `functionName(input: Type): ReturnType` — [what it does]
**Dependencies**: [Which other modules it imports from]
**Error handling**: [What errors it throws/returns and when]

[Repeat for each module]

## Data Flow
[How data moves through the system — from input to output. Include the happy path and the main error path.]

## External Dependencies
| Package | Version | Why |
|---------|---------|-----|
| [name] | [version] | [one-line reason] |

## Security Considerations
[Input validation, SQL injection prevention, auth, secrets handling — specific to this project]
```

## The shared types.ts pattern

This is the key improvement over naive parallel builds. ALL interfaces, types, and enums that cross module boundaries live in one `types.ts` (or `types/` directory). Every coder subagent receives this file. This prevents:
- Two modules defining incompatible versions of the same interface
- Type drift during parallel implementation
- Integration failures from mismatched function signatures

The types file is written DURING the design phase, not during build. It is the contract.

## Dependency ordering

Identify which modules depend on which. Draw a dependency graph. Components at the leaves (no dependencies) can build in parallel. Components that depend on other components build after their dependencies.

Example:
```
types.ts       → (no deps, built first as part of design)
utils/format   → depends on types
db/connection  → depends on types
analysis/      → depends on types, db/
tools/         → depends on types, analysis/, db/
server.ts      → depends on types, tools/
index.ts       → depends on server
```

Build order: types (design phase) → utils + db (parallel) → analysis (after db) → tools (after analysis + db) → server → index
