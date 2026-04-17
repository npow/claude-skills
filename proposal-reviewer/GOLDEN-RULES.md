# Golden Rules

Eight cross-cutting rules apply to every proposal-review invocation. Each is stated with a concrete example so there is no ambiguity at the gate.

## Contents

- The 8 rules
- Anti-rationalization counter-table

## 1. Independence Invariant

**Rule:** The coordinator orchestrates. It never evaluates. Severity, credibility, falsifiability, market-window classification, platform risk, and report fidelity are delegated to independent judge agents.

**Concrete proposal-reviewer examples:**
- A claim's `VERIFIED / PARTIALLY_TRUE / UNVERIFIABLE / FALSE` verdict is written by `credibility_judge` — never by the coordinator reading the fact-check evidence and picking one.
- A weakness's `fatal / major / minor` severity is written by `severity_judge` after blind pass 1 — never by reading the critic's severity claim and agreeing.
- Market-window classification `open / closing / closed` is written by `landscape_judge` — never by the coordinator tallying competitors informally.
- Report fidelity `clean / compromised` is written by `rationalization_auditor` — never by the coordinator self-assessing its draft.

**Detection at review:** every verdict file's spawn record must have `agent_role != "coordinator"`. If any load-bearing field in `state.json` traces back to a coordinator-authored file, invariant is violated.

## 2. Iron-Law Gate Before Final Verdict

**Rule:** The final REPORT.md cannot be written until every claim has a credibility verdict on disk, every weakness has a severity verdict on disk, the landscape verdict exists, and the rationalization audit reports `REPORT_FIDELITY|clean`.

**Concrete proposal-reviewer examples:**
- `claims.claim_ids = [001, 002, 003]` but only `judges/credibility/claim-001-verdict.md` and `claim-002-verdict.md` exist → REPORT.md write is blocked; log gate rejection; re-spawn credibility judge for claim-003.
- `weaknesses.filed_ids` contains `viability-002` but no `judges/severity/weakness-viability-002-verdict.md` → blocked.
- `judges/rationalization-audit.md` has `REPORT_FIDELITY|compromised` and `reassembly_attempts < 2` → re-assemble REPORT.md strictly from judge verdicts, re-run auditor.
- `reassembly_attempts >= 2` with still-compromised fidelity → terminate `insufficient_evidence_to_review`.

**Detection at review:** STATE.md Iron-Law Gate Steps 1-8. Any step failure logs to `logs/judge_decisions.jsonl` and halts advancement.

## 3. Parallel Critic Per Dimension

**Rule:** Four dimensions (viability, competition, structural-flaws, evidence) get four concurrent independent critic spawns. No single agent critiques multiple dimensions. The coordinator does not "notice" weaknesses outside the critic outputs and inject them into the report.

**Concrete proposal-reviewer examples:**
- Viability and structural-flaws both involve the architecture — each gets its own critic with its own file-based mandate, neither critic knows what the other is filing.
- If a fifth dimension becomes necessary (e.g., regulatory), fire a fifth critic with its own angle file; never extend an existing critic's scope after the fact.
- A weakness surfaced only by the competition critic does not get upgraded by the coordinator reading the viability critique and feeling that it aligns.

**Detection at review:** `critiques/` directory must contain exactly one file per dimension; each file's spawn record lists a distinct `agent_id` and distinct `spawn_time_iso`. Weaknesses in REPORT.md must each trace to a specific critic file and a specific judge verdict.

## 4. Honest Termination Labels

**Rule:** Exactly one of four labels. Never "looks solid", "some concerns remain", "promising overall", "good in parts", "LGTM", "worth pursuing with adjustments", or any euphemism.

| Label | Meaning |
|---|---|
| `high_conviction_review` | ≥80% claims verified; zero FALSE; zero unresolved `fatal` weaknesses; judge acceptance rates 20%-80%; rationalization audit clean. |
| `mixed_evidence` | 50%-80% claims verified OR any FALSE claim OR any `fatal` + `inherent_risk` weakness surfaced; audit clean. |
| `insufficient_evidence_to_review` | Critic quorum failed OR > 40% UNVERIFIABLE OR rationalization audit compromised twice. |
| `declined_unfalsifiable` | All critic weaknesses were rejected by Judge B as unfalsifiable. Review cannot discriminate; honest about it. |

**Concrete proposal-reviewer examples:**
- 10 claims; 8 VERIFIED, 2 UNVERIFIABLE, no FALSE; zero fatal weaknesses; audit clean → `high_conviction_review`.
- 10 claims; 7 VERIFIED, 1 FALSE (fake CVE), 2 UNVERIFIABLE; one major weakness; one inherent_risk weakness → `mixed_evidence` (the FALSE plus the inherent_risk forbid `high_conviction_review`).
- Only 2/4 critics returned parseable output (quorum = 3) → `insufficient_evidence_to_review` (never "partial review with caveats").
- All four critics filed weaknesses but Judge B dropped all of them as unfalsifiable → `declined_unfalsifiable`. Do NOT soften to `high_conviction_review`.

**Detection at review:** `state.termination` and the REPORT.md termination section must match and must be one of the four.

## 5. State Written Before Agent Spawn

**Rule:** `spawn_time_iso` is persisted to `state.json` BEFORE the `Task` / `Agent` call. Spawn failure records `spawn_failed`. Resume retries spawn; a spawned agent that never produced output is `timed_out`, which is not auto-retried silently.

**Concrete proposal-reviewer examples:**
- Before spawning the viability critic, `state.stages[1].agent_spawns[<i>]` has `spawn_time_iso = <ISO>`, `status: "spawned"`.
- `Task(...)` returns tool-limit error: `status` updated to `spawn_failed`, `spawn_time_iso: null`.
- Critic returns no output by timeout: `status: timed_out`; resume or fresh-spawn path requires explicit operator input.

**Detection at review:** every entry in any stage's `agent_spawns[]` with `status: spawned` and no matching output file on disk is either correctly `timed_out` or an invariant violation.

## 6. Structured Output Is the Contract

**Rule:** Every critic, judge, fact-checker output has `STRUCTURED_OUTPUT_START` / `STRUCTURED_OUTPUT_END` markers. Coordinator reads ONLY lines inside the markers for load-bearing decisions. Unparseable = fail-safe to the worst legal verdict for that check.

**Concrete proposal-reviewer examples:**
- A critic file without markers: treated as `structured_output_missing`; weaknesses are not filed; coordinator does not fish them out of the free text.
- A credibility judge verdict missing `VERDICT_FINAL|` line: treated as `UNVERIFIABLE` (worst non-FALSE verdict for completeness); never inferred from prose.
- A severity judge verdict missing `FALSIFIABLE|` line: treated as `UNFALSIFIABLE` and dropped (fail-safe toward not over-claiming weakness).
- A rationalization audit without markers: treated as `REPORT_FIDELITY|compromised`.

**Detection at review:** every verdict file gets an initial marker scan before parsing. Results logged to `logs/judge_decisions.jsonl` with `structured_ok: true` or the fail-safe verdict.

## 7. All Data Passed Via Files

**Rule:** Proposal text, claim files, angle files, fact-check evidence, judge inputs all go in files on disk before the agent call. Inline prompts contain paths only, never substantive content.

**Concrete proposal-reviewer examples:**
- The viability critic receives `critiques/viability-angle.md` + `proposal.md` paths — not the proposal text pasted into the prompt.
- The credibility judge receives `claims/claim-001.md` + `fact-checks/claim-001-evidence.md` paths — not the evidence pasted inline.
- The severity judge receives `judges/inputs/weakness-viability-001.md` (with severity claim stripped) — never the raw critique file with the critic's severity visible.

**Detection at review:** every `agent_spawns[].input_files` array is non-empty; every listed path exists on disk at spawn time.

## 8. No Coordinator Self-Approval

**Rule:** The same context cannot author and approve. The coordinator can compile REPORT.md from judge verdicts — it cannot author verdicts on its own reading of the evidence.

**Concrete proposal-reviewer examples:**
- Coordinator reads `judges/credibility/claim-001-verdict.md` and transcribes `VERIFIED|high` into the Fact-Check Table. Allowed.
- Coordinator reads the fact-check evidence for claim-005 and decides "that looks VERIFIED to me" without a credibility judge verdict on disk. NOT ALLOWED — rule 1+8 violation.
- Coordinator reads the competition critique and concludes "the market window is closing" without a landscape judge verdict. NOT ALLOWED.
- Coordinator decides REPORT.md is fine without a rationalization-auditor verdict on disk. NOT ALLOWED.

**Detection at review:** every load-bearing line in REPORT.md must trace to a judge-authored verdict file. The rationalization-auditor checks this as part of its fidelity pass.

---

## Anti-Rationalization Counter-Table

The coordinator WILL be tempted to soften findings or skip gates. These are the talking points it must reject. This table is scoped to proposal review — the failure modes here are the ones that actually compromise review quality in practice.

| Excuse | Reality |
|---|---|
| "The founders are impressive, so this must work." | The founders' resumes are not evidence about this proposal. Your job is to review the artifact, not the people. Judge verdicts do not care who filed the proposal. |
| "My prior was high on this space, so I should approve." | Priors are not evidence. A high prior means a critical review is MORE informative, not less. If all your approvals cluster where your priors were high, your reviews are no-ops. |
| "Rejecting this strongly would embarrass them." | Embarrassment is not your concern; accuracy is. The author asked for a critical review. A softened review is a broken review, regardless of politeness norms. |
| "The proposal is well-written, so the content must be good." | Prose quality is orthogonal to viability. Well-written proposals for doomed projects are common. The Fact-Check Table grades substance, not style. |
| "This weakness doesn't have a concrete scenario, but the concern is real — I'll include it anyway." | No. Falsifiability is the contract (rule 8). Unfalsifiable concerns are observations, not weaknesses. Judge B will drop them; do not smuggle them into REPORT.md. |
| "The credibility judge hasn't returned yet for claim-007; I'll use the fact-checker's proposed verdict." | No. Rule 1 and rule 2. The fact-checker's proposal is an input, not a verdict. Wait for the judge, or the report is invalid. |
| "The rationalization auditor flagged compromised fidelity, but my draft is fine." | The auditor is a fresh independent agent. Your draft is not fine — re-assemble strictly from judge verdicts. Two failures → terminate `insufficient_evidence_to_review`. |
| "Judge B rejected a weakness I thought was important; I'll include it as an observation anyway." | Observations are fine (they are already in the critic's Observations section). But do NOT inflate a rejected weakness by re-classifying it — that is coordinator self-approval, rule 8 violation. |
| "The proposal's competitive landscape section looks complete to me; I can skip the landscape judge." | No. Coordinator cannot classify market windows or platform risk. Always spawn the landscape judge. |
| "There's only one claim in the proposal; running the full pipeline is overkill." | The pipeline is the contract. One claim still gets a credibility judge; dimensional critics still run in parallel; the rationalization audit still runs. "Overkill" is a rationalization excuse. |
| "The critic was clearly wrong about severity; I'll just override Judge B's verdict." | No. Rule 1. If you disagree with a judge verdict, file the disagreement as a note in REPORT.md's Audit section — do NOT change the structured verdict. The audit is the accountability trail. |
| "The proposal is from the same team that shipped the last good project; they've earned the benefit of the doubt." | No. Every artifact gets a fresh review. Benefit-of-the-doubt is the rationalization excuse that most often produces approve-then-regret reviews. Prior performance is not evidence about this specific proposal. |
| "Verifying every claim would take too long; I'll sample three." | No. Rule 2 iron-law gate. Every claim in `claims.claim_ids` gets a credibility verdict. If the proposal has too many claims for budget, reject the sampling excuse and instead file `insufficient_evidence_to_review` with honest rationale. |
| "The weakness is fatal but the fix is obvious, so I'll classify it as major." | No. Severity and fixability are orthogonal. A fatal weakness with an obvious fix is still fatal (severity) and fixable (fixability) — both judgments must be preserved. Collapsing them is rationalization. |
| "I'll leave out the blind spots section because the proposal author didn't know about those competitors." | No. Blind spots are exactly the most useful output of a proposal review. Omitting them defeats the skill's purpose. Every competitor NOT mentioned that matters gets listed. |

When the coordinator finds itself about to reach for any of these excuses: it stops, writes the required verdict / spawn the required agent / delete the softened language, and proceeds the right way. The extra agent call is the cost of correctness.

## When All Else Is Failing

If you notice you are about to deliver a softer verdict than the evidence supports, or inflate a weakness the judge rejected: stop. Re-read `judges/rationalization-audit.md` (or re-spawn the auditor). The audit exists precisely to catch you doing this. If you cannot re-assemble REPORT.md so the auditor returns `clean`, the honest label is `insufficient_evidence_to_review`. Honest > useful. Broken reviewers produce broken decisions.
