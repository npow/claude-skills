# claude-skills

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

Make Claude Code do complex multi-step workflows reliably with a single slash command.

## The problem

Claude Code is powerful, but complex tasks — scaffolding a Python library, initializing a GitHub repo with CI/CD, diagnosing flaky tests — require careful prompting and domain knowledge that gets lost between sessions. You end up re-explaining the same workflows, catching the same mistakes, and missing the same steps.

## Skills

| Skill | Trigger | What it does |
|-------|---------|-------------|
| **build-python-library** | `/build-python-library` | Scaffolds pip-installable Python packages with src layout, pyproject.toml, and pytest |
| **create-skill** | `/create-skill` | Builds new Claude Code skills with table-of-contents architecture and self-review loops |
| **develop-board-game** | `/develop-board-game` | Creates faithful digital board games as single-file HTML/JS/CSS apps with Playwright tests |
| **flaky-test-diagnoser** | `/flaky-test-diagnoser` | Runs multi-run experiments, isolation tests, and timing analysis to diagnose test flakiness |
| **gap-finder** | `/gap-finder` | Generates product ideas in batches, validates against real competitors, kills weak ones |
| **init-github-repo** | `/init-github-repo` | Initializes repos with JTBD README, CI/CD, license, .gitignore, and SEO-optimized metadata |
| **prod-readiness** | `/prod-readiness` | Scans codebases for 24 production readiness items and produces a scored report |
| **proposal-reviewer** | `/proposal-reviewer` | Reviews proposals for viability, fact-checks claims, maps competitive landscape |
| **ship-it** | `/ship-it` | Takes a product idea through design, build, test, integrate, and package phases |

## Install

Copy or symlink individual skills into `~/.claude/skills/`:

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

Once installed, invoke any skill by typing its name as a slash command in Claude Code:

```
/init-github-repo
/build-python-library
/ship-it
```

Each skill includes a `SKILL.md` with the workflow, golden rules, and a self-review checklist.

## How it works

Each skill is a directory containing markdown files that Claude Code loads as context:

- `SKILL.md` — Main entry point with workflow steps, golden rules, and self-review checklist
- Additional `.md` files — Reference material for specific phases (templates, patterns, examples)

Skills use a table-of-contents architecture: the main `SKILL.md` links to reference files so Claude loads detailed context only when needed.

## Development

```bash
# Edit skills in place
vim ~/.claude/skills/build-python-library/SKILL.md

# Commit and push
cd ~/.claude/skills
git add -A && git commit -m "Update build-python-library"
git push
```

## License

[Apache 2.0](LICENSE)
