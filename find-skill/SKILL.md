---
name: find-skill
description: Search across all installed skills (user + plugin) by keyword to discover relevant skills whose descriptions may have been truncated from the main listing. Use when the user references a skill by partial/fuzzy name, asks "is there a skill for X?", or when the main skill listing seems incomplete. Trigger phrases include "find a skill", "is there a skill for", "search skills", "what skill does X", "find skill", "skill search", "look for a skill", "any skill that handles".
---

# find-skill

Searches `~/.cache/claude-skill-index.json` (built by the `inject-skill-hints` hook) across all SKILL.md files in `~/.claude/skills/` and `~/.claude/plugins/`. Returns matches with full descriptions, scores, and paths.

## When to use

- User asks "is there a skill for X?" or names a skill fuzzily ("the kafka skill")
- Main skill listing has truncated descriptions and you suspect a relevant skill exists but you can't see its trigger phrases
- You want to discover skills before committing to a manual approach

## How to use

Run the CLI:

```bash
python3 ~/.claude/skills/find-skill/find_skill.py <query terms>
```

**Flags:**
- `--limit N` — max results (default 10)
- `--full` — show full descriptions (default truncates to 200 chars)
- `--rebuild` — force index rebuild (otherwise cached for 24h)

**Output:** ranked list with score, namespaced ID (e.g. `ods-datastores:wal-observability`), description, and path.

## Examples

```bash
# Find anything related to GPU queues
python3 ~/.claude/skills/find-skill/find_skill.py gpu queue capacity

# Search for kafka-related skills with full descriptions
python3 ~/.claude/skills/find-skill/find_skill.py --full kafka

# Force a fresh index rebuild after installing new skills
python3 ~/.claude/skills/find-skill/find_skill.py --rebuild metaflow
```

## Scoring

- +1 per query keyword that appears in the skill's description tokens
- +3 per query keyword that appears in the skill name
- +1 per query keyword that appears as a substring of the description

Skills with the same leaf name (after `:`) are deduped; cache/ entries (authoritative plugin IDs) are preferred over marketplaces/ entries.

## Once you find a relevant skill

Invoke it via the Skill tool:

```
Skill(skill="<namespaced-id>")
```

If the ID has spaces or special characters that don't match a Skill tool entry, the listing in your conversation's system reminder is authoritative — cross-reference there.

## Related

- `~/.claude/hooks/inject-skill-hints.py` — UserPromptSubmit hook that auto-surfaces top matches on every prompt; this skill is the manual companion for explicit search.
