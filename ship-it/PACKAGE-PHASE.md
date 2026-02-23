# Phase 6: Package

Generate documentation, packaging, and verify the project works from a clean install.

## Process

### Step 1: Generate README.md

Use this structure (adapt to project type):

```markdown
# [Product Name]

[One-liner from SPEC.md]

## Quick Start

[Shortest possible path to using the product — 1-3 commands]

## Installation

[npm install / pip install / npx command]

## Usage

[2-3 concrete examples showing the main features]

## Configuration

[Environment variables, config files, connection strings]

## API / Tools

[For MCP: table of tools with inputs/outputs]
[For CLI: table of commands with flags]
[For library: key functions with signatures]

## Development

[How to clone, install, build, test]

## License

MIT
```

Do NOT pad the README with badges, contribution guidelines, or boilerplate until the product actually has users. A clear install + usage section matters more than a pretty badge wall.

### Step 2: Generate LICENSE

Write the MIT license file (or whatever was specified in SPEC.md).

### Step 3: Generate .gitignore

Standard for the tech stack:
- `node_modules/`, `dist/`, `.env` for TypeScript/Node
- `__pycache__/`, `*.pyc`, `.venv/`, `dist/` for Python

### Step 4: Verify package.json / pyproject.toml

Check:
- `name` matches the intended package name
- `version` is `0.1.0`
- `bin` entry exists if it's a CLI (`"bin": { "tool-name": "dist/cli.js" }`)
- `files` array includes only dist/ (not src/, test/, etc.)
- `scripts` include: build, test, start (if applicable)
- `main` / `exports` point to the correct entry file
- `type: "module"` if using ESM

### Step 5: Clean install test (THE FINAL GATE)

This is the most important step. Run:

```bash
# Save current state
cp -r node_modules node_modules_backup 2>/dev/null

# Clean install test
rm -rf node_modules dist
npm install
npm run build
npm test

# Restore if needed
rm -rf node_modules
mv node_modules_backup node_modules 2>/dev/null
```

For Python:
```bash
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

If this fails, the project is NOT shippable. Fix whatever broke and re-run.

### Step 6: Verify the CLI / entry point works

For CLI tools:
```bash
node dist/cli.js --help    # Must print usage info
```

For MCP servers:
```bash
# Start and immediately kill — verifies it doesn't crash on startup
timeout 5 node dist/cli.js --connection postgres://fake 2>&1 || true
# Should see "connecting" or "error: connection failed" — not a crash/stack trace
```

### Step 7: Initialize git repo

```bash
git init
git add -A
git commit -m "Initial commit: [product name] MVP"
```

Do NOT push to remote unless the user explicitly asks.

## Gate

Phase 6 passes when:
- [ ] README.md exists with install + usage sections
- [ ] LICENSE file exists
- [ ] .gitignore exists
- [ ] Clean install + build + test passes
- [ ] Entry point runs without crashing
- [ ] Git repo initialized with initial commit

## What "done" looks like

When Phase 6 passes, tell the user:

```
Ship It complete. Project is at [path].

Summary:
- [X] source files, [Y] test files
- [Z] tests passing
- Clean install verified

To publish:
  npm publish          # to npm
  # or
  pip publish          # to PyPI

To push to GitHub:
  git remote add origin [url]
  git push -u origin main
```
