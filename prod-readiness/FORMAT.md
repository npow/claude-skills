# Output Formats

All judge outputs and the final scorecard use structured markers. Coordinator reads ONLY lines between `STRUCTURED_OUTPUT_START` and `STRUCTURED_OUTPUT_END`. Narrative outside markers is for human review only and has no load-bearing meaning.

## Contents
- [Defect registry schema (per-item verdict)](#defect-registry-schema-per-item-verdict)
- [Judge input file](#judge-input-file)
- [Applicability judge verdict](#applicability-judge-verdict)
- [Final scorecard](#final-scorecard)
- [Risks file](#risks-file)
- [Parser rules](#parser-rules)

---

## Defect registry schema (per-item verdict)

Each of the 24 items gets one judge verdict file at `prod-readiness-{run_id}/evidence/{item_id}/verdict.md`. The judge writes narrative findings above the markers and a structured line below.

```markdown
# Item {item_id}: {item_name}

**Written by:** judge-{item_id}-{slug}
**Model tier:** haiku
**Spawn time:** 2026-04-16T15:30:22Z
**Stack:** {detected stack label}
**Searches attempted:**
1. `{primary_pattern}` — {n} hits
2. `{framework_pattern}` — {n} hits
3. `{fallback_pattern}` — {n} hits

## Findings
{narrative}

## Evidence considered
- `path/to/file.ext:line` — `{verbatim excerpt, ~80 chars}`
- `path/to/other.yml:line` — `{verbatim excerpt}`

STRUCTURED_OUTPUT_START
ITEM|{item_id}|{status}|{severity}|{evidence_path}|{evidence_excerpt}
ITEM_ALT|{item_id}|{evidence_path}|{evidence_excerpt}
SEARCHES|{pattern_1}|{pattern_2}|{pattern_3}
REASON|{machine-readable reason code}
NA_JUSTIFICATION|{text if status==na, else omitted}
STRUCTURED_OUTPUT_END
```

### Field definitions

| Field | Values | Required for |
|---|---|---|
| `item_id` | `1`..`24` | every line |
| `status` | `pass` \| `warn` \| `fail` \| `na` \| `scan_incomplete` | ITEM |
| `severity` | `critical` \| `high` \| `medium` \| `low` | ITEM (from CHECKS.md, verbatim) |
| `evidence_path` | `relative/path/to/file.ext:line` OR `—` when fail/na | ITEM |
| `evidence_excerpt` | verbatim slice from the cited file, max 160 chars, newlines escaped as `\n` | required for `pass`/`warn`, omitted for `fail`/`na`/`scan_incomplete` |
| `ITEM_ALT` | additional evidence lines (up to 2 more), same shape as ITEM but path + excerpt only | optional — only for `pass`/`warn` |
| `SEARCHES` | three pipe-separated pattern strings, in the order attempted | every line — required to prove three-search protocol |
| `REASON` | machine-parseable code (see below) | every line |
| `NA_JUSTIFICATION` | free-text one-liner explaining why the item does not apply | required iff `status==na`, absent otherwise |

### `status` semantics

| Status | Meaning | Evidence requirement |
|---|---|---|
| `pass` | Full implementation detected. | ≥1 `evidence_path:line` + verbatim `evidence_excerpt` |
| `warn` | Partial implementation detected. | ≥1 `evidence_path:line` + verbatim `evidence_excerpt` AND `REASON` describes the gap |
| `fail` | Three-search protocol returned nothing. | `evidence_path = —`, no excerpt, `REASON` describes what was searched |
| `na` | Item does not apply to this project type. | `NA_JUSTIFICATION` mandatory; must be decided by the applicability judge, not the item judge alone |
| `scan_incomplete` | Judge could not complete (timeout, malformed output, ambiguous finding). | `REASON` describes the failure mode |

### `REASON` codes (non-exhaustive)

| Code | When |
|---|---|
| `full_impl_detected` | `pass` — clean hit on primary pattern with confirming excerpt |
| `partial_impl_detected` | `warn` — implementation present but missing (e.g., timeout on some clients, logging without JSON) |
| `three_searches_empty` | `fail` — primary + framework + fallback all returned nothing |
| `na_per_applicability_judge` | `na` — confirmed by applicability judge verdict |
| `judge_timeout` | `scan_incomplete` — exceeded 120s |
| `missing_evidence_excerpt` | `scan_incomplete` — judge claimed pass but did not quote the file |
| `hallucinated_excerpt` | `scan_incomplete` — coordinator verified excerpt not present in cited file |
| `conflicting_verdicts` | `scan_incomplete` — re-spawned judge disagreed with first; coordinator escalates |

### Example — item 1 (Health Check Endpoints), pass

```
STRUCTURED_OUTPUT_START
ITEM|1|pass|critical|src/server/routes/health.ts:14|router.get('/healthz', healthCheck);
ITEM_ALT|1|src/server/index.ts:42|app.use('/health', healthRouter);
SEARCHES|/healthz|@godaddy/terminus|app\.get.*health
REASON|full_impl_detected
STRUCTURED_OUTPUT_END
```

### Example — item 2 (Graceful Shutdown), fail

```
STRUCTURED_OUTPUT_START
ITEM|2|fail|critical|—|
SEARCHES|process.on.*SIGTERM|stoppable|beforeExit
REASON|three_searches_empty
STRUCTURED_OUTPUT_END
```

### Example — item 20 (DB Migrations), na

```
STRUCTURED_OUTPUT_START
ITEM|20|na|medium|—|
SEARCHES|flyway|alembic|migrations/
REASON|na_per_applicability_judge
NA_JUSTIFICATION|Stateless AWS Lambda; no database dependency detected (evidence/20/applicability-verdict.md)
STRUCTURED_OUTPUT_END
```

---

## Judge input file

Written by the coordinator to `prod-readiness-{run_id}/evidence/{item_id}/input.md` BEFORE spawning the judge. Judges are passed path only, never inline content.

```markdown
# Judge Input: Item {item_id} — {item_name}

**Item definition:** (verbatim from CHECKS.md)
{full check block}

**Detected stack:** {stack label}
**Candidate patterns:**
- Primary: `{pattern}`
- Framework-specific ({stack}): `{pattern}`
- Broad fallback: `{pattern}`

**Candidate files (pre-scanned by coordinator, for judge reference only):**
- `path/to/file.ext`
- `path/to/other.yml`

**Instructions:**
1. Run ALL THREE search patterns. Record hit counts in your `SEARCHES` line.
2. For any hit, open the file and read the cited region. Copy the relevant line verbatim into `evidence_excerpt`.
3. If all three searches return no hits: status = `fail`, evidence_path = `—`.
4. Emit exactly one `STRUCTURED_OUTPUT_START`/`END` block with the schema in FORMAT.md.
5. Do NOT return `na` — applicability is decided by a separate judge.
6. Do NOT mark `pass` without a verbatim `evidence_excerpt` from the cited file.

**Output path:** `prod-readiness-{run_id}/evidence/{item_id}/verdict.md`
```

---

## Applicability judge verdict

Spawned separately when an item judge wants to claim `na` or when the coordinator pre-flags an item as likely `na` based on stack (e.g., item 20 on Lambda; item 22 on a CLI tool). One applicability judge per disputed item.

Output at `prod-readiness-{run_id}/evidence/{item_id}/applicability-verdict.md`:

```markdown
# Applicability Verdict: Item {item_id}

**Written by:** applicability-judge-{item_id}
**Reviewed:** detected stack + project-type signals

STRUCTURED_OUTPUT_START
APPLICABILITY|{item_id}|applies|does_not_apply|conditionally_applies
JUSTIFICATION|{one-line text}
STACK_SIGNAL|{signal that drove the verdict}
STRUCTURED_OUTPUT_END
```

`does_not_apply` is the only verdict that permits the item judge to emit `na`. `conditionally_applies` means the item judge must run normally but the coordinator may accept `warn` where full implementation is not feasible for the project type.

---

## Final scorecard

Written by the coordinator to `prod-readiness-{run_id}/scorecard.md` AFTER all 24 item verdicts and any applicability verdicts are on disk and verified.

```markdown
# Production Readiness Report

**Project:** {detected project name}
**Stack:** {language} / {framework} / {container tooling}
**Run ID:** {run_id}
**Date:** {ISO date}
**Termination label:** `ready_for_prod | partial_with_accepted_risks | blocked | scan_incomplete | scan_inconclusive`
**Score:** {XX}% (Grade {X})

## Summary

| Status | Count |
|--------|-------|
| PASS   | {n}   |
| WARN   | {n}   |
| FAIL   | {n}   |
| N/A    | {n}   |
| SCAN_INCOMPLETE | {n} |

## Scorecard — Reliability

| # | Check | Status | Severity | Evidence |
|---|-------|--------|----------|----------|
| 1 | Health Check Endpoints | PASS | Critical | `src/server/routes/health.ts:14` — `router.get('/healthz', healthCheck);` |
| 2 | Graceful Shutdown | FAIL | Critical | — (three searches: process.on.*SIGTERM, stoppable, beforeExit) |
| ... | ... | ... | ... | ... |

## Scorecard — Observability
{same table format}

## Scorecard — Security
{same table format}

## Scorecard — Operations
{same table format}

## FAIL items — required fixes

### Item 2: Graceful Shutdown (Critical)
**Missing:** SIGTERM/SIGINT handler that drains in-flight requests before process exit.
**Fix:** Add signal handler using `@godaddy/terminus` or manual `process.on('SIGTERM', ...)` with `server.close()` and drain timeout.
**Code snippet for {detected stack}:**
```
{5-15 line snippet tailored to the stack}
```
**File location:** `src/server/index.ts` (new handler block) or `src/bootstrap.ts`.

## WARN items — recommended improvements
{same format as FAIL, focused on the gap}

## Accepted risks
See `risks.md` for items explicitly accepted by the user.

## Coverage gaps
- Item {id}: `scan_incomplete` — {reason}

## Invocation
- Run ID: `{run_id}`
- State directory: `prod-readiness-{run_id}/`
- Evidence directory: `prod-readiness-{run_id}/evidence/`
- Total judges spawned: {n}
- Total judge retries: {n}
- Applicability judges spawned: {n}
- Coordinator never assigned pass/fail: `true` (invariant)
```

### Grade thresholds (unchanged from SCORING legacy)

| Percentage | Grade |
|---|---|
| 90-100% | A |
| 75-89% | B |
| 60-74% | C |
| 40-59% | D |
| 0-39% | F |

### Score formula

```
applicable_checks = 24 - na_count - scan_incomplete_count
score = (pass_count * 100 + warn_count * 50) / (applicable_checks * 100) * 100
```

`scan_incomplete` items are EXCLUDED from the denominator (they are unknown, not failed). The termination label captures the coverage honestly.

---

## Risks file

Written at `prod-readiness-{run_id}/risks.md` when the user wants to accept WARN/FAIL items as known risks and still be assigned `partial_with_accepted_risks` rather than `blocked`.

```markdown
# Accepted Risks

STRUCTURED_OUTPUT_START
ACCEPT|{item_id}|{severity}|{rationale_one_line}|{signed_off_by}|{date}
ACCEPT|{item_id}|{severity}|{rationale}|{signer}|{date}
STRUCTURED_OUTPUT_END
```

Rules:
- `severity == critical`: NOT acceptable via this file. Critical FAILs must be fixed; the file parser rejects critical ACCEPT lines and logs `critical_accept_rejected` to `logs/gate_decisions.jsonl`.
- `signed_off_by`: required non-empty string. Missing → ACCEPT line ignored.
- The coordinator READS this file; it does not WRITE it. Users write accept-rationale themselves.

---

## Parser rules

- Pipe (`|`) delimits fields. Parser splits on the declared field count for each line type.
- Lines outside `STRUCTURED_OUTPUT_START`/`END` are ignored by the coordinator.
- Unknown line types inside markers: logged to `logs/gate_decisions.jsonl` with `event: unknown_structured_line`; parser continues.
- Missing required fields on a structured line: discard the line, log the discard.
- Files without both markers: treated as `scan_incomplete` for the covered item; coordinator records `reason: missing_structured_markers`.
- Excerpts containing literal `|` must be escaped as `\|` or the field is truncated at the first unescaped pipe.
- Excerpts with newlines must escape them as `\n`; the coordinator verifies excerpts by re-reading the file and allowing a `\n` in the excerpt to match any whitespace sequence of length ≥1.

## Logs

**`prod-readiness-{run_id}/logs/judge_spawns.jsonl`** — one line per judge spawn:
```jsonl
{"ts":"<ISO>","event":"judge_spawn","item_id":1,"judge_id":"judge-1-health","generation":12}
{"ts":"<ISO>","event":"judge_complete","item_id":1,"verdict":"pass","generation":13}
{"ts":"<ISO>","event":"judge_timeout","item_id":3,"generation":14}
```

**`prod-readiness-{run_id}/logs/gate_decisions.jsonl`** — one line per verdict verification:
```jsonl
{"ts":"<ISO>","gate":"evidence_gate","item_id":1,"verdict":"pass","excerpt_verified":true}
{"ts":"<ISO>","gate":"evidence_gate","item_id":7,"verdict":"pass","excerpt_verified":false,"action":"downgrade_to_scan_incomplete"}
{"ts":"<ISO>","gate":"critical_accept_rejected","item_id":13,"reason":"critical_fails_cannot_be_accepted"}
```
