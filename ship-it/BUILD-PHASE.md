# Phase 3: Build

Implement all modules using parallel subagents with code review.

## Prerequisites

- SPEC.md approved by user
- DESIGN.md approved by critic subagent
- `types.ts` (shared types) already written during design phase
- `package.json` / `tsconfig.json` scaffolded with dependencies installed

## Process

### Step 1: Scaffold the project

Before launching build subagents, set up the project skeleton:
1. Create directory structure from DESIGN.md file tree
2. Write `package.json` with all dependencies from DESIGN.md
3. Write `tsconfig.json` (or equivalent config)
4. Run `npm install` (or equivalent)
5. Write `types.ts` with all shared types from DESIGN.md
6. Verify the skeleton compiles: `npx tsc --noEmit` should pass

### Step 2: Determine build order

From DESIGN.md dependency graph, identify:
- **Wave 1**: Modules with no internal dependencies (only depend on types.ts)
- **Wave 2**: Modules that depend on Wave 1 modules
- **Wave 3**: Modules that depend on Wave 2 modules
- etc.

Modules within the same wave build in parallel. Waves execute sequentially.

### Step 3: Launch build subagents (per wave)

For each wave, launch one `coder_loop` subagent per module. The `coder_loop` subagent type has built-in coder → reviewer → arbitrator cycling.

**Subagent prompt template** (adapt per module):

```
You are implementing the [MODULE_NAME] module for [PROJECT_NAME].

## Context files to read:
- [PROJECT_PATH]/SPEC.md — product specification
- [PROJECT_PATH]/DESIGN.md — architecture and module API contracts
- [PROJECT_PATH]/src/types.ts — shared types (DO NOT MODIFY THIS FILE)

## Your task:
Implement [PROJECT_PATH]/src/[MODULE_PATH]/[MODULE_NAME].ts

## Requirements from DESIGN.md:
[Paste the module's section from DESIGN.md — responsibility, public API, dependencies, error handling]

## Rules:
1. Import all shared types from '../types.js' (or correct relative path)
2. Implement EVERY function listed in the module's public API from DESIGN.md
3. Match function signatures EXACTLY as specified in DESIGN.md
4. Handle all error cases listed in DESIGN.md
5. No placeholder/stub implementations — every function must have real logic
6. No console.log in production code — use proper error returns
7. Write the test file alongside: [MODULE_NAME].test.ts with tests for every public function + error paths
```

### Step 4: Collect results

After each wave completes:
1. Read all generated files
2. Verify they compile: `npx tsc --noEmit`
3. If compilation fails, identify which module has the error and re-run its coder_loop with the error message
4. Once the wave compiles, proceed to the next wave

### Parallelization rules

- **DO parallelize**: Independent modules in the same wave (e.g., utils + db in wave 1)
- **DO NOT parallelize**: Modules that depend on each other (e.g., tools depends on analysis)
- **DO NOT parallelize** more than 5 subagents simultaneously — diminishing returns and context confusion
- **ALWAYS** include types.ts and DESIGN.md in every subagent's context

### Handling build subagent failures

| Failure | Response |
|---------|----------|
| Subagent produces stub/placeholder code | Re-run with explicit instruction: "No stubs. Implement real logic for every function." |
| Subagent modifies types.ts | Revert types.ts to the design-phase version. Re-run the subagent with "DO NOT MODIFY types.ts" |
| Subagent imports from wrong path | Fix the import path and re-run compilation check |
| Subagent misses a function from DESIGN.md | Diff the module's public API against what was implemented. Re-run with the missing functions listed explicitly |
| coder_loop hits max iterations without approval | Read the arbitrator's last rejection reason. Fix the specific issue manually, then move on |
