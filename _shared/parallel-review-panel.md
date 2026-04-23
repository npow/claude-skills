# Parallel Review Panel

Shared pattern for skills that need final review before declaring completion. Replaces the previous two-stage sequential review (spec-compliance → code-quality) with parallel reviewers who each get **full context** and a **primary lens**, plus a meta-reviewer that resolves conflicts.

**Used by:** team (Step 5), loop-until-done (Step 7), ship-it (Phase 6).

**Not yet wired:** autopilot (Phase 4) — listed as a candidate but still uses its existing three-judge protocol. Wire when autopilot is next revised.

**Not used by:** deep-qa, deep-design, deep-debug, deep-research (these use the cross-finding-coherence + per-finding-judge pattern instead).

---

## Why this pattern exists

The previous two-stage sequential review had three structural weaknesses exposed by Org-Bench coordination research:

1. **Partial context per reviewer.** The spec-compliance reviewer saw the spec but didn't think about code quality. The code-quality reviewer saw the code but didn't reference the spec deeply. Each reviewer was excellent in its lane and blind outside it — the Oracle anti-pattern.

2. **No end-to-end usage verification.** Both reviewers analyzed *code* — neither tried to *use* the artifact. Oracle's benchmark failure: all four specialized reviewers passed, the user couldn't commit a cell value. Our review gates verified "does the code match the spec?" and "is the code well-built?" but not "does the thing actually work when you try it?"

3. **Sequential bottleneck.** Stage B waited for Stage A to complete. Total review time was sum, not max. With parallel execution, review takes as long as the slowest reviewer, not the sum of all reviewers.

The parallel review panel fixes all three: every reviewer gets full context (spec + code + tests + build output), has a primary lens (so accountability isn't diffused), and runs concurrently with peers. The smoke-test reviewer tries to *use* the artifact, not just read the code.

---

## The pattern

### Panel composition (4 reviewers)

| Slot | Primary Lens | Model | What they focus on |
|---|---|---|---|
| **Spec-compliance** | Does the output match the plan? | Sonnet | Every acceptance criterion has matching evidence; no spec items missing from implementation; no implementation items absent from spec |
| **Code-quality** | Is it built well? | Sonnet | Dead code, duplication, error handling, test coverage, security surfaces, maintainability |
| **Smoke-test** | Does it actually work? | Sonnet | Execute the golden-path user scenario end-to-end; try 2-3 edge cases; report what breaks |
| **Integration-coherence** | Do the parts work together? | Sonnet | Cross-component contracts honored; API boundaries consistent; data flows end-to-end without silent drops; no stub/placeholder left in integration paths |

Each reviewer receives **full context** — they are empowered to flag anything they see, not just findings in their primary lane. The primary lens determines their *focus* and *accountability*, not their *scope*.

### Cross-lane empowerment rule

Every reviewer prompt includes:

> Your primary lens is {lens}. Focus your analysis there. However, if you see a blocking defect outside your lane — a security hole while reviewing spec-compliance, a spec gap while reviewing code quality — FILE IT. Cross-lane findings are tagged `CROSS_LANE|{your_lens}|{finding_lens}` in structured output so the meta-reviewer knows who found what.

This prevents the Facebook-mesh "nobody owns correctness" failure: each reviewer has a primary responsibility, but none is blind outside it.

### Inputs (all reviewers receive the same full context)

All passed as file paths, never inline:

1. **Spec/PRD file** — the plan the implementation was built against
2. **Modified files list** — what changed
3. **Diff** — the actual code changes
4. **Test output** — test suite results
5. **Build/integration output** — build logs, smoke test logs if they exist
6. **Prior defect registries** — any defects found in earlier phases (so reviewers don't re-litigate resolved issues)

The smoke-test reviewer additionally receives:
7. **Reproduction instructions** — how to run the artifact (commands, URLs, entry points)

### Spawn protocol

All 4 reviewers spawn in parallel (not sequentially). Each follows the standard contracts:
- `spawn_time_iso` written to state.json BEFORE Agent call
- Output path pre-declared: `{run_dir}/review/{lens}-review.md`
- `STRUCTURED_OUTPUT_START/END` markers required
- Timeout: 180s per reviewer (smoke-test gets 300s since it actually runs the artifact)

### Reviewer structured output format

Each reviewer writes:

```
STRUCTURED_OUTPUT_START
LENS|{spec-compliance|code-quality|smoke-test|integration-coherence}
VERDICT|{approved|rejected}
DEFECT|{id}|{severity}|{lane}|{description}
  (lane = the reviewer's primary lens, OR CROSS_LANE|{own_lens}|{finding_lens} for out-of-lane findings)
PASS|{checklist_item}|{evidence_path_or_description}
STRUCTURED_OUTPUT_END
```

### Smoke-test reviewer prompt template

The smoke-test reviewer is the structural answer to Oracle's blind spot. It doesn't read code — it uses the artifact.

```
You are a smoke-test reviewer. Unlike the other reviewers who read code and specs, your job is to USE the artifact as an end user would.

You have:
- Spec file: {spec_path} — read this to understand what the artifact is supposed to do
- Reproduction instructions: {repro_path} — how to run/launch/invoke the artifact
- Build output: {build_path} — to verify it built successfully

Instructions:
1. Read the spec. Identify the 3 most important user scenarios (the "golden paths").
2. For each golden path:
   a. Actually execute the scenario using the provided instructions
   b. Record what happened vs. what the spec says should happen
   c. If something fails: capture the exact error, the command that triggered it, and the expected behavior
3. Try 2-3 edge cases:
   - Empty/missing input
   - The smallest valid input
   - An input that exercises a boundary in the spec
4. Record each test as PASS (with evidence) or DEFECT (with scenario, actual vs. expected)

You do NOT review code quality. You do NOT check spec compliance by reading code. You CHECK spec compliance by TRYING the thing.

If the reproduction instructions don't work (can't launch, can't connect, missing dependency):
- That IS a defect: "Cannot reproduce golden path — {specific failure}"
- Do not attempt to debug the build — just report what failed

Your structured output must include at least 3 golden-path tests and 2 edge-case tests. If you cannot execute any test (e.g., no server to hit, no CLI to run, artifact is a library with no entry point), report: "SMOKE_TEST_BLOCKED|{reason}" — this is NOT a pass, it is a gap in the review.

IMPORTANT: You succeed by finding things that work differently than the spec says. You fail by reading code and saying "looks correct." You must EXECUTE, not ANALYZE.
```

### Meta-reviewer protocol

After all 4 reviewers complete (or timeout), a **meta-reviewer** resolves conflicts and produces the panel verdict.

**Quorum:** 3 of 4 reviewers must return parseable output. If smoke-test times out (it's the most likely to timeout), the panel proceeds in degraded mode with `SMOKE_TEST_UNAVAILABLE` flagged prominently.

**Meta-reviewer agent:**
- Model: Sonnet (independent agent, fresh context)
- Input: all 4 reviewer output files + spec + diff
- Job: resolve contradictions between reviewers, assign final verdict per defect, produce aggregate verdict

**Meta-reviewer structured output:**

```
STRUCTURED_OUTPUT_START
PANEL_VERDICT|{approved|rejected_fixable|rejected_unfixable}
DEFECT_FINAL|{id}|{severity}|{status}
  status: confirmed (2+ reviewers agree) | confirmed_cross_lane (found outside primary lens) |
          single_reviewer (only one reviewer flagged it) | contradicted (reviewers disagree — meta-reviewer decides) |
          dismissed (meta-reviewer overrules with rationale)
COVERAGE|{lens}|{status}
  status: covered | timed_out | parse_failed | smoke_blocked
CROSS_LANE_FINDINGS|{count}
STRUCTURED_OUTPUT_END
```

**Verdict rules:**
- `approved` — zero critical/major defects across all lenses; smoke-test golden paths all pass
- `rejected_fixable` — critical/major defects exist but are code-level fixes (not architectural)
- `rejected_unfixable` — defects require architectural change or spec revision

**Independence:** The meta-reviewer does NOT re-review the code. It synthesizes reviewer verdicts. It can dismiss a defect only when two other reviewers explicitly contradict it (majority rules). A single-reviewer finding that's uncontradicted is `single_reviewer` status — weaker signal but NOT dismissed.

---

## How skills consume the panel verdict

### team (Step 5)

Replaces the current two-stage protocol. The panel verdict replaces `verify/verdict.md`:
- `approved` → proceed to Step 7 (termination)
- `rejected_fixable` → proceed to Step 6 (team-fix) with defect registry from panel
- `rejected_unfixable` → terminate with `blocked_unresolved`

Per-worker completion gates remain as-is (those are lightweight per-diff checks, not full panel reviews). The panel fires once on the aggregate output of all workers.

### loop-until-done (Step 7)

Replaces the current Step 7a (spec-compliance) + Step 7b (code-quality) sequential protocol. Both reviewers PLUS smoke-test and integration-coherence fire in parallel. The meta-reviewer verdict replaces the `VERDICT|approved|` / `VERDICT|rejected|` gate:
- `approved` → proceed to Step 8 (deslop)
- `rejected_fixable` → re-queue failed stories, return to Step 3
- `rejected_unfixable` → terminate with `blocked_unresolved`

Rejection counting still applies: `reviewer_rejection_count` increments per panel rejection, cap at 5.

### ship-it (Phase 6)

Replaces the current three-judge protocol (correctness + security + quality). The panel's 4 lenses subsume the three judges:
- Spec-compliance ⊇ correctness judge
- Code-quality ⊇ quality judge
- Smoke-test = new (not previously covered)
- Integration-coherence ⊇ correctness judge's cross-component checks

Security is folded into code-quality's primary lens (security surfaces are explicitly in its checklist) and is also flaggable cross-lane by any reviewer. The meta-reviewer replaces ship-it's mechanical aggregation step.

### autopilot (Phase 4) — NOT YET WIRED

Candidate for the same pattern as ship-it Phase 6 (panel replaces three-judge protocol). Not yet wired — autopilot still uses its existing sequential three-judge protocol. Wire when autopilot is next revised.

---

## Failure modes and mitigations

| Failure | Mitigation |
|---|---|
| Smoke-test can't run the artifact (no entry point, library-only) | `SMOKE_TEST_BLOCKED` is NOT a pass. Panel proceeds in degraded mode. Final report prominently warns: "End-to-end usage not verified — smoke test blocked: {reason}." |
| All reviewers approve (100% pass rate) | Log `PANEL_UNANIMOUS_PASS` — not necessarily wrong (unlike judge 100% accept, unanimous review pass is possible for clean work) but flag in report for transparency. |
| Reviewers contradict each other | Meta-reviewer resolves by majority. Contradictions are surfaced in the final report — the user sees both perspectives. |
| 3+ reviewers time out | Panel failed — cannot produce a verdict from 1 reviewer. Retry with increased timeout. If retry fails: terminate with `review_unavailable`. |
| Cross-lane finding is a duplicate of primary-lane finding | Meta-reviewer deduplicates. The cross-lane tag is informational (shows redundancy in the review = higher confidence), not a separate defect. |

---

## What this pattern does NOT do

- It does NOT replace per-finding severity judges in critic-based skills (deep-qa, deep-design) — those use cross-finding-coherence + judge, not review panels
- It does NOT replace per-worker completion gates in team execution — those are lightweight per-diff checks, not full panel reviews
- It does NOT produce fix suggestions — reviewers file defects, executors produce fixes
- It does NOT run more than once per review cycle — if rejected, the panel runs fresh after fixes (previous panel results do NOT carry forward)

---

## Integration checklist

Each skill importing this pattern must:

- [ ] Spawn all 4 reviewers in parallel (not sequentially)
- [ ] Pass full context to every reviewer (spec + diff + tests + build output)
- [ ] Smoke-test reviewer receives reproduction instructions and gets extended timeout (300s)
- [ ] Meta-reviewer is a fresh independent agent (not a reviewer re-asked)
- [ ] Panel verdict replaces the previous two-stage verdict in state.json
- [ ] `SMOKE_TEST_BLOCKED` is prominently flagged in the final report (not silently passed)
- [ ] Cross-lane findings are tagged and deduplicated by meta-reviewer
- [ ] Previous panel results do NOT carry forward across fix iterations — fresh panel every time
- [ ] Quorum is 3 of 4 (smoke-test timeout doesn't block the other three)
