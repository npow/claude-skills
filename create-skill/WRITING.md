# Writing Skill Content

How to write effective metadata, SKILL.md, reference files, golden rules, and checklists.

This document covers the mechanical "how do I write good content" layer. Companions:

- [FORMAT.md](FORMAT.md) defines the MANDATORY sections every produced skill must contain — counter-table, termination labels, iron-law gate language.
- [GOLDEN-RULES.md](GOLDEN-RULES.md) is the consolidated rule set that every produced skill must absorb.
- [PRESSURE-TESTING.md](PRESSURE-TESTING.md) is the RED-GREEN-REFACTOR protocol — authored pressure scenarios, RED baseline, GREEN verification, REFACTOR loophole closing.
- [INTEGRATION.md](INTEGRATION.md) documents composition with `deep-qa` for skill review and `deep-design` for design review, including degraded-mode fallbacks.

**Iron law:** No skill ships without a `pressure-tests/baseline.md` file on disk recording what a subagent does WITHOUT the skill loaded. Write SKILL.md before baseline exists → delete SKILL.md → go to [PRESSURE-TESTING.md](PRESSURE-TESTING.md) Step 2.

## Metadata: name and description

### Name

- Lowercase letters, numbers, hyphens only (no parentheses, special chars)
- Max 64 characters
- **Use active voice, verb-first.** Name by what you DO or the core insight, not the category.
  - ✅ `creating-skills`, `condition-based-waiting`, `flatten-with-flags`, `root-cause-tracing`
  - ❌ `skill-creation`, `async-test-helpers`, `data-structure-refactoring`, `debugging-techniques`
- **Gerunds (-ing) work well for processes** (the ongoing action you're taking): `creating-skills`, `testing-skills`, `debugging-with-logs`.
- **Verb-noun works for one-shot generators**: `create-skill`, `develop-board-game`, `review-pr`.
- Avoid generic names: `helper`, `utils`, `tool`, `reference`, `details`.

### Description

The description is a search index entry. Claude uses it to decide whether to load the skill. Write it in third person.

**Formula**: `Use when [trigger conditions, symptoms, and phrases].`

⚠️ **The description is ONLY triggers, NEVER a workflow summary.** When a description summarizes what the skill does, Claude follows the description as a shortcut and skips the skill body. Empirical example: a description that said "runs two-stage review" caused Claude to do ONE review, because the skill body explaining the two stages was never read. Describe the *when*, not the *how*.

```yaml
# ✅ GOOD: just triggers, no workflow summary
description: Use when creating, editing, scaffolding, or reviewing a Claude Code skill, slash command, or agent capability.

# ✅ GOOD: triggers including symptoms and error messages
description: Use when tests have race conditions, timing dependencies, or pass/fail inconsistently

# ❌ BAD: summarizes the workflow — Claude will follow this shortcut instead of reading the skill
description: Use when creating skills — runs RED-GREEN-REFACTOR, writes companion files, closes loopholes.

# ❌ BAD: states what the skill DOES rather than WHEN to use it
description: Creates well-structured skills by applying harness engineering best practices.

# ❌ BAD: vague, no triggers
description: Helps with creating things.

# ❌ BAD: first person
description: I can help you build skills.
```

**Keyword coverage**: Claude does substring matching on descriptions. If "edit" is missing, a user saying "edit my skill" won't route here. Include every word a user might type.

Cover these keyword classes:
- **Synonyms**: create/build/scaffold/generate/write; edit/modify/update/revise; review/audit/check/verify
- **Error messages the user might paste**: "Hook timed out", "ENOTEMPTY", "race condition"
- **Symptoms**: "flaky", "hanging", "intermittent", "pollution"
- **Tools and file types**: actual CLI names, library names, extensions (`.ipynb`, `.pptx`)
- **Alternative terminology**: "slash command" vs "skill", "subagent" vs "agent capability"

**Length**: Under 1024 characters total (frontmatter limit). Aim for 1-3 sentences of pure triggers — a workflow summary inflates length without helping routing.

## Token efficiency (critical for hot skills)

Every skill's `name` and `description` load into the system prompt for every conversation. A bloated description burns context across every turn, not just when the skill triggers.

**Word-count targets:**

| Skill type | Target |
|---|---|
| Getting-started / always-loaded workflows | <150 words total |
| Frequently-loaded (5+ hits per session) | <200 words total |
| Standard workflow skills | <500 words in SKILL.md body |
| Long-tail skills (loaded rarely) | <1000 words in SKILL.md body; unlimited in companion files |

**Token-efficiency techniques:**

- **Move detail to tool help**: `Run --help for flags` beats listing every flag.
- **Cross-reference instead of repeat**: `Use [other-skill] for workflow` beats re-stating it.
- **Compress examples**: one minimal example > three verbose ones.
- **Eliminate redundancy**: don't repeat what's in cross-referenced skills, don't explain what's obvious from command syntax.
- **Push heavy content to companion files**: companion files load only when Claude reads them. Use this.

**Verification:**

```bash
wc -w SKILL.md   # body word count
```

If SKILL.md exceeds the target, either delete content or move it to a companion file. Never pad for "thoroughness".

## SKILL.md body: the table of contents

Every produced SKILL.md has the mandatory sections defined in [FORMAT.md](FORMAT.md):

1. YAML frontmatter
2. Title + one-line purpose
3. Execution Model (workflow skills only)
4. Workflow (numbered, one line each)
5. Honest termination labels (workflow skills only)
6. Self-review checklist
7. Golden rules
8. Anti-rationalization counter-table
9. Reference/companion file index

This document covers the mechanics of writing each section well. [FORMAT.md](FORMAT.md) is the authoritative template.

### 1. Title and one-line purpose

```markdown
# Skill Name

One sentence: what this skill builds and how.
```

### 2. Workflow

Numbered steps, one line each. Each step names what to do and points to a reference file for details:

```markdown
## Workflow

1. **Verb phrase** — brief description. See [REFERENCE.md](REFERENCE.md).
2. **Verb phrase** — brief description. See [OTHER.md](OTHER.md).
...
```

Rules for workflow steps:
- Start each step with a **bold verb phrase**
- Follow with an em-dash and a one-line description
- End with a link to the relevant reference file
- No code blocks, no multi-line explanations
- 5-12 steps is the sweet spot. Fewer means the skill is trivial. More means it needs splitting.

### 3. Self-review checklist

Checkbox items that the agent must verify after completing the workflow:

```markdown
## Self-review checklist

Before delivering, verify ALL:

- [ ] Concrete, verifiable condition
- [ ] Another concrete condition
...
```

Rules for checklist items:
- Every item must be objectively verifiable (can you answer yes/no without judgment?)
- Bad: "Code is clean" (subjective)
- Good: "No console errors during a full run" (objective)
- Bad: "Tests pass" (too vague)
- Good: "All 5 test categories pass: init, moves, win, negative, visual" (specific)
- 6-12 items. Fewer means you're not checking enough. More means you're micromanaging.

### 4. Golden rules

Hard mechanical rules specific to this skill's domain:

```markdown
## Golden rules

Hard rules. Never violate these.

1. **Rule name.** Imperative explanation of what to always/never do.
2. **Rule name.** Another hard rule.
...
```

Rules for golden rules:
- 3-8 rules per skill
- Use imperative voice: "Never", "Always", "Must", "Do not"
- Never use soft language: "Consider", "Try to", "Prefer", "Should"
- Each rule prevents a specific failure mode **observed in the RED baseline** (not hypothetical)
- Each rule is mechanical — an agent can follow it without judgment

**How to derive golden rules**: Look at the rationalizations captured in `pressure-tests/baseline.md`. For each observed rationalization, write a rule that prevents it:

| Observed rationalization | Golden rule |
|---|---|
| "Tests probably pass, I'll skip running them" | "Never claim completion without `test-output.txt` on disk matching `Tests: \d+ passed, 0 failed` from this session." |
| "SKILL.md is cleaner if I add examples inline" | "SKILL.md is a map. If you're writing a code block in SKILL.md, it belongs in a companion file." |
| "Obvious what to do, I'll skip the description keywords" | "Description is discovery. If the description doesn't contain keywords a user would say, the skill won't trigger." |
| "I'll hand-wave the verification" | "Every completion claim is file-gated. `Verify` / `check` / `ensure` without a concrete file-existence check is forbidden." |

### 5. Anti-rationalization counter-table

MANDATORY section (new). Captures the exact rationalizations observed in `pressure-tests/baseline.md` and pairs each with a concrete reality.

```markdown
## Anti-rationalization counter-table

| Excuse | Reality |
|---|---|
| "<verbatim excuse observed in baseline>" | <specific action the agent must take instead> |
```

Rules:
- Minimum 5 rows for discipline-enforcing skills. Minimum 3 rows for one-shot generators.
- Every row references a real excuse observed in `pressure-tests/baseline.md`. No imagined rows.
- Reality column is a concrete action, not a platitude.

Bad row: `| "Tests will pass eventually" | Be patient. |` — platitude, not an action.
Good row: `| "Tests will pass eventually" | Run `npm test`, save output to `test-output.txt`, only claim completion if exit code is 0. |` — concrete action.

### 6. Honest termination labels (workflow skills only)

MANDATORY for any produced skill that makes completion claims. A finite enum, 3-6 labels, each with an observable condition on disk.

```markdown
## Honest termination labels

| Label | Meaning |
|---|---|
| `complete` | Every AC verified green; zero unresolved critical/major defects. |
| `partial_with_accepted_unfixed` | Critical defects fixed; some major/minor explicitly accepted with rationale. |
| `blocked_unresolved` | Critical defect with no path forward AND budget not exhausted. |
| `budget_exhausted` | Fix budget reached with unresolved critical/major defects. |
| `cancelled` | User interrupted. |
```

Never `done` / `all good` / `no issues remain`. One of the N labels must be `cancelled`. Every label's meaning references observable evidence files, not the coordinator's judgment.

### 7. Reference file index

A table linking to every reference file:

```markdown
## Reference files

| File | Contents |
|------|----------|
| [FILE.md](FILE.md) | One-line summary |
```

## Reference files: the details

Each reference file covers one concern (architecture, testing, visual design, workflow details, etc.).

### Structure of a reference file

```markdown
# Topic Name

Brief (1-2 sentence) purpose statement.

## Section 1
[Content]

## Section 2
[Content]
```

### What goes in reference files

- **Code patterns and templates**: Full code blocks, boilerplate, example implementations
- **Detailed step instructions**: Multi-paragraph explanations of how to do something
- **Domain-specific reference**: APIs, schemas, protocol definitions, data formats
- **Examples**: Input/output pairs, before/after comparisons
- **Testing methodology**: Test patterns, verification steps, checklists
- **Visual standards**: CSS systems, design tokens, layout patterns
- **Failure diagnosis**: Symptom → cause → fix tables

### Writing effective reference files

**Start with context, not instructions.** The first paragraph should tell Claude what this file is about and when to use it. Claude may read just the first few lines to decide whether to continue.

**Use headers liberally.** Claude can scan headers to find the right section. A reference file with no headers forces a full read.

**Code blocks should be copy-paste ready.** Don't write pseudocode unless the intent is for Claude to adapt it significantly. If the code should be used as-is, make it complete and runnable.

**Tables for structured data.** Decision trees, symptom→fix mappings, and option comparisons are better as tables than prose.

**Keep under 500 lines.** If approaching this limit, split into two files. Each file should have a focused topic.

## Writing feedback loops

Every skill needs at least one feedback loop — a cycle where the agent does work, verifies it, and fixes issues. The most impactful skill improvement you can make is adding a concrete feedback loop.

### Anatomy of a feedback loop

```
Do → Check → Diagnose → Fix → Re-check
```

Each step must be concrete:

| Step | Vague (bad) | Concrete (good) |
|---|---|---|
| Do | "Write the code" | "Implement `getValidMoves` as a pure function" |
| Check | "Test it" | "Run `npx playwright test` and verify zero failures" |
| Diagnose | "Fix any issues" | "If assertion fails on game state, log `applyMove` input/output" |
| Fix | "Update the code" | "Fix the specific function identified in diagnosis" |
| Re-check | "Test again" | "Re-run the same test suite, verify the previously failing test now passes" |

### Types of feedback loops

**Automated test loop** (strongest): Run a test suite, parse results, fix failures.
```
Write code → Run tests → If failures: read error, fix specific issue → Re-run tests
```

**Self-review loop**: Agent reviews its own output against a checklist.
```
Complete task → Check each item in self-review checklist → Fix any failures → Re-check
```

**Visual verification loop**: Agent takes a screenshot and inspects it.
```
Render UI → Take screenshot → Check against visual standards → Fix issues → Re-render
```

**Rules audit loop**: Agent verifies domain rules are satisfied.
```
Implement feature → Walk through each rule → Verify with test case → Fix gaps
```

## Writing failure diagnosis

When the agent gets stuck, the skill must help it figure out WHY. The pattern is a table:

```markdown
| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Specific observable problem | Root cause | Specific action to take |
```

Rules:
- Symptoms must be things the agent can observe (error messages, unexpected output, test failures)
- Causes must be specific (not "something went wrong")
- Fixes must be actions (not "investigate further")
- Include the most common 5-10 failure modes
- End with a catch-all: "If none of the above: log the state before and after the failing operation and inspect the diff."

## Avoiding AI slop

"AI slop" is output that looks reasonable but is generic and inconsistent. It happens when instructions are vague.

### The adjective test

Search your skill for adjectives. For each one, ask: "Could two runs of this skill produce different output because this adjective is subjective?"

| Slop | Concrete replacement |
|---|---|
| "Clean code" | "Functions under 30 lines, no nested callbacks deeper than 2" |
| "Good design" | "CSS variables on `:root`, `system-ui` font, hover states on interactives" |
| "Appropriate error handling" | "Every `catch` logs the error and returns a structured `{ success: false, error: string }`" |
| "Well-tested" | "Unit tests for all pure functions, integration test for the main workflow, negative tests for invalid input" |
| "Clear documentation" | "JSDoc on exported functions, README with install/run/test sections" |

### The copy-paste test

For any code pattern in your skill: could an agent copy it verbatim and get a working result? If not, make it more complete. Pseudocode invites improvisation. Complete code enforces consistency.

### The diff test

Run the skill twice on the same input. Diff the outputs. Anything that differs between runs indicates an underspecified instruction. Fix the instruction to make it deterministic.

## Anti-patterns to avoid

These are concrete authoring mistakes that produce broken skills. Each has a fix.

### ❌ Narrative example
"In session 2025-10-03, we found empty projectDir caused..."
**Why bad:** too specific, non-reusable, degrades over time as the referenced events fade.
**Fix:** restate as a general pattern: "When projectDir is empty, ..."

### ❌ Multi-language dilution
`example-js.js`, `example-py.py`, `example-go.go`
**Why bad:** each implementation is mediocre, maintenance is 3x, no single example is authoritative.
**Fix:** one excellent example in the most relevant language. Claude ports accurately to other languages.

### ❌ Code blocks in SKILL.md
A skill whose SKILL.md contains inline code forces every triggered invocation to pay the token cost of that code, even for agents that won't execute it.
**Fix:** move code to a companion file. SKILL.md points to the file; the file is read only when needed.

### ❌ Code in flowcharts
```dot
step1 [label="import fs"];
step2 [label="read file"];
```
**Why bad:** not copy-pasteable, harder to read than a code block, node labels carry no semantics.
**Fix:** use a numbered list or a code block. Flowcharts are for branching decision points, not linear sequences.

### ❌ Generic labels
`helper1`, `helper2`, `step3`, `pattern4`, `option-a`, `option-b`
**Why bad:** labels must carry semantic meaning so the agent knows what it's selecting.
**Fix:** name each item by what it does: `retry-with-backoff`, `fail-fast`, `lazy-load`.

### ❌ Workflow summary in description
`description: Use when creating skills — runs RED-GREEN-REFACTOR across N phases`
**Why bad:** Claude follows the description as a shortcut and skips the skill body. A skill body describing 5 phases becomes a 1-phase skill in practice.
**Fix:** triggers only. `description: Use when creating, editing, or reviewing a skill.`

### ❌ Soft rules ("consider", "try to", "prefer")
A rule that says "Consider running tests" is a suggestion agents skip under pressure.
**Fix:** hard imperative. "Run tests. If `test-output.txt` does not exist, do not claim completion."

### ❌ Iron-law gate weakened to a reminder
`Verify tests pass before completion` is a reminder, not a gate.
**Fix:** file-gated check. `Before claiming completion, read test-output.txt and assert it matches 'Tests: \d+ passed, 0 failed' from this session.`

### ❌ Inline table-of-contents in SKILL.md for a flat skill
A skill under 300 lines that still ships with FORMAT.md + STATE.md + etc. is over-engineered — companion-split is for skills that need it.
**Fix:** keep flat skills flat. Split only when you cross the 300-line threshold.

## Technology selection

Skills that produce code must guide technology choices. Agents work best with boring technology.

### Prefer boring technology

"Boring" means: composable, stable API, well-documented, widely used, well-represented in training data. Agents model boring technology accurately because they've seen thousands of examples.

| Boring (prefer) | Exotic (avoid unless necessary) |
|---|---|
| Vanilla JS, HTML, CSS | Svelte, Solid, HTMX |
| `fetch` API | Axios, superagent |
| CSS Grid / Flexbox | Tailwind (requires build), CSS-in-JS |
| Node.js built-ins | Obscure npm packages |
| SQLite | Exotic databases |
| `system-ui` font stack | Custom font loading pipelines |

### Reimplement over wrapping opaque dependencies

When a library is opaque, brittle, or poorly documented, it's cheaper for the agent to reimplement the needed subset than to fight upstream behavior. A skill should say: "Implement X directly using Y" rather than "Install library Z."

Example: Instead of depending on a game physics library, implement the specific collision detection the game needs with 20 lines of math.

### Centralize invariants in shared functions

Agents replicate patterns they see — even bad ones. If the same logic appears in 3 places, the agent will copy-paste and eventually drift. Instead:

- Extract common logic into named functions
- Define constants in one place and import them
- Use a config object for values that might change

This is the "shared utility packages over hand-rolled helpers" principle. One function, one truth.

## Promoting rules from docs to code

Documentation says what to do. Code enforces it. When a doc instruction is repeatedly violated, promote it.

### The promotion ladder

```
1. Comment         → weakest: agents often skip comments
2. SKILL.md rule   → medium: agents follow golden rules most of the time
3. Validation fn   → strong: code rejects invalid output at runtime
4. Linter/test     → strongest: CI catches violations before they land
```

When possible, encode rules as validation functions or tests, not just instructions. A rule that says "all moves must be validated" is weaker than a `performMove` function that actually calls `getValidMoves` and rejects invalid input.

### Error messages as agent context

When writing validation functions, make error messages self-documenting:

```javascript
// Bad: agent doesn't know how to fix this
throw new Error('Invalid move');

// Good: agent knows exactly what went wrong and what to do
throw new Error(
  `Invalid move: {row: ${move.row}, col: ${move.col}} is not in validMoves. ` +
  `Current player: ${state.currentPlayer}. ` +
  `Valid moves: ${JSON.stringify(state.validMoves.slice(0, 5))}...`
);
```

Custom linters and validators with remediation instructions become force multipliers: once encoded, they correct the agent everywhere at once, automatically.

## Discoverability: if it's not in the files, it doesn't exist

The agent can only see what's in the skill directory and the user's repo. External knowledge is invisible.

### What must live in skill files

- All domain conventions and patterns
- All technology choices and their rationale
- All structural requirements (file naming, data shapes, API contracts)
- All known failure modes and their fixes
- All quality standards with concrete specifications

### What's invisible to the agent

- Slack conversations about "how we usually do this"
- External documentation not linked or inlined
- Team norms that aren't written down
- Assumptions that "everyone knows"

If a constraint matters, write it in a skill file. If it's not written, it will be violated.

## Architectural philosophy

### Enforce boundaries centrally, allow autonomy locally

A skill should be strict about boundaries (state shape, API contracts, validation rules, file structure) but permissive about implementation details within those boundaries.

**Enforce centrally**: Data shapes, naming conventions, required functions, test API signatures, CSS variable system, file layout.

**Allow autonomy locally**: How to implement a specific game rule, which CSS colors to choose within the variable system, how to structure internal helper functions, AI difficulty algorithm.

This gives the agent guardrails without micromanaging.

### Corrections are cheap, waiting is expensive

In an agent workflow, it's faster to build something, test it, find problems, and fix them than to plan everything perfectly upfront. Skills should encode a "build → test → fix" loop, not a "plan exhaustively → build perfectly" approach.

This doesn't mean skip planning. It means: get to testable output fast, then iterate based on real failures rather than hypothetical ones.
