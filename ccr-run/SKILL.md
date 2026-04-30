---
name: ccr-run
description: "Run a task on any model via claude-code-router. Usage: /ccr-run [model] <task>"

category: tool
input_types: [task, question, code-path]
output_types: [code]
complexity: moderate
cost_profile: low
maturity: beta
metadata_source: inferred
---

You are a model router. Parse the user's input to determine the model and task.

## Prerequisites

Requires [claude-code-router](https://github.com/npow/claude-code-router) running (`ccr start`). See `/ccr-models` to list available models.

## Step 1: Resolve the model

Check if the FIRST word matches a shortcut or full model ID. If it does, use that model and treat the rest as the task. If it doesn't match anything below, treat the ENTIRE input as the task and use AskUserQuestion to let the user pick a model.

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

If no model is identified, use AskUserQuestion with these options:
- "codex" — GPT-5.3 Codex (code generation)
- "gemini" — Gemini 2.5 Pro (long context, multimodal)
- "gpt" — GPT-5.4 (general purpose)
- "o3" — O3 (deep reasoning)

## Step 2: Spawn the subagent

Spawn an Agent. Place this tag at the very START of the agent's prompt (before anything else):

<CCR-SUBAGENT-MODEL>{resolved model ID}</CCR-SUBAGENT-MODEL>

Then include the user's task as the rest of the prompt. The tag is stripped by the router before the model sees it.
