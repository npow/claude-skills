# Phase 4: Test

Run all tests, fix failures, repeat until green. This is the primary quality gate.

## Prerequisites

- All modules implemented (Phase 3 complete)
- Each module has a `.test.ts` / `_test.py` file from the build phase
- Project compiles (`tsc --noEmit` or equivalent passes)

## Process

### Step 1: Run all tests

```bash
npm test          # TypeScript/Node
# or
pytest            # Python
# or
vitest run        # If using vitest
```

Capture the full output including any failures.

### Step 2: If all tests pass → proceed to Phase 5

This is the happy path. Move to integration.

### Step 3: If tests fail → enter fix loop

For each failing test:

1. Read the error message and stack trace
2. Determine the category:
   - **Implementation bug**: The code is wrong, the test is right
   - **Test bug**: The test is wrong (testing the wrong thing, wrong assertion)
   - **Missing dependency**: An import or mock is missing
   - **Type error**: Types don't match between modules
3. Launch a **fixer subagent** (Task tool, subagent_type: coder_loop):

```
Fix the failing test in [PROJECT_PATH].

## Error output:
[paste full test failure output]

## Failing test file:
[paste test file path]

## Source file under test:
[paste source file path]

## Rules:
1. Read both the test file and the source file
2. Determine if the bug is in the source or the test
3. If the source is wrong: fix the source, do not change the test
4. If the test is wrong (testing something not in SPEC.md): fix the test
5. Run the tests again after your fix to verify
6. Do not add console.log debugging — use the error output to reason about the fix
```

### Step 4: Re-run all tests

After fixes, re-run the full test suite. If new failures appeared (regression), repeat step 3.

### Step 5: Max iterations

The fix loop runs a maximum of **5 iterations**. If tests still fail after 5 rounds:
1. List every still-failing test with its error
2. Categorize: which are real bugs vs. flaky/environmental
3. Present to the user with the specific errors
4. Do NOT silently skip Phase 4 or mark it as passed

## Test quality requirements

Tests written during the build phase must cover:

| Category | Minimum |
|----------|---------|
| Happy path (main feature works) | 1 test per public function |
| Error path (bad input, missing data) | 1 test per documented error case |
| Edge cases (empty input, null, boundary values) | 1 test per module |
| Integration (modules work together) | Added in Phase 5, not here |

## Anti-patterns to watch for

- **Tests that always pass**: Tests that don't actually assert anything (`expect(true).toBe(true)`)
- **Tests that test implementation details**: Mocking everything makes tests brittle and useless
- **Tests that duplicate the implementation**: `expect(add(1,2)).toBe(1+2)` — this tests nothing
- **Snapshot-only tests**: Snapshots without semantic assertions miss real bugs
