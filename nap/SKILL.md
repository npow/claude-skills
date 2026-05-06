---
name: nap
description: Context compactor — prunes old sagaflow runs, archives stale memory files, compacts MEMORY.md indexes, compresses aimee journals. Like Squad's `squad nap` but for our Claude Code setup.
user_invocable: true
argument: |
  [--deep] [--dry-run]
category: meta
---

# nap

Compact Claude Code context state to free disk and reduce token load.

## Usage

When invoked, run the nap script:

```bash
python3 ~/code/npow-dotfiles/scripts/nap.py [flags]
```

### Flags from user args

- If the user says `--dry-run` or "dry run" or "what would it do": add `--dry-run`
- If the user says `--deep` or "deep" or "aggressive": add `--deep`
- If no flags specified: run with `--dry-run` first, show the report, then run for real

### What it does

1. **PRUNE** — deletes sagaflow run dirs older than 7 days (3 with --deep)
2. **COMPACT** — removes dead pointers from MEMORY.md index files
3. **ARCHIVE** — moves memory files not touched in 30 days (14 with --deep) to `archive/` subdirs
4. **COMPRESS** — archives old aimee journal entries (>7 days or >50KB; >3 days or >20KB with --deep)

### Workflow

1. Run with `--dry-run` first unless the user explicitly said to just do it
2. Show the report output to the user
3. If dry-run, ask once: "Run it for real?" — then execute without `--dry-run`
4. Show the final report
