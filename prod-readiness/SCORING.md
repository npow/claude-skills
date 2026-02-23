# Scoring Methodology

How to score checks, format the output, and write fix suggestions.

## Score values

| Score | Meaning | Points | When to use |
|-------|---------|--------|-------------|
| PASS | Evidence found | 100 | At least one `file:line` reference confirms implementation |
| WARN | Partial evidence | 50 | Implementation exists but is incomplete or has gaps |
| FAIL | No evidence | 0 | Three search attempts (primary, framework-specific, broad fallback) all returned nothing |
| N/A | Not applicable | excluded | Check category does not apply to this project type |

## Overall percentage formula

```
applicable_checks = total_checks - n/a_count
score = (PASS_count * 100 + WARN_count * 50) / (applicable_checks * 100) * 100
```

Round to the nearest integer. Display as `XX%`.

## Grade thresholds

| Percentage | Grade | Meaning |
|-----------|-------|---------|
| 90-100% | A | Production ready |
| 75-89% | B | Near ready — address FAIL items before deploy |
| 60-74% | C | Significant gaps — not safe for production |
| 40-59% | D | Major gaps — substantial work needed |
| 0-39% | F | Not production ready |

## Output format

Use this exact markdown structure:

```markdown
# Production Readiness Report

**Project**: [detected project name]
**Stack**: [language] / [framework] / [container tooling]
**Score**: [XX]% (Grade [X])
**Date**: [current date]

## Summary

| Status | Count |
|--------|-------|
| PASS   | [n]   |
| WARN   | [n]   |
| FAIL   | [n]   |
| N/A    | [n]   |

## Scorecard

### Reliability

| # | Check | Status | Evidence / Issue |
|---|-------|--------|-----------------|
| 1 | Health Check Endpoints | PASS | `src/routes/health.ts:14` |
| 2 | Graceful Shutdown | FAIL | No SIGTERM handler found |
| ... | ... | ... | ... |

### Observability

| # | Check | Status | Evidence / Issue |
|---|-------|--------|-----------------|
| 7 | Structured Logging | WARN | Logging exists (`src/logger.ts:3`) but uses plaintext format |
| ... | ... | ... | ... |

### Security

| # | Check | Status | Evidence / Issue |
|---|-------|--------|-----------------|
| ... | ... | ... | ... |

### Operations

| # | Check | Status | Evidence / Issue |
|---|-------|--------|-----------------|
| ... | ... | ... | ... |

## Fixes Required

### FAIL Items

#### [Check Name] (Critical/High/Medium/Low)

**What's missing**: [one sentence]
**How to fix**: [framework-specific instruction]
**Example**:
[short code snippet or config snippet showing the fix for the detected stack]

### WARN Items

#### [Check Name] (Critical/High/Medium/Low)

**Current state**: [what exists]
**Gap**: [what's missing]
**How to fix**: [specific improvement instruction]
```

## Fix suggestion rules

1. Every fix must reference the detected framework by name
2. Every fix must include a code or config snippet of 5-15 lines
3. Every fix must specify the file where the change belongs (existing file if possible, new file if necessary)
4. Fixes for Critical items must appear first, then High, then Medium, then Low

## Evidence formatting

- Always use `relative/path/to/file.ext:lineNumber` format
- When multiple files provide evidence, list up to 3 with the most relevant first
- For WARN, show the evidence that exists AND describe what's missing

## Severity definitions

| Severity | Meaning | Deploy guidance |
|----------|---------|-----------------|
| Critical | System will fail or be vulnerable in production | Must fix before any production deployment |
| High | System will degrade or have blind spots in production | Must fix before GA; acceptable for beta/canary |
| Medium | Operational burden or reduced capability | Fix within first sprint post-launch |
| Low | Best practice gap | Address when convenient |
