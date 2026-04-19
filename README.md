---
description: Documentation index for claude-skills repository (not an invocable skill)
---

# claude-skills

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE) [![Docs](https://img.shields.io/badge/docs-mintlify-18a34a?style=flat-square)](https://mintlify.com/npow/claude-skills)

Claude Code skills. Each skill is a directory of markdown files that Claude loads when you invoke it with a slash command. Skills live in `~/.claude/skills/`, so they're always available.

## Which skill do I want?

| Task | Skill |
|---|---|
| Idea → working code, autonomously | `/autopilot` |
| Turn a conversation into a technical spec | `/spec` |
| Stress-test a design for flaws | `/deep-design` |
| Audit an artifact (doc, code, spec) for defects | `/deep-qa` |
| Research a topic with cited sources | `/deep-research` |
| Generate genuinely novel ideas | `/deep-idea` |
| Scaffold a Python library | `/build-python-library` |
| Diagnose a flaky test | `/flaky-test-diagnoser` |
| Check production readiness | `/prod-readiness` |
| Build a new skill | `/create-skill` |

## Skills

### Building & Shipping

- **`/build-python-library`** — pip-installable Python packages with src layout, pyproject.toml, and pytest.
- **`/develop-board-game`** — digital board games as single-file HTML/JS/CSS apps with Playwright tests.
- **`/init-github-repo`** — new repo with README, CI/CD, license, .gitignore, SEO topics.
- **`/ship-it`** — idea through design, build, test, integrate, package phases with iron-law gates between each.

### Design & Specification

- **`/deep-design`** — adversarial design stress-test via parallel critic agents across correctness, usability, economics, operability, security. Iterates until coverage saturates.
- **`/proposal-reviewer`** — critical review of proposals, pitches, and grants. Parallel critics across viability, competition, structural flaws, evidence. Falsifiability-gated weaknesses.
- **`/spec`** — conversation to technical spec (Problem, Goals, API, Data Model, Failure Modes, Success Metrics).

### Orchestration

Multi-agent coordination with file-based state, independent judges, and iron-law verification gates. Composes with `/deep-design` and `/deep-qa`. Ordered bottom-up:

- **`/parallel-exec`** — fire N subagents in parallel with tier routing and mandatory verification commands. Independent convergence checker detects cross-task conflicts.
- **`/team`** — N coordinated agents on a staged pipeline (plan → prd → exec → verify → fix). Two-stage verify via `/deep-qa --diff` and code-quality review.
- **`/loop-until-done`** — PRD-driven persistence loop. Keeps working until every acceptance criterion has fresh verified evidence.
- **`/deep-plan`** — Planner → Architect → Critic loop. All three are fully independent agents. Critic rejections require falsifiable failure scenarios.
- **`/autopilot`** — idea through five phases (expand → plan → exec → qa → validate). Delegates each phase to the right specialist. Three independent judges at the end.

### Quality & Audit

- **`/deep-qa`** — defect audit on any artifact (document, spec, code, skill). Parallel critics across artifact-typed dimensions. Batched severity judges.
- **`/flaky-test-diagnoser`** — multi-run experiments, isolation tests, ordering permutations, timing analysis. Competing-hypothesis tracking. Red-green-red demonstration required.
- **`/prod-readiness`** — 24-item production readiness scan. Independent judge per item. Every verdict requires exact file/line evidence.

### Research & Ideation

- **`/competitive-matrix`** — market landscape as an interactive color-coded comparison matrix.
- **`/deep-idea`** — novel idea generation with adversarial novelty killer, independent novelty judge, and prior-art verification.
- **`/deep-research`** — multi-dimensional research (WHO/WHAT/HOW/WHERE/WHEN/WHY) with source quality tiers, cross-source corroboration, counter-evidence, temporal validity.
- **`/gap-finder`** — viable product/business ideas through adversarial generation-and-kill cycles against real market data.
- **`/research-brief`** — structured, cited research brief with counterevidence.

### Visualization

- **`/chart`** — interactive Chart.js charts.
- **`/diagram`** — draggable node-and-edge diagrams via Cytoscape.js.
- **`/slides`** — Reveal.js slide decks.
- **`/table`** — sortable, filterable tables with zero dependencies.
- **`/timeline`** — Gantt-style timelines via vis-timeline.

### Authoring

- **`/create-skill`** — new skills via RED-GREEN-REFACTOR: pressure scenarios first, baseline observed, skill written, rationalization loopholes closed.
- **`/magic-fetch`** — logs capability gaps in real time for a prioritized integration roadmap.

## Install

```bash
git clone https://github.com/npow/claude-skills.git

# Add one skill
ln -s "$(pwd)/claude-skills/deep-research" ~/.claude/skills/deep-research

# Or use the whole repo as your skills directory
mv ~/.claude/skills ~/.claude/skills.bak
ln -s "$(pwd)/claude-skills" ~/.claude/skills
```

## Usage

```
/deep-research
/ship-it "build a CLI habit tracker"
/autopilot "REST API for a bookstore with TypeScript"
```

## Design

All skills use file-based state, independent judges for any load-bearing evaluation, iron-law verification gates, structured outputs, explicit termination labels, and anti-rationalization counter-tables. The orchestration suite composes bottom-up: `/parallel-exec` → `/team` / `/loop-until-done` / `/deep-plan` → `/autopilot`. Full spec at [`docs/specs/2026-04-16-orchestration-suite-design.md`](docs/specs/2026-04-16-orchestration-suite-design.md).

## Contributing

1. Fork the repository
2. Use `/create-skill` to scaffold and pressure-test your skill
3. Submit a PR

## License

[Apache 2.0](LICENSE)
