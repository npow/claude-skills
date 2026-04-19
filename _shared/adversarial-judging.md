# Adversarial Judging Patterns

Shared reference for skills that run parallel critics + independent judges on an artifact and need to prevent coordinator rationalization, judge rubber-stamping, or filed-but-useless weaknesses.

**Imported by:** `deep-qa`, `proposal-reviewer`. Candidates for future adoption: `deep-design`, `deep-debug`, `deep-plan`.

**Scope:** the four structural mechanisms that make critic output adversarial without drifting into inflation or nitpicking. These are structural — the mechanisms close specific rationalization loopholes, not just state rules.

**Not in scope:** claim extraction, fact-check research, landscape analysis, domain-specific dimension taxonomies — those belong in each skill.

---

## The four mechanisms

| # | Mechanism | Loophole it closes |
|---|---|---|
| 1 | Blind severity protocol (two-pass) | Judge anchors on critic's severity claim |
| 2 | Mandatory author counter-response | Unfalsifiable "this might be a problem" filings |
| 3 | Rationalization auditor | Coordinator drift during final assembly |
| 4 | Falsifiability drop (not downgrade) | Noise floor of theoretical concerns in final report |

---

## 1. Blind severity protocol (two-pass judge)

**Problem:** if the judge sees the critic's severity claim, the judge anchors on it. Judges that agree with critics 100% of the time are broken, and coordinators can't detect that because the data looks reasonable.

**Pass 1 — blind:**
1. Coordinator writes `judges/inputs/{id}.md` with: the defect/weakness title, scenario, root cause, counter-response — but **strips the critic's proposed severity** before handoff.
2. Spawn an independent judge (fresh context — NEVER the same agent that authored the critique). Judge writes structured verdict:
   ```
   DEFECT_ID|{id}
   SEVERITY|fatal|major|minor|rejected
   CONFIDENCE|high|medium|low
   RATIONALE|{one line}
   ```
3. Judge writes to `judges/severity/{id}-verdict.md`.

**Pass 2 — informed:**
1. Coordinator adds the critic's original severity claim to the judge's input file (append, do not replace pass-1 verdict).
2. Same judge (or a fresh one) may: confirm, upgrade, or downgrade the pass-1 verdict with rationale.
3. Final verdict is the pass-2 conclusion.

**Calibration signal:** if pass-1 and pass-2 verdicts match 100% across all defects, the judge is anchoring despite the blind protocol (suspicious — investigate). If they disagree substantially, the two-pass is doing work.

**Judge prompt boilerplate:**
```
You succeed by rejecting or downgrading. You fail by rubber-stamping.
A 100% acceptance rate OR 100% rejection rate is evidence of failure.
If you cannot articulate a concrete reason this defect is real, reject it.
Calibrate against evidence, not the desire to seem diligent or generous.
```

**Skip condition:** for skills with ≤3 critics/round, blind severity adds overhead without signal. Use only when critic pool is ≥4 OR the artifact is high-stakes (production deploy, grant decision, hiring).

---

## 2. Mandatory author counter-response

**Problem:** "this MIGHT be unclear" is not a defect — it's a concern. Without a concrete scenario AND a plausible defense the artifact's author could mount, the filing cannot be resolved by disagreement; it just floats.

**Contract:** every filed weakness must ship with ALL of:
- Concrete failure scenario (who, what, when, consequence)
- Root cause (one line)
- **Author counter-response** — what the artifact's author could plausibly say to defend this point. If the critic cannot write a plausible counter-response, the weakness is not falsifiable and is filed as a minor observation instead, NOT a weakness.

**Why the counter-response specifically:** it forces the critic to consider whether the defect will survive rebuttal. A weakness without a plausible counter-response is either (a) trivially correct (not a defect) or (b) unfalsifiable (noise). Either way, don't file it as a weakness.

**Critic prompt boilerplate:**
```
For every filed weakness, produce:
- Title
- Severity claim (fatal/major/minor) — will be stripped before judge sees it
- Concrete failure scenario (who, what, when, why it fails)
- Root cause (one line)
- **Author counter-response — what the author could plausibly say in defense.**
  This is REQUIRED. If you cannot write a plausible counter-response,
  the weakness is not falsifiable; do NOT file it as a weakness.
  File it as a minor observation instead.
- Suggested fix direction (one line, optional)
```

**Report section to emit (not just track internally):** the counter-response goes into the final report beside each weakness. This tells the artifact owner: "we thought about your likely rebuttal, and we still think this is a weakness — here's why."

---

## 3. Rationalization auditor

**Problem:** the coordinator assembles the final report from judge verdicts. Along the way, the coordinator is free to summarize, soften, combine, or drop defects — and no one checks.

**Audit agent spec:**
1. Spawned after all judges complete, BEFORE final report assembly.
2. Input: the complete `judges/` directory — every verdict file.
3. Output: `judges/rationalization-audit.md` with structured verdict:
   ```
   ACCEPTANCE_RATE_{DIMENSION}|{rate}   # one line per dimension
   DEFECTS_TOTAL|{count}
   DEFECTS_CARRIED|{count}              # how many made it into draft report
   DEFECTS_DROPPED|{count}              # how many were filtered
   SUSPICIOUS_PATTERNS|{list or "none"}
   REPORT_FIDELITY|clean|compromised
   ```

**What the auditor checks:**
- Did every falsifiable weakness with `SEVERITY != rejected` make it into the draft report?
- Do judge acceptance rates fall within the expected band (20%-80% per dimension is healthy; 0% or 100% is suspicious)?
- Is the draft summary consistent with the per-defect verdicts, or does it soften/omit?
- Has the coordinator used any excuse from the anti-rationalization counter-table?

**Failure response:** if `REPORT_FIDELITY|compromised`:
1. Coordinator halts assembly.
2. Re-assemble the report **strictly from judge verdicts** — coordinator cannot add, combine, or soften.
3. Re-run the auditor. Two successive failures → terminate with label `insufficient_evidence_to_review` (or domain equivalent).

**Independence invariant:** the auditor is a fresh agent with no prior context in the run. It reads the `judges/` directory and the coordinator's draft — nothing else.

---

## 4. Falsifiability drop (not downgrade)

**Problem:** skills that keep unfalsifiable filings as "minor notes" end up with a defect registry padded with noise. Report consumers triage from the top — noise at the bottom erodes trust in the top.

**Rule:** any weakness where Judge verdict sets `FALSIFIABLE|no` is **dropped from the final report entirely**. It does not appear as a minor. It does not appear as a note. It appears only in the `logs/judge_decisions.jsonl` drop log with the reason for dropping.

**Why drop instead of downgrade:**
- Downgrade-to-minor is rationalization disguised as rigor. ("I filed the concern AND acknowledged it's weak — defensible!") It inflates registry size without helping anyone.
- Unfalsifiable = the concern cannot be resolved by disagreement. The artifact owner cannot act on it. Keeping it is performative.
- If the critic's concern is real but unfalsifiable, the fix is: rewrite the concern as a falsifiable weakness, not to keep the unfalsifiable version.

**Difference from deep-qa's current practice:** deep-qa's nitpick filter keeps unfalsifiable issues as "minor notes." The adversarial-judging pattern says: drop them from the report entirely and log the drop. If a skill wants to retain the soft-concerns channel, split it from the defect registry explicitly.

**Drop-log format (append-only JSON lines):**
```json
{"defect_id": "viability-003", "dropped_at": "2026-04-18T10:30:00Z", "reason": "FALSIFIABLE|no", "judge_verdict_path": "judges/severity/viability-003-verdict.md"}
```

---

## Integration checklist

When importing this reference into a skill, the skill's SKILL.md must include:

- [ ] A `## Adversarial judging` section with a one-line cross-reference: `See [_shared/adversarial-judging.md](../_shared/adversarial-judging.md) for the blind severity protocol, counter-response contract, rationalization auditor, and falsifiability drop.`
- [ ] A decision about which of the four mechanisms apply to this skill. Skills that skip any mechanism MUST record the reason (e.g., "blind severity skipped — only 2 critics per round").
- [ ] The critic prompt template includes the counter-response requirement (quote it verbatim from §2).
- [ ] The judge prompt template includes the adversarial mandate (quote from §1).
- [ ] The Phase 5/6/assembly step includes a call to the rationalization auditor before report synthesis.
- [ ] The state/file layout has a `judges/` directory with `inputs/`, `severity/`, `credibility/` (as applicable), and `rationalization-audit.md`.
- [ ] The final report schema has a `Weaknesses (Falsifiable Only)` section with per-weakness counter-response.
- [ ] The drop-log path is documented.

---

## Anti-rationalization counter-table (judge/critic specific)

| Excuse | Reality |
|---|---|
| "The judge agrees with the critic 100% of the time — they're aligned." | Alignment at 100% is calibration failure. Either the judge is anchoring, or the critics are inflating. Investigate the pass-1 verdicts. |
| "The counter-response requirement adds noise — let's skip it for minor filings." | The counter-response is the falsifiability test. Without it, minor is a landing zone for unfalsifiable filings that should have been dropped. Keep the requirement. |
| "The coordinator can safely skip the rationalization auditor if the critic output looks clean." | Coordinator drift happens during assembly, not during critic output. The auditor checks assembly, not critics. Skipping it defeats the point. |
| "Dropping a defect is harsh — let's keep it as a minor note." | Downgrade-to-minor is rationalization disguised as rigor. Unfalsifiable filings cannot be resolved; keeping them inflates the registry. Drop and log. |
| "Pass-1 blind severity adds a round-trip — let's just give the judge the critic's severity." | The round-trip IS the mechanism. A judge that sees the severity claim anchors on it; that's the empirical finding the protocol exists to address. |
| "The counter-response the critic wrote is weak — the defect is still real." | Weak counter-response = the critic didn't think the defect could be rebutted. That's the signal. Require a stronger counter-response or drop the defect. Do not file it without one. |
| "100% rejection rate from the judge means the judge is adversarial (which is good)." | 100% rejection rate means the judge is broken. Adversarial means rigorous, not reflexive. Investigate the judge's rationales — they should differentiate between filings. |

---

## Open questions (not resolved here)

- Who writes the counter-response when the critic cannot? (Current answer: nobody; the defect is dropped. Alternative: a "devil's advocate" pass. Undecided.)
- Should the auditor also check critic acceptance rates, or only judge acceptance rates? (Current answer: judge only; critic acceptance is orthogonal. Open to revision.)
- Does the falsifiability drop apply to `CRITICAL`-severity defects, or only to `major`/`minor`? (Current answer: drop regardless of severity. A critical-but-unfalsifiable filing is still unfalsifiable. If it's really critical, the critic can restate it falsifiably.)

Skills importing this reference should resolve these for their domain and document the decision in their SKILL.md.
