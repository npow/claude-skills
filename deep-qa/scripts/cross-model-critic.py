#!/usr/bin/env python3
"""Cross-model critic for deep-qa: sends an angle + artifact to a non-Claude model.

Usage:
    python3 cross-model-critic.py \
        --angle-file deep-qa-run/angles/angle-1.md \
        --artifact-file deep-qa-run/artifact.md \
        --output-file deep-qa-run/critiques/angle-1-gpt.md \
        --model gpt-5.4 \
        --angle-id angle-1 \
        --dimension correctness \
        --mode code \
        --known-defects-file deep-qa-run/known-defects.md

Requires an OpenAI-compatible endpoint. Set CRITIC_BASE_URL and CRITIC_API_KEY env vars.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

CRITIC_BASE = os.environ.get("CRITIC_BASE_URL") or os.environ.get("OPENAI_BASE_URL", "")
CRITIC_KEY = os.environ.get("CRITIC_API_KEY") or os.environ.get("OPENAI_API_KEY", "")

MAX_ARTIFACT_CHARS = 120_000
MAX_COMPLETION_TOKENS = 16_384
TIMEOUT_SECONDS = 120

SYSTEM_PROMPTS = {
    "code": """\
You are an independent code critic performing adversarial quality review.
You have NO prior context about this codebase's history, design decisions, or ongoing work.
Review purely based on what you see. Flag anything that appears problematic.
Your findings will be validated by a senior engineer with full context.""",
    "doc": """\
You are an independent specification critic performing adversarial quality review.
You have NO prior context about this project's history, constraints, or decisions.
Review purely based on what you see. Flag ambiguities, contradictions, missing requirements,
unspecified error paths, and gaps that would cause divergent implementations.
Your findings will be validated by the specification owner.""",
    "research": """\
You are an independent research critic performing adversarial quality review.
You have NO prior context about this research topic or methodology.
Review purely based on what you see. Flag unsupported claims, methodological gaps,
missing evidence, logical fallacies, and conclusions that don't follow from the data.
Your findings will be validated by the research lead.""",
    "skill": """\
You are an independent skill/workflow critic performing adversarial quality review.
You have NO prior context about this skill's design intent or operational environment.
Review purely based on what you see. Flag workflow gaps, missing error handling,
ambiguous instructions, untested edge cases, and contract violations.
Your findings will be validated by the skill maintainer.""",
    "security": """\
You are an independent security critic performing adversarial review.
You have NO prior context about the threat model or security architecture.
Review purely based on what you see. Flag injection vectors, auth gaps, data exposure,
privilege escalation paths, and unsafe defaults.
Your findings will be validated by the security team.""",
}

OUTPUT_FORMAT = """\

Output format — for EACH defect found, use EXACTLY this markdown structure:

### Defect: {title}
**Severity:** critical | major | minor

**Scenario:**
A concrete, specific scenario demonstrating the defect. Not abstract — describe a real consumer
encountering the problem step by step.

**Root Cause:**
WHY this is broken. The underlying gap, assumption, or omission — not just the symptom.

**Suggested Remediation Direction (optional):**
How to address the root cause. Brief — the artifact owner decides how to fix it.

---

After all defects, include:

## New QA Angles Discovered
List 1-3 genuinely novel angles, or "None — this dimension is thoroughly covered."

## Mini-Synthesis
3+ sentences covering: what defect patterns this angle revealed, how they connect,
and what this changes about your understanding of the artifact's overall quality risks.

## Exhaustion Assessment
**Score: {1-5}**
1 = barely scratched the surface, 5 = fully QA'd
**What's missing (if score < 4):** specific gaps a follow-up pass should target

If no defects found, output "No defects found for this angle." and explain why in Mini-Synthesis.
Do NOT soften findings. Do NOT assume patterns are intentional. Report everything."""


def _check_config() -> None:
    if not CRITIC_BASE:
        print("CRITIC_BASE_URL (or OPENAI_BASE_URL) must be set.", file=sys.stderr)
        sys.exit(1)
    if not CRITIC_KEY:
        print("CRITIC_API_KEY (or OPENAI_API_KEY) must be set.", file=sys.stderr)
        sys.exit(1)


def read_file(path: str, max_chars: int = 0) -> str:
    with open(path, "r") as f:
        content = f.read()
    if max_chars and len(content) > max_chars:
        content = content[:max_chars] + f"\n\n[TRUNCATED at {max_chars} chars]"
    return content


def call_critic(model: str, messages: list[dict], temperature: float = 0.7) -> str:
    url = f"{CRITIC_BASE}/chat/completions"
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
            "Authorization": f"Bearer {CRITIC_KEY}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"Critic HTTP {e.code}: {body[:500]}", file=sys.stderr)
        raise
    except urllib.error.URLError as e:
        print(f"Critic connection error: {e.reason}", file=sys.stderr)
        raise


def main():
    parser = argparse.ArgumentParser(description="Cross-model critic for deep-qa")
    parser.add_argument("--angle-file", required=True)
    parser.add_argument("--artifact-file", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--model", default="gpt-5.4-pro")
    parser.add_argument("--angle-id", required=True)
    parser.add_argument("--dimension", required=True)
    parser.add_argument("--mode", default="code", choices=list(SYSTEM_PROMPTS.keys()))
    parser.add_argument("--known-defects-file", default="")
    parser.add_argument("--temperature", type=float, default=0.7)
    args = parser.parse_args()

    _check_config()
    angle = read_file(args.angle_file)
    artifact = read_file(args.artifact_file, max_chars=MAX_ARTIFACT_CHARS)

    known_defects = ""
    if args.known_defects_file and os.path.exists(args.known_defects_file):
        known_defects = read_file(args.known_defects_file)

    system_prompt = SYSTEM_PROMPTS[args.mode] + OUTPUT_FORMAT

    user_msg = f"## QA Angle\n\n{angle}\n\n"
    if known_defects:
        user_msg += f"## Already-Known Defects (do NOT re-report these)\n\n{known_defects}\n\n"
    user_msg += f"## Artifact Under Review\n\n{artifact}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]

    print(f"Calling {args.model} via cross-model endpoint (mode={args.mode})...", file=sys.stderr)
    response = call_critic(args.model, messages, temperature=args.temperature)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    header = (
        f"# {args.angle_id}: cross-model critique ({args.model})\n"
        f"**Artifact Type:** {args.mode}\n"
        f"**QA Dimension:** {args.dimension}\n"
        f"**Depth:** 0\n"
        f"**Parent:** seed\n"
        f"**Date:** {date_str}\n\n"
        f"## Defects Found\n\n"
    )
    with open(args.output_file, "w") as f:
        f.write(header + response)

    print(f"Wrote {len(response)} chars to {args.output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
