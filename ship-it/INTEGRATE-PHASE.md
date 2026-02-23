# Phase 5: Integrate

Assemble all modules, verify the full build, and run smoke tests that exercise the actual product end-to-end.

## Why this phase exists

Components pass unit tests individually but may fail when assembled:
- Import paths don't resolve across module boundaries
- Type mismatches between what module A exports and module B expects
- Circular dependency issues that only appear at runtime
- Missing re-exports in barrel files
- Environment/config assumptions that differ between modules

Summon-style tools skip this phase. That's why they produce code that compiles but doesn't work.

## Process

### Step 1: Full build

```bash
# TypeScript
npm run build    # must exit 0

# Python
python -m py_compile src/**/*.py   # or similar
```

If the build fails, fix each error. Common integration failures:

| Error | Fix |
|-------|-----|
| `Cannot find module './foo'` | Check the import path. ESM needs `.js` extensions. |
| `Type X is not assignable to type Y` | One module diverged from types.ts. Diff against the design. |
| `Circular dependency detected` | Restructure: extract shared logic into a third module. |
| `Export 'X' was not found in 'Y'` | Check barrel exports (index.ts files). |

### Step 2: Wire up the entry point

The entry point (CLI, MCP server, API) imports from all modules and wires them together. Verify:
- The main entry point imports all modules and they resolve
- For CLI: `node dist/cli.js --help` works
- For MCP: `node dist/index.js` starts without crashing (test with a timeout)
- For API: the server starts and responds to a health check

### Step 3: Smoke tests

Write 2-3 end-to-end tests that exercise the ACTUAL PRODUCT, not just individual functions.

For an MCP server:
```typescript
// test/smoke.test.ts
// Spawn the MCP server, send a tool call, verify the response structure
```

For a CLI:
```typescript
// test/smoke.test.ts
// Run the CLI with sample input, verify it produces expected output
```

For a library:
```typescript
// test/smoke.test.ts
// Import the public API, call the main functions, verify end-to-end flow
```

Smoke tests must:
- Use the real code (no mocks)
- Test the public interface (what a user would call)
- Verify the output is useful (not just "didn't crash")

### Step 4: Run full test suite (unit + smoke)

```bash
npm test    # All unit tests + smoke tests must pass
```

If smoke tests fail but unit tests pass, the integration is broken. Debug by tracing the data flow from the smoke test input through the modules to find where it diverges from expected.

### Step 5: Verify no stubs/placeholders remain

```bash
grep -r "TODO\|FIXME\|PLACEHOLDER\|throw new Error('Not implemented')\|pass  # TODO" src/
```

If any are found, they must be implemented or explicitly removed with a comment explaining why.

## Gate

Phase 5 passes when:
- [ ] `npm run build` exits 0
- [ ] Entry point runs without crashing
- [ ] All smoke tests pass
- [ ] All unit tests still pass (no regressions)
- [ ] Zero TODO/FIXME/placeholder in source code
