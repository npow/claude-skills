#!/usr/bin/env python3
"""Cross-model critic for deep-qa: sends an angle + artifact to a non-Claude model via MGP.

Usage:
    python3 cross-model-critic.py \
        --angle-file deep-qa-run/angles/angle-1.md \
        --artifact-file deep-qa-run/artifact.md \
        --output-file deep-qa-run/critiques/angle-1-gpt.md \
        --model gpt-5.4 \
        --known-defects-file deep-qa-run/known-defects.md

Models route through Netflix Model Gateway (MGP) OpenAI-compatible endpoint.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

MGP_BASE = os.environ.get(
    "OPENAI_BASE_URL",
    "http://mgp.local.dev.netflix.net:9123/proxy/npowws/v1",
)
MGP_KEY = os.environ.get("OPENAI_API_KEY", "sk-dummy")

MAX_ARTIFACT_CHARS = 120_000
MAX_COMPLETION_TOKENS = 16_384
TIMEOUT_SECONDS = 120

SYSTEM_PROMPT = """\
You are an independent code critic performing adversarial quality review.
You have NO prior context about this codebase's history, design decisions, or ongoing work.
Review purely based on what you see. Flag anything that appears problematic.
Your findings will be validated by a senior engineer with full context.

Output format — one defect per block, using EXACTLY this structure:

DEFECT|<id>|<severity>|<dimension>|<title>
<description>
EVIDENCE: <specific code or pattern>
AUTHOR_COUNTER: <strongest argument that this is intentional>
---

Severity: critical, major, minor
If no defects found for this angle, output: NO_DEFECTS|<dimension>|<reason>

Do NOT soften findings. Do NOT assume patterns are intentional. Report everything.\
"""


def read_file(path: str, max_chars: int = 0) -> str:
    with open(path, "r") as f:
        content = f.read()
    if max_chars and len(content) > max_chars:
        content = content[:max_chars] + f"\n\n[TRUNCATED at {max_chars} chars]"
    return content


def call_mgp(model: str, messages: list[dict], temperature: float = 0.7) -> str:
    url = f"{MGP_BASE}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
        "temperature": temperature,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MGP_KEY}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"MGP HTTP {e.code}: {body[:500]}", file=sys.stderr)
        raise
    except urllib.error.URLError as e:
        print(f"MGP connection error: {e.reason}", file=sys.stderr)
        raise


def main():
    parser = argparse.ArgumentParser(description="Cross-model critic for deep-qa")
    parser.add_argument("--angle-file", required=True)
    parser.add_argument("--artifact-file", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--model", default="gpt-5.4")
    parser.add_argument("--known-defects-file", default="")
    parser.add_argument("--temperature", type=float, default=0.7)
    args = parser.parse_args()

    angle = read_file(args.angle_file)
    artifact = read_file(args.artifact_file, max_chars=MAX_ARTIFACT_CHARS)

    known_defects = ""
    if args.known_defects_file and os.path.exists(args.known_defects_file):
        known_defects = read_file(args.known_defects_file)

    user_msg = f"## QA Angle\n\n{angle}\n\n"
    if known_defects:
        user_msg += f"## Already-Known Defects (do NOT re-report these)\n\n{known_defects}\n\n"
    user_msg += f"## Artifact Under Review\n\n{artifact}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    print(f"Calling {args.model} via MGP...", file=sys.stderr)
    response = call_mgp(args.model, messages, temperature=args.temperature)

    header = f"# Cross-Model Critique ({args.model})\n\n"
    with open(args.output_file, "w") as f:
        f.write(header + response)

    print(f"Wrote {len(response)} chars to {args.output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
