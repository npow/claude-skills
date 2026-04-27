---
name: ccr-models
description: List available models from claude-code-router

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
print()
print('SHORTCUTS for /ccr-run:')
for name, model in [('codex','gpt-5.3-codex'),('gpt','gpt-5.4'),('gpt-mini','gpt-5.4-mini'),('gpt-pro','gpt-5.4-pro'),('4o','gpt-4o'),('4.1','gpt-4.1'),('gemini','gemini-2.5-pro'),('flash','gemini-2.5-flash'),('o3','o3'),('o3-pro','o3-pro'),('o4','o4-mini'),('o1','o1'),('opus','claude-opus-4-7'),('sonnet','claude-sonnet-4-6'),('haiku','claude-haiku-4-5')]:
    print(f'  {name:10s} -> {model}')
"
```

If the curl fails (connection refused), tell the user to start the router with `ccr start`.
