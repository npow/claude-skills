# QA Dimensions by Artifact Type

## Type Detection Rules

| Signal | Inferred type |
|--------|--------------|
| SKILL.md frontmatter (YAML block with `name:`, `user_invocable:`, `argument:` fields) AND "## Workflow" or "## Phase" or "## Steps" or "## Golden Rules" | `skill` |
| `.md` with research findings, bibliography, "## Sources", "## Findings", "Executive Summary" + citation tables | `research` |
| `.md` with "## Architecture", "## API", "## Requirements", "## Spec", "## Interface", RFC-style numbering | `doc` |
| `.py`, `.ts`, `.go`, `.java`, `.rs`, etc. or content where code blocks exceed 50% | `code` |
| Ambiguous (mixed signals — e.g., has "## Workflow" but no SKILL.md frontmatter) | Prompt user: show which signals matched each type, ask user to confirm |

**Conflict resolution:** If signals from multiple rows match, apply this priority order: (1) explicit `--type` flag (always wins), (2) SKILL.md frontmatter present → `skill`, (3) code file extension → `code`, (4) research indicators → `research`, (5) doc indicators → `doc`. Show matched signals in the ambiguity prompt so the user can make an informed choice.

---

## Document / Spec (`doc`)

Applies to: technical specs, design docs, RFCs, API docs, architecture documents, requirements.

| Dimension | Description | Required Category |
|-----------|-------------|------------------|
| COMPLETENESS | Are all referenced components fully specified? Are all paths, flows, and states covered? | completeness |
| INTERNAL CONSISTENCY | Do sections contradict each other? Are terms used consistently throughout? | internal_consistency |
| AMBIGUITY | Are there underspecified requirements open to multiple valid interpretations? | completeness |
| FEASIBILITY | Can this actually be built as specified? Are assumptions about infrastructure, performance, or capabilities realistic? | feasibility |
| EDGE CASES | What happens at boundaries? Error paths, failure modes, empty/null/extreme inputs? | edge_cases |
| SECURITY/MISUSE | How could this spec lead to insecure implementations? What misuse vectors exist? | — |
| TESTABILITY | Can compliance with this spec be verified? Are acceptance criteria present for each requirement? | — |
| STAKEHOLDER ALIGNMENT | Does this serve its stated audience? Are requirements from all stakeholders captured? | — |

**Required categories for `doc`:** `completeness`, `internal_consistency`, `feasibility`, `edge_cases`

**Typical angles per dimension (2-4 each):**
- COMPLETENESS: "Are all referenced components fully specified or just labeled?", "What happens when [key flow] fails — is the error path specified?", "Are all state transitions defined?"
- INTERNAL CONSISTENCY: "Do terms in the glossary/Section 1 match usage in later sections?", "Does the requirements list conflict with the stated constraints?", "Do the examples match the rules they illustrate?"
- AMBIGUITY: "Which requirements have measurable acceptance criteria? Which don't?", "What does [vague term like 'fast', 'reasonable', 'appropriate'] mean concretely?", "Where could two implementers make different but spec-compliant choices that would be mutually incompatible?"
- FEASIBILITY: "What assumptions does this spec make about available infrastructure or capabilities?", "Are performance/scale requirements achievable with the described approach?", "Does the spec require capabilities that don't exist in the target environment?"
- EDGE CASES: "What happens when [key input] is empty, null, or maximal?", "What are the boundary conditions for [key parameter]?", "What happens when two requirements conflict in practice?"
- SECURITY/MISUSE: "How could a malicious implementer produce a spec-compliant but insecure system?", "Are trust boundaries and authentication requirements specified at every interface?"
- TESTABILITY: "Which requirements could not be verified by any automated test?", "Are success/failure criteria defined for each requirement?"

**Cross-dimensional angles for `doc`:**
- "completeness × feasibility" — "Are the complete requirements actually buildable, or do completeness demands create infeasible obligations?"
- "internal_consistency × edge_cases" — "Does the behavior at boundary conditions contradict the general rules stated elsewhere?"
- "ambiguity × testability" — "Which ambiguous requirements could lead to test suites that technically pass but violate intent?"

---

## Code / System (`code`)

Applies to: source code files, system architecture descriptions, API implementations.

| Dimension | Description | Required Category |
|-----------|-------------|------------------|
| CORRECTNESS | Does the logic do what it claims? Algorithmic errors? Edge cases in logic flow? | correctness |
| ERROR HANDLING | What happens with invalid input, service failures, data corruption, network timeouts? | error_handling |
| SECURITY | Injection vulnerabilities, auth gaps, data exposure, OWASP Top 10, trust boundary violations | security |
| PERFORMANCE | Hot paths, N+1 queries, memory leaks, unbounded growth, blocking I/O in async paths | — |
| TESTABILITY | Is code testable? Test coverage gaps? Are existing tests meaningful or tautological? | testability |
| MAINTAINABILITY | Readability, naming clarity, cyclomatic complexity, coupling, future change hazards | — |
| API DESIGN | Interface clarity, backwards compatibility, breaking change risk, error contracts | — |
| CONCURRENCY | Race conditions, deadlocks, thread safety, shared mutable state | — |

**Required categories for `code`:** `correctness`, `error_handling`, `security`, `testability`

**Typical angles:**
- CORRECTNESS: "What happens at the boundary values of [key function]?", "Does the algorithm handle empty, null, zero, and maximum-value inputs?", "Is the return value correct for all code paths including error paths?"
- ERROR HANDLING: "What happens if [external service] returns a 5xx? A malformed response? A timeout?", "Are errors surfaced to callers or silently swallowed?", "Is the error handling consistent — or do some call sites ignore errors that others handle?"
- SECURITY: "Where does user input flow into [query/command/template] without sanitization?", "What happens if an authenticated user guesses another user's resource ID?", "Are secrets handled correctly (not logged, not in error messages, not in URLs)?"
- PERFORMANCE: "What is the algorithmic complexity of [key operation] as N grows?", "Are there database queries inside loops?", "What happens to memory when [large input] is processed?"
- TESTABILITY: "Which functions have side effects that make them hard to test in isolation?", "Are there time.Now() / random calls that make tests non-deterministic?", "Can the tests actually fail, or do they always pass regardless of the code?"
- CONCURRENCY: "Is [shared data structure] accessed from multiple goroutines/threads without synchronization?", "Can two requests interleave in a way that produces inconsistent state?"

**Cross-dimensional angles for `code`:**
- "correctness × error_handling" — "Do the error paths maintain the correctness guarantees of the happy path?"
- "security × api_design" — "Does the API surface expose more capability than callers should have?"
- "testability × correctness" — "Are the most critical correctness properties the ones actually tested?"

---

## Research Report (`research`)

Applies to: research reports, literature reviews, deep-research outputs, findings summaries, analyses.

| Dimension | Description | Required Category |
|-----------|-------------|------------------|
| ACCURACY | Are claims supported by cited evidence? Do citations actually say what is attributed to them? | accuracy |
| CITATION VALIDITY | Are citations accessible, correctly tiered (primary/secondary/unverified), and attributed correctly? | citation_validity |
| PROVENANCE | For every claim of the form "X did/owns/authored Y," does re-querying Y's source system confirm X — with a query whose semantics match the claim? Trust the source of truth, not the report's chain of evidence. | provenance |
| INTERNAL CONSISTENCY | Within this artifact, do counts add up, do distant claims agree, and are proper nouns / dates / numbers reconciled across all sections? | internal_consistency |
| LOGICAL CONSISTENCY | Do conclusions follow from evidence? Are there logical leaps? Hidden assumptions? | logical_consistency |
| COVERAGE GAPS | What significant angles weren't covered? Counter-evidence missing? | coverage_gaps |
| METHODOLOGY | Is the research methodology sound? Selection bias? Sampling bias? Scope appropriate? | — |
| COUNTER-EVIDENCE | What contradicts the findings? Is it acknowledged fairly and with appropriate weight? | — |
| NUMERICAL CLAIMS | Are statistics exact and appropriate for the claim? Unit confusion? Percentage of what? | accuracy |
| REPRODUCIBILITY | Could the research be reproduced? Methods described sufficiently? Sources accessible? | — |

**Required categories for `research`:** `accuracy`, `citation_validity`, `provenance`, `internal_consistency`, `logical_consistency`, `coverage_gaps`

**When PROVENANCE applies:** any time the report makes a claim of the form "*subject* did/owns/authored/reported *artifact*." Typical cases: person/team activity reports, project audits, customer references, promo packets, authorship attributions. Pure topic-level literature reviews (where no subject owns the artifacts) can answer this dimension "not applicable — no subject-attribution claims" and that counts as coverage.

**Why it's a separate dimension from accuracy/citation_validity:** accuracy asks "does the source say what we claim it says"; citation validity asks "is the source accessible and tiered correctly." Neither catches "the source is real and accessible, but it isn't the subject's." A report can cite 100 valid, accessible, accurate artifacts and still get every attribution wrong. Attribution lives in a trust chain — subject → intermediate data → report — and any link in that chain can silently corrupt the mapping (parallel query swap, stale cache, content-heuristic mismatch, rename/account migration, co-author vs sole-author confusion, assignee vs reporter confusion, forwarded/quoted content, and classes not yet seen). The only reliable check is to re-query the source system for each attribution independently.

**Typical angles:**
- ACCURACY: "Do the cited papers actually support the specific claims made, or is the attribution stretched?", "Are numerical figures reported accurately from the source, or are they approximate?", "Does the executive summary accurately reflect what the findings section says?"
- CITATION VALIDITY: "Are primary vs. secondary sources correctly distinguished?", "Are any key claims supported only by unverified, paywalled, or blog-tier sources?", "Do citations point to the actual source or to a secondary summary of it?"
- PROVENANCE:
  - "Sample N attribution claims stratified across artifact type, recency, and project/topic cluster. For each, re-query the artifact's source system using a query scoped to the subject (not the artifact); verify the artifact appears in the result."
  - "If the re-query does not surface the artifact, the attribution is a defect. Severity scales with claim weight: attribution underpinning a headline project → critical; attribution in a long-tail ledger entry → major."
  - "Do not substitute weaker checks for re-query: content-pattern matching, naming conventions, project-prefix heuristics, 'the URL works,' or 'it's in the right era' are all unreliable. Re-query or flag."
  - "Include cross-cluster samples: when the report groups attributions by theme/project, sample at least one from each cluster (attribution bugs often swap entire clusters between subjects with similar signatures)."
  - "For human subjects, check both authorship modes the source system distinguishes (e.g., assignee vs reporter, author vs committer vs co-author, owner vs editor). A report that conflates these has a class of latent bugs."
  - "**Query-semantic precision.** Every claim has an implicit predicate that the re-query must match exactly. A wrong predicate produces a query that returns results, looks like it confirmed the claim, and silently misses the bug. Audit each claim type:"
    - "*\"X did/owns Y\"* → re-query must use the **strongest ownership predicate** the system offers (`assignee = X` for tickets; `author.login = X` for PRs/commits; `owner = X` for docs). The looser `assignee = X OR reporter = X` (and equivalents) does NOT confirm ownership — it confirms only **involvement**. If the strongest predicate fails, file as 'reported/scoped/co-touched, not owned' — this is a separate, lower-strength claim and must be downgraded in the report."
    - "*\"merged on date D\"* / *\"shipped\"* → query the source's **terminal-event timestamp** (`mergedAt`, `released_at`, `closed_at`-with-merged-state), NOT `createdAt` or Slack-message timestamp. PR sat-open lag is routinely months; a 'merged March' claim sourced from `createdAt` is wrong by however long the review cycle took."
    - "*\"in window [start, end]\"* → the predicate must match the activity claimed. 'Activity in window' means `resolved >= start` for completed work, `merged >= start` for shipped PRs, NOT `created >= start`. A ticket created in 2022 and resolved in 2025 is in-window for *completion* but not for *origination* — pick the right one for the claim."
    - "*\"currently open / in progress / status = S\"* → re-query at QA time. Snapshot data ages: a PR labeled 'open' in the report may have merged or been closed in the interim. For status claims that are load-bearing (e.g., 'this work is still in progress'), staleness is a defect; for incidental status (e.g., 'as of generation time, 5 PRs were open'), confirm the report's snapshot caveat is present."
    - "*\"PR X did Y\"* / *\"the PR titled Z\"* → re-query the canonical PR title and description, NOT a Slack summary or report paraphrase. If the report's description of the PR's scope diverges from the actual title/description, the claim is a paraphrase defect — file as wrong scope, not just wrong wording."
    - "Operational rule: when sampling for re-query, vary the predicate per sample. If the report has 100 attribution claims and only the loose predicate is used for all 100, the lax-predicate class of bugs slips through. Mix at least one of each: strict-ownership, terminal-date, window-resolved, real-time-status, and PR-canonical-title."
  - "**Cross-platform identity.** A subject may have different handles on different systems: GHE login, OSS GitHub login, Slack handle, email username, Pandora ID, ticket assignee field. Build the identity map once (e.g., `npow` on GHE = `nissanpow` on OSS = `npow@netflix.com` in Jira) and use it in every re-query. A report that hardcodes one handle in all queries will silently miss attributions on other platforms (e.g., OSS PRs authored under a personal handle won't return for the corp handle). When the source system can return zero results for a valid claim because of a handle mismatch, that's a re-query defect, not a missing-attribution defect — but the report's claim is still untrustworthy until the strict predicate succeeds under the right handle."
  - "**Hallucination check (proper-noun audit).** For each unusual proper noun in the report (project names, internal tool names, person names, codenames, product names, acronyms not defined elsewhere), verify it has at least one backing citation in the artifact. A proper noun that appears in prose but has zero supporting URL/ticket/Slack/doc citation is a likely hallucination — sample-verify by querying source systems for the noun and confirm it is real. This is especially important for: (a) names of teammates other than the subject (LLM may confabulate familiar-sounding names), (b) tool/product names that resemble real ones (e.g., 'OPIC' vs 'Opik'), (c) acronyms (LLM may expand to plausible but wrong full forms). File a defect for any unverified proper noun, even if the surrounding sentence reads plausibly."
  - "**Prose-claim consistency check.** Attribution is not only structured citation — it includes every prose description of what the subject does: role descriptions, project themes, focus-area summaries, TL;DR taglines, 'X is working on Y' sentences, section headings, and one-liners in tables. For each named work area or theme attributed to the subject in prose, verify it is supported by the subject's own evidence set in the same artifact: at least one cited ticket, PR, doc, or other concrete artifact on that theme. A theme that appears in the prose summary but has zero supporting evidence citations is a provenance defect — the prose is asserting something the evidence doesn't support. This catches 'stale prose, fresh data' (prose was written when the data was different) and 'fabricated theme' (prose generalized beyond what the evidence shows)."
  - "**Composite-artifact scope.** When the artifact is a collection (gist with TOC, doc with navigation index, portfolio of reports, dashboard with links), the derived files (README, TOC, index, summary, overview pane) are themselves attribution artifacts and inherit this dimension's obligations. Check consistency between the derived file and the primary files: every subject-description in the TOC/index must match the subject's actual report. If the report says 'Chaoying does not work on NRT' but the TOC tagline reads 'Chaoying: NRT engineer,' that is a defect — the composite artifact is self-inconsistent. Treat the TOC/index/README as a first-class QA target, not a trivial wrapper. In Phase 0a multi-file discovery, include derived/index files automatically."
- INTERNAL CONSISTENCY (research):
  - "**Independent count audit (tool-derived, not eyeball-derived).** For every claimed total (N tickets, N PRs, N docs, N artifacts), independently re-count the items via deterministic tool matching the source shape — `jq '.array | length'` for JSON, `wc -l` for JSONL / line-per-item, `awk '/^\\|/{c++} END{print c-2}'` for markdown tables, `grep -cE <anchor>` for structured prose with identifiable per-item tokens (ticket IDs, URLs, timestamps). See SKILL.md §Counting-substrate hierarchy for the full tool matrix. Do NOT count by reading. All model tiers (Haiku, Sonnet, Opus) confabulate plausible totals when asked to enumerate 30+ items inline; the confabulation is silent and matches the tool's shape well enough to pass casual review. Protocol: (1) fetch/paginate the source, (2) Write each page verbatim to /tmp/<file>-pN.<ext>, (3) sum across pages with the shape-appropriate tool, (4) compare to claimed total. Common defects: (a) total claimed in summary doesn't match the tables; (b) total in section header doesn't match the rows below; (c) post-edit drift after pass-1 fixes deleted items but didn't decrement the total; (d) silent exclusions (e.g., 'VUL tickets excluded' without a caveat); (e) the claimed total was itself agent-counted at report-gen time and is off-by-N. Recompute every total at QA time via tool. If the source is unstructured prose with no regular anchor pattern, either extract-then-count (SKILL.md fallback A) or file an `unverifiable_count` defect (fallback B) — never eyeball the blob."
  - "**Duplicate detection.** Scan tables and lists for items appearing twice — same ticket ID in two sections, same PR in two themes, same artifact double-counted. Duplicates inflate totals and overstate breadth."
  - "**Distant-claim contradiction sweep.** Cross-reference claims that appear in physically distant sections of the document: summary vs body, project section vs evidence index, TOC tagline vs section header. Common defect patterns: 'shipped to production' (summary) vs 'yanked within 5 days' (body); 'EM was X' (line 30) vs 'EM was Y' (line 80); 'lead' (project section) vs 'contributor' (evidence section); date in narrative vs date in cited PR. List every contradiction explicitly."
  - "**Dates-vs-cited-evidence reconciliation.** For every date claim in narrative text (e.g., 'shipped in May 2025', 'project ran from Jan to March'), check whether the cited evidence (PR, ticket, doc) supports that date. A common defect is narrative dates drifting from source dates — the report says 'May 2025' but the cited PR merged in 2026. Report the contradiction even if either date alone is internally defensible."
  - "**Acronym/name-form consistency.** Track every unusual proper noun across the document. Spelling drift ('Opik' vs 'OPIC'), capitalization drift ('GraphQL' vs 'graphql'), and abbreviation drift ('Model Hub' vs 'ModelHub') often signal copy-paste errors or LLM-generated variants. Pick the canonical form per the source-of-truth and flag every divergent form as a consistency defect."
- LOGICAL CONSISTENCY: "Are causal claims made where only correlation evidence exists?", "Does the conclusion in the summary follow from the findings in the body?", "Are there leaps from 'X was observed' to 'X always occurs'?"
- COVERAGE GAPS: "What major competing approaches or viewpoints weren't covered?", "Are the known limitations of the cited evidence acknowledged?", "What would a critic of the dominant framing cite?"
- COUNTER-EVIDENCE: "What findings contradict the report's main conclusions?", "Is contradictory evidence dismissed too quickly or given insufficient weight?"
- NUMERICAL CLAIMS: "Are percentages calculated relative to the right denominator?", "Are 'improvement' figures relative to a clearly stated baseline?"

**Cross-dimensional angles for `research`:**
- "accuracy × logical_consistency" — "Are the conclusions logically valid given the (accurately cited) evidence, or does the argument require stronger evidence than exists?"
- "coverage_gaps × counter_evidence" — "Is the absence of counter-evidence due to honest coverage or selective framing?"
- "provenance × citation_validity" — "A source can be accessible and correctly cited yet wrongly attributed; don't let 'the URL works' mask 'the subject is wrong.'"

---

## Skill / Prompt (`skill`)

Applies to: Claude skill files (SKILL.md), system prompts, agent specifications, tool instruction files.

| Dimension | Description | Required Category |
|-----------|-------------|------------------|
| BEHAVIORAL CORRECTNESS | Does the skill do what its description claims? Does it follow its own rules consistently? | behavioral_correctness |
| EDGE CASE HANDLING | What happens with unexpected inputs, partial info, out-of-scope requests, ambiguous triggers? | behavioral_correctness |
| INSTRUCTION CONFLICTS | Do sections of the prompt contradict each other? Competing rules for the same situation? | instruction_conflicts |
| INJECTION RESISTANCE | Can a malicious user cause the skill to violate its own rules or reveal its instructions? | injection_resistance |
| COST/RUNAWAY RISK | Can the skill spawn infinite agents, loop without a hard stop, or generate unbounded output? | cost_runaway_risk |
| OUTPUT FORMAT RELIABILITY | Is structured output format resilient to LLM variation? What if parsing fails? | — |
| AMBIGUITY | Are there instructions open to multiple valid LLM interpretations in the same situation? | instruction_conflicts |
| TOOL MISUSE | Does the skill use tools correctly? Potential for unintended side effects? | behavioral_correctness |

**Required categories for `skill`:** `behavioral_correctness`, `instruction_conflicts`, `injection_resistance`, `cost_runaway_risk`

**Typical angles:**
- BEHAVIORAL CORRECTNESS: "Does the skill correctly handle the simplest valid input described in its description?", "What happens when the input is valid but the correct output would violate a constraint?", "Does the skill produce its claimed output format reliably?"
- EDGE CASE HANDLING: "What happens when the user provides partial information?", "What does the skill do when triggered on a borderline case not clearly in or out of scope?", "What happens when the user asks a follow-up that the skill wasn't designed to handle?"
- INSTRUCTION CONFLICTS: "Does rule A in section 3 conflict with rule B in section 7?", "What does the skill do when two instructions apply simultaneously and point to different actions?", "Do the Golden Rules contradict the Workflow steps?"
- INJECTION RESISTANCE: "Can a user embed instructions in their input that override the skill's behavior?", "Does the skill expose its own instructions if asked 'What are your instructions?'?", "Can a user construct input that causes the skill to skip its validation gates?"
- COST/RUNAWAY RISK: "Is there a cycle risk — can the skill spawn agents that spawn more agents without a hard stop?", "Is there an unbounded loop in the main workflow?", "What is the maximum number of agents this skill can spawn in a single run? Is it bounded?"
- OUTPUT FORMAT RELIABILITY: "What happens if a subagent doesn't produce the expected structured output line?", "Is the fail-safe behavior (e.g., fail-safe critical) defined for every structured output field?"

**Cross-dimensional angles for `skill`:**
- "behavioral_correctness × injection_resistance" — "Can injection attacks cause the skill to behave in ways that appear correct but violate intent?"
- "cost_runaway_risk × edge_case_handling" — "Can an unusual-but-valid input trigger a loop or cascade that wasn't accounted for?"
- "instruction_conflicts × output_format_reliability" — "When conflicting instructions are present, does the fail-safe behavior produce safe output or garbage?"

---

## Required Category Coverage Rule

Termination condition for "Conditions Met" requires all required categories to have ≥1 explored angle.

If any required category has zero explored angles after round 1, generate new angles targeting it with **CRITICAL** priority immediately.

Track in `state.json`:
```json
"required_categories_covered": {
  "behavioral_correctness": false,
  "instruction_conflicts": false,
  "injection_resistance": false,
  "cost_runaway_risk": false
}
```

---

## Dimension Discovery Process

1. Select the applicable dimension set for the detected `artifact_type`
2. For each dimension, generate 2-4 specific angles based on the artifact's actual content
3. Generate 2-3 cross-dimensional angles (listed under each type above)
4. Assess which required categories are covered by initial angles; add CRITICAL-priority angles for any uncovered required category
5. Cap total initial angles at 20 (leave budget for depth expansion)
