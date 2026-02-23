# README Template

How to write a JTBD-focused README with badges, structured for GitHub rendering.

## Contents
- README structure
- Badge templates
- Writing rules per section
- Examples of JTBD vs feature-list openings
- Failure diagnosis

## README structure

Every README follows this exact section order:

```markdown
# package-name

[badges line]

[One-sentence JTBD hook — what problem does this solve for the reader?]

## The problem

[2-3 sentences: the pain point, who has it, why existing solutions fall short]

## Quick start

[Shortest possible path from zero to working — install + one usage example]

## Install

[All install methods: pip/npm/cargo, from source, optional deps]

## Usage

[2-3 concrete examples showing the most common use cases]

## How it works

[Brief architecture explanation — only if the mechanism matters to the user]

## Configuration

[Only if there are user-facing config options]

## Development

[For contributors: clone, install dev deps, run tests]

## License

[One line: license name + link to LICENSE file]
```

Rules:
- "The problem" comes before "Quick start" — the reader must know WHY before HOW
- "Quick start" is the absolute minimum to get running — 3-5 lines of code max
- No "Features" section. Features are demonstrated through usage examples, not bullet lists
- No "Table of Contents" unless the README exceeds 300 lines
- No "Contributing" section unless the project has specific contribution rules

## Badge templates

Badges go on one line directly under the H1 title. Use shields.io format.

### Python project (pyproject.toml detected)

```markdown
[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/PACKAGE)](https://pypi.org/project/PACKAGE/)
[![License: LICENSE_SPDX](https://img.shields.io/badge/License-LICENSE_SPDX-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
```

Replace:
- `OWNER/REPO` → from `gh repo view --json nameWithOwner -q .nameWithOwner` or the directory name + git remote
- `PACKAGE` → from `[project].name` in pyproject.toml
- `LICENSE_SPDX` → from `[project].license` in pyproject.toml (e.g., `Apache--2.0`, `MIT`)
- Python version → from `[project].requires-python` in pyproject.toml

### Node.js project (package.json detected)

```markdown
[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)
[![npm](https://img.shields.io/npm/v/PACKAGE)](https://www.npmjs.com/package/PACKAGE)
[![License: LICENSE_SPDX](https://img.shields.io/badge/License-LICENSE_SPDX-blue.svg)](LICENSE)
[![Node.js 18+](https://img.shields.io/badge/node-18+-blue.svg)](https://nodejs.org/)
```

Replace:
- `PACKAGE` → from `name` in package.json
- `LICENSE_SPDX` → from `license` in package.json

### Rust project (Cargo.toml detected)

```markdown
[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)
[![Crates.io](https://img.shields.io/crates/v/PACKAGE)](https://crates.io/crates/PACKAGE)
[![License: LICENSE_SPDX](https://img.shields.io/badge/License-LICENSE_SPDX-blue.svg)](LICENSE)
```

### Go project (go.mod detected)

```markdown
[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)
[![Go Reference](https://pkg.go.dev/badge/MODULE_PATH.svg)](https://pkg.go.dev/MODULE_PATH)
[![License: LICENSE_SPDX](https://img.shields.io/badge/License-LICENSE_SPDX-blue.svg)](LICENSE)
```

Replace `MODULE_PATH` → from `module` line in go.mod.

## Writing rules per section

### The one-sentence hook (directly under badges)

This is the most important line. It must:
- Be one sentence, under 20 words
- State what job the reader can accomplish, not what the tool is
- Use "you" — address the reader directly

| Bad (describes the tool) | Good (describes the job) |
|---|---|
| "A Python library for memory integrity defense" | "Stop memory poisoning attacks on your AI agents" |
| "Fast, lightweight HTTP server framework" | "Ship HTTP APIs in Python without the boilerplate" |
| "CLI tool for managing Docker containers" | "Run your Docker stack with one command" |
| "A comprehensive testing framework" | "Find bugs before your users do" |

### The problem section

2-3 sentences answering:
1. What situation is the reader in? (context)
2. What goes wrong? (pain)
3. Why can't they solve it with what exists? (gap)

Must NOT mention the tool name. This section is entirely about the reader's world.

### Quick start

The minimum viable example:
1. Install command (one line)
2. Usage code (3-5 lines max)
3. Expected output (if applicable)

No explanations. No options. No edge cases. Just the shortest path from zero to "it works."

### Usage section

2-3 examples, each showing a different use case. Each example has:
1. A one-line description of what it demonstrates
2. A code block
3. (Optional) expected output

No prose between examples. The code speaks for itself.

## Examples: JTBD vs feature-list openings

### Bad: feature-list opening

```markdown
# memshield

MemShield is a Python library that provides memory integrity defense for AI agents.

## Features

- Consensus validation on memory reads
- Cryptographic provenance tracking
- Behavioral drift detection
- Support for LangGraph, Chroma, OpenAI, Ollama
- Provider-agnostic LLM interface
```

### Good: JTBD opening

```markdown
# memshield

[![CI](...)][...]

Stop memory poisoning attacks on your AI agents.

## The problem

When an attacker poisons your agent's memory — its RAG knowledge base or conversation history —
every future decision is compromised. Unlike prompt injection, memory poisoning is a one-time attack
with permanent effect. No production defense tool exists today.
```

## Failure diagnosis

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Badge shows "not found" on GitHub | OWNER/REPO slug is wrong in the badge URL | Run `gh repo view --json nameWithOwner` and use the actual value |
| PyPI badge shows "unknown" | Package not yet published to PyPI | This is expected for new projects — badge will resolve after first publish |
| README looks wrong on GitHub | Markdown rendering differences between local and GitHub | Check for bare URLs (wrap in angle brackets), HTML in markdown (GitHub strips some), and relative link paths |
| README is too long (>300 lines) | Too much detail in Usage or Configuration sections | Move detailed examples to a `docs/` directory and link from README |
| If none of the above | View the README raw on GitHub (`?plain=1` URL parameter) and compare to local file |
