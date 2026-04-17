# claude-skills

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE) [![Docs](https://img.shields.io/badge/docs-mintlify-18a34a?style=flat-square)](https://mintlify.com/npow/claude-skills)

**Make Claude Code do complex multi-step workflows reliably with a single slash command.**

Claude Code is powerful out of the box, but complex tasks — scaffolding a Python library, stress-testing a design, diagnosing a flaky test, shipping a product idea end-to-end — require careful prompting and domain knowledge that gets lost between sessions. You end up re-explaining the same workflows, catching the same mistakes, and missing the same steps.

Skills fix that. Each skill is a directory of markdown files that Claude loads as context when you invoke it. The main `SKILL.md` defines the workflow, golden rules, and a self-review checklist. Companion files (`FORMAT.md`, `STATE.md`, `GOLDEN-RULES.md`, `INTEGRATION.md`) cover schemas and discipline patterns, loaded only when needed. Because they live in `~/.claude/skills/`, they're always available.

## Which skill do I want?

| If you want to… | Use |
|---|---|
| Go from a vague idea to working verified code, autonomously | [`/autopilot`](#orchestration) |
| Turn a conversation into a technical spec | [`/spec`](#design--specification) |
| Research a topic rigorously with cited sources | [`/deep-research`](#research--ideation) |
| Stress-test a design to find its flaws before you commit | [`/deep-design`](#design--specification) |
| Audit a document, codebase, or skill for defects | [`/deep-qa`](#quality--audit) |
| Generate genuinely novel ideas (not obvious recombinations) | [`/deep-idea`](#research--ideation) |
| Find a viable market gap to build into | [`/gap-finder`](#research--ideation) |
| Critically review a proposal or grant | [`/proposal-reviewer`](#design--specification) |
| Scaffold a pip-installable Python library | [`/build-python-library`](#building--shipping) |
| Initialize a GitHub repo with CI/CD, README, license, topics | [`/init-github-repo`](#building--shipping) |
| Ship a product idea end-to-end (design → package) | [`/ship-it`](#building--shipping) |
| Diagnose a flaky test and produce a reproducible fix | [`/flaky-test-diagnoser`](#quality--audit) |
| Check whether a codebase is production-ready | [`/prod-readiness`](#quality--audit) |
| Visualize data — chart, diagram, table, timeline, slides | [visualization skills](#quick-visualization) |
| Create a new Claude Code skill | [`/create-skill`](#authoring) |

---

## Jump to

- [Install](#install) · [Usage](#usage)
- Skills: [Quick Visualization](#quick-visualization) · [Research & Ideation](#research--ideation) · [Design & Specification](#design--specification) · [Building & Shipping](#building--shipping) · [Quality & Audit](#quality--audit) · [Orchestration](#orchestration) · [Authoring](#authoring)
- [Architecture](#architecture) · [Design principles](#design-principles) · [Contributing](#contributing)

---

## Install

**Common case — add one skill to your existing setup:**

```bash
git clone https://github.com/npow/claude-skills.git
ln -s "$(pwd)/claude-skills/deep-research" ~/.claude/skills/deep-research
```

**Full install — use the repo as your skills directory:**

```bash
mv ~/.claude/skills ~/.claude/skills.bak
ln -s "$(pwd)/claude-skills" ~/.claude/skills
```

## Usage

Invoke any skill by typing its name as a slash command:

```
/deep-research
/ship-it "build a CLI tool for tracking habits"
/autopilot "REST API for a bookstore inventory with TypeScript"
```

If a skill conflicts with a plugin skill (e.g., `/team` vs `oh-my-claudecode:team`), unprefixed slash invocations hit the user skill. For autonomous selection preferences, configure `skillOverrides` in `~/.claude/settings.json`.

---

## Skills

### Quick Visualization

Lightweight rendering skills — produce interactive browser output from context-supplied data. No state, no workflow, just output.

- **`/chart`** — Interactive Chart.js charts (bar, line, pie, radar, time series).
- **`/diagram`** — Interactive, draggable node-and-edge diagrams via Cytoscape.js.
- **`/slides`** — Reveal.js slide decks opened live in the browser.
- **`/table`** — Sortable, filterable comparison tables with zero dependencies.
- **`/timeline`** — Gantt-style timelines and roadmaps via vis-timeline.

### Research & Ideation

Gather evidence or generate candidates with honest coverage reports and adversarial kill-chains.

- **`/deep-research`** — Systematic multi-dimensional research across orthogonal dimensions (WHO/WHAT/HOW/WHERE/WHEN/WHY) with source quality tiers, cross-source corroboration, counter-evidence tracking, and temporal validity checks.
- **`/research-brief`** — Structured, cited research brief with counterevidence and synthesis from web sources.
- **`/competitive-matrix`** — Market landscape research rendered as an interactive color-coded comparison matrix in the browser.
- **`/deep-idea`** — Genuinely novel idea generation via five orthogonal forcing functions, adversarial novelty killing, independent novelty judge, and prior-art verification.
- **`/gap-finder`** — Viable product/business ideas through adversarial generation-and-kill cycles validated against real market data.

### Design & Specification

Turn ideas into specs, stress-test designs, critically review proposals.

- **`/spec`** — Turn a conversation into a complete technical specification — Problem Statement, Goals/Non-Goals, API, Data Model, Failure Modes, Success Metrics. Saved as `spec-<slug>.md`.
- **`/deep-design`** — Adversarially stress-test a design with parallel critic agents across orthogonal dimensions (correctness, usability, economics, operability, security). Iterates until coverage saturates. Output is a battle-tested spec with honest coverage report.
- **`/proposal-reviewer`** — Critically reviews proposals via parallel critic agents across four dimensions (viability, competition, structural flaws, evidence), independent credibility + severity judges, and falsifiability-gated weaknesses.

### Building & Shipping

Take ideas through to working artifacts.

- **`/build-python-library`** — Pip-installable Python packages with src layout, pyproject.toml, and pytest. Builds core abstractions with adapters and verifies each module before proceeding.
- **`/init-github-repo`** — Git repo with JTBD-focused README, CI/CD workflow, license, .gitignore, and SEO-optimized description and topics.
- **`/develop-board-game`** — Faithful digital board games as single-file HTML/JS/CSS apps — rules, multiplayer, Playwright tests.
- **`/ship-it`** — Idea through design → build → test → integrate → package phases using parallel subagents with iron-law quality gates between each phase. Delegates to `/consensus-plan`, `/team`, `/deep-qa`, `/loop-until-done`.

### Quality & Audit

Find defects in existing artifacts — documents, code, tests, production readiness.

- **`/deep-qa`** — Audits any artifact (document, spec, code, skill) for defects via parallel critic agents across artifact-type-tailored QA dimensions. Batched independent severity judges. Structured defect registry with honest termination labels.
- **`/prod-readiness`** — Scans codebases for 24 production readiness items via independent judges per item. Every verdict requires exact file/line evidence — no "looks ok."
- **`/flaky-test-diagnoser`** — Multi-run experiments, isolation tests, ordering permutations, and timing analysis with competing-hypothesis tracking, falsifiability gates, and mandatory red-green-red demonstration before a diagnosis is accepted.

### Orchestration

Multi-agent coordination with independent-judge architecture, two-stage review on source modifications, iron-law verification gates, and file-based state (no MCP dependency). Integrate deeply with `/deep-design` and `/deep-qa`.

Ordered bottom-up (primitive → composed → autonomous):

- **`/parallel-exec`** — *Primitive.* Fires N independent subagents in parallel with inline tier routing (Haiku/Sonnet/Opus). Every task carries a mandatory verification command; an independent convergence-checker detects cross-task conflicts before any aggregate success claim.
- **`/team`** — *Composed.* N coordinated agents on a staged pipeline (plan → prd → exec → verify → fix) using Claude Code's native team tools. Structured handoff docs, two-stage verify via `/deep-qa --diff` plus code-quality review, bounded fix budget, honest termination labels.
- **`/loop-until-done`** — *Composed.* PRD-driven persistence loop until every story's acceptance criterion has fresh verified evidence. Structured criteria with executable verification commands, two-stage review per story, mandatory deslop pass.
- **`/consensus-plan`** — *Composed.* Planner → Architect → Critic loop producing an ADR-backed plan. All three roles are fully independent agents reading/writing via files. Critic rejections require falsifiable failure scenarios, not opinions.
- **`/autopilot`** — *Top of stack.* Takes a vague idea through five phases (expand → plan → exec → qa → validate). Delegates each phase to the right specialist skill and ends with three fully independent judges (correctness, security, quality).

### Authoring

Build and maintain skills themselves.

- **`/create-skill`** — Creates new skills following RED-GREEN-REFACTOR (from superpowers/writing-skills): pressure-scenarios first, baseline-without-skill observed, skill written, rationalization loopholes closed. Every output inherits the discipline patterns (golden rules, anti-rationalization tables, iron-law gates, honest termination labels).
- **`/magic-fetch`** — Logs capability gaps in real time. When Claude hits a wall, it records exactly what tool, API, or access would have solved it — building a prioritized integration roadmap over time.

---

## Architecture

The orchestration skills compose into a full-lifecycle stack. Each box delegates to the skills below it — the coordinator never evaluates, always an independent judge agent does.

```
/autopilot                          ← top: idea → verified code
   │
   ├─► Phase 0: Expand      →  /spec | /deep-design | deep-interview
   ├─► Phase 1: Plan        →  /consensus-plan
   ├─► Phase 2: Execute     →  /team
   │                              ├─ /parallel-exec  (fanout)
   │                              └─ /deep-qa --diff (verify)
   ├─► Phase 3: QA          →  /deep-qa + /loop-until-done
   └─► Phase 4: Validate    →  3 independent judges (correctness/security/quality)
```

`/ship-it` is a parallel composition for product-ideation projects, delegating to the same building blocks.

---

## Design principles

Every skill in this repo follows:

1. **Independence invariant** — the coordinator orchestrates but never evaluates. Severity, completeness, and approval are delegated to independent judge agents with no stake in the outcome.
2. **Iron-law verification gate** — no completion claims without fresh evidence. Every stage transition requires an evidence file (test output, judge verdict, lint exit code) on disk.
3. **Structured output contract** — judges and critics emit machine-parseable lines between `STRUCTURED_OUTPUT_START`/`STRUCTURED_OUTPUT_END` markers. Free text is ignored by the coordinator; unparseable output fails safe.
4. **Honest termination labels** — explicit per-skill vocabulary (e.g., `consensus_reached`, `blocked_unresolved`, `budget_exhausted`). Never "complete" or "no issues remain" as a catch-all.
5. **Anti-rationalization counter-table** — every skill includes a defensive table naming the specific excuses agents reach for under pressure and the iron-law response.
6. **Falsifiability gate** — critic/reviewer rejections require concrete scenarios and verification commands, not opinions.
7. **File-based state, no MCP dependency** — skills work in plain Claude Code. Runtime state lives in `{skill-name}-{run_id}/` with a `generation` counter for atomic writes.

The `docs/specs/2026-04-16-orchestration-suite-design.md` spec documents these patterns in full.

---

## Contributing

Skills live directly in this repository. To contribute:

1. Fork the repository
2. Use `/create-skill` to scaffold and pressure-test your new skill
3. Submit a PR

Your new skill will automatically inherit the discipline patterns (golden rules, anti-rationalization table, iron-law gates, honest termination labels) via `/create-skill`.

See `create-skill/SKILL.md` for the complete guide.

## License

[Apache 2.0](LICENSE)
