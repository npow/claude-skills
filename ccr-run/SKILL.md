---
name: ccr-run
description: "Use when the user asks to run a task on a specific model, compare model outputs, or says 'run this on GPT/Gemini/Sonnet'. Routes tasks to any model via claude-code-router. Usage: /ccr-run [model] <task>"

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

See [`_shared/ccr-shortcuts.md`](../_shared/ccr-shortcuts.md) for the model shortcut table.

If no model is identified, use AskUserQuestion with these options:
- "codex" — GPT-5.3 Codex (code generation)
- "gemini" — Gemini 2.5 Pro (long context, multimodal)
- "gpt" — GPT-5.4 (general purpose)
- "o3" — O3 (deep reasoning)

## Step 2: Spawn the subagent

Spawn an Agent. Place this tag at the very START of the agent's prompt (before anything else):

<CCR-SUBAGENT-MODEL>{resolved model ID}</CCR-SUBAGENT-MODEL>

Then include the user's task as the rest of the prompt. The tag is stripped by the router before the model sees it.
