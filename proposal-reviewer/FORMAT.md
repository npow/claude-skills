# Output Formats

All structured outputs MUST be enclosed in `STRUCTURED_OUTPUT_START` / `STRUCTURED_OUTPUT_END` markers. Files without these markers are treated as failed (not partially consumed). Coordinator reads only structured lines; lines outside the markers are ignored for parsing purposes (they may still appear in the report as narrative).

Parser contract:
- Pipe (`|`) splits fields. Parser splits on the first N pipes per line, where N is the declared field count for the line type.
- Unknown line types inside markers: logged to `logs/judge_decisions.jsonl` with `event: unknown_structured_line`; parser continues.
- Missing required fields in a structured line: the whole line is discarded and logged.
- Files without both markers: treated as failed. Coordinator records `failure_reason: "missing_structured_markers"` in `state.json`.

## Contents

- Claim registry schema
- Per-claim file schema
- Critic output schema (per dimension)
- Fact-check evidence schema
- Credibility judge verdict schema (per claim)
- Severity + falsifiability judge verdict schema (per weakness)
- Landscape judge verdict schema
- Rationalization audit schema
- Final REPORT.md skeleton
- Logs

## Claim Registry Schema

Used in `claims/REGISTRY.md`. Written by the claim-extractor agent.

```markdown
# Claim Registry

**Run:** {run_id}
**Extractor:** {agent_id}
**Proposal file:** `proposal-review-{run_id}/proposal.md`

## Claims

- **claim-001** — {one-line description}
- **claim-002** — {one-line description}
- ...

STRUCTURED_OUTPUT_START
CLAIM|001|{category}|{specificity}|{one-line description}
CLAIM|002|{category}|{specificity}|{one-line description}
TOTAL_CLAIMS|{n}
STRUCTURED_OUTPUT_END
```

`{category}` is one of: `statistic|funding|cve|github_metric|publication|org_statement|market|attribution|negative_existence|standard_classification`.

`{specificity}` is `HIGH` (names a specific source/number/date) or `LOW` (vague attribution).

## Per-Claim File Schema

Used in `claims/claim-{NNN}.md`.

```markdown
# Claim {NNN}
**Category:** {category}
**Specificity:** HIGH|LOW
**Location in proposal:** {section name or line range}

## Verbatim text
> {exact quote from proposal}

## Parsed assertion
{what the claim asserts, neutrally restated}

## Verification strategy hint (for fact-check agent)
{e.g., "search NVD for CVE number", "check arXiv for paper title", "check Crunchbase for funding round"}

STRUCTURED_OUTPUT_START
CLAIM_ID|{NNN}
CATEGORY|{category}
SPECIFICITY|HIGH|LOW
ASSERTION|{one-line neutral restatement}
STRUCTURED_OUTPUT_END
```

## Critic Output Schema (Per Dimension)

Used in `critiques/{dimension}-critique.md`. Written by independent dimension critic.

```markdown
# Critique: {dimension}

**Critic:** {agent_id}
**Dimension:** viability|competition|structural-flaws|evidence
**Proposal:** `proposal-review-{run_id}/proposal.md`
**Core claim under review:** {locked core_claim verbatim}

## Findings

### Finding: {title}
- **Severity claim:** fatal|major|minor (stripped before judge sees this file)
- **Scenario:** {concrete failure scenario — who, what, when}
- **Root cause:** {one line}
- **Suggested fix direction:** {one line}
- **Author counter-response:** {plausible defense the proposal author could mount}

### Finding: {title}
(repeat for each weakness; max 5 per critic)

## Observations (unfalsifiable — not weaknesses)
{list any concerns that do not meet falsifiability; these are for context only and do not enter the judge pipeline}

STRUCTURED_OUTPUT_START
DIMENSION|{dimension}
WEAKNESS|{NNN}|{severity_claim}|{title}|{one-line scenario}
WEAKNESS|{NNN}|{severity_claim}|{title}|{one-line scenario}
OBSERVATION|{one-line unfalsifiable concern}
NEW_ANGLE_SUGGESTION|{text}
STRUCTURED_OUTPUT_END

SEVERITY_CLAIM_BLOCK_START
WEAKNESS|001|{severity_claim}|{rationale for severity}
WEAKNESS|002|{severity_claim}|{rationale for severity}
SEVERITY_CLAIM_BLOCK_END
```

The coordinator strips `SEVERITY_CLAIM_BLOCK_START` → `SEVERITY_CLAIM_BLOCK_END` from the file before handing to Judge B, enabling blind severity protocol (pass 1).

## Fact-Check Evidence Schema

Used in `fact-checks/claim-{NNN}-evidence.md`. Written by independent fact-check agent.

```markdown
# Fact-Check: claim-{NNN}

**Fact-checker:** {agent_id}
**Claim:** {verbatim quote}

## Searches performed
- Search 1: {query} → {source(s) consulted}
- Search 2: {query} → {source(s) consulted}
- ...

## Evidence found
- {URL or citation} — {one-line quote or paraphrase}
- {URL or citation} — {one-line quote or paraphrase}

## Proposed verdict (this is a proposal, not the authoritative verdict)
{VERIFIED | PARTIALLY_TRUE | UNVERIFIABLE | FALSE}

## Confidence
{high | medium | low}

STRUCTURED_OUTPUT_START
CLAIM_ID|{NNN}
SEARCHES_RUN|{count}
SOURCES_CONSULTED|{count}
PROPOSED_VERDICT|VERIFIED|PARTIALLY_TRUE|UNVERIFIABLE|FALSE
CONFIDENCE|high|medium|low
EVIDENCE_URL|{url}
EVIDENCE_URL|{url}
STRUCTURED_OUTPUT_END
```

The `PROPOSED_VERDICT` line is stripped by the coordinator before the credibility judge reads the evidence (blind verdict protocol, pass 1).

## Credibility Judge Verdict Schema (Per Claim)

Used in `judges/credibility/claim-{NNN}-verdict.md`. Written by independent credibility judge.

```markdown
# Credibility Verdict: claim-{NNN}

**Judge:** {agent_id}
**Input files:** {list}

## Pass 1 (blind — fact-checker's proposed verdict not shown)
- Verdict: {VERIFIED | PARTIALLY_TRUE | UNVERIFIABLE | FALSE}
- Confidence: {high | medium | low}
- Rationale: {one line}

## Pass 2 (with fact-checker's proposed verdict)
- Fact-checker's proposal: {VERIFIED | PARTIALLY_TRUE | UNVERIFIABLE | FALSE}
- Final verdict (confirm/upgrade/downgrade): {VERIFIED | PARTIALLY_TRUE | UNVERIFIABLE | FALSE}
- Rationale for confirm/upgrade/downgrade: {one line}

STRUCTURED_OUTPUT_START
CLAIM_ID|{NNN}
EVIDENCE_FOUND|yes|partial|no
VERDICT_PASS_1|VERIFIED|PARTIALLY_TRUE|UNVERIFIABLE|FALSE
VERDICT_FINAL|VERIFIED|PARTIALLY_TRUE|UNVERIFIABLE|FALSE
CONFIDENCE|high|medium|low
RATIONALE|{one-line}
STRUCTURED_OUTPUT_END
```

## Severity + Falsifiability Judge Verdict Schema (Per Weakness)

Used in `judges/severity/weakness-{dim}-{NNN}-verdict.md`. Written by independent severity judge.

```markdown
# Severity Verdict: weakness-{dim}-{NNN}

**Judge:** {agent_id}
**Input file:** {path — stripped of critic's severity claim}

## Falsifiability check
- Concrete scenario present: yes|no
- Plausible author counter-response present: yes|no
- Verdict: FALSIFIABLE|UNFALSIFIABLE

## Pass 1 (blind severity assignment)
- Severity: fatal|major|minor|rejected
- Fixability: fixable|inherent_risk|fatal
- Rationale: {one-line}

## Pass 2 (with critic's severity claim)
- Critic's claimed severity: {from SEVERITY_CLAIM_BLOCK}
- Final severity (confirm/upgrade/downgrade): fatal|major|minor|rejected
- Rationale: {one-line}

STRUCTURED_OUTPUT_START
WEAKNESS_ID|{dim}-{NNN}
FALSIFIABLE|yes|no
SEVERITY_PASS_1|fatal|major|minor|rejected
SEVERITY_FINAL|fatal|major|minor|rejected
FIXABILITY|fixable|inherent_risk|fatal
CONFIDENCE|high|medium|low
RATIONALE|{one-line}
STRUCTURED_OUTPUT_END
```

Severity definitions (calibration):
- `fatal` — the weakness, if realized in the scenario, breaks the proposal's core promise. No fix keeps the core claim intact.
- `major` — the weakness significantly degrades viability; fix may be available but costly.
- `minor` — edge case, polish, easily mitigated.
- `rejected` — the weakness is already mitigated by the proposal's existing structure OR is unfalsifiable. Do NOT inflate to signal diligence.

Fixability definitions:
- `fixable` — proposal can be rewritten to address; core approach remains.
- `inherent_risk` — no amount of rewriting eliminates; must be accepted and planned around.
- `fatal` — the weakness makes the core claim untenable.

## Landscape Judge Verdict Schema

Used in `judges/landscape-verdict.md`.

```markdown
# Landscape Verdict

**Judge:** {agent_id}
**Input files:** {competition critique + landscape/ research outputs}

## Findings
- Direct competitors: {count} — {threat level distribution}
- Adjacent competitors: {count}
- Platform vendors signaling intent: {list}
- Open-source alternatives: {count}
- Blind spots (competitors not mentioned in proposal): {list}

## Market window assessment
{narrative with evidence}

## Platform risk assessment
{narrative with evidence}

STRUCTURED_OUTPUT_START
MARKET_WINDOW|open|closing|closed
PLATFORM_RISK|low|medium|high
MOST_LIKELY_PLATFORM_THREAT|{vendor}|{timeline_months}
COMPETITORS_NOT_MENTIONED|{count}
BLIND_SPOT|{competitor_name}|{why_it_matters}
BLIND_SPOT|{competitor_name}|{why_it_matters}
RATIONALE|{one-line}
STRUCTURED_OUTPUT_END
```

## Rationalization Audit Schema

Used in `judges/rationalization-audit.md`. Written by independent rationalization-auditor.

```markdown
# Rationalization Audit

**Auditor:** {agent_id}
**Input:** full judges/ directory + coordinator's draft REPORT.md

## Judge acceptance rates
- Viability critic: {n_weaknesses}, {n_accepted}, rate {%}
- Competition critic: ... (similar)
- Structural-flaws critic: ...
- Evidence critic: ...

## Distribution of severities (across all accepted weaknesses)
- fatal: {n}
- major: {n}
- minor: {n}

## Suspicious patterns
{list any of: 100% acceptance on any dimension, 100% rejection on any dimension, severity distribution skewed to minor when scenarios describe fatal failures, weaknesses tagged FALSIFIABLE dropped from REPORT.md anyway, coordinator draft uses rationalization-table excuses}

## Report fidelity check
{does the coordinator's draft REPORT.md faithfully reflect the judge verdicts, or does it soften/inflate them?}

STRUCTURED_OUTPUT_START
ACCEPTANCE_RATE_VIABILITY|{percent}
ACCEPTANCE_RATE_COMPETITION|{percent}
ACCEPTANCE_RATE_STRUCTURAL|{percent}
ACCEPTANCE_RATE_EVIDENCE|{percent}
SUSPICIOUS_PATTERN|{pattern_name}|{evidence}
REPORT_FIDELITY|clean|compromised
STRUCTURED_OUTPUT_END
```

## Final REPORT.md Skeleton

Fixed structure. See SKILL.md Step 7 for the authoritative template. Coordinator may phrase the 2-3 sentence Summary but must not introduce claims absent from judge verdicts. The fact-check table, weaknesses list, landscape section, and audit section are generated directly from structured judge output.

## Logs

**`logs/angle_spawn_log.jsonl`** — one line per critic/judge/fact-checker spawn:
```jsonl
{"ts":"<ISO>","event":"spawn","role":"viability_critic","spawn_time_iso":"<ISO>","input_files":["..."],"output_file":"..."}
{"ts":"<ISO>","event":"spawn_failed","role":"viability_critic","reason":"tool_limit"}
{"ts":"<ISO>","event":"completed","role":"viability_critic","structured_output_markers_present":true}
```

**`logs/judge_decisions.jsonl`** — one line per judge verdict or drop decision:
```jsonl
{"ts":"<ISO>","event":"credibility_verdict","claim_id":"001","verdict":"VERIFIED","confidence":"high"}
{"ts":"<ISO>","event":"severity_verdict","weakness_id":"viability-003","falsifiable":"yes","severity_final":"major"}
{"ts":"<ISO>","event":"weakness_dropped_unfalsifiable","weakness_id":"competition-002","reason":"no_counter_response"}
{"ts":"<ISO>","event":"rationalization_audit","report_fidelity":"clean"}
```
