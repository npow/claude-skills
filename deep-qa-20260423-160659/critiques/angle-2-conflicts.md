STRUCTURED_OUTPUT_START
DIMENSION|instruction_conflicts
ANGLE|cross-lane-empowerment-rule-ambiguity
REVIEWER|angle-2-conflicts
NEW_ANGLES|3
STRUCTURED_OUTPUT_END

---

# QA Critique — Angle 2: Instruction Conflicts in the Cross-Lane Empowerment Rule

## Summary

The cross-lane empowerment rule is structurally ambiguous in three ways that, working together, can cause a reviewer to invert their primary/secondary duty, file scope-creep findings unchecked, and produce a panel verdict that the meta-reviewer cannot meaningfully resolve. The defects below are independent and additive.

---

## Defect 1 — "Blocking" Is Undefined, Making the Filing Threshold an Open Invitation

**Severity: Critical**

**Concrete scenario:**
The spec-compliance reviewer reads the diff and notices that a helper function has no docstring, the variable names are terse, and a loop could be replaced with a list comprehension. None of these prevent the artifact from working. The reviewer, lacking any definition of "blocking," decides all three are "blocking" in the sense that they block future maintainability, and files three `CROSS_LANE|spec-compliance|code-quality` findings. Meanwhile, it spends a fraction of its time on acceptance criteria. The meta-reviewer receives three cross-lane findings from a reviewer whose job was spec-compliance, and zero primary-lane findings. The panel verdict is now dominated by noise.

**Root cause:**
The cross-lane prompt says "if you see a **blocking** defect outside your lane — FILE IT" but never defines "blocking." The only two illustrative examples given are a "security hole" and a "spec gap" — both are extreme, unambiguous cases. For the vast middle ground (performance issues, code smell, missing error handling, unclear naming), the reviewer has no rule. LLMs default to expansive interpretation when given an open invitation to file; "blocking" will be read as "I would block a PR on this," which varies per reviewer.

**Remediation:**
Define "blocking" inline in the prompt with an actionable threshold. Example: "A cross-lane defect is blocking only if it would cause the artifact to fail a primary-lane reviewer's verdict independently — i.e., the code-quality reviewer would `rejected` on this finding alone, or the security finding would constitute a severity=critical by itself." Alternatively, restrict cross-lane filing to a single severity tier ("cross-lane findings must be severity=critical or the panel ignores them").

---

## Defect 2 — No Quantitative Cap or Ratio Guard on Cross-Lane Volume

**Severity: Major**

**Concrete scenario:**
A well-intentioned reviewer has been given full context (spec + diff + tests + build output) and is explicitly told it is "empowered to flag anything it sees." It identifies 12 potential cross-lane issues. Because no cap or ratio rule exists, it files all 12 with `CROSS_LANE|...` tags. Its primary-lens section contains 2 findings. The meta-reviewer now has a panel where one reviewer contributed 12 cross-lane and 2 primary findings; another contributed 0 cross-lane and 9 primary findings. The meta-reviewer has no rule for detecting that the first reviewer has effectively abandoned its lane. The `CROSS_LANE_FINDINGS|{count}` aggregate in the meta-reviewer output tells you the total count but does not flag per-reviewer inversion.

**Root cause:**
The pattern says "the primary lens determines their *focus* and *accountability*" but provides no enforcement mechanism. Focus and accountability are stated as intentions, not enforced constraints. The structured output format logs `CROSS_LANE|{own_lens}|{finding_lens}` tags, which enables deduplication but not ratio checking. The meta-reviewer protocol has no rule for "reviewer filed more cross-lane than primary-lane findings."

**Remediation:**
Add a hard cap in the reviewer prompt: "File at most 2 cross-lane findings per review session. If you see more than 2 cross-lane blocking defects, list the remainder as a single summary note, not as individual DEFECT lines." Additionally, add a meta-reviewer check: if any reviewer's cross-lane count exceeds its primary-lane DEFECT count, flag `LANE_INVERSION|{lens}` in the meta-reviewer output.

---

## Defect 3 — The Empowerment Preamble in the Panel-Composition Table Contradicts the Prompt Rule

**Severity: Major**

**Concrete scenario:**
A reviewer agent reads both the panel-composition section and the cross-lane empowerment rule. The table says "The primary lens determines their *focus* and *accountability*, not their *scope*." This directly implies scope is unlimited. The prompt rule then says "Focus your analysis there. However, if you see a blocking defect outside your lane — FILE IT." An LLM reading these two instructions together concludes: "My scope is unlimited (table), and I must file blocking cross-lane defects (prompt). Therefore I should actively scan all lenses for blocking defects, not merely note them opportunistically." The word "however" in the prompt is meant to signal an exception; instead, the unlimited-scope framing in the table transforms it into a mandate to conduct a secondary full-scope review.

**Root cause:**
The table-level claim ("not their *scope*") and the prompt-level instruction ("Focus your analysis there. However...") are pointing in opposite directions. The table removes scope boundaries entirely. The prompt implies a cost ("focus... however") that is undercut by the table's framing. The two are never reconciled. A reviewer that reads both — which it will, because full context is passed — receives contradictory signals about whether cross-lane filing is opportunistic or systematic.

**Remediation:**
Revise the table caption to: "The primary lens determines their *focus*, *accountability*, and primary *scope*. Cross-lane findings are an exception path for critical defects, not a parallel review mandate." Then make the prompt consistent: "Your job is {lens}. Spend 90%+ of your analysis time there. Only interrupt your primary review to file a cross-lane finding if you encounter a defect that is independently critical."

---

## Defect 4 — The Smoke-Test Reviewer Has No Meaningful Cross-Lane Filing Capability, But the Rule Applies to It Equally

**Severity: Minor**

**Concrete scenario:**
The smoke-test reviewer is explicitly told "You do NOT review code quality. You do NOT check spec compliance by reading code." It is executing golden paths, not reading source. The cross-lane empowerment rule applies to all four reviewers equally ("Every reviewer prompt includes"). But the smoke-test reviewer, by its own design, never reads the spec deeply or analyzes code. It has no realistic path to discover a cross-lane "spec gap" or "security hole" through execution alone. If it files a cross-lane finding anyway (e.g., "the error message was unclear" tagged as `CROSS_LANE|smoke-test|code-quality`), the meta-reviewer has no rule for weighting this differently than a code-quality reviewer's primary-lane finding on the same issue.

**Root cause:**
The cross-lane empowerment rule was written for code-reading reviewers. The smoke-test reviewer operates in a fundamentally different modality (execution, not analysis). The rule does not account for this asymmetry. The result is either (a) smoke-test cross-lane findings are structurally weaker but treated equally, or (b) smoke-test reviewer is confused about whether "something looked wrong at runtime" counts as a cross-lane filing or a primary-lane finding.

**Remediation:**
Exclude the smoke-test reviewer from the cross-lane empowerment rule, or provide a separate variant: "If during execution you observe behavior that indicates a code-quality or spec-compliance defect — not just 'it failed' but 'the failure mode suggests X' — you may file a `CROSS_LANE|smoke-test|{lane}` finding with the observed evidence. Your primary output is always execution results, not analysis."

---

## Defect 5 — Cross-Lane Findings Can Manufacture a False "Confirmed" Status via Tag Launder

**Severity: Major**

**Concrete scenario:**
Reviewer A (spec-compliance) files a primary-lane finding: `DEFECT|D1|major|spec-compliance|Missing acceptance criterion for error recovery`. Reviewer B (code-quality) independently notices the same gap and files: `DEFECT|D2|major|CROSS_LANE|code-quality|spec-compliance|Error recovery not implemented per spec`. The meta-reviewer deduplicates them and assigns `confirmed (2+ reviewers agree)` status. But Reviewer B's finding is cross-lane — it was filed by a reviewer not focused on spec-compliance, looking at the same full-context document, effectively re-reading the spec. This is not independent confirmation; it is the same evidence path, re-traversed. The "confirmed" status implies two independent review efforts reached the same conclusion, but both findings stem from reading the same spec line in the same document.

**Root cause:**
The meta-reviewer deduplication rule for `confirmed (2+ reviewers agree)` does not distinguish between:
- Two primary-lane reviewers finding the same issue through independent analysis (high-confidence confirmation)
- One primary-lane reviewer plus one cross-lane reviewer reading the same artifact and noticing the same thing (lower-confidence, same-evidence-path re-traversal)

The `confirmed_cross_lane` status exists in the meta-reviewer output format but is defined as "found outside primary lens" — it still counts toward the `confirmed` threshold. There is no documented rule for whether `confirmed_cross_lane` has equal or lesser weight than `confirmed`.

**Remediation:**
Define explicitly: "`confirmed` requires 2+ primary-lane verdicts OR 1 primary-lane + 1 cross-lane verdict from a reviewer whose primary lens is orthogonal (i.e., would not naturally see the same evidence). A cross-lane finding from a reviewer that read the same document as the primary-lane reviewer does NOT elevate status to `confirmed`; it remains `single_reviewer` with a note `supported_cross_lane`."

---

## New Angles Discovered During This Analysis

**New Angle A — Verdict pollution by cross-lane severity inflation:**
A reviewer might file a cross-lane defect at `severity=critical` to ensure it isn't dismissed, knowing the meta-reviewer defaults to keeping uncontradicted single-reviewer findings. There is no rule preventing severity escalation for cross-lane findings. A reviewer that files a critical cross-lane defect effectively forces the meta-reviewer to treat it as load-bearing, regardless of whether the primary-lane reviewer (the accountable party) would have rated it critical.

**New Angle B — The integration-coherence reviewer's cross-lane surface is almost unbounded:**
Integration-coherence focuses on "cross-component contracts honored; API boundaries consistent; data flows end-to-end." Its primary lens is already cross-cutting. When it files a cross-lane finding tagged `CROSS_LANE|integration-coherence|code-quality`, this is structurally indistinguishable from its primary work. The cross-lane rule provides no additional clarity for a reviewer whose primary lens already spans multiple components.

**New Angle C — No timeout behavior specified for cross-lane analysis within a reviewer's budget:**
Reviewers have a 180s timeout. If a reviewer spends time actively scanning for cross-lane issues (which the unlimited-scope framing encourages), it may timeout before completing its primary-lane checklist. The timeout failure mode table only covers total reviewer timeout — it does not address within-budget priority ordering between primary-lane analysis and cross-lane scanning.
