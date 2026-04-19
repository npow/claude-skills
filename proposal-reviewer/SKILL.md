---
name: proposal-reviewer
description: Critically reviews project proposals, grant applications, and business plans. Use when the user asks to review, critique, evaluate, or assess a proposal, pitch, grant application, or business plan for viability, competition, or flaws. Fact-checks claims, maps competitive landscape, identifies structural problems, and provides honest recommendations.
---

# Proposal Reviewer Skill

Adversarially review a proposal by extracting every factual claim, attacking the proposal across four orthogonal critique dimensions in parallel (viability, competition, structural flaws, evidence), and delegating every severity / credibility / falsifiability verdict to independent judge agents. The coordinator orchestrates and assembles the final report; it never classifies, weighs, or approves on its own.

## Execution Model

Non-negotiable contracts (same spine as `deep-design`, `deep-qa`, `/team`):

- **All data passed to agents via files, never inline.** Proposal text, claim lists, angle definitions, fact sheets, judge inputs — all written to `proposal-review-{run_id}/` before the agent call. Inline data is silently truncated.
- **State written before agent spawn.** `spawn_time_iso` is written to `state.json` before the Agent/Task call. Spawn failure records `spawn_failed`. Resume retries spawn; it does not wait.
- **Structured output is the contract.** Critics, judges, fact-checkers produce machine-parseable lines inside `STRUCTURED_OUTPUT_START` / `STRUCTURED_OUTPUT_END` markers. Coordinator reads ONLY structured fields. Unparseable → fail-safe (treated as the worst legal verdict for that check).
- **No coordinator self-review of anything load-bearing.** Claim credibility, flaw severity, market-window classification, viability verdict, falsifiability of weaknesses — all written to disk by independent agents. The coordinator compiles; it does not evaluate.
- **Iron-law gate before the final verdict.** A final viability verdict cannot be rendered until every claim has a judge-written credibility verdict AND every weakness has a judge-written severity + falsifiability verdict on disk. This is checked by reading `state.json` plus `ls` of listed paths.
- **Honest termination labels.** Exactly one of: `high_conviction_review` | `mixed_evidence` | `insufficient_evidence_to_review` | `declined_unfalsifiable`. Never "looks solid", "some concerns remain", "promising overall".

**Shared contracts:** this skill inherits the four execution-model contracts (files-not-inline, state-before-agent-spawn, structured-output, independence-invariant) from [`_shared/execution-model-contracts.md`](../_shared/execution-model-contracts.md). The items listed above are the skill-specific elaborations; the shared file is authoritative for the base contracts.

**Subagent watchdog:** every `run_in_background=true` spawn (fact-check agents, credibility judges, competitor-research agents) MUST be armed with a staleness monitor per [`_shared/subagent-watchdog.md`](../_shared/subagent-watchdog.md). Use Flavor A with thresholds `STALE=10 min`, `HUNG=30 min` for research/fact-check agents (web fetches legitimately take time); `STALE=3 min`, `HUNG=10 min` for Haiku judges. `TaskOutput` status is not evidence of progress. Contract inheritance: `timed_out_heartbeat` joins this skill's per-claim / per-competitor termination vocabulary; `stalled_watchdog` / `hung_killed` join per-lane state. A watchdog-killed fact-check or competitor-research lane leaves its claims `insufficient_evidence_to_review` at the lane level — never silently marked `VERIFIED`.

## Adversarial judging (full adoption)

See [`_shared/adversarial-judging.md`](../_shared/adversarial-judging.md) for the pattern definition. This skill implements all four mechanisms:

| Mechanism | Implementation location |
|---|---|
| Blind severity protocol (two-pass) | Step 5 Judge A pass 1 (blind) + pass 2 (informed); Judge B pass 1 + pass 2. |
| Mandatory author counter-response | Step 3 critic prompt template requires `author-counter-response`; Judge B drops filings without one via `FALSIFIABLE|no`. |
| Rationalization auditor | Step 6 spawns an independent `rationalization-auditor` with the full `judges/` directory as input; `REPORT_FIDELITY|compromised` halts assembly. |
| Falsifiability drop (not downgrade) | Step 5 Judge B: weaknesses with `FALSIFIABLE|no` are dropped from the final report and logged in `logs/judge_decisions.jsonl`. |

When this skill's contract or the shared reference diverges, the shared reference is authoritative for the pattern definition; this skill's domain-specific detail (claim extraction, fact-check research, landscape window judge) remains local.

## Philosophy

A proposal reviewer is only as honest as its weakest gate. The rationalization patterns are well-known: "the founders are impressive, so this must work"; "my prior was high, I should approve"; "rejecting this would embarrass them". This skill counters rationalization structurally — no single agent (coordinator included) gets to both generate a claim and approve it. Every severity call is made by someone with no stake in the outcome. Every weakness must ship with a falsifiable scenario and a concrete counter-response the proposal author could make.

The default posture is adversarial but truthful. A reviewer that approves everything is broken. A reviewer that rejects everything is also broken. Calibration is measured across the critic and judge corpus — a judge with 100% acceptance or 100% rejection is evidence of failure.

## Workflow

### Step 0: Input Validation Gate

Before any work begins, validate the proposal:

**Rubric — reject if any apply:**
- Proposal is < 200 words and not a structured artifact (grant SF-424, pitch deck with scaffold, etc.) → request more detail
- Proposal is a one-line idea ("build X for Y") → suggest `/spec` or `deep-design` instead; this skill reviews *artifacts*, not ideas
- Request is for rubber-stamp / encouragement rather than critique → decline politely with a note that the skill's value is adversarial review
- Proposal requests harm (weapon, exploit, deceptive monetization) → decline

**Parse the invocation:**
1. Extract the proposal text verbatim. Store as `proposal_text`; compute `proposal_text_sha256`. Locked — never paraphrased into agent prompts.
2. Extract a 1-2 sentence **core claim** — the specific outcome this proposal promises that similar proposals do not. This is the drift-reference used in Step 6.
3. Note whether the user requested a rewrite; default is NO rewrite. Rewriting is opt-in (Step 8).

**Print:** `Starting proposal review on: {one-line summary} [run: {run_id}]`

### Step 1: Initialize

- Generate run ID: `$(date +%Y%m%d-%H%M%S)` — e.g., `20260416-153022`
- Create directory structure:
  - `proposal-review-{run_id}/state.json` — run state (see STATE.md)
  - `proposal-review-{run_id}/proposal.md` — verbatim copy of the input
  - `proposal-review-{run_id}/claims/` — one file per extracted claim + dedup registry
  - `proposal-review-{run_id}/critiques/` — one file per critique angle (parallel critics)
  - `proposal-review-{run_id}/fact-checks/` — one file per claim verification agent
  - `proposal-review-{run_id}/judges/` — per-claim credibility verdicts + per-weakness severity/falsifiability verdicts
  - `proposal-review-{run_id}/landscape/` — per-competitor research outputs
  - `proposal-review-{run_id}/logs/` — `angle_spawn_log.jsonl`, `judge_decisions.jsonl`
  - `proposal-review-{run_id}/REPORT.md` — final output (written at Step 7)
- Write initial `state.json` with `run_id`, `proposal_text`, `proposal_text_sha256`, `core_claim`, `skill: "proposal-reviewer"`, `generation: 0`, `termination: null`
- Check for `deep-qa` availability; record in `state.integrations`. Missing → fact-check stage runs degraded inline critics (see INTEGRATION notes in this file).

### Step 2: Claim Extraction

**Agent:** `claim-extractor` (opus, single pass, independent).

**Input files:**
- `proposal-review-{run_id}/proposal.md`
- Locked `core_claim` text (from state.json)

**Work:**
1. Agent reads the full proposal and extracts every verifiable factual claim — statistics, funding amounts, CVEs, star counts, citations, standards references, negative existence claims ("no one has built X").
2. Agent writes one file per claim to `claims/claim-{NNN}.md` using the schema in FORMAT.md.
3. Agent writes `claims/REGISTRY.md` listing all claim IDs + one-line descriptions, with `STRUCTURED_OUTPUT_START/END` markers.

**Coordinator does NOT filter or re-classify claims.** If the extractor misses a claim, that is a bug in the extractor; do not paper over it by adding claims from the coordinator's reading.

**Exit gate:** `claims/REGISTRY.md` exists with structured markers and at least one claim (unless the proposal is pure narrative with zero verifiable statements — note explicitly in state.json).

See [FACT-CHECK.md](FACT-CHECK.md) for claim taxonomy and extraction rubric.

### Step 3: Parallel Critique Round (Four Orthogonal Dimensions)

Fire four independent critic agents concurrently, each owning one dimension. This is the deep-design parallel-critic pattern applied to proposal review.

**The four dimensions (each gets at least one critic; more if the proposal is complex):**

| Dimension | Critic focus | Reference |
|---|---|---|
| **viability** | Business model sustainability, go-to-market, revenue path, team capacity, scope vs time | STRUCTURAL.md |
| **competition** | Direct / adjacent / platform / open-source competitors; the "do nothing" alternative; market timing | LANDSCAPE.md |
| **structural-flaws** | Technical architecture, failure modes, cost model, dependencies, adversarial evasion | STRUCTURAL.md |
| **evidence** | Claim quality, citation integrity, "research shows" without source, fabricated specifics, embellishment patterns | FACT-CHECK.md |

**Spawning contract (per critic):**
- Write angle file to `critiques/{dimension}-angle.md` with the locked `core_claim` + dimension-specific mandate.
- Write spawn record to `state.json` (see STATE.md: `agent_spawns[]`) with `spawn_time_iso` BEFORE the Agent call.
- Spawn via `Task(subagent_type: general-purpose, model: opus)` with file paths — not inline content.
- Output file: `critiques/{dimension}-critique.md`.

**Critic prompt template (each dimension gets the same backbone with dimension-specific mandate injected):**

See `CRITIC_PROMPT_TEMPLATE` at the bottom of this file.

**Critic output contract (enforced by FORMAT.md):**
- File MUST have `STRUCTURED_OUTPUT_START/END` markers; files without are treated as failed.
- Each filed weakness includes: title, dimension, concrete failure scenario, root cause, one-line suggested fix direction, and a **counter-response** — what the proposal author could plausibly say to defend the point. This is the falsifiability contract (Step 5 judge enforces it).
- Each critic files **every load-bearing weakness** — no cap on real findings. Quality and signal density matter more than count. Critics MUST exclude nitpicks (cosmetic issues, stylistic preferences, prose polish, taste-based wording quibbles); a critique padded with cosmetics erodes trust in every weakness it carries.
- Each critic may suggest at most **1 additional angle** for a future round (rarely triggered; this is a single-round skill by default).

**Quorum:** Round is complete if ≥ 3 of 4 critics return parseable output within timeout (180s base). If < 3 parseable: label the run `insufficient_evidence_to_review` and stop; do not synthesize from incomplete critique data. Circuit-break-like behavior; matches deep-design's quorum rule.

### Step 4: Parallel Fact-Check Round

Fire one fact-check agent per claim (or one agent per claim cluster if >20 claims, grouped by category per FACT-CHECK.md).

**Agent spawning:**
- If `deep-qa` is available and claims can be fed as a bundle: invoke `deep-qa --type doc` on the claim registry against the proposal. Output tagged as Stage A spec-compliance-style registry.
- Otherwise: spawn one `fact-check-research` agent per claim (or per 3-5 claims grouped by category) with the claim file path + the proposal path.

**Research execution per claim (follows FACT-CHECK.md):**
- For named vulnerabilities/attacks: CVE databases, advisories, vendor confirmations.
- For research citations: arXiv, Google Scholar, conference proceedings — verify the paper says what the proposal claims.
- For competitor/market claims: Crunchbase, TechCrunch, GitHub, product pages.
- For standards/framework claims: primary OWASP/MITRE/NIST documents.
- For "no one has built X": 5+ distinct searches before VERIFIED classification.

**Output per claim:**
Agent writes `fact-checks/claim-{NNN}-evidence.md` with:
- What was searched (terms + sources queried)
- What was found (URL + one-line quote or paraphrase)
- Proposed verdict: one of `VERIFIED / PARTIALLY_TRUE / UNVERIFIABLE / FALSE`
- Confidence: `high / medium / low`

**Important:** The fact-check agent PROPOSES a verdict. It does NOT author the authoritative verdict. That is the credibility judge's job in Step 5. The fact-check agent's role is evidence gathering.

### Step 5: Independent Judges (Per Claim, Per Weakness)

The independence invariant from `deep-design` and `/team` is the non-negotiable core of this skill. Every evaluation below is performed by an agent that did NOT produce the thing being evaluated.

**Judge A — Credibility judge (one per claim):**

For each claim in `claims/REGISTRY.md`:
1. Coordinator writes `judges/inputs/claim-{NNN}.md` containing: claim text, fact-check evidence file path, but NOT the fact-checker's proposed verdict (stripped before handoff — blind verdict protocol).
2. Spawn an independent judge (opus, fresh context) with the inputs.
3. Judge writes `judges/credibility/claim-{NNN}-verdict.md` with structured output per FORMAT.md:
   - `CLAIM_ID|{NNN}`
   - `EVIDENCE_FOUND|yes|partial|no`
   - `VERDICT|VERIFIED|PARTIALLY_TRUE|UNVERIFIABLE|FALSE`
   - `CONFIDENCE|high|medium|low`
   - `RATIONALE|{one-line}`
4. Pass 2 (addendum): coordinator supplies the fact-checker's proposed verdict; judge may confirm, upgrade, or downgrade with rationale. Final verdict is the pass-2 conclusion.

**Judge B — Weakness severity + falsifiability judge (one per weakness):**

For each weakness filed in any `critiques/{dimension}-critique.md`:
1. Coordinator writes `judges/inputs/weakness-{dim}-{NNN}.md` containing: the weakness title + scenario + root cause + counter-response, but NOT the critic's severity claim (stripped — blind severity protocol).
2. Spawn independent judge (opus, fresh context).
3. Judge writes `judges/severity/weakness-{dim}-{NNN}-verdict.md` with structured output:
   - `WEAKNESS_ID|{dim}-{NNN}`
   - `FALSIFIABLE|yes|no` — does the weakness ship with a concrete scenario AND a plausible author counter-response that would settle the dispute?
   - `SEVERITY|fatal|major|minor|rejected` — rejected = unfalsifiable or already mitigated by the proposal's existing structure.
   - `FIXABILITY|fixable|inherent_risk|fatal` — per STRUCTURAL.md taxonomy.
   - `CONFIDENCE|high|medium|low`
   - `RATIONALE|{one-line}`
4. Pass 2: coordinator supplies the critic's original severity claim; judge may confirm/upgrade/downgrade with rationale.

**Falsifiability gate:** Any weakness with `FALSIFIABLE|no` is **dropped from the final report** — it does not count as a finding. The coordinator logs the drop to `logs/judge_decisions.jsonl`. This is the structural counterpart to golden-rule-3 in `deep-design`: unfalsifiable flaws are noise.

**Judge adversarial mandate (injected into every judge prompt):** "You succeed by rejecting or downgrading. You fail by rubber-stamping. A 100% acceptance rate or 100% rejection rate is evidence of failure. If three weaknesses are filed and you accept all three at claimed severity, you are broken. Calibrate against the structure of the evidence, not the desire to seem diligent or generous."

**Judge C — Landscape window + platform risk judge (one per proposal):**

Reads `landscape/` outputs (competitor research from Step 3's competition critic + any deep-research follow-ups) and issues:
- `MARKET_WINDOW|open|closing|closed`
- `PLATFORM_RISK|low|medium|high`
- `MOST_LIKELY_PLATFORM_THREAT|{vendor}|{timeline}`
- `RATIONALE|{one-line}`

Written to `judges/landscape-verdict.md`.

### Step 6: Anti-Rationalization Self-Check (Before Assembly)

Before writing the final report, the coordinator spawns one more independent agent — the **rationalization-auditor** — with the complete judges/ directory as input. The agent's job:

1. Read every verdict file.
2. Compute: (a) judge acceptance rate per dimension, (b) distribution of severities, (c) whether all weaknesses with `FALSIFIABLE|yes` were carried into the report.
3. Check against the anti-rationalization counter-table in GOLDEN-RULES.md. Has the coordinator made any of the listed excuses in its draft assembly?
4. Write `judges/rationalization-audit.md` with:
   - `ACCEPTANCE_RATE_VIABILITY|{rate}` (similar per dimension)
   - `SUSPICIOUS_PATTERNS|{list or "none"}`
   - `REPORT_FIDELITY|clean|compromised` — compromised means the coordinator's draft summary deviates from the judge verdicts in the direction of rationalization.
5. If `REPORT_FIDELITY|compromised`: coordinator halts; re-assembles the report strictly from judge verdicts, then re-runs the auditor. Two failures → `insufficient_evidence_to_review` label.

### Step 7: Assemble Final Report

**Coordinator reads — it does not evaluate:**
- `claims/REGISTRY.md`
- Every `judges/credibility/*.md`
- Every `judges/severity/*.md`
- `judges/landscape-verdict.md`
- `judges/rationalization-audit.md`

**REPORT.md structure (fixed — no freeform prose in the sections that carry verdicts):**

```markdown
# Proposal Review Report

**Run ID:** {run_id}
**Date:** {ISO}
**Termination label:** {one of four — see below}

## Summary
{2-3 sentence synthesis — coordinator may phrase, but must not add claims not present in judge verdicts}

## Fact-Check Table
| Claim | Verdict | Confidence | Evidence |
|---|---|---|---|
| {claim text} | VERIFIED/PARTIALLY_TRUE/UNVERIFIABLE/FALSE | high/med/low | {source} |

## Weaknesses (Falsifiable Only)
### {weakness title} — {dimension}
- **Severity (judge):** fatal / major / minor
- **Fixability (judge):** fixable / inherent_risk / fatal
- **Scenario (critic):** {concrete scenario}
- **Author counter-response (critic):** {what the proposal author could plausibly say}
- **Root cause (critic):** {one line}
- **Suggested fix direction (critic):** {one line}

## Market Landscape + Platform Risk
- **Window (judge):** open / closing / closed
- **Platform risk (judge):** low / medium / high
- **Most likely threat (judge):** {vendor + timeline}

## Anti-Rationalization Audit
- **Judge acceptance rates:** {per dimension}
- **Suspicious patterns detected:** {list or "none"}
- **Report fidelity:** clean / compromised

## Recommendations (Not a Rewrite)
- {one bullet per fixable weakness: what change would shift the verdict}
- {inherent risks listed explicitly as non-fixable}

## Termination

{one of the four labels, with condition justification}
```

**Termination labels (honest, exhaustive):**

| Label | Condition |
|---|---|
| `high_conviction_review` | ≥ 80% of claims VERIFIED or PARTIALLY_TRUE; zero FALSE; zero unresolved `fatal` weaknesses; judge acceptance rates 20%-80% (neither rubber-stamp nor uniform rejection); rationalization audit `clean`. |
| `mixed_evidence` | 50%-80% claims verified; OR any FALSE claim present; OR any `fatal` + `inherent_risk` weakness surfaced; rationalization audit clean. |
| `insufficient_evidence_to_review` | Critic quorum failed (< 3/4 dimensions returned parseable output) OR > 40% of claims are UNVERIFIABLE OR rationalization audit `compromised` twice. |
| `declined_unfalsifiable` | Every critic's weaknesses were rejected by Judge B as unfalsifiable. The proposal may be good or bad, but the review cannot discriminate. Honest output, not a polite approval. |

**Never use:** "looks solid", "some concerns", "promising overall", "good in parts", or any label outside the four above.

### Step 8: Rewrite (Opt-In Only)

Only rewrite when the user explicitly asks. See [REWRITE.md](REWRITE.md) for the rewrite protocol. Preserve the original default behavior — the skill's baseline output is the REPORT.md above.

## Golden Rules

See [GOLDEN-RULES.md](GOLDEN-RULES.md) for the full 8 cross-cutting rules + anti-rationalization counter-table. One-line summary:

1. **Independence invariant.** Coordinator orchestrates; independent judges evaluate.
2. **Iron-law gate.** No final verdict without per-claim and per-weakness judge verdicts on disk.
3. **Parallel critic per dimension.** Viability / competition / structural-flaws / evidence — orthogonal, concurrent, independent.
4. **Honest termination labels.** Four labels, no euphemisms.
5. **State written before agent spawn.** `spawn_failed` ≠ "silent spawn."
6. **Structured output is the contract.** Unparseable = fail-safe worst verdict.
7. **All data passed via files.** Inline is truncated.
8. **Falsifiability is mandatory.** Every weakness ships with a scenario AND a plausible author counter-response. Unfalsifiable weaknesses are dropped, not softened.

## Self-Review Checklist

Before writing `REPORT.md`:

- [ ] `state.json` is valid JSON; `generation` monotonic; `termination` is one of the four labels.
- [ ] `proposal_text_sha256` matches stored `proposal_text`.
- [ ] `claims/REGISTRY.md` exists with structured markers.
- [ ] Every claim in the registry has a `judges/credibility/claim-{NNN}-verdict.md` with structured markers.
- [ ] All four critique dimensions returned parseable output OR the run is labeled `insufficient_evidence_to_review`.
- [ ] Every filed weakness has a `judges/severity/weakness-{dim}-{NNN}-verdict.md`.
- [ ] Every weakness with `FALSIFIABLE|no` is excluded from REPORT.md and logged in `judge_decisions.jsonl`.
- [ ] `judges/landscape-verdict.md` exists.
- [ ] `judges/rationalization-audit.md` exists with `REPORT_FIDELITY|clean` OR the report has been re-assembled.
- [ ] REPORT.md structure matches the schema above exactly; no freeform paragraphs replace structured sections.
- [ ] Termination label is one of the four; no euphemisms.
- [ ] No claim in REPORT.md is unsourced — every assertion traces to a judge verdict or a fact-check evidence file.
- [ ] Competitors NOT mentioned in the proposal are explicitly listed as blind spots.
- [ ] Fixable flaws are separated from inherent risks.

## Reference Files

| File | Contents |
|------|----------|
| [FACT-CHECK.md](FACT-CHECK.md) | Claim taxonomy, extraction rubric, verification methods per claim category |
| [LANDSCAPE.md](LANDSCAPE.md) | Competitor research strategy, window assessment, platform-risk analysis |
| [STRUCTURAL.md](STRUCTURAL.md) | Business model, architecture, cost, scope, sustainability analysis + flaw classification |
| [REWRITE.md](REWRITE.md) | Opt-in rewrite protocol: preserve what works, fix what's broken, maintain author's voice |
| [FORMAT.md](FORMAT.md) | Structured output schemas for critics, judges, fact-checkers (with STRUCTURED_OUTPUT markers) |
| [STATE.md](STATE.md) | state.json schema + resume protocol |
| [GOLDEN-RULES.md](GOLDEN-RULES.md) | 8 cross-cutting rules + anti-rationalization counter-table |

## Critic Prompt Template

When spawning each dimension critic, use this backbone; the `{dimension_specific_mandate}` is injected from the relevant reference file (FACT-CHECK.md for evidence, LANDSCAPE.md for competition, STRUCTURAL.md for viability and structural-flaws).

```
You are an adversarial proposal critic for the {dimension} dimension. Your job is to
BREAK this proposal — find weaknesses that would cause it to fail in practice. Do NOT
be polite. Do NOT say "overall this looks promising." Find REAL problems.

**Your dimension:** {viability | competition | structural-flaws | evidence}
**Your specific mandate:** {dimension_specific_mandate}
**Proposal core claim (locked):** {core_claim}
**Proposal file:** {proposal_path}

**Instructions:**
1. Read the proposal end-to-end through the lens of your dimension.
2. Identify every genuine load-bearing weakness — **no cap** on real findings. Quality and signal density matter more than count. Exclude nitpicks: cosmetic issues, stylistic preferences, prose polish, taste-based wording quibbles. Every filed weakness must describe a concrete failure mode in practice, not a taste preference.
3. For EACH weakness, produce:
   - A clear title
   - Severity claim (fatal/major/minor) — this will be stripped before the judge sees it
   - A concrete failure scenario (who, what, when, why it fails)
   - Root cause (one line)
   - Suggested fix direction (one line)
   - An **author counter-response** — a plausible defense the proposal author could
     mount against this weakness. This is REQUIRED. If you cannot write a plausible
     counter-response, the weakness is not falsifiable; do NOT file it as a weakness.
     File it as a minor observation instead.
4. Write findings to: {critique_path}
5. Use the FORMAT specified in FORMAT.md; include STRUCTURED_OUTPUT_START/END markers.

**FALSIFIABILITY REQUIREMENT (non-negotiable):** Every weakness must include a
concrete scenario AND a plausible author counter-response. Claims like "the market
might be too small" with no scenario are not weaknesses — they are concerns. Unfalsifiable
concerns are filed as minor observations, not weaknesses. Judge B will drop any weakness
that fails falsifiability; do not waste effort on unfalsifiable filings.

**ADVERSARIAL MANDATE:** You succeed by finding real problems. You fail by rubber-stamping.
100% approval on any dimension is evidence you are broken.

**COMMON CRITIC FAILURE MODES TO AVOID:**
- "The founders are impressive, so this must work" — irrelevant to your dimension.
- "My prior was high, so I should approve" — priors are not evidence.
- "Rejecting this strongly would be rude" — rudeness is not your concern; accuracy is.
- "This feels right" — feelings are not evidence.
- "Other competitors have failed at this" — so what? Is THIS proposal better or worse?
- "The writing is good" — prose quality is not a viability signal.
- "The wording on page 3 is awkward" — nitpick. Prose polish is not a weakness. Skip cosmetic concerns; only file load-bearing problems.
- "I should pad the report to look thorough" — inflated reports erode trust. File only load-bearing weaknesses; if the proposal has only one true weakness in your dimension, file one. No cap, but no padding.

Focus on: concrete scenarios, evidence-backed claims, named competitors, cited costs,
specific timeline calculations, measurable market signals.
```

---

*Supplementary files: FACT-CHECK.md, LANDSCAPE.md, STRUCTURAL.md, REWRITE.md (preserved domain knowledge); FORMAT.md, STATE.md, GOLDEN-RULES.md (parallel-critic + independent-judge machinery).*
