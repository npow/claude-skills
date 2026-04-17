# Golden Rules

Eight cross-cutting rules plus the iron-law evidence requirement. Every `prod-readiness` invocation honors these. Coordinator never assigns pass/fail.

## Contents
- [The iron law](#the-iron-law)
- [Eight cross-cutting rules](#eight-cross-cutting-rules)
- [Anti-rationalization counter-table](#anti-rationalization-counter-table)

---

## The iron law

**No item gets a `pass` verdict without an exact `file:line` or config `key=value` reference that a third party can open and read.**

- "Health checks look configured" — rejected.
- "I saw Spring Actuator listed in the dependencies somewhere" — rejected.
- "`src/main/resources/application.yml:12` sets `management.endpoints.web.exposure.include=health,info,prometheus`" — accepted.
- "`pom.xml:47` declares `spring-boot-starter-actuator`" AND "`build/.../HealthController.java:23` returns composite health" — accepted.

Every judge's `evidence_excerpt` must be a verbatim slice that the coordinator can verify exists by re-reading the cited file. No paraphrasing. No "the file contains logic equivalent to."

If a judge cannot cite a slice it read: the verdict is `fail` or `warn`. Coordinator never upgrades a verdict to compensate for missing evidence.

---

## Eight cross-cutting rules

### 1. Independence Invariant

**Rule:** The coordinator orchestrates 24 parallel Haiku judges, one per item. The coordinator NEVER assigns `pass`, `warn`, or `fail` itself. Even for "obvious" items.

**Concrete examples:**
- Item 13 (Secrets Management): verdict written by `judge-13-secrets`. Coordinator reads `evidence/13/verdict.json` and records only what the judge said.
- Item 24 (Documentation): even if the coordinator sees `README.md` in the first 20 tokens of its initial scan, it does NOT mark item 24 pass. It spawns `judge-24-docs` with the file list and lets the judge decide.
- 24 independent Haiku calls are cheap. Coordinator efficiency is not an acceptable trade for verdict soundness.

**Detection at review:** every verdict line in `state.json` must have `written_by: "judge-{item_id}"`. Any `written_by: "coordinator"` is an invariant violation — the run halts.

### 2. Iron-Law Evidence Gate

**Rule:** A `pass` verdict requires at least one `evidence_path` that exists on disk AND an `evidence_excerpt` copied verbatim from that file. Verdicts without both fail the gate and are downgraded to `fail` with reason `missing_evidence`.

**Concrete examples:**
- Judge 1 (Health Check Endpoints) returns `STATUS|pass|src/routes/health.ts:14|router.get('/healthz', ...)`. Coordinator opens `src/routes/health.ts`, confirms line 14 contains that substring. Accept.
- Judge 1 returns `STATUS|pass|src/routes/health.ts|endpoint exists`. No line number, no excerpt. Reject: downgrade to `fail`, reason `missing_evidence`.
- Judge 18 (Container Health Probes) returns `STATUS|pass|k8s/deployment.yaml:47|livenessProbe: ...`. Coordinator confirms file exists and excerpt matches. Accept.

**Detection at review:** the post-judge verification step in STATE.md reads every `pass`/`warn` verdict and confirms the excerpt appears verbatim in the cited file.

### 3. Three-Search Protocol Before FAIL

**Rule:** Every judge must attempt three searches before returning `fail`: primary pattern, framework-specific pattern (per PATTERNS.md for the detected stack), and broad fallback. A judge that returns `fail` after one search is rejected and re-spawned.

**Concrete examples:**
- Judge 3 (Circuit Breakers) on a Java project searches: `resilience4j` → finds nothing; `HystrixCommand` → finds nothing; broad `(circuit|breaker|OPEN.*CLOSED)` → finds nothing. Now `fail` is valid.
- Judge 3 searches `resilience4j` only, finds nothing, returns `fail`. Rejected: re-spawn with explicit three-pattern instruction.

**Detection at review:** judge output includes `searches_attempted` field enumerating the three patterns run. Fewer than 3 → re-spawn.

### 4. Honest Termination Labels

**Rule:** Exactly one of five labels. Never "all passed", "looks good", "ship it."

| Label | Meaning |
|---|---|
| `ready_for_prod` | Every applicable item PASS; zero WARN on Critical/High items; zero FAIL. |
| `partial_with_accepted_risks` | Some WARN/FAIL items, all documented with explicit accept-rationale signed by the user (written to `risks.md`). Critical FAILs cannot be accepted this way. |
| `blocked` | At least one Critical FAIL with no accept-rationale; deploy gate should be closed. |
| `scan_incomplete` | Fewer than 24 items produced a verdict (judge timeout, missing evidence gate failures, spawn failures). |
| `scan_inconclusive` | Multiple conflicting judges after re-spawn; coordinator cannot resolve without human review. |

**Concrete examples:**
- 22 PASS, 2 WARN on Medium items → `ready_for_prod` only if those WARN items are explicitly accepted in `risks.md`; otherwise `partial_with_accepted_risks`.
- 1 Critical FAIL (secrets hardcoded) + 23 PASS → `blocked`. The 23 passes do not offset the critical.
- 20 judges returned verdicts, 4 timed out after retry → `scan_incomplete`. Report lists which 4 and why.
- Judge 8 (Metrics) returned `pass` but re-verification revealed the excerpt was hallucinated → judge re-spawned, second attempt disagreed with first → `scan_inconclusive` for that item, overall label `scan_inconclusive` if more than 2 items conflict.

**Detection at review:** the final report's termination label must match the enum exactly. Any non-enum value is a bug.

### 5. State Written Before Judge Spawn

**Rule:** Each item's state entry records `spawn_time_iso` in `state.json` BEFORE the Agent call. Spawn failure is recorded as `spawn_failed`. A spawned judge that never produced output is `timed_out`.

**Concrete examples:**
- Before spawning `judge-12-validation`, `state.items["12"].spawn_time_iso = "2026-04-16T15:30:00Z"`, `status: "spawned"`.
- Agent call errors → `status: "spawn_failed"`, `spawn_time_iso: null`, retry once.
- 120s elapses, no output file → `status: "timed_out"`. Does NOT auto-retry silently; surfaces for the user or contributes to `scan_incomplete`.

**Detection at review:** every `state.items[id].status == "spawned"` older than 120s without an output file on disk is either `timed_out` or an invariant violation.

### 6. Structured Output Is the Contract

**Rule:** Every judge outputs `STRUCTURED_OUTPUT_START`/`STRUCTURED_OUTPUT_END` markers with the defect-registry schema in FORMAT.md. Coordinator parses only lines inside markers; unparseable output → fail-safe `scan_incomplete` for that item.

**Concrete examples:**
- Judge 13 output has `STRUCTURED_OUTPUT_START`/`END` with `ITEM|13|pass|...` line. Parse cleanly. Accept.
- Judge 13 output has narrative only, no markers. Reject: record the item as `scan_incomplete`, re-spawn once, then stop.
- Judge 13 output has markers but `ITEM|13|OK|...` (non-enum status). Discard line; record `scan_incomplete` for item 13.

**Detection at review:** pre-consume scan for markers. Results logged to `logs/gate_decisions.jsonl`.

### 7. All Data Passed Via Files

**Rule:** Each judge receives file paths, not inline content. The item definition, stack detection output, and permitted search patterns are written to `evidence/{item_id}/input.md` before the Agent call.

**Concrete examples:**
- `judge-7-logging` receives `evidence/7/input.md` (item definition + patterns + stack) and `evidence/7/manifest.md` (list of candidate files). Not the source of `logger.ts` inline.
- Stack detection output written to `state.stack.json`; judges read it by path, not by inlined repetition.

**Detection at review:** every `state.items[id].spawn_input_files[]` is non-empty and every path exists on disk at spawn time.

### 8. No Coordinator Self-Approval

**Rule:** Same context cannot author and approve. The coordinator can write the final scorecard table summarizing what the judges produced — it cannot override a judge's verdict on its own reading.

**Concrete examples:**
- Judge 20 (Database Migrations) says `fail`; coordinator thinks "but this is obviously a stateless function, N/A applies." Coordinator does NOT flip the verdict. Coordinator spawns a fresh `judge-applicability-20` to decide whether `N/A` is warranted, and records that verdict separately.
- Judge 15 (CORS) says `warn` with excerpt showing `*` origin; coordinator thinks "but this is a dev config." Coordinator does NOT downgrade. If dev-only, the user must add explicit accept-rationale in `risks.md` and termination shifts to `partial_with_accepted_risks`.

**Detection at review:** every verdict in `state.items[id].verdict` has `written_by != "coordinator"`. Coordinator-authored rationale lives in `risks.md` only, and only the user can sign it.

---

## Anti-rationalization counter-table

The coordinator WILL be tempted to skip the discipline. These are the talking points it must reject.

| Excuse | Reality |
|---|---|
| "It's just a dev env, the missing TLS doesn't matter." | The scan labels what the code and config show, not what the deployment story is. If TLS is off, FAIL stands. If dev-only is intentional, it goes in `risks.md` with explicit accept-rationale and the label shifts to `partial_with_accepted_risks`. |
| "We'll fix that later; mark it PASS for now." | No. The scan is a snapshot of current state. "Will fix later" is not evidence of a current fix. |
| "It's an acceptable risk — no need to flag." | Unacceptable risks are FAILs. "Acceptable" is a judgment the user signs, not the coordinator. Write it to `risks.md`, let the user accept explicitly. Otherwise the FAIL stands. |
| "The dashboard is monitored, so alerting isn't needed in code." | Dashboards without alert rules fail check 10. A human watching a dashboard is not an alert; the codebase must define rules. |
| "I scanned this repo last week, nothing's changed." | Previous scans are stale. Every invocation spawns 24 fresh judges. No carry-over. |
| "This item is obviously PASS, I'll skip the judge." | No. Independence invariant holds for trivial cases. 24 Haiku calls are cheap. Skipping a judge is the skip that hides the bug. |
| "The judge returned `fail` but I see the evidence right there." | Then the judge's search patterns were too narrow. Re-spawn with explicit patterns in the input file. Do NOT manually flip the verdict — that is coordinator self-approval. |
| "I can't find evidence for three of the items; I'll call them N/A to get a clean score." | N/A requires a written reason that survives review. "Can't find evidence" is `fail` or `scan_incomplete`, not `N/A`. |
| "The critical FAIL is historical debt, not this PR's problem." | Scan is repo-level, not PR-level (unless `--diff` invoked). Critical FAILs in main block `ready_for_prod`, regardless of who wrote them. |
| "The judge excerpt doesn't exactly match the file but it's close enough." | No. Iron law: verbatim excerpt from cited file. Mismatch = hallucinated evidence = downgrade to `fail`. Re-spawn the judge if the evidence probably exists but was paraphrased. |

When the coordinator is about to reach for any of these excuses: stop, write the judge spawn, let the judge decide, or escalate honestly to `scan_incomplete` / `partial_with_accepted_risks`. The extra agent call is the cost of a scan the user can trust.
