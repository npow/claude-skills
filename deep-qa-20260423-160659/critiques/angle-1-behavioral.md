STRUCTURED_OUTPUT_START
ANGLE|behavioral_correctness
REVIEWER|claude-sonnet-4-6
DEFECT_COUNT|9
STRUCTURED_OUTPUT_END

---

# Behavioral Correctness Critique — Structured Output Format Ambiguity

**Angle:** Are the STRUCTURED_OUTPUT formats for reviewers and meta-reviewer unambiguous enough that an LLM agent would produce parseable output on the first attempt? Are there edge cases where the format spec allows contradictory interpretations?

**Consumer:** An LLM agent (Sonnet) implementing a reviewer or meta-reviewer role.

---

## DEFECT-1: The `lane` field in DEFECT lines has two incompatible value shapes with no separator disambiguation

**Severity:** critical

**Scenario:**
A code-quality reviewer finds a cross-lane defect. The format spec says lane is either:
- The reviewer's primary lens (e.g., `code-quality`)
- `CROSS_LANE|{own_lens}|{finding_lens}` for out-of-lane findings

This produces lines like:
```
DEFECT|D1|major|code-quality|Missing null check
DEFECT|D2|major|CROSS_LANE|code-quality|spec-compliance|Missing acceptance criterion
```

The second line has **6 pipe-delimited fields** while the first has **5**. A parser splitting on `|` gets a different number of columns depending on whether the finding is in-lane or cross-lane. There is no escape mechanism for `|` in descriptions, no fixed field count, no sentinel, and no indication in the format spec that the parser must handle variable-width rows. An LLM agent implementing a downstream parser has no canonical way to distinguish "the 4th token is a compound cross-lane value" from "the description started with CROSS_LANE". This is structurally ambiguous — a naive split produces a broken parse for all cross-lane defects.

**Root cause:** The cross-lane value was embedded inside a positional field rather than promoted to a separate field or encoded as a non-pipe token (e.g., using a different delimiter for the sub-structure).

**Remediation:** Either (a) make `CROSS_LANE` a fixed field at position 4 and add `own_lens` and `finding_lens` as positions 5 and 6 with description at position 7, or (b) encode the cross-lane substructure without using `|` (e.g., `CROSS_LANE[code-quality->spec-compliance]`), or (c) add a separate `CROSS_LANE_TAG` line after the DEFECT line.

---

## DEFECT-2: `VERDICT` field admits `approved` with defects present — no constraint stated

**Severity:** critical

**Scenario:**
A reviewer writes:
```
VERDICT|approved
DEFECT|D1|minor|spec-compliance|Typo in error message
```

Is this valid? The format spec says nothing about the relationship between `VERDICT` and the presence of `DEFECT` lines. A compliant reviewer could issue `VERDICT|approved` with minor defects filed (perhaps they consider them non-blocking). A downstream parser checking only the `VERDICT` field would see "approved" and proceed, discarding all DEFECT lines. The meta-reviewer aggregation logic then receives a reviewer verdict of `approved` from a reviewer who filed defects — contradicting itself in a structurally valid way.

The artifact defines verdict rules only for the **meta-reviewer** (`approved` = zero critical/major defects), but not for individual reviewers. An LLM agent implementing the reviewer role will invent its own interpretation of what `VERDICT|approved` means, and different reviewers will apply different thresholds.

**Root cause:** The reviewer format specifies the `VERDICT` field's allowed values but not its contract — what conditions must hold for each value to be issued.

**Remediation:** Add explicit contract: "VERDICT|approved is only valid if no DEFECT lines are present. VERDICT|rejected must accompany at least one DEFECT line." Or: replace the binary reviewer verdict with severity-threshold language.

---

## DEFECT-3: `DEFECT` lines have no cardinality constraint — zero DEFECTs with `rejected` verdict is valid per format

**Severity:** major

**Scenario:**
An LLM agent writes:
```
VERDICT|rejected
PASS|all-checks|Everything looks fine
```

The format spec shows `DEFECT` lines as optional (the format block uses repetition syntax but no minimum-cardinality requirement). An LLM agent that is uncertain but cautious might issue `VERDICT|rejected` with zero DEFECT lines. The meta-reviewer then sees a rejection with no defect registry — it cannot compute `DEFECT_FINAL` statuses, cannot apply the "2+ reviewers agree" rule, and cannot distinguish this from a parse failure.

**Root cause:** The format spec does not state that `VERDICT|rejected` requires at least one `DEFECT` line, nor that `VERDICT|approved` prohibits them.

**Remediation:** Explicitly state: "If VERDICT|rejected, at least one DEFECT line is required. If VERDICT|approved and DEFECT lines are present, they must all be severity=minor."

---

## DEFECT-4: `DEFECT` `{id}` field has no specified format — agents will produce incompatible ID schemes

**Severity:** major

**Scenario:**
Reviewer A produces: `DEFECT|1|critical|spec-compliance|Missing auth check`
Reviewer B produces: `DEFECT|SEC-001|critical|spec-compliance|Missing auth check`
Reviewer C produces: `DEFECT|missing-auth-check|critical|spec-compliance|Missing auth check`

The meta-reviewer receives all three and must determine that these refer to the same defect to set `confirmed (2+ reviewers agree)`. But the IDs are incompatible — the meta-reviewer cannot mechanically match them. It must semantically compare descriptions across three different ID namespaces with no deduplication key. An LLM agent meta-reviewer will do its best, but the format spec made a claim ("confirmed (2+ reviewers agree)") that requires ID coordination it never specified.

**Root cause:** The `{id}` placeholder has no format contract — no prefix, no namespace, no uniqueness constraint, no cross-reviewer coordination mechanism.

**Remediation:** Either (a) specify that IDs are sequential integers scoped per reviewer (`R1-D1`, `R2-D1`) and deduplication is purely semantic (as the meta-reviewer's job), or (b) require a canonical ID scheme that forces reviewers to use the same IDs (e.g., keyed on a defect hash). The current spec implies ID matching without specifying how IDs relate across reviewers.

---

## DEFECT-5: `DEFECT_FINAL` in meta-reviewer output references `{id}` but the ID namespace is undefined

**Severity:** major

**Scenario:**
The meta-reviewer writes:
```
DEFECT_FINAL|D1|critical|confirmed
```

What is `D1`? Is it Reviewer A's ID? Reviewer B's ID? A new meta-reviewer-assigned ID? The format spec does not specify whether the meta-reviewer (a) adopts one reviewer's existing ID, (b) creates a new canonical ID, or (c) must enumerate all reviewer IDs. A downstream consumer parsing `DEFECT_FINAL|D1` cannot resolve this to specific reviewer reports without knowing which ID namespace was used.

**Root cause:** The `{id}` in `DEFECT_FINAL` is unanchored — it floats between the four reviewer reports with no binding rule.

**Remediation:** Specify that the meta-reviewer assigns new sequential IDs (`MR-001`, `MR-002`) and includes a mapping to source reviewer IDs in a separate `DEFECT_MAP` line, OR specify that the meta-reviewer adopts the first reviewer's ID verbatim and downstream consumers must look it up in that reviewer's output.

---

## DEFECT-6: `SMOKE_TEST_BLOCKED` is defined in the prompt template but absent from the reviewer structured output format

**Severity:** major

**Scenario:**
The smoke-test reviewer prompt says: "report: `SMOKE_TEST_BLOCKED|{reason}`". But the reviewer structured output format block shows only `LENS`, `VERDICT`, `DEFECT`, and `PASS` as valid line types. `SMOKE_TEST_BLOCKED` is not listed in the format. An LLM agent following the format spec strictly would not know where to place this token — before `VERDICT`? As a `DEFECT`? After `STRUCTURED_OUTPUT_END`?

More concretely: if the reviewer emits `SMOKE_TEST_BLOCKED`, what should `VERDICT` be? The prompt says this "is NOT a pass, it is a gap in the review." But the format only allows `approved` or `rejected`. There is no `blocked` verdict. An LLM will invent one (`VERDICT|blocked`) or pick the least-wrong option, producing either a parse failure or a semantically incorrect verdict.

**Root cause:** The `SMOKE_TEST_BLOCKED` token was defined in the prose prompt but not integrated into the structured output format block.

**Remediation:** Add `SMOKE_TEST_BLOCKED|{reason}` as a first-class line type in the reviewer format. Specify what `VERDICT` must be when this line is present (e.g., `VERDICT` is omitted, or a new value `incomplete` is defined).

---

## DEFECT-7: `COVERAGE` field in meta-reviewer format uses `smoke_blocked` but the reviewer emits `SMOKE_TEST_BLOCKED` — token mismatch

**Severity:** major

**Scenario:**
The meta-reviewer format lists `COVERAGE|smoke-test|smoke_blocked` as a valid status. The reviewer's prompt says to output `SMOKE_TEST_BLOCKED|{reason}`. These are different tokens (`smoke_blocked` vs. `SMOKE_TEST_BLOCKED`). A meta-reviewer parsing the smoke-test output file looking for the string `SMOKE_TEST_BLOCKED` to set the coverage status must invent the mapping between these two representations. If the meta-reviewer instead looks for `VERDICT|blocked` (which it might, since that's the natural location for status), it finds nothing and may incorrectly set `COVERAGE|smoke-test|parse_failed` instead of `smoke_blocked`.

**Root cause:** The token used in the reviewer output (`SMOKE_TEST_BLOCKED`) was not aligned with the token used in the meta-reviewer's COVERAGE status field (`smoke_blocked`). No parsing rule bridges them.

**Remediation:** Use identical tokens throughout. Either always use `SMOKE_TEST_BLOCKED` or always use `smoke_blocked`. Add an explicit parsing rule: "If the reviewer output file contains `SMOKE_TEST_BLOCKED`, set COVERAGE status to `smoke_blocked`."

---

## DEFECT-8: `confirmed_cross_lane` status in `DEFECT_FINAL` is undefined — when does a finding get this status vs. `confirmed`?

**Severity:** minor

**Scenario:**
The meta-reviewer format defines two "agreement" statuses:
- `confirmed` — "2+ reviewers agree"
- `confirmed_cross_lane` — "found outside primary lens"

But what does "found outside primary lens" mean for `confirmed_cross_lane`? If 2 reviewers agree on a finding and one of them filed it as a cross-lane finding, is the status `confirmed` or `confirmed_cross_lane`? If only 1 reviewer flagged it (as a cross-lane finding), is it `confirmed_cross_lane` or `single_reviewer`? The two axes (agreement count, in-lane vs. cross-lane) are not combined into a decision matrix. An LLM meta-reviewer will make an arbitrary choice.

**Root cause:** `confirmed_cross_lane` is not precisely defined — it does not specify the required agreement count or the relationship to `confirmed`.

**Remediation:** Add a decision matrix: "confirmed_cross_lane applies when: (a) the finding was tagged CROSS_LANE by the filing reviewer, AND (b) at least one other reviewer corroborates it (even if in-lane). If only one reviewer flagged it cross-lane, use single_reviewer."

---

## DEFECT-9: `PANEL_VERDICT|approved` condition references smoke-test golden paths but smoke-test may be in degraded mode

**Severity:** minor

**Scenario:**
The verdict rule states: `approved` requires "smoke-test golden paths all pass." But the quorum rule explicitly allows the panel to proceed in "degraded mode" if smoke-test times out. In degraded mode, smoke-test golden paths have not been verified — they neither passed nor failed. The meta-reviewer cannot simultaneously honor both rules: `approved` requires golden paths to all pass, but degraded mode means golden path status is unknown.

An LLM meta-reviewer resolving a panel where smoke-test timed out, all 3 other reviewers approved, and no defects were filed will face a genuine contradiction: it cannot issue `approved` (golden paths unverified) but has no basis for `rejected_fixable` or `rejected_unfixable` either.

**Root cause:** The verdict rules were defined without accounting for the degraded mode scenario explicitly documented in the quorum section.

**Remediation:** Add a fourth verdict value `approved_degraded` for the case where quorum passes but smoke-test is unavailable, OR explicitly state "In degraded mode without smoke-test, `approved` may be issued if all other conditions hold, with `SMOKE_TEST_UNAVAILABLE` prominently flagged."

---

## New Angles Discovered

1. **Ordering ambiguity:** The format block does not specify whether `LENS` must appear before `VERDICT`, or whether `DEFECT` and `PASS` lines can be interleaved. An LLM generating output in its natural reasoning order may produce `PASS` lines before `DEFECT` lines, or `VERDICT` before `LENS`. Parsers expecting fixed ordering will break.

2. **Multi-line description escape:** The `{description}` field in `DEFECT` lines contains no constraint preventing newlines or pipe characters in the description text. A defect description like "Missing validation for input|boundary condition" would corrupt the pipe-split parse.

3. **No `PASS` cardinality minimum:** The format requires `PASS` lines but specifies no minimum. A reviewer filing only `DEFECT` lines with no `PASS` lines is structurally valid per format, even though the spec conceptually requires both.
