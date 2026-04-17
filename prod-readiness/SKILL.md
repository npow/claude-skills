---
name: prod-readiness
description: Scans a codebase and config for 24 production readiness items and produces a scored report. Use when the user asks to check production readiness, audit for prod, review operational concerns, scan for health checks, verify deployment readiness, or assess if code is ready for production.
---

# Production Readiness Scanner

Scans code and config for 24 production readiness items using **24 independent Haiku judges in parallel** — one per item. Coordinator orchestrates; it never assigns pass/fail. Produces a structured defect registry with verbatim file/line evidence, a scored scorecard, and an honest termination label.

## Contents
- [Workflow](#workflow)
- [Model tier strategy](#model-tier-strategy)
- [Integration with other skills](#integration-with-other-skills)
- [Degraded mode](#degraded-mode)
- [Self-review checklist](#self-review-checklist)
- [Reference files](#reference-files)

---

## Workflow

### Phase 0: Stack detection (coordinator)

1. Generate `run_id: $(date +%Y%m%d-%H%M%S)`.
2. Create `prod-readiness-{run_id}/` in CWD with subdirectories per STATE.md.
3. Write `prod-readiness-{run_id}.lock` in CWD; verify write succeeded.
4. Detect language, framework, package manager, container tooling, CI tooling per PATTERNS.md project-type table.
5. Write findings to `prod-readiness-{run_id}/stack.json` and to `state.json` under `stack` key.
6. Initialize the 24 item entries in `state.items` per STATE.md; each starts `status: "not_started"`.

**If `--diff [ref]` is passed:** scope is the git diff only; still run all 24 judges, but judges narrow their search to changed files + callers.

### Phase 1: Compile per-item judge inputs (coordinator)

For each of the 24 items (parallel-safe, so write in parallel):

1. Read the full item definition from CHECKS.md.
2. Select the three search patterns for the detected stack from PATTERNS.md (primary, framework-specific, fallback). If no framework-specific pattern exists, document as `framework_pattern: "(none for this stack; use primary)"`.
3. Compile the candidate file list using Glob against the stack's file extensions and infrastructure directories (config, Dockerfiles, k8s manifests, CI workflows).
4. Write `prod-readiness-{run_id}/evidence/{item_id}/input.md` per the FORMAT.md schema — item definition + patterns + candidate files + output path.
5. Write `prod-readiness-{run_id}/evidence/{item_id}/manifest.md` with the candidate file list.
6. Verify both files exist on disk and are non-empty. Record `spawn_input_files` in state.

**Flag contested applicability** when the stack signals an item likely does not apply (e.g., item 20 DB Migrations on a stateless Lambda, items 22-24 on a CLI tool). Add to `state.applicability_flags[<id>] = "contested"`. These will get a separate applicability judge in Phase 2.

### Phase 2: Spawn 24 independent Haiku judges in parallel

**This is the core of the skill. The coordinator does not evaluate. Judges evaluate.**

1. For each of the 24 items, write spawn metadata to state (status: `spawned`, `spawn_time_iso`) per STATE.md reference patterns.
2. Spawn all 24 judges in parallel using the prompt template below. Each judge reads its input file by path — not inline content.
3. For each contested-applicability item, spawn an additional applicability judge in parallel. Output to `evidence/{item_id}/applicability-verdict.md` per FORMAT.md.
4. Spawn timeout: 120s per judge. If a judge times out: mark `timed_out`; do NOT auto-retry. Records as `scan_incomplete` in final tally.
5. Wait for all judges to produce output files OR time out.

**Judge prompt template (per item judge):**

```
You are a production readiness judge for item {item_id}: {item_name}.

Read your input file: {absolute_path_to_input_md}
Read the candidate files manifest: {absolute_path_to_manifest_md}

Your job is to decide one verdict for this item: pass, warn, fail, or scan_incomplete.
You may NOT return `na` — applicability is decided by a separate judge.

**The iron law:** you may only return `pass` or `warn` if you can cite a specific
`file:line` AND copy a verbatim excerpt from that file proving the verdict.
"Looks ok" / "seems implemented" / "probably there" are REJECTED by the coordinator.

**Three-search protocol:**
1. Run the PRIMARY pattern from your input file.
2. Run the FRAMEWORK pattern for the detected stack.
3. Run the FALLBACK pattern.
Record hit counts for all three. The coordinator verifies that all three ran.

**Verdict rules:**
- `pass`: full implementation detected with verbatim excerpt proving it.
- `warn`: partial implementation detected (e.g., timeouts on some clients but not all,
  logging configured but not JSON); verbatim excerpt showing the partial state.
- `fail`: all three searches returned no relevant hits.
- `scan_incomplete`: you could not complete the check (output confused, conflict, etc.).

**Falsifiability:** "theoretical risk" / "could be a problem" is not a defect.
A defect is a specific scenario where the item fails its consumer.

Write your output to {absolute_path_to_verdict_md} using the schema in FORMAT.md.
Your output MUST include STRUCTURED_OUTPUT_START/END markers with the ITEM, SEARCHES,
and REASON lines. Unparseable output is treated as scan_incomplete for this item.
```

**Applicability judge prompt (when an item is flagged `contested`):**

```
You are an applicability judge for item {item_id}: {item_name} on this project.

Read the item definition and the detected stack in: {absolute_path_to_input_md}
Read the stack detection output: {absolute_path_to_stack_json}

Decide whether this item applies to this project. Return exactly one verdict:
- `applies`: normal check required.
- `does_not_apply`: the item is not relevant (e.g., DB migrations on a stateless Lambda,
  API versioning on a CLI tool).
- `conditionally_applies`: the item is relevant but full implementation is not feasible;
  the item judge should use `warn` as the ceiling.

Write output to {absolute_path_to_applicability_verdict_md} with the FORMAT.md schema.
```

### Phase 3: Evidence verification gate (coordinator)

For every completed judge output, the coordinator runs the iron-law evidence gate (STATE.md):

1. Read `evidence/{item_id}/verdict.md`.
2. Confirm `STRUCTURED_OUTPUT_START`/`END` markers.
3. Parse `ITEM` line; extract `evidence_path` and `evidence_excerpt`.
4. For `pass`/`warn`: open the file at `evidence_path`, read ±1 line around the cited line, confirm `evidence_excerpt` substring is present verbatim. If not present: downgrade to `scan_incomplete` with reason `hallucinated_excerpt`.
5. For `fail`: confirm `SEARCHES` line lists exactly 3 patterns. Fewer: downgrade to `scan_incomplete` with reason `three_searches_empty` check failed.
6. For `na`: confirm companion `applicability-verdict.md` exists and contains `APPLICABILITY|...|does_not_apply`. Missing → downgrade to `scan_incomplete`.
7. Write the verified verdict into `state.items[<id>]` (status, verdict, evidence_path, evidence_excerpt, evidence_excerpt_verified=true, written_by=judge_id).
8. For every `scan_incomplete`, re-spawn the judge ONCE with a corrected input emphasizing the failed check. On second failure: lock in `scan_incomplete`.

**Coordinator never flips a verdict on its own judgment.** If the coordinator believes the judge is wrong, the only remedies are: re-spawn the judge once (Phase 3 step 8), or surface the conflict to the user as `scan_inconclusive`.

### Phase 4: Score and write scorecard (coordinator)

1. Tally verdicts: `pass_count`, `warn_count`, `fail_count`, `na_count`, `scan_incomplete_count`.
2. Compute applicable checks: `24 - na_count - scan_incomplete_count`.
3. Compute percentage: `(pass_count * 100 + warn_count * 50) / (applicable_checks * 100) * 100`, rounded.
4. Assign grade per FORMAT.md thresholds.
5. Read any user-authored `risks.md`. Parse ACCEPT lines (reject any with severity=critical per FORMAT.md).
6. Assign termination label per rules:
   - `ready_for_prod` — zero FAIL on Critical/High items AND zero `scan_incomplete` AND (zero WARN on Critical/High OR all WARN items accepted in risks.md).
   - `partial_with_accepted_risks` — some WARN/FAIL exist; every one on Critical/High has a matching ACCEPT line in risks.md signed off; no FAIL on Critical items remains.
   - `blocked` — at least one Critical FAIL without accept-rationale.
   - `scan_incomplete` — any item with `scan_incomplete` verdict after retries.
   - `scan_inconclusive` — multiple items with conflicting judge verdicts across retries.
7. Spawn a Haiku subagent to write `prod-readiness-{run_id}/scorecard.md` per FORMAT.md, passing state.json path and evidence directory path. The subagent reads judge verdicts from files; it does NOT re-evaluate.
8. Verify scorecard exists and is non-empty. If missing: write a minimal emergency report from state.json directly.

### Phase 5: Self-review and deliver

Run the self-review checklist below. Surface any invariant violations before delivering.

---

## Model tier strategy

| Tier | Model | Used for |
|---|---|---|
| Coordinator | (main session) | Stack detection, state writes, evidence gate, score computation, orchestration only |
| Judge | haiku | Per-item verdict (24 in parallel) + applicability judges |
| Synthesis | haiku | Final scorecard write-up from state + verdicts |

**Why haiku for judges:** 24 parallel judges is cheap enough that there is no excuse for the coordinator to "take a shortcut" and skip any. Haiku handles grep + verbatim excerpt extraction reliably. The independence invariant is the load-bearing property, not the judge's cleverness.

---

## Integration with other skills

| Where | Calls | Why |
|---|---|---|
| Used standalone on a repo | n/a | Main use. 24 judges, scored report. |
| Used inside `/team` team-verify stage | `/team` invokes this skill | Runs after deep-qa to add operational-readiness signal to the verify gate. |
| Used inside `/autopilot` Phase 3 or Phase 4 | `/autopilot` invokes this skill | Pre-deployment gate; output feeds the three-judge validation. |
| `--diff [ref]` mode | invoked by `deep-qa --diff`-style callers | Scoped scan; judges still run 24 items but constrained to diff + callers. |

---

## Degraded mode

If the coordinator cannot spawn 24 parallel Agents (rate limit, harness failure):

1. Spawn in batches of 6 (matches deep-qa's frontier cap). Total wall-clock increases linearly.
2. Tag scorecard with `MODE: degraded_sequential`. Termination label is unchanged.
3. If the coordinator cannot spawn ANY Agent (harness broken): halt with `scan_incomplete` termination; do NOT attempt to assign verdicts from the coordinator context. That is coordinator self-approval and is forbidden.

---

## Self-review checklist

Before delivering, verify ALL:

- [ ] All 24 items have a final verdict in `state.items` (pass/warn/fail/na/scan_incomplete); none left at `not_started` or `spawned`
- [ ] Every `pass` and `warn` verdict has `evidence_excerpt_verified: true` (coordinator opened the file and matched the excerpt verbatim)
- [ ] Every `fail` verdict has `searches_attempted` listing exactly 3 patterns
- [ ] Every `na` verdict has a matching `applicability-verdict.md` on disk with `APPLICABILITY|...|does_not_apply`
- [ ] Every verdict line in `state.items` has `written_by != "coordinator"` (independence invariant)
- [ ] The scorecard uses the exact markdown format from FORMAT.md with severity-sorted FAIL items first
- [ ] Category groupings (Reliability, Observability, Security, Operations) are present
- [ ] Fix suggestions reference the detected framework, not generic advice
- [ ] Termination label is exactly one of the five values (`ready_for_prod`, `partial_with_accepted_risks`, `blocked`, `scan_incomplete`, `scan_inconclusive`)
- [ ] If termination is `ready_for_prod`: zero Critical/High FAILs AND zero `scan_incomplete` entries
- [ ] If termination is `partial_with_accepted_risks`: every WARN/FAIL on Critical/High has a signed ACCEPT in `risks.md`; no Critical FAIL accepted
- [ ] The overall percentage matches the formula: `(pass*100 + warn*50) / (applicable*100) * 100` with `applicable = 24 - na - scan_incomplete`
- [ ] `prod-readiness-{run_id}/logs/gate_decisions.jsonl` has one entry per evidence-gate evaluation
- [ ] `prod-readiness-{run_id}/logs/judge_spawns.jsonl` has spawn + completion entries for all 24 judges

---

## Golden rules

Hard rules. Never violate these. See [GOLDEN-RULES.md](GOLDEN-RULES.md) for the full statement with per-rule examples and the anti-rationalization counter-table.

1. **Iron-law evidence.** Every `pass` cites `file:line` with a verbatim excerpt the coordinator re-reads to verify. No excerpt → no pass.
2. **Independent judge per item.** 24 Haiku judges, one per item, coordinator never assigns verdicts.
3. **Three-search protocol before FAIL.** Primary + framework-specific + broad fallback. Fewer than 3 → re-spawn.
4. **Structured output is the contract.** Every judge emits `STRUCTURED_OUTPUT_START`/`END` with the defect-registry schema. Unparseable → `scan_incomplete`.
5. **Honest termination labels.** Five labels only. Never "all passed" or "looks good."
6. **State written before spawn.** `spawn_time_iso` recorded before the Agent call.
7. **All data passed via files.** Item definitions, patterns, candidate files — all written to `evidence/{item_id}/input.md` before the Agent call.
8. **No coordinator self-approval.** Coordinator can write the scorecard summary; cannot override a judge verdict on its own reading.

---

## Reference files

| File | Contents |
|------|----------|
| [CHECKS.md](CHECKS.md) | All 24 check definitions with descriptions, what to look for, severity, pass/warn/fail criteria |
| [PATTERNS.md](PATTERNS.md) | Framework-specific search patterns for Java/Spring, Node/Express, Python/Flask/FastAPI, Go, Rust, and container/infra tooling |
| [SCORING.md](SCORING.md) | Legacy scoring methodology (superseded by FORMAT.md — retained for the fix-suggestion patterns and severity definitions) |
| [FORMAT.md](FORMAT.md) | Defect registry schema, judge input format, applicability verdict format, final scorecard format, parser rules |
| [STATE.md](STATE.md) | `state.json` schema, directory layout, iron-law evidence gate, resume protocol, state invariants |
| [GOLDEN-RULES.md](GOLDEN-RULES.md) | The 8 cross-cutting rules with per-rule examples + anti-rationalization counter-table |
