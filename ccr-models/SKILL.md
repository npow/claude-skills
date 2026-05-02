---
name: ccr-models
description: Use when the user asks "what models are available", "list models", "show models", or wants to see which LLM models are accessible via claude-code-router.

category: tool
capabilities: [backoff-retry]
input_types: [code-path]
output_types: [code, data]
complexity: moderate
cost_profile: low
maturity: beta
metadata_source: inferred
---

## Prerequisites

Requires [claude-code-router](https://github.com/npow/claude-code-router) running (`ccr start`).

## Instructions

Run this command and display the output to the user:

```bash
curl -s http://127.0.0.1:3456/v1/models -H 'x-api-key: test' | python3 -c "
import sys, json
d = json.load(sys.stdin)
models = [m for m in d['data'] if ',' in m['id']]
claude = [m for m in models if m['id'].startswith('claude,')]
gateway = [m for m in models if m['id'].startswith('gateway,')]
print('CLAUDE (claudecode proxy, no rate limits):')
for m in claude: print(f'  {m[\"id\"]}')
print()
print('GATEWAY (Model Gateway - OpenAI + Gemini):')
for m in gateway: print(f'  {m[\"id\"]}')
"
```

See [`_shared/ccr-shortcuts.md`](../_shared/ccr-shortcuts.md) for the model shortcut table.

If the curl fails (connection refused), tell the user to start the router with `ccr start`.
