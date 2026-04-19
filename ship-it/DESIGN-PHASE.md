# Phase 2: Design

Architect the project from the approved spec. Delegate consensus architectural work to `/deep-plan`; produce `DESIGN.md` in Ship-It's canonical shape; freeze the shared types contract for Phase 3.

## Process

1. Update `state.json`: `current_phase: "design"`, `phases.design.spawn_time_iso = <iso>`, `phases.design.status = "in_progress"`.
2. Invoke `/deep-plan` with arguments `--spec ship-it-{run_id}/spec/SPEC.md --output ship-it-{run_id}/design/` per [INTEGRATION.md](INTEGRATION.md). `/deep-plan` internally runs Planner → Architect → Critic independent agents with falsifiability-gated rejection. Ship-It does not re-implement any of that.
3. After completion, parse `design/consensus-termination.md`:
   - `consensus_reached_at_iter_N` → continue
   - `max_iter_no_consensus` or `user_stopped` → phase gate fails; terminate as `blocked_at_phase_2`
4. Read the consensus plan output (`design/deep-plan.md` or equivalent from `/deep-plan`).
5. Adapt the consensus plan into `ship-it-{run_id}/design/DESIGN.md` using the Ship-It design schema below. The file tree, shared-types pattern, and packaging layout are Ship-It concerns; the architectural content (module boundaries, API contracts, risk analysis) comes from `/deep-plan`. Do NOT author architectural content — only reshape the consensus output into the template.
6. Copy `design/DESIGN.md` to the project root as the live working copy for Phase 3 subagents.
7. Extract all shared types, interfaces, and enums into `types.ts` (or `types/__init__.py` for Python). This file becomes immutable for the rest of the run — enforced by `invariants.types_ts_immutable_after_design`.
8. Copy the `/deep-plan` ADR verbatim to `ship-it-{run_id}/design/adr.md`.

## Degraded-mode fallback

If `/deep-plan` is unavailable (detected at Phase 1 init), run the inline critic flow per [INTEGRATION.md](INTEGRATION.md). Tag all outputs with `VERIFICATION_MODE: degraded (no /deep-plan installed)`. Quality is measurably lower; surface in the completion report.

## DESIGN.md structure (Ship-It canonical shape)

```markdown
# Design: [Product Name]

## File Tree
```
project-root/
  src/
    index.ts          # Entry point / CLI
    server.ts         # [if MCP: McpServer registration]
    types.ts          # Shared types and interfaces (ALL modules import from here; IMMUTABLE after Phase 2)
    [module]/
      [module].ts     # Implementation
      [module].test.ts # Tests
  package.json
  tsconfig.json
  README.md
```

## Shared Types (types.ts)
[Every interface, type, and enum that crosses module boundaries. Single source of truth. Prevents divergence during parallel builds.]

## Module: [Name]
**Responsibility**: [One sentence]
**Public API**:
  - `functionName(input: Type): ReturnType` — [what it does]
**Dependencies**: [Which other modules it imports from]
**Error handling**: [What errors it throws/returns and when]

[Repeat for each module]

## Data Flow
[How data moves through the system — input to output. Include happy path and main error path.]

## External Dependencies
| Package | Version | Why |
|---------|---------|-----|
| [name] | [version] | [one-line reason] |

## Security Considerations
[Input validation, SQL injection prevention, auth, secrets handling — specific to this project]

## Build Wave Order (for Phase 3 /team)
- Wave 1: [modules with only types.ts deps]
- Wave 2: [modules depending on Wave 1]
- Wave 3: [...]

## Acceptance Criteria (falsifiable, from /deep-plan)
[Each one from the consensus plan, with a verification command. Used to seed Phase 4 test criteria if defects are found.]
```

## The shared types.ts pattern

ALL interfaces, types, and enums that cross module boundaries live in one file. Every coder subagent receives this file. This prevents:
- Two modules defining incompatible versions of the same interface
- Type drift during parallel implementation
- Integration failures from mismatched function signatures

The types file is written during the design phase and becomes immutable. `/team`'s subagents receive it with explicit "DO NOT MODIFY" instructions. Ship-It tracks immutability via `invariants.types_ts_immutable_after_design` — if it flips to false, the run is invalid.

## Dependency ordering

Identify which modules depend on which. Draw a dependency graph. The wave order is captured in DESIGN.md so `/team` can honor it during Phase 3.

Example:
```
types.ts       → (no deps, frozen in Phase 2)
utils/format   → depends on types
db/connection  → depends on types
analysis/      → depends on types, db/
tools/         → depends on types, analysis/, db/
server.ts      → depends on types, tools/
index.ts       → depends on server
```

Build order: types (already frozen) → utils + db (parallel Wave 1) → analysis (Wave 2) → tools (Wave 3) → server (Wave 4) → index (Wave 5).

## Iron-law gate (Phase 2 → Phase 3)

Fresh phase-gate subagent reads evidence. Required:
- `design/DESIGN.md` with all required sections
- `design/adr.md` from `/deep-plan`
- `design/consensus-termination.md` with `CONSENSUS_LABEL|consensus_reached_at_iter_N` (or degraded-mode tag)
- `types.ts` written to project root and compiling (skeleton must pass `npx tsc --noEmit` / `python -m py_compile`)

Any missing/unparseable → `ADVANCE: false` → terminate as `blocked_at_phase_2`.
