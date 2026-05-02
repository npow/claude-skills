# Standard Config Resolution Pattern

All report skills follow the same configuration lifecycle. Each skill defines its own schema (field names, types, defaults), but the resolution logic is identical.

## Config File Location

`~/.claude/skills/{skill-name}/config.json`

## Resolution Order (first match wins)

1. **User's explicit arguments in the prompt** override everything
2. **config.json** defaults (read from the path above)
3. **Built-in defaults** defined in the skill's Arguments section

## Required Scope

Every report skill requires at least one "scope" field to be set — the field(s) that determine what the report covers (e.g., repos, apps, flows, channel IDs, owners). The skill's Arguments section documents which fields are scope fields.

If no scope is set (neither in the prompt nor in config.json), the skill must:

1. **Ask once** — prompt the user for the missing scope value(s)
2. **Save to config.json** — write the user's answer so future runs (including scheduled runs) don't need to ask again
3. **Never block silently** — do not proceed with an empty scope and produce an empty report

## Config File Format

The config file is always a flat JSON object. Example skeleton:

```json
{
  "<scope_field>": "<value or array>",
  "lookback_days": 7
}
```

Each skill's SKILL.md specifies the exact field names and types in its **Arguments** section.

## Implementation Notes

- **Scheduled runs** depend on config.json existing. The "ask once and save" behavior ensures the first interactive run bootstraps the config for all future automated runs.
- **Merging, not replacing.** When saving a new field to config.json, read the existing file first and merge — never overwrite unrelated fields.
- **Validation.** If config.json exists but is malformed (invalid JSON, wrong types), warn the user and fall back to prompting, rather than crashing silently.
