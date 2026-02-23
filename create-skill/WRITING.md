# Writing Skill Content

How to write effective metadata, SKILL.md, reference files, golden rules, and checklists.

## Metadata: name and description

### Name

- Lowercase letters, numbers, hyphens only
- Max 64 characters
- Use gerund form or action-oriented: `create-skill`, `develop-board-game`, `review-pr`
- Avoid generic names: `helper`, `utils`, `tool`

### Description

The description is a search index entry. Claude uses it to decide whether to load the skill. Write it in third person.

**Formula**: [What it does]. Use when [trigger conditions].

```yaml
# Good: specific, keyword-rich, includes triggers
description: Creates well-structured Claude Code skills from scratch. Use when the user asks to build, design, or scaffold a new skill, slash command, or agent capability.

# Bad: vague, no triggers
description: Helps with creating things.

# Bad: first person
description: I can help you build skills.
```

**Keyword coverage**: Include the words a user would actually say. If users might say "slash command" instead of "skill", include both. If they might say "scaffold" or "generate" or "create", include all three.

**Length**: Under 1024 characters. Aim for 1-3 sentences.

## SKILL.md body: the table of contents

SKILL.md has exactly four sections:

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
- Each rule prevents a specific failure mode identified in the design phase
- Each rule is mechanical — an agent can follow it without judgment

**How to derive golden rules**: Look at your failure modes list from the design phase. For each failure mode, write a rule that prevents it:

| Failure mode | Golden rule |
|---|---|
| Agent puts all content in SKILL.md | "SKILL.md is a map. If you're writing a code block in SKILL.md, it belongs in a reference file." |
| Agent writes vague descriptions | "Description is discovery. If the description doesn't contain the keywords a user would say, the skill won't trigger." |
| Agent skips testing | "Every skill must have at least one feedback loop: do → check → fix." |
| Output is inconsistent between runs | "Replace every adjective with a specification." |

### 5. Reference file index

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
