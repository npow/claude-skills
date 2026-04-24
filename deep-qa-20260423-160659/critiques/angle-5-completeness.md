STRUCTURED_OUTPUT_START
ANGLE|behavioral_correctness
SUB_ANGLE|failure_modes_completeness
VERDICT|rejected
DEFECT_COUNT|7
STRUCTURED_OUTPUT_END

---

# QA Critique — Angle 5: Failure Modes Table Completeness

**Artifact:** Parallel Review Panel (parallel-review-panel skill)
**Dimension:** behavioral_correctness
**Sub-angle:** Are the 5 listed failure modes exhaustive?
**Verdict:** REJECTED — multiple reachable error states have no defined behavior.

---

## Defect 1: Meta-reviewer output is unparseable

**Severity:** CRITICAL

**Scenario:** The meta-reviewer agent returns garbled output — truncated at token limit, missing `STRUCTURED_OUTPUT_START/END` markers, or containing only prose with no structured fields. The consuming coordinator (team Step 5, loop-until-done Step 7, ship-it Phase 6) attempts to parse `PANEL_VERDICT|`, `DEFECT_FINAL|`, and `COVERAGE|` lines and finds none of them.

**Root cause:** The failure modes table covers reviewer parse failures only implicitly (the quorum rule mentions "parseable output" for the 4 reviewers), but the meta-reviewer is the *single* synthesizing authority whose structured output is what the consuming coordinator actually reads. The table has no row for `meta_review_parse_failed`. The quorum logic (3 of 4 reviewers must return parseable output) governs reviewers, not the meta-reviewer. The meta-reviewer is a separate agent with its own failure surface.

**What the coordinator does with no parseable meta-verdict:** Undefined. Does it retry? Does it escalate? Does it default to `approved` or `rejected`? The spec is silent. A consuming skill that falls through here has no defined behavior — it either crashes, silently approves, or silently blocks, depending on implementation.

**Remediation:** Add a row: "Meta-reviewer output unparseable or missing PANEL_VERDICT line → retry meta-reviewer once with same inputs. If retry also fails: surface raw reviewer files to coordinator and terminate with `meta_review_unavailable`. Do NOT default to approved or rejected."

---

## Defect 2: All reviewers approve but smoke-test was blocked — conflated with clean unanimous pass

**Severity:** HIGH

**Scenario:** Spec-compliance, code-quality, and integration-coherence all return `VERDICT|approved`. Smoke-test returns `SMOKE_TEST_BLOCKED|no entry point`. The meta-reviewer, following the quorum rule (3 of 4 parseable), produces `PANEL_VERDICT|approved`. The consuming skill treats this as a clean approval.

**Root cause:** The existing failure mode row #2 says: "All reviewers approve → Log `PANEL_UNANIMOUS_PASS`." The existing failure mode row #1 says: "Smoke-test blocked → flag prominently." But there is no row for the *intersection*: all non-blocked reviewers approve AND smoke-test is blocked. The spec says `SMOKE_TEST_BLOCKED` "is NOT a pass" and must be "prominently flagged" — but the verdict rules (`approved` → "smoke-test golden paths all pass") literally require golden paths to pass for an `approved` verdict.

**The contradiction:** The verdict definition says `approved` requires "smoke-test golden paths all pass." If smoke-test is blocked, zero golden paths passed. Therefore `approved` is definitionally wrong in this scenario. But the panel would still produce `approved` because the quorum rule says smoke-test timeout doesn't block the other three. The failure modes table never resolves this contradiction.

**Observable consequence:** A coordinator receives `PANEL_VERDICT|approved` on an artifact that was never end-to-end tested. The whole point of the smoke-test reviewer was to catch what spec-compliance and code-quality miss. This silently regresses to the Oracle failure mode the pattern was designed to prevent.

**Remediation:** Add a distinct verdict value (e.g., `approved_smoke_blocked`) or require that `SMOKE_TEST_BLOCKED` forces the verdict to `rejected_fixable` with a specific defect: "End-to-end verification not performed." The failure modes table must have an explicit row for this combination rather than leaving the meta-reviewer to reconcile two contradictory rules.

---

## Defect 3: Reviewer produces logically inconsistent structured output (VERDICT|approved + critical DEFECT lines)

**Severity:** HIGH

**Scenario:** A reviewer writes:
```
STRUCTURED_OUTPUT_START
LENS|code-quality
VERDICT|approved
DEFECT|CQ-01|critical|code-quality|SQL injection via unsanitized user input — attacker can exfiltrate all data
STRUCTURED_OUTPUT_END
```

The reviewer labeled the defect `critical` but set `VERDICT|approved`. The meta-reviewer ingests this. What does it do?

**Root cause:** The structured output format has no defined invariant that `VERDICT|approved` is incompatible with `DEFECT|...|critical|...`. The spec does not say "a reviewer with critical defects MUST emit `VERDICT|rejected`." The meta-reviewer protocol says it "resolves contradictions between reviewers" but this is an *intra-reviewer* contradiction, not an inter-reviewer one. The meta-reviewer's job description doesn't cover this case.

**Failure modes:**
- Meta-reviewer may trust the `VERDICT` line and count this reviewer as approving.
- Meta-reviewer may trust the `DEFECT` lines and override the verdict.
- Meta-reviewer may flag the inconsistency but the spec gives it no rule to apply.
- If the meta-reviewer trusts `VERDICT|approved` and the other 2 reviewers also approve, the critical SQL injection defect is lost — it appears in the output file but never surfaces in `DEFECT_FINAL` as `confirmed`.

**Observable consequence:** A critical security defect is filed by a reviewer but lost in aggregation because the inconsistent verdict was taken at face value. The consuming coordinator sees `PANEL_VERDICT|approved`, no `DEFECT_FINAL|...|critical` lines, and ships.

**Remediation:** Add a validation rule: "If a reviewer emits any `DEFECT|...|critical|...` or `DEFECT|...|major|...` line, the reviewer's `VERDICT` MUST be `rejected`. If `VERDICT|approved` is present alongside critical/major defects, the meta-reviewer MUST treat the verdict as `rejected` for that reviewer and flag `REVIEWER_INCONSISTENCY|{lens}` in its output."

---

## Defect 4: Exactly 2 reviewers time out (boundary condition in quorum rule)

**Severity:** MEDIUM

**Scenario:** Smoke-test and integration-coherence both time out. Only spec-compliance and code-quality return parseable output. Quorum is defined as "3 of 4 reviewers must return parseable output." Two returned output; two timed out. Quorum is not met.

**Root cause:** The failure modes table has a row for "3+ reviewers time out → retry, then `review_unavailable`." But there is no row for the 2-timeout case. The quorum rule says 3 of 4 must return — so 2 timeouts = quorum not met — but the failure mode table only triggers the retry/escalation path at 3+ timeouts. This leaves the 2-timeout case in a gap: quorum is broken, but the defined failure mode (row #4) doesn't fire.

**Observable consequence:** A coordinator checking "did we hit the 3+ timeout failure mode?" answers no. It then tries to proceed with 2 reviewers, violating the quorum requirement with no defined behavior. Or it tries to invoke the meta-reviewer with only 2 reviewer files, and the meta-reviewer produces a verdict based on half the panel.

**Remediation:** The failure modes table row should read "fewer than 3 reviewers return parseable output (for any reason — timeout, parse failure, crash)" rather than "3+ reviewers time out." The current wording accidentally covers only the extreme case.

---

## Defect 5: Meta-reviewer dismisses a defect that appears in all 4 reviewers

**Severity:** MEDIUM

**Scenario:** All 4 reviewers flag defect FOO-01 as critical. The meta-reviewer, reasoning independently, determines the defect is based on a misunderstanding and marks it `dismissed`. The consuming coordinator sees `DEFECT_FINAL|FOO-01|critical|dismissed` and no rejected verdict.

**Root cause:** The independence rule says "A meta-reviewer can dismiss a defect only when two other reviewers explicitly contradict it (majority rules)." But the meta-reviewer is described as a fresh independent agent that also receives the spec and diff. There is no rule preventing the meta-reviewer from reasoning about the defect itself and overriding unanimous reviewer agreement. The dismissal rule says "two other reviewers explicitly contradict it" — but if all 4 agree, there is no contradiction to invoke. However the rule is structural: it only prevents dismissal under majority contradiction. It does not prohibit dismissal of unanimous findings.

**Observable consequence:** A meta-reviewer that reasons poorly can silently dismiss a unanimous critical finding. The consuming coordinator has no way to detect this — it only sees the meta-reviewer's output.

**Remediation:** Add invariant: "A defect flagged by 3 or more reviewers MUST NOT be dismissed — maximum status is `confirmed`. Meta-reviewer may only dismiss defects found by a single reviewer with no cross-lane corroboration."

---

## Defect 6: Panel produces a verdict but the meta-reviewer was never spawned (silent skip)

**Severity:** MEDIUM

**Scenario:** A coordinator implementation spawns the 4 reviewers but the meta-reviewer spawn fails silently (e.g., timeout at spawn, agent call never returns, state.json write never happens). The coordinator's error handling assumes the meta-reviewer's output file exists. It does not. The coordinator reads a missing file as empty, parses zero structured output fields, and because there is no `PANEL_VERDICT|rejected` line, defaults to treating the panel as approved.

**Root cause:** The spawn protocol defines `spawn_time_iso` written to state.json before Agent call and output path pre-declared — but only for the 4 reviewers. There is no spawn protocol, timeout, or failure handling defined for the meta-reviewer itself. The failure modes table has no row for "meta-reviewer not spawned" or "meta-reviewer spawn failed."

**Observable consequence:** A coordinator silently approves an artifact because the meta-reviewer never ran. No retry. No `review_unavailable`. No signal to the user.

**Remediation:** Apply the same spawn protocol to the meta-reviewer (spawn_time_iso, output path, timeout). Add a failure mode row: "Meta-reviewer not spawned or output file missing → do not default to approved; treat as `review_unavailable` and retry or escalate."

---

## Defect 7: CROSS_LANE finding on a dismissed defect has no defined resolution

**Severity:** LOW

**Scenario:** Spec-compliance reviewer flags defect FOO-02 as critical (primary lane). Code-quality reviewer finds the same issue cross-lane and tags it `CROSS_LANE|code-quality|spec-compliance`. The meta-reviewer dismisses the spec-compliance primary finding (because the third and fourth reviewers contradicted it). But the cross-lane finding from code-quality remains. The meta-reviewer deduplication rule says cross-lane findings are deduplicated against primary-lane findings — "the cross-lane tag is informational."

**Root cause:** If the primary-lane finding is dismissed, the deduplication removes the only surviving record of this finding. The cross-lane finding was supposed to be informational reinforcement of a primary finding — but when the primary finding is dismissed, the cross-lane finding is also silently dropped via deduplication, even though it was filed by an independent reviewer with independent reasoning.

**Observable consequence:** A defect found by two independent reviewers (one primary, one cross-lane) is treated as if it was found by zero reviewers after the primary is dismissed. The cross-lane finding's signal is destroyed.

**Remediation:** Rule: "A cross-lane finding is only suppressed by deduplication if the corresponding primary finding is confirmed or single_reviewer — not if it is dismissed. A dismissed primary finding with an uncontradicted cross-lane finding should be escalated to `single_reviewer` status (from the cross-lane finder's perspective) rather than fully dismissed."

---

## New angles surfaced by this analysis

1. **Coordinator parse contract:** The consuming skill coordinators (team, loop-until-done, ship-it) parse the meta-reviewer's structured output. There is no defined contract for what the coordinator does when `PANEL_VERDICT` is present but `COVERAGE` lines are missing, or when the count of `DEFECT_FINAL` lines doesn't match what the reviewers filed. A separate QA angle should audit the coordinator-side parsing contract.

2. **Timeout cascade interaction:** If smoke-test times out AND one other reviewer times out simultaneously (2 timeouts), the quorum logic breaks in ways not covered by either the "smoke-test degraded mode" or "3+ timeout" rows. The interaction between the smoke-test-specific degraded mode and the general quorum rule is underspecified.

3. **Verdict value exhaustiveness:** The meta-reviewer verdict has 3 values: `approved`, `rejected_fixable`, `rejected_unfixable`. There is no `review_unavailable` at the meta-reviewer level — that value only appears in the failure mode prose for the 3+ timeout case but is never part of the formal `PANEL_VERDICT` enum. Consuming skills must handle it but it is not in the structured output contract.

4. **Rejection count interaction with `review_unavailable`:** loop-until-done increments `reviewer_rejection_count` per panel rejection (cap at 5). If a panel fails with `review_unavailable` (not a rejection, just an error), should the rejection count increment? The spec is silent. A coordinator that increments on error could terminate a workflow that was never actually rejected on merit.
