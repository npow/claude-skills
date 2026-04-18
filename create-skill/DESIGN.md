# Skill Design

How to analyze a domain, design the file structure, and apply progressive disclosure.

## Step 1: Understand the domain

Before designing anything, answer these questions. If you can't answer them, ask the user.

### What does the skill do?

Write a single sentence: "This skill [verb]s [object] by [method]."

Examples:
- "This skill builds digital board games by implementing rules engines and rendering game UIs in a single HTML file."
- "This skill generates API clients by reading OpenAPI specs and producing typed TypeScript code."
- "This skill reviews pull requests by analyzing diffs against project conventions and producing structured feedback."

If the sentence has "and" more than once, the skill is too broad. Split it.

### When should it trigger?

List the exact phrases a user would say:
- "build a chess game" → board game skill
- "create an API client for Stripe" → API client skill
- "review this PR" → PR review skill

Also list when it should NOT trigger:
- "explain how chess works" → this is a question, not a build request
- "fix the API client bug" → this is a bug fix, not generation

These become the `description` keywords and the negative test cases.

### What does it produce?

- Files? Which ones, what format?
- Terminal output? What structure?
- Side effects? (git commits, API calls, file writes)

### What tools does it need?

- Read/Write/Edit for file operations
- Bash for running commands
- Glob/Grep for searching
- External tools (Playwright, npm, etc.)

If the skill needs specific tools, add `allowed-tools` to frontmatter.

### What can go wrong?

List the top 5-10 failure modes. These become:
- Golden rules (preventive)
- Self-review checklist items (detective)
- Failure diagnosis table entries (corrective)

## Step 2: Design the file structure

### The two-level rule

Every skill has exactly two levels of content:

```
my-skill/
├── SKILL.md           # Level 1: map (always loaded on trigger)
└── reference files     # Level 2: details (loaded when Claude reads them)
```

SKILL.md points to reference files. Reference files do NOT point to other reference files. This is the "one level deep" rule. Deeply nested references cause Claude to partially read files and miss information.

### The 300-line companion-split threshold

If the skill's total content (SKILL.md + all reference files) exceeds 300 lines, switch to the npow orchestration companion split:

```
my-skill/
├── SKILL.md           # lean map only — workflow, golden rules, counter-table, labels
├── FORMAT.md          # output templates and schemas for every artifact the skill produces
├── STATE.md           # state.json schema, resume protocol, pre-transition gate checks
├── GOLDEN-RULES.md    # rules with concrete examples + full anti-rationalization counter-table
├── INTEGRATION.md     # composition with deep-qa, deep-design, degraded-mode fallbacks
└── pressure-tests/
    ├── scenarios.md
    ├── baseline.md
    └── with-skill.md
```

This is mandatory above 300 lines. It's not bureaucracy — long SKILL.md bodies get partial-read by Claude, and the split enables progressive disclosure. See [FORMAT.md](FORMAT.md) for templates.

### How to split content

| Content type | Where it goes | Why |
|---|---|---|
| Workflow steps (numbered, one-line each) | SKILL.md | Claude needs the overview immediately |
| Self-review checklist | SKILL.md | Must be checked every time |
| Golden rules | SKILL.md | Must be visible every time |
| Reference file index | SKILL.md | Map to deeper content |
| Code patterns and templates | Reference file | Only needed when implementing |
| Detailed step instructions | Reference file | Only needed when on that step |
| Examples and samples | Reference file | Only needed when relevant |
| Testing methodology | Reference file | Only needed during testing phase |
| Visual/style standards | Reference file | Only needed during UI work |
| Domain-specific reference (APIs, schemas) | Reference file | Only needed for specific questions |

### How many reference files?

- **1-2 files**: Simple skills (conventions, style guides, single-tool workflows, under 300 lines total)
- **3-5 files**: Medium skills (multi-step workflows, 300-800 lines — companion split applies)
- **6-8 files**: Complex skills (orchestrators, full application builders, 800+ lines — companion split + extra reference files)
- **More than 8**: The skill is too broad. Split into multiple skills.

Above 300 lines total, the core five files are always: SKILL.md, FORMAT.md, STATE.md (if workflow), GOLDEN-RULES.md, INTEGRATION.md. Extra topic-specific reference files come on top of those five.

### Naming reference files

Use descriptive names that indicate content:

Good: `TESTING.md`, `VISUAL.md`, `ARCHITECTURE.md`, `WORKFLOW.md`
Bad: `DETAILS.md`, `MORE.md`, `PART2.md`, `REFERENCE.md`

Claude uses filenames as signals for relevance. `TESTING.md` is clearly about testing. `DETAILS.md` could be about anything.

### Scripts and executable content

If the skill involves running commands, consider bundling scripts:

```
my-skill/
├── SKILL.md
├── TESTING.md
└── scripts/
    ├── validate.sh    # Claude runs this, doesn't read it
    └── template.html  # Claude copies/adapts this
```

Scripts are more reliable than generated code — Claude executes them without consuming context tokens for the script body.

## Step 3: Apply progressive disclosure

### What loads when

| Phase | What Claude sees | Token cost |
|---|---|---|
| Startup | `name` + `description` from all skills | ~100 tokens per skill |
| Trigger | SKILL.md body | The full file |
| As-needed | Reference files, one at a time | Only when read |

### Design for minimal initial load

SKILL.md should contain ONLY:
- The workflow (numbered steps, one line each)
- The self-review checklist
- The golden rules
- The reference file index

Everything else goes in reference files. This keeps the initial context load small and focused.

### Design for selective reference loading

Not every task needs every reference file. Structure reference files so Claude can determine from the filename and the one-line summary in SKILL.md whether it needs that file.

Example: A board game skill has `MULTIPLAYER.md`. If the user asks for a single-player solitaire game, Claude won't need to read it. The one-line summary in SKILL.md ("Host-authoritative model, hidden info, networking...") tells Claude it's not relevant.

### Long reference files: add a table of contents

If a reference file exceeds 100 lines, add a table of contents at the top:

```markdown
# Architecture Patterns

## Contents
- State management pattern
- Grid-based boards
- Card-based games
- AI opponent (minimax)
- Undo system
```

This helps Claude navigate to the right section without reading the entire file.

## Step 3.5: Flowchart usage rules

Flowcharts are expensive (they render inconsistently, take vertical space, and are ultimately read linearly — eliminating their non-linear advantage). Use them only where they pay for themselves.

### ✅ Use flowcharts for
- **Non-obvious decision points** where an agent might branch the wrong way
- **Process loops** where an agent might stop too early (pressure-test loops, verification loops, retry limits)
- **"When to use A vs B"** decisions between similar skills or patterns

### ❌ Never use flowcharts for
- **Reference material** — use tables or lists
- **Linear instructions** — use numbered lists
- **Code examples** — use markdown code blocks (not node labels inside a flowchart)
- **Labels without semantic meaning** — nodes named `step1`, `helper2`, `branch3` are worse than no flowchart

### Format requirements
- Every node label carries semantic meaning (no `step1`, `helper2`)
- Edge labels ("yes" / "no", or specific conditions) are always present
- Flowchart fits on one screen (≤10 nodes in SKILL.md bodies; ≤20 in reference files)
- Rendering: use `dot` / graphviz syntax inside a ` ```dot ` code block — Claude parses this reliably

## Step 4: Decide invocation settings

### Who invokes the skill?

| Setting | Use case |
|---|---|
| Default (both user and Claude) | Most skills — Claude triggers when relevant, user can also `/invoke` |
| `disable-model-invocation: true` | Dangerous operations (deploy, publish, delete) — user triggers only |
| `user-invocable: false` | Background knowledge (conventions, context) — Claude uses as needed |

### Should it fork?

Add `context: fork` when:
- The skill is a self-contained task (research, analysis, generation)
- It doesn't need conversation history
- Its output is a complete deliverable (a file, a report, a plan)

Do NOT fork when:
- The skill provides conventions/context that apply to the current conversation
- It needs to interact with the user mid-task
- Its guidance applies across multiple tool calls

## Checklist before moving to writing

- [ ] Single-sentence purpose statement written
- [ ] Trigger phrases listed (positive and negative)
- [ ] Output format defined
- [ ] Required tools identified
- [ ] Failure modes listed (5-10)
- [ ] File structure designed (flat or companion-split based on 300-line threshold)
- [ ] Each reference file has a clear name and single responsibility
- [ ] Invocation settings decided
- [ ] Pressure scenarios drafted (3-5, at least 2 pressure types) — see [PRESSURE-TESTING.md](PRESSURE-TESTING.md). These are authored BEFORE SKILL.md is written.
- [ ] Termination labels sketched (if workflow) — see [FORMAT.md](FORMAT.md) mandatory section 5.
- [ ] Integration decisions made: will the skill invoke `deep-qa` for self-review? `deep-design` for design review? — see [INTEGRATION.md](INTEGRATION.md).
