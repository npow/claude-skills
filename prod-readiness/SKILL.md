---
name: prod-readiness
description: Scans a codebase and config for 24 production readiness items and produces a scored report. Use when the user asks to check production readiness, audit for prod, review operational concerns, scan for health checks, verify deployment readiness, or assess if code is ready for production.
---

# Production Readiness Scanner

Scans code and config files for 24 production readiness items and produces a scorecard with pass/fail/warning, suggested fixes, and an overall readiness percentage.

## Workflow

1. **Detect project stack** — identify language, framework, package manager, and container tooling by scanning project root files. See [PATTERNS.md](PATTERNS.md).
2. **Load check definitions** — read the 24 production readiness checks and their framework-specific search patterns. See [CHECKS.md](CHECKS.md).
3. **Scan the codebase** — for each check, use Glob and Grep with the patterns from CHECKS.md to find evidence of implementation. Record file paths and line numbers for every match.
4. **Score each check** — assign PASS (evidence found), WARN (partial evidence), or FAIL (no evidence) using the scoring rules in [SCORING.md](SCORING.md).
5. **Generate scorecard** — output the markdown scorecard table, category summaries, fix suggestions for FAIL/WARN items, and overall percentage. Use the exact output format in [SCORING.md](SCORING.md).
6. **Self-review** — verify the scorecard against the checklist below before delivering.

## Self-review checklist

Before delivering, verify ALL:

- [ ] All 24 checks from CHECKS.md appear in the scorecard (none skipped)
- [ ] Every FAIL item has a specific, actionable fix suggestion referencing the project's stack
- [ ] Every PASS item lists at least one file path as evidence
- [ ] The overall percentage matches the formula: `(PASS_count * 100 + WARN_count * 50) / (24 * 100) * 100`
- [ ] No false FAILs: re-scan with alternative patterns from PATTERNS.md before marking FAIL
- [ ] The scorecard uses the exact markdown format from SCORING.md
- [ ] Category groupings (Reliability, Observability, Security, Operations) are present
- [ ] Fix suggestions reference the detected framework, not generic advice

## Golden rules

Hard rules. Never violate these.

1. **Every check gets three search attempts.** Never mark FAIL after a single Grep. Use the primary pattern, then the framework-specific pattern from PATTERNS.md, then a broad fallback pattern. Only mark FAIL after all three miss.
2. **Evidence is file paths and line numbers.** Never mark PASS without recording at least one `file:line` reference. "I saw it somewhere" is not evidence.
3. **Fixes must name the framework.** Never suggest "add a health check endpoint." Always suggest "add a Spring Boot Actuator `/health` endpoint" or "add an Express `/healthz` route" based on the detected stack.
4. **WARN means partial.** Mark WARN only when evidence exists but is incomplete (e.g., logging exists but is not structured, timeouts exist on some clients but not all). Never use WARN as "I'm not sure."
5. **Scan depth over speed.** Always search the full project tree. Never limit to `src/` alone — config, Docker, CI, and infra files contain critical production readiness signals.
6. **Do not invent findings.** If a check category does not apply to the project type (e.g., database migrations for a stateless Lambda), mark it N/A with a one-line reason, and exclude it from the percentage calculation.

## Reference files

| File | Contents |
|------|----------|
| [CHECKS.md](CHECKS.md) | All 24 check definitions with descriptions, what to look for, and severity |
| [SCORING.md](SCORING.md) | Scoring methodology, output format template, fix suggestion patterns |
| [PATTERNS.md](PATTERNS.md) | Framework-specific search patterns for Java/Spring, Node/Express, Python/Flask/FastAPI, Go, Rust, and container/infra tooling |
