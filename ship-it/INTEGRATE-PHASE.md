# Phase 5: Integrate

Assemble all modules, verify the full build, run smoke tests, and scan for residual stubs. Any failure routes through `/loop-until-done` — no coordinator-authored code fixes.

## Why this phase exists

Components pass unit tests individually but may fail when assembled:
- Import paths don't resolve across module boundaries
- Type mismatches between module exports and consumer imports
- Circular dependency issues that only appear at runtime
- Missing re-exports in barrel files
- Environment/config assumptions that differ between modules
- Entry-point wiring missing a module

Summon-style tools skip this phase. That's why they produce code that compiles but doesn't work.

## Process

Phase 5 is inline to the coordinator (not delegated), but evaluations are still gated — the phase-gate subagent reads outputs and renders the verdict, not the coordinator.

### Step 1: Full build

1. Update `state.json`: `phases.integrate.spawn_time_iso = <iso>`, `status = "in_progress"`.
2. Run the production build:
   - Node: `npm run build`
   - Python: `python -m py_compile src/**/*.py` or `python -m build` (if packaging to sdist/wheel)
3. Capture full output at `ship-it-{run_id}/integrate/build-output.txt`. Exit code must be 0.

If build fails: synthesize a one-story PRD with the failure as the acceptance criterion and invoke `/loop-until-done --max-iter=3`. Do NOT hand-patch.

Common integration failures (`/loop-until-done` handles the fix):

| Error | Hint for fix loop |
|-------|-------------------|
| `Cannot find module './foo'` | Import path resolution; ESM needs `.js` extensions |
| `Type X is not assignable to type Y` | One module diverged from types.ts (impossible if immutability invariant holds) |
| `Circular dependency detected` | Extract shared logic into a third module |
| `Export 'X' was not found in 'Y'` | Check barrel exports (index.ts files) |

### Step 2: Entry-point startup probe

The entry point (CLI, MCP server, API) must import from all modules and start without crashing.

1. For CLI: `node dist/cli.js --help` — must print usage info, not a stack trace
2. For MCP server: spawn with short timeout (`timeout 5 node dist/index.js 2>&1 || true`) — must show "connecting" or "error: connection failed", not a crash
3. For library: write a 3-line import test — `import { publicApi } from './dist/index.js'; console.log(Object.keys(publicApi))`

Capture output at `ship-it-{run_id}/integrate/startup-probe.txt`.

If the probe fails: route via `/loop-until-done` with the failure as a new acceptance criterion.

### Step 3: Smoke tests

Write 2-3 end-to-end tests exercising the ACTUAL PRODUCT, not just individual functions. These tests are added by a fresh `/team` or `/loop-until-done` invocation — not by the coordinator — to maintain the two-stage-review discipline.

1. Synthesize a one-story PRD: "Add smoke tests that exercise the public interface end-to-end with real code (no mocks)". Include concrete verification commands.
2. Invoke `/loop-until-done --prd ship-it-{run_id}/integrate/smoke-prd.json --max-iter=2`.
3. After smoke tests exist, run the full test suite again and capture output at `ship-it-{run_id}/integrate/smoke-output.txt`.

Smoke tests must:
- Use real code (no mocks)
- Test the public interface (what a user would call)
- Verify output is useful (not just "didn't crash")

Template guidance (for the `/loop-until-done` worker, not the coordinator):

- For MCP server: spawn the server, send a tool call, verify response structure
- For CLI: run the CLI with sample input, verify expected output
- For library: import the public API, call main functions, verify end-to-end flow

### Step 4: Stub/placeholder scan

Run:
```bash
grep -rn "TODO\|FIXME\|PLACEHOLDER\|throw new Error('Not implemented')\|pass  # TODO" src/ test/
```

Capture output at `ship-it-{run_id}/integrate/stub-scan.txt` with the structured block from [FORMAT.md](FORMAT.md).

Rule: `UNANNOTATED_COUNT == 0` is required to advance. Each match must either be removed or annotated with a trailing comment explaining why it's intentional. The annotation is the evidence — "known limitation" in the coordinator's head is not annotation.

If matches remain: route via `/loop-until-done` to remove or annotate. The coordinator does not edit the files.

## Iron-law gate (Phase 5 → Phase 6)

Fresh phase-gate subagent reads evidence. Required:
- `integrate/build-output.txt` with exit code 0
- `integrate/startup-probe.txt` showing non-crash startup
- `integrate/smoke-output.txt` with all smoke tests passing AND all prior unit tests still passing (no regressions)
- `integrate/stub-scan.txt` with `UNANNOTATED_COUNT == 0`
- `integrate/phase-gate.md` with `ADVANCE: true`

Any missing/unparseable → `ADVANCE: false`.

## Anti-patterns

- Coordinator hand-patching an import path in integrate/. Violation of rule 3 (two-stage review on source modifications). Route via `/loop-until-done`.
- Coordinator deciding a TODO is fine without annotating it. Violation of rule 8 (no self-approval). Either annotate or remove.
- Coordinator running smoke tests with mocks to get them to pass. Violation of smoke-test charter. Smoke tests use real code.
- Accepting a flaky smoke test. If it's not reproducibly passing, it's failing. Fix the flakiness or remove the test (and document why).
