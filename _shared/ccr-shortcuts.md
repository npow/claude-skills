# CCR Model Shortcuts

Canonical shortcut table for [claude-code-router](https://github.com/npow/claude-code-router). Used by both `/ccr-models` and `/ccr-run`.

**Shortcuts** (case-insensitive):
| Shortcut | Model ID |
|----------|----------|
| codex | gateway,gpt-5.3-codex |
| gpt | gateway,gpt-5.4 |
| gpt-mini | gateway,gpt-5.4-mini |
| gpt-nano | gateway,gpt-5.4-nano |
| gpt-pro | gateway,gpt-5.4-pro |
| 4o | gateway,gpt-4o |
| 4.1 | gateway,gpt-4.1 |
| gemini | gateway,gemini-2.5-pro |
| flash | gateway,gemini-2.5-flash |
| o3 | gateway,o3 |
| o3-pro | gateway,o3-pro |
| o3-mini | gateway,o3-mini |
| o4 | gateway,o4-mini |
| o1 | gateway,o1 |
| opus | claude,claude-opus-4-7 |
| sonnet | claude,claude-sonnet-4-6 |
| haiku | claude,claude-haiku-4-5-20251001 |

Any `gateway,*` or `claude,*` string is treated as a full model ID directly.
