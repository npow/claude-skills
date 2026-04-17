# claude-skills

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE) [![Docs](https://img.shields.io/badge/docs-mintlify-18a34a?style=flat-square)](https://mintlify.com/npow/claude-skills)

Make Claude Code do complex multi-step workflows reliably with a single slash command.

## How it works

Claude Code is powerful out of the box, but complex tasks — scaffolding a Python library, initializing a GitHub repo with CI/CD, diagnosing flaky tests, shipping a product idea end-to-end — require careful prompting and domain knowledge that gets lost between sessions. You end up re-explaining the same workflows, catching the same mistakes, and missing the same steps.

Skills fix that. Each skill is a directory of markdown files that Claude loads as context when you invoke it. The main `SKILL.md` defines workflow steps, golden rules, and a self-review checklist. Additional reference files cover specific phases — templates, patterns, examples — loaded only when needed. Because they live in `~/.claude/skills/`, they're always available.

## Skills

### Building & Shipping

- **`/build-python-library`** — Scaffolds pip-installable Python packages with src layout, pyproject.toml, and pytest, building core abstractions with adapters and verifying each module before proceeding.
- **`/develop-board-game`** — Creates faithful digital board games as single-file HTML/JS/CSS apps, handling rules, multiplayer, and Playwright tests.
- **`/init-github-repo`** — Initializes repos with a JTBD-focused README, CI/CD workflow, license, .gitignore, and SEO-optimized description and topics.
- **`/ship-it`** — Takes a product idea through design, build, test, integrate, and package phases using parallel subagents with quality gates between each phase.

### Orchestration

Multi-agent coordination skills with independent-judge architecture, two-stage review, and iron-law verification gates. File-based state (no MCP dependency). Integrate deeply with `/deep-design` and `/deep-qa`.

- **`/autopilot`** — Takes a vague idea through five phases (expand → plan → exec → qa → validate) using iron-law evidence gates between each transition. Delegates each phase to the right specialist skill (`deep-design`, `/consensus-plan`, `/team`, `deep-qa`) and ends with three fully independent judges (correctness, security, quality).
- **`/consensus-plan`** — Planner → Architect → Critic loop producing an ADR-backed plan. All three roles are fully independent agents reading and writing via files; critic rejections require falsifiable failure scenarios, not opinions. Outputs include per-criterion verification commands.
- **`/loop-until-done`** — PRD-driven persistence loop that keeps working until every story's acceptance criterion has fresh evidence. Structured criteria with executable verification commands, two-stage review per story (spec compliance → code quality via `deep-qa`), honest termination labels, mandatory deslop pass.
- **`/parallel-exec`** — Fires independent subagents in parallel with inline tier routing. Every task carries a mandatory verification command; an independent convergence-checker reads all task outputs and detects conflicts between siblings before any aggregate success claim.
- **`/team`** — N coordinated agents on a staged pipeline (plan → prd → exec → verify → fix) using Claude Code's native team tools. Structured handoff docs between stages, two-stage verify via `deep-qa --diff` plus code-quality review, bounded fix budget, honest termination labels.

### Research & Design

- **`/competitive-matrix`** — Researches a market and renders an interactive, color-coded comparison matrix in the browser.
- **`/deep-design`** — Adversarially stress-tests a design with parallel critic agents across dimensions like security, scalability, and UX. Iterates until flaws are saturated. Output is a battle-tested spec.
- **`/deep-idea`** — Generates genuinely novel ideas via five orthogonal forcing functions and adversarial novelty killing. Forces extrapolation over interpolation.
- **`/deep-qa`** — Audits any artifact (document, spec, code, skill) for defects using parallel critic agents across QA dimensions tailored to the artifact type.
- **`/deep-research`** — Systematic multi-dimensional research using parallel agents across orthogonal dimensions (WHO/WHAT/HOW/WHERE/WHEN/WHY). Source quality tiers, spot-checked verification, honest coverage report.
- **`/gap-finder`** — Finds viable product or business ideas through adversarial generation-and-kill cycles, validating each candidate against real market data.
- **`/proposal-reviewer`** — Critically reviews proposals by fact-checking claims against primary sources, mapping the competitive landscape, and identifying structural flaws.
- **`/research-brief`** — Produces a structured, cited research brief with counterevidence and synthesis from web sources.
- **`/spec`** — Turns a conversation or rough idea into a complete, structured technical specification saved as a markdown file.

### Visualization

- **`/chart`** — Renders interactive Chart.js charts (bar, line, pie, radar, time series) live in the browser from context-supplied data.
- **`/diagram`** — Renders interactive, draggable node-and-edge diagrams in the browser using Cytoscape.js.
- **`/slides`** — Converts content into a Reveal.js slide deck and opens it live in the browser.
- **`/table`** — Renders sortable, filterable comparison tables live in the browser with zero dependencies.
- **`/timeline`** — Renders interactive Gantt-style timelines and roadmaps in the browser using vis-timeline.

### Debugging & Quality

- **`/flaky-test-diagnoser`** — Runs multi-run experiments, isolation tests, ordering permutations, and timing analysis to find the root cause of a flaky test.
- **`/prod-readiness`** — Scans codebases for 24 production readiness items and produces a scored report with pass/fail/warning and suggested fixes.

### Meta

- **`/create-skill`** — Builds new Claude Code skills following harness engineering best practices: table-of-contents architecture, golden rules, self-review loops, progressive disclosure.
- **`/magic-fetch`** — Logs capability gaps in real-time. When Claude hits a wall, it records exactly what tool, API, or access would have solved it — building a prioritized integration roadmap over time.

## Install

```bash
# Clone the repo
git clone https://github.com/npow/claude-skills.git

# Option A: Symlink individual skills
ln -s "$(pwd)/claude-skills/build-python-library" ~/.claude/skills/build-python-library

# Option B: Use the repo as your skills directory
# (back up any existing skills first)
mv ~/.claude/skills ~/.claude/skills.bak
ln -s "$(pwd)/claude-skills" ~/.claude/skills
```

## Usage

Invoke any skill by typing its name as a slash command in Claude Code:

```
/deep-research
/ship-it
/flaky-test-diagnoser
```

## Contributing

Skills live directly in this repository. To contribute:

1. Fork the repository
2. Use `/create-skill` to scaffold and test your new skill
3. Submit a PR

See `create-skill/SKILL.md` for the complete guide.

## License

[Apache 2.0](LICENSE)
