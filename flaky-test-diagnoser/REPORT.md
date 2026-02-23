# Diagnosis Report Format

The exact output structure for the flaky test diagnosis report.

## Report template

Use this exact markdown structure:

```markdown
# Flaky Test Diagnosis Report

**Test**: [full test identifier — file::class::method or file > describe > it]
**Runner**: [detected test runner and version]
**Date**: [current date]

## Verdict

**Root cause**: [ORDERING | TIMING | SHARED_STATE | EXTERNAL_DEPENDENCY | RESOURCE_LEAK | NON_DETERMINISM]
**Confidence**: [HIGH | MEDIUM | LOW] — [one sentence justifying confidence level]
**Fail rate**: [X]% (Y failures in Z runs)

## Evidence Summary

[2-3 sentences summarizing the key finding that identifies the root cause. Reference specific experiment results.]

## Experiment Results

### 1. Multi-Run (Confirm Flakiness)

**Command**: `[exact command]`
**Runs**: [N]
**Results**: [P F P P F P P P P P]
**Fail rate**: [X]%

### 2. Isolation Test

**Isolated (5 runs)**: [P P P P P] — fail rate: [X]%
**In-suite (5 runs)**: [P F P F P] — fail rate: [X]%
**Conclusion**: [Ordering-dependent | Not ordering-dependent | Inconclusive]

### 3. Ordering Bisection

[Include only if ordering-dependent]

**Suite size**: [N] tests before target
**Bisection steps**: [N]
**Interfering test**: [full test identifier]
**Confirmation**: [INTERFERER + TARGET ran 5 times: F P F F P — confirmed]

### 4. Timing Analysis

**Parallel mode (5 runs)**: [results] — fail rate: [X]%
**Serial mode (5 runs)**: [results] — fail rate: [X]%
**Timing variance**:
- Setup: median=[X]ms, max=[Y]ms ([Z]x variance)
- Test body: median=[X]ms, max=[Y]ms ([Z]x variance)
- Teardown: median=[X]ms, max=[Y]ms ([Z]x variance)

### 5. Environment Analysis

| Factor | Finding |
|--------|---------|
| Parallelism config | [e.g., "4 workers via pytest-xdist"] |
| External calls in test | [e.g., "None detected" or "HTTP call to api.example.com"] |
| Shared state signals | [e.g., "Module-level `_cache` dict mutated by 3 tests"] |
| Resource cleanup | [e.g., "DB connection opened in setUp, not closed in tearDown"] |

### 6. Code Analysis

**Flakiness signals found in test code**:
- [file:line] — [description of signal, e.g., "time.sleep(0.1) used to wait for async operation"]
- [file:line] — [description of signal]

## Recommended Fix

### Root cause explanation

[1-2 paragraphs explaining the exact mechanism causing flakiness. Reference specific code locations.]

### Fix

[Specific code change with file path and line numbers. Describe what to change and why.]

**Before** (the problematic pattern):
[3-10 lines showing the current code]

**After** (the fix):
[3-10 lines showing the corrected code]

### Verification

After applying the fix, run this command to verify:
`[exact command to run the test N times]`

Expected result: 0 failures in [N] runs.
```

## Confidence levels

| Level | Criteria |
|-------|----------|
| HIGH | Root cause confirmed by at least 2 independent experiments (e.g., bisection found interferer AND isolation confirmed ordering dependency) |
| MEDIUM | Root cause supported by 1 experiment and consistent with code analysis signals |
| LOW | Experiments inconclusive but code analysis points to a likely cause. Report states "probable" and recommends additional investigation. |

## When experiments are inconclusive

If no single root cause emerges clearly:

```markdown
## Verdict

**Root cause**: INCONCLUSIVE
**Top candidates**:
1. [CATEGORY] — [evidence for] — [evidence against]
2. [CATEGORY] — [evidence for] — [evidence against]

**Recommended next steps**:
1. [Specific additional experiment to run]
2. [Specific additional experiment to run]
```

Never fabricate a root cause when evidence is insufficient. "Inconclusive with recommendations" is a valid diagnosis.

## Omitting sections

- Omit "Ordering Bisection" section if isolation test showed the test fails in isolation (not ordering-dependent)
- Omit "Timing Analysis" if ordering bisection already found a confirmed interferer with HIGH confidence
- Never omit Multi-Run or Isolation — these always run

## Report length targets

- Verdict + Evidence Summary: 5-10 lines
- Each experiment section: 5-15 lines
- Recommended Fix: 10-30 lines
- Total report: 60-120 lines
