---
name: pr-status
description: Check open PRs for a GitHub user — status, CI/Jenkins checks, failing tests with counts and grouped failure categories. Use when asked about someone's PRs, CI status, test failures, or PR health.
compatibility: gh CLI (GHE-authenticated)
allowed-tools: ["Bash(${CLAUDE_SKILL_DIR}/scripts/*:*)", "Bash(gh:*)"]
---

# PR Status Check

## Quick Start

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/pr_status.py --user USERNAME
# Or for a specific repo:
python3 ${CLAUDE_SKILL_DIR}/scripts/pr_status.py --user USERNAME --repo corp/mli-metaflow-custom
# Or check a single PR directly:
python3 ${CLAUDE_SKILL_DIR}/scripts/pr_status.py --pr 1843 --repo corp/mli-metaflow-custom
```

The script outputs JSON with PR metadata, CI check status, and netflix-octocat bot test summaries.

## Analyzing Results

### CI Checks

The script includes `checkSummary` per PR with passing/failing/pending counts and a `checks` array with per-check details. Map check conclusions:
- `SUCCESS` → passing
- `FAILURE` → failing
- `PENDING`/`QUEUED` → in progress
- `CANCELLED`/`SKIPPED` → not run

### Test Failures

The `botComment` field contains the netflix-octocat test summary. Parse it for:
- Pass/fail/skip counts
- Failed test names and modules

If the bot comment lacks detail or is missing, dig deeper:

1. **Metaflow pytest report** — extract `mftest_group:TAG` from the bot comment, then use the `get_pytest_report` MCP tool
2. **Jenkins console** — use `jenkins-plugin:jenkins` skill with the build URL from the check's `detailsUrl`
3. **PR check output** — `gh api repos/ORG/REPO/check-runs/ID --hostname github.netflix.net --jq '.output'`

### Grouping Failures

Group test failures by:
1. **Module** — test directory (e.g., `test/algo_commons`, `test/core`)
2. **Error class** — exception type (`AssertionError`, `ImportError`, `TimeoutError`)
3. **Pattern** — recurring error message substring across tests

### Presentation

Summary table first, then details for PRs with failures:

```
PR #NUM: TITLE (repo)
  Branch: head → base | Draft/Open | Reviews: STATE | Mergeable: Y/N
  Size: +A/-D across N files

  CI: X/Y passing, Z failing, W pending
  | Check         | Status | Link    |
  |---------------|--------|---------|
  | Jenkins #1234 | FAIL   | url     |

  Tests: P passed, F failed, S skipped
  Failures by module:
    test/module_a (N):
      - test_name: ErrorType — message
    test/module_b (M):
      - test_name: ErrorType — message
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--user` | current gh user | GitHub username to check |
| `--repo` | all repos | Restrict to one repo |
| `--pr` | (none) | Check a single PR number (requires `--repo`) |
| `--host` | github.netflix.net | GHE hostname |
| `--no-checks` | checks on | Skip CI check fetching |
| `--no-comments` | comments on | Skip bot comment fetching |
