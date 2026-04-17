# Phase 6: Package

Generate README, LICENSE, .gitignore. Verify packaging metadata. Run the clean-install reproducibility gate. Spawn three independent judges (correctness, security, quality) for final validation. Aggregate verdicts mechanically. Write the completion report.

## Process

### Step 1: Generate README.md

Structure (adapt to project type):

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

Do NOT pad with badges, contribution guidelines, or boilerplate. Install + usage matters more than a badge wall.

README generation routes through a `/loop-until-done` call (one-story PRD: "Generate README.md per the Ship-It schema; verify install commands actually work"). This keeps the quality judge's audit honest — the README is reviewed the same way everything else is.

### Step 2: LICENSE, .gitignore, manifest

1. Write LICENSE (MIT by default unless SPEC.md specified otherwise).
2. Write .gitignore standard for tech stack:
   - Node: `node_modules/`, `dist/`, `.env`, `*.log`, `coverage/`
   - Python: `__pycache__/`, `*.pyc`, `.venv/`, `dist/`, `build/`, `*.egg-info/`
3. Verify `package.json` / `pyproject.toml`:
   - `name` matches intended package name
   - `version` is `0.1.0`
   - `bin` entry exists if CLI (`"bin": { "tool-name": "dist/cli.js" }`)
   - `files` array includes only `dist/` (not `src/`, `test/`)
   - `scripts` include: build, test, start
   - `main` / `exports` point to correct entry
   - `type: "module"` if ESM
4. All metadata changes route through `/loop-until-done` (not coordinator hand-edit) — a one-story PRD with the verification command being the clean-install run below.

### Step 3: Clean install test (THE REPRODUCIBILITY GATE)

This is the hardest gate. Run from a truly clean state:

```bash
# Node
rm -rf node_modules dist
npm install
npm run build
npm test
```

```bash
# Python
rm -rf .venv dist build *.egg-info
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Capture full output at `ship-it-{run_id}/package/clean-install-output.txt`. Every step must exit 0.

If any step fails: synthesize a one-story PRD and invoke `/loop-until-done --max-iter=3`. Do NOT paper over flaky or transient failures; re-run until deterministic pass OR investigate the flakiness.

### Step 4: Git init

```bash
git init
git add -A
git commit -m "Initial commit: [product name] MVP"
```

Do NOT push to remote unless user explicitly requests.

### Step 5: Entry-point final check

For CLI:
```bash
node dist/cli.js --help    # Must print usage info
```

For MCP servers:
```bash
timeout 5 node dist/cli.js --connection fake://fake 2>&1 || true
# Should show "connecting" or "error: connection failed" — not a crash/stack trace
```

Capture output as evidence.

### Step 6: Three-judge validation

This is Phase 6's final gate. The three judges are fresh Agent invocations with no shared context, no coordinator orchestration.

1. Write `ship-it-{run_id}/package/judge-input.md` per [FORMAT.md](FORMAT.md). Contains ONLY file paths.
2. Update `state.json`: write `spawn_time_iso` for each judge separately (three writes; three independent pre-records).
3. **Spawn three judges in parallel**:
   - `correctness_judge` → writes `package/correctness-verdict.md`
   - `security_judge` → writes `package/security-verdict.md`
   - `quality_judge` → writes `package/quality-verdict.md`
4. Judge prompts are in the main SKILL.md "Judge Prompt Templates" section. Each judge reads input paths from the judge-input file itself (not from the coordinator's context).
5. After all three verdicts are on disk, coordinator reads them and writes `package/aggregation.md` using the mechanical aggregation rule from [FORMAT.md](FORMAT.md). NO commentary, NO rationale — just the rule applied verbatim.

### Step 7: Handle rejection

If any judge returns `VERDICT|rejected`:

1. Extract the blocking scenarios from the rejected verdict.
2. Synthesize each scenario into an acceptance criterion with the judge's suggested verification command.
3. Write the PRD at `ship-it-{run_id}/package/revalidation-{N}/prd.json`.
4. Invoke `/loop-until-done --prd <path> --max-iter=2 --critic=deep-qa`.
5. After the fix loop, rename current verdict files to `{dimension}-verdict.v{N}.md`, increment `phases.package.revalidation_round`.
6. **Re-spawn FRESH judge agents** for round N+1. NEVER reuse the rejecting judge — stale context.
7. Maximum 2 re-validation rounds. After 2 rounds still-rejected: gate fails; terminate as `blocked_at_phase_6`.

### Step 8: Completion report

After `AGGREGATE|approved` (or `conditional` with user-acknowledged conditions):

1. Update `state.json`: `current_phase: "cleanup"`.
2. Spawn a completion-report subagent that reads all Phase 1–6 evidence files and writes `ship-it-{run_id}/completion-report.md` per the schema in [FORMAT.md](FORMAT.md).
3. Report MUST include:
   - Termination label (mechanical — `complete` iff all structured fields check out)
   - Shipped items (verified fresh this session)
   - Unverified items (stale, missing, or cannot_evaluate)
   - Accepted tradeoffs (from earlier phases)
   - Files modified
   - Evidence manifest
   - Degraded mode notes (if any)
   - Shipping commands (publish, push)
4. Report is written BEFORE any state deletion.
5. Coordinator prints the completion-report path and the termination label verbatim.
6. State deletion is optional and gated. If `TERMINATION|complete`, offer to delete `ship-it-{run_id}/`. Otherwise preserve the full tree for resume.

## Iron-law gate (Phase 6 final)

Required:
- `package/clean-install-output.txt` — every step exit 0
- `package/correctness-verdict.md`, `package/security-verdict.md`, `package/quality-verdict.md` — all parseable
- `package/aggregation.md` with `AGGREGATE ∈ {approved, conditional}`
- `package/phase-gate.md` with `ADVANCE: true`
- Git repo initialized with initial commit
- `completion-report.md` exists with parseable structured block

`AGGREGATE|rejected` after 2 re-validation rounds → `ADVANCE: false` → terminate as `blocked_at_phase_6`.

## What "done" looks like

When all six phase gates pass AND Phase 6 aggregation is `approved` (not `conditional`) AND `UNVERIFIED_COUNT == 0` AND `ACCEPTED_TRADEOFFS_COUNT == 0`, tell the user:

```
Ship It: complete

Project: [path]
Completion report: [ship-it-{run_id}/completion-report.md]

Summary:
- [X] source files, [Y] test files
- [Z] tests passing
- Clean install verified
- 3/3 judges approved

To publish:
  npm publish          # to npm
  # or
  pip publish          # to PyPI

To push to GitHub:
  git remote add origin [url]
  git push -u origin main
```

If `partial_with_accepted_tradeoffs`, list the tradeoffs verbatim from the completion report — do not soften.

If `blocked_at_phase_N` or `budget_exhausted`, state the label and the blocking reason verbatim — do not paraphrase into optimism.
