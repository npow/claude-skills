# Claude Skills

A library of composable skills for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Each skill is a self-contained directory that Claude loads when you invoke it — giving your coding agent structured workflows for research, debugging, QA, visualization, and multi-agent orchestration.

## Quickstart

Skills depend on shared contracts in `_shared/` and compose with each other (`/autopilot` → `/deep-plan` → `/deep-qa`), so install the whole repo:

```bash
git clone https://github.com/npow/claude-skills.git
mv ~/.claude/skills ~/.claude/skills.bak
ln -s "$(pwd)/claude-skills" ~/.claude/skills
```

Then in Claude Code:

```
/deep-research "how do vector databases handle updates?"
/autopilot "REST API for a bookstore in TypeScript"
/deep-qa --path spec.md
```

## How It Works

Skills are markdown files that define structured workflows for Claude Code. When you type `/deep-qa`, Claude loads the skill and follows its workflow — spawning parallel critics, running independent judges, applying severity thresholds — rather than improvising an approach from scratch.

The skills compose bottom-up. `/deep-plan` produces a verified implementation plan. `/team` coordinates multiple agents through plan → build → verify → fix stages. `/autopilot` chains everything together: expand an idea, plan it, execute it, QA it, validate it. Each layer delegates to the one below, and every load-bearing evaluation uses an independent judge.

Skills with `workflow.py` get bespoke [Temporal](https://temporal.io/) workflows via [sagaflow](https://github.com/npow/sagaflow) — durable execution that survives session crashes. Skills without them use sagaflow's generic interpreter. Fire-and-forget while you do other work:

```bash
pip install sagaflow
sagaflow launch deep-qa --path spec.md --arg max_rounds=1 --await
```

## Skills Library

### Quality & Audit

| Skill | What it does |
|---|---|
| `/deep-qa` | Adversarial defect audit on any artifact. Parallel critics, cross-model diversity (GPT + Gemini), batched severity judges, rationalization auditor. |
| `/canon-pr-review` | PR review against 20 best practices from 35 software engineering books. Structured scores across 4 dimensions. |
| `/canon-design-review` | Architecture review evaluating 15 DDD/DDIA/Release It! practices. |
| `/prod-readiness` | 24-item production readiness scan with per-item evidence. |
| `/flaky-test-diagnoser` | Multi-run experiments, isolation tests, ordering permutations, timing analysis. |

### Debugging

| Skill | What it does |
|---|---|
| `/deep-debug` | Hypothesis-driven root cause analysis. Competing hypotheses, independent plausibility judges, falsification-first. |
| `/deep-debug-ensemble-v1` | Same as deep-debug but with multi-provider ensemble judging. |

### Design & Planning

| Skill | What it does |
|---|---|
| `/deep-design` | Adversarial design stress-test via parallel critics across correctness, usability, economics, operability, security. |
| `/deep-plan` | Planner → Architect → Critic consensus loop producing ADR-backed implementation plans. |
| `/spec` | Conversation to technical spec (Problem, Goals, API, Data Model, Failure Modes, Success Metrics). |

### Research & Ideation

| Skill | What it does |
|---|---|
| `/deep-research` | Multi-dimensional research (WHO/WHAT/HOW/WHERE/WHEN/WHY) with source quality tiers and coverage reporting. |
| `/deep-idea` | Novel idea generation with adversarial novelty killer and prior-art verification. |
| `/competitive-matrix` | Interactive color-coded market comparison matrix rendered in browser. |
| `/gap-finder` | Finds viable product ideas through generation-and-kill cycles against real market data. |

### Orchestration

Multi-agent coordination with file-based state and verification gates. Ordered bottom-up:

| Skill | What it does |
|---|---|
| `/team` | N agents on a staged pipeline (plan → PRD → exec → verify → fix). Durable Temporal-backed. |
| `/loop-until-done` | PRD-driven persistence loop — keeps working until every criterion has verified evidence. |
| `/autopilot` | Idea through five phases (expand → plan → exec → qa → validate). Delegates to specialists. |
| `/build` | Durable Temporal-backed build workflow for implementing a spec. |

### Visualization

All render live in the browser — never static images.

| Skill | What it does |
|---|---|
| `/chart` | Interactive Chart.js charts (bar, line, pie, radar, time series). |
| `/diagram` | Draggable node-and-edge diagrams via Cytoscape.js. |
| `/slides` | Reveal.js slide decks from bullet points or research. |
| `/table` | Sortable, filterable tables with zero dependencies. |
| `/timeline` | Gantt-style timelines via vis-timeline. |

### Building

| Skill | What it does |
|---|---|
| `/build-python-library` | pip-installable Python packages with src layout, pyproject.toml, pytest. |
| `/develop-board-game` | Digital board games as single-file HTML/JS/CSS with Playwright tests. |
| `/init-github-repo` | New repo with README, CI/CD, license, .gitignore, SEO topics. |

### Documents

| Skill | What it does |
|---|---|
| `/docx` | Create, read, edit Word documents — TOCs, tracked changes, templates. |
| `/pptx` | Create, read, edit PowerPoint presentations. |
| `/xlsx` | Create, read, edit spreadsheets — formulas, charts, data cleaning. |

### Reports

| Skill | What it does |
|---|---|
| `/ci-health-report` | CI/CD health, build failures, flaky tests, success rates. |
| `/code-quality-trends` | Tech debt, TODO growth, test coverage, PR size distribution. |
| `/dora-lite-report` | DORA metrics — deployment frequency, lead time, change failure rate, MTTR. |
| `/deploy-status-report` | Deployment status, canary results, pending rollouts. |
| `/dependency-audit` | Outdated packages, CVEs, security vulnerabilities. |
| `/ml-pipeline-report` | ML pipeline health, flow status, failed runs. |
| `/pipeline-health-report` | Data pipeline health, workflow status, failures. |
| `/slack-digest` | Weekly Slack digest, key discussions, channel activity. |
| `/sprint-retro` | Sprint retrospective from GitHub, Slack, Jira, Confluence data. |
| `/user-activity-report` | What someone's been working on — prep for 1:1s. |
| `/platform-friction-detector` | Scan for silent user workarounds around your libraries. |

### Meta

| Skill | What it does |
|---|---|
| `/create-skill` | Scaffold new skills via RED-GREEN-REFACTOR pressure testing. |
| `/magic-fetch` | Log capability gaps for a prioritized integration roadmap. |
| `/goal-manager` | Track multi-session goals and detect drift. |
| `/update-stop-gate` | Add behavior patterns to the stop-gate autonomy rules. |
| `/retrospect` | Session retrospective — scan for failures and propose patches. |
| `/nap` | Context compactor — prune old runs, archive stale memory. |
| `/ccr-run` | Route tasks to any model via claude-code-router. |
| `/ccr-models` | List available models in claude-code-router. |
| `/monitor` | Health checking for services, pipelines, code, deployments. |

## Cross-Model Critics

Deep-qa and deep-debug can spawn critics on non-Claude models (GPT, Gemini) for blind-spot diversity. This requires an OpenAI-compatible endpoint. Set these env vars:

```bash
export CRITIC_BASE_URL="https://your-openai-compatible-endpoint/v1"
export CRITIC_API_KEY="your-key"
```

Or set them in Claude Code's `settings.json` under `env`. Falls back to `OPENAI_BASE_URL` / `OPENAI_API_KEY`. Disable with `--no-cross-model`.

## Design Principles

- **Independent judges for load-bearing evaluations.** No skill trusts its own output — severity scoring, plausibility checks, and rationalization audits all use separate agents.
- **File-based state.** Every run writes to a directory. Crash mid-run? Resume from the last checkpoint.
- **Composable bottom-up.** `/autopilot` delegates to `/deep-plan` which delegates to `/deep-qa`. Each layer works standalone.
- **Anti-rationalization.** Skills include counter-tables that map common rationalizations to their rebuttals, making it harder for Claude to talk itself out of following the workflow.

## Contributing

1. Fork the repository
2. Use `/create-skill` to scaffold and pressure-test your skill
3. Submit a PR

## License

[Apache 2.0](LICENSE)
