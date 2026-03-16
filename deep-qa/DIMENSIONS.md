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
| LOGICAL CONSISTENCY | Do conclusions follow from evidence? Are there logical leaps? Hidden assumptions? | logical_consistency |
| COVERAGE GAPS | What significant angles weren't covered? Counter-evidence missing? | coverage_gaps |
| METHODOLOGY | Is the research methodology sound? Selection bias? Sampling bias? Scope appropriate? | — |
| COUNTER-EVIDENCE | What contradicts the findings? Is it acknowledged fairly and with appropriate weight? | — |
| NUMERICAL CLAIMS | Are statistics exact and appropriate for the claim? Unit confusion? Percentage of what? | accuracy |
| REPRODUCIBILITY | Could the research be reproduced? Methods described sufficiently? Sources accessible? | — |

**Required categories for `research`:** `accuracy`, `citation_validity`, `logical_consistency`, `coverage_gaps`

**Typical angles:**
- ACCURACY: "Do the cited papers actually support the specific claims made, or is the attribution stretched?", "Are numerical figures reported accurately from the source, or are they approximate?", "Does the executive summary accurately reflect what the findings section says?"
- CITATION VALIDITY: "Are primary vs. secondary sources correctly distinguished?", "Are any key claims supported only by unverified, paywalled, or blog-tier sources?", "Do citations point to the actual source or to a secondary summary of it?"
- LOGICAL CONSISTENCY: "Are causal claims made where only correlation evidence exists?", "Does the conclusion in the summary follow from the findings in the body?", "Are there leaps from 'X was observed' to 'X always occurs'?"
- COVERAGE GAPS: "What major competing approaches or viewpoints weren't covered?", "Are the known limitations of the cited evidence acknowledged?", "What would a critic of the dominant framing cite?"
- COUNTER-EVIDENCE: "What findings contradict the report's main conclusions?", "Is contradictory evidence dismissed too quickly or given insufficient weight?"
- NUMERICAL CLAIMS: "Are percentages calculated relative to the right denominator?", "Are 'improvement' figures relative to a clearly stated baseline?"

**Cross-dimensional angles for `research`:**
- "accuracy × logical_consistency" — "Are the conclusions logically valid given the (accurately cited) evidence, or does the argument require stronger evidence than exists?"
- "coverage_gaps × counter_evidence" — "Is the absence of counter-evidence due to honest coverage or selective framing?"

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
