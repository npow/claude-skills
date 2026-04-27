#!/usr/bin/env python3
"""Stop hook that blocks stall-asking by calling an LLM classifier.

Reads Claude Code's Stop-hook JSON on stdin, extracts the last assistant
message + recent context from the transcript, sends it to a fast Claude model
via the Anthropic API (or any compatible proxy), and:

  - Exits 0  → stop is legitimate (task done, or matches an enumerated "ask" category)
  - Exits 2  → stop is a stall; stderr feedback tells Claude to continue executing

Fails OPEN: any internal error (network, parse, missing transcript) → exit 0.
A broken hook must never brick the session.

Source of truth for what counts as "legitimate ask": ~/.claude/autonomy-rules.md
The classifier reads that file at each invocation so edits take effect immediately.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
RULES_FILE = HOME / ".claude" / "autonomy-rules.md"
LOG_FILE = HOME / ".claude" / "hooks" / "stop-gate.log"

# All endpoint/key/model selection is env-driven so the hook + settings.json
# are portable across machines. Precedence (first non-empty wins):
#   1. CLAUDE_STOP_GATE_API_URL / _API_KEY / _MODEL — hook-specific overrides
#   2. ANTHROPIC_BASE_URL / ANTHROPIC_API_KEY        — same env vars Claude Code itself uses
#   3. Hardcoded Anthropic defaults                  — works on any machine with a valid API key
# This lets a proxy setup "just work" (settings.json already exports
# ANTHROPIC_BASE_URL) while a vanilla box can point at api.anthropic.com.

_ANTHROPIC_DEFAULT_BASE = "https://api.anthropic.com"


def _resolve_api_url() -> str:
    explicit = os.environ.get("CLAUDE_STOP_GATE_API_URL")
    if explicit:
        return explicit
    base = (os.environ.get("ANTHROPIC_BASE_URL") or _ANTHROPIC_DEFAULT_BASE).rstrip("/")
    # Callers may set ANTHROPIC_BASE_URL either to a root ("https://api.anthropic.com")
    # or to a proxy path that already ends in "/proxy/<project>". Either way we append
    # the standard /v1/messages suffix; the proxy handles routing.
    return f"{base}/v1/messages"


def _resolve_api_key() -> str:
    return (
        os.environ.get("CLAUDE_STOP_GATE_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or "sk-dummy"  # placeholder; auth will fail fast and hook fails open
    )


API_URL = _resolve_api_url()
API_KEY = _resolve_api_key()
ANTHROPIC_VERSION = "2023-06-01"
CLASSIFIER_MODEL = os.environ.get("CLAUDE_STOP_GATE_MODEL", "claude-sonnet-4-6")
REQUEST_TIMEOUT_SEC = 12.0

# How much of the transcript to send. The classifier needs the last user turn
# (to see grants / directives) and the last assistant turn (to classify).
RECENT_MESSAGES_TO_SEND = 6
MAX_MESSAGE_CHARS = 8000  # truncate each message to keep the prompt compact
TAIL_BYTES = 256 * 1024  # only read the last 256 KB of a transcript (enough for 6+ messages)


def log(msg: str) -> None:
    """Append one line to the hook log. Silent failure if log dir is unwritable."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def read_transcript_messages(path: Path) -> list[dict]:
    """Return the last N messages from a Claude Code JSONL transcript.

    Each message is the normalised {role, text} dict the classifier consumes.
    Returns [] on any parse failure.

    Optimisation: only reads the last TAIL_BYTES of the file, which is enough
    to find RECENT_MESSAGES_TO_SEND messages without parsing multi-MB transcripts.
    """
    if not path.is_file():
        return []
    try:
        size = path.stat().st_size
        if size == 0:
            return []
        with path.open("r", errors="replace") as f:
            if size > TAIL_BYTES:
                f.seek(size - TAIL_BYTES)
                f.readline()  # discard partial first line
            raw_lines = f.readlines()
    except Exception:
        return []

    messages: list[dict] = []
    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = rec.get("message") if isinstance(rec, dict) else None
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        if role not in ("user", "assistant"):
            continue
        content = msg.get("content")
        text = _extract_text(content)
        if not text:
            continue
        messages.append({"role": role, "text": text[:MAX_MESSAGE_CHARS]})

    return messages[-RECENT_MESSAGES_TO_SEND:]


def _extract_text(content) -> str:
    """Pull text and tool-use summaries out of Anthropic-format content.

    Tool-use blocks are summarised as "[Tool calls: Bash, Read, ...]" so the
    classifier can distinguish "announced then executed" from "announced then
    stopped."
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        tool_names: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_names.append(block.get("name", "unknown"))
        if tool_names:
            parts.append(f"[Tool calls: {', '.join(tool_names)}]")
        return "\n".join(parts)
    return ""


def load_rules() -> str:
    """Return the autonomy-rules.md content, or a minimal fallback."""
    try:
        return RULES_FILE.read_text()
    except Exception:
        return (
            "DEFAULT = execute. Stop is legitimate only when the task is truly "
            "complete OR the action requires sending a communication, pushing "
            "to main, merging a PR, deploying, deleting irrecoverable data, "
            "mutating shared infra, or needs a credential the system lacks. "
            "Session grants from the user override these defaults."
        )


def build_classifier_prompt(rules: str, messages: list[dict]) -> str:
    """Assemble the classifier's user-message prompt."""
    convo = "\n\n".join(f"### {m['role'].upper()}\n{m['text']}" for m in messages)
    return f"""You are a classifier deciding whether Claude's turn-end is legitimate or a stall.

AUTONOMY RULES (the source of truth — read carefully, including session-grant logic and the "does NOT require asking" list):

{rules}

---

CONVERSATION (most recent messages, oldest first):

{convo}

---

Classify Claude's LAST ASSISTANT MESSAGE. Apply the rules above.

TOOL CALL CONTEXT: Lines like "[Tool calls: Bash, Read, ...]" in an assistant message mean the assistant actually invoked those tools in that turn. An announcement like "Let me check X" followed by "[Tool calls: Bash]" means it DID check X — that is NOT a stall. Only flag as a stall if the announcement has NO corresponding tool calls.

BRAINSTORMING OVERRIDE: If the user's LAST message is exploratory (asking for options, trade-offs, "what do you think?", "how should we?", "pros and cons") and Claude responds with a recommendation or options, that is a LEGITIMATE_COMPLETION — the user asked for deliberation, not execution. Only apply stall rules when the user has given an execution directive.

MASTER TEST: If the question or decision Claude is stopping for could be answered by an LLM, it is a STALL. The only valid stops require something no LLM can provide: a human credential, human authorization for an irreversible external action, or a genuinely mutually exclusive trade-off with no clear winner.

A stop is a STALL if ANY of:

  (a) Permission-seeking stall — ALL of:
    - The last assistant message ends by asking for permission / confirmation / a go-ahead
    - The requested permission does NOT match any enumerated A/B/C/D category
    - The user has NOT given a relevant session grant earlier
    - There is an executable next step the assistant could have taken instead

  (b) Procrastination stall — ALL of:
    - The last assistant message declares work done or hands off
    - It defers, lists, or mentions achievable improvements/gaps/TODOs that Claude could do right now
    - The deferred work is within the user's stated scope and Claude's capabilities
    - No A/B/C/D category blocks the deferred work

  (c) False-dilemma stall — ALL of:
    - The last assistant message presents multiple options/approaches and asks the user to choose
    - The options are NOT mutually exclusive — they could all be done, or one is clearly best
    - The user has not requested to be consulted on this kind of choice

A stop is LEGITIMATE_COMPLETION if the task is actually done and the close is a summary / handoff (no "want me to…?" / "say the word" / "ready to…" ask).

A stop is LEGITIMATE_ASK if the assistant genuinely hits one of the A/B/C/D categories and no session grant exempts it.

Output ONLY valid JSON on a single line, no markdown, no prose before or after:

{{"verdict":"legitimate_completion"|"legitimate_ask"|"stall","category":"A1"|"A2"|...|"D2"|null,"reason":"<one sentence>","instruction":"<if stall, one sentence telling Claude what to do instead; else empty>"}}
"""


def classify(prompt: str) -> dict | None:
    """Call the Claude API. Returns parsed JSON dict or None on failure."""
    body = json.dumps({
        "model": CLASSIFIER_MODEL,
        "max_tokens": 400,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": API_KEY,
            "anthropic-version": ANTHROPIC_VERSION,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SEC) as resp:
            raw = resp.read().decode("utf-8")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        log(f"classifier HTTP error: {e}")
        return None
    except Exception as e:
        log(f"classifier unknown error: {e}")
        return None

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        log(f"classifier response not JSON: {raw[:200]!r}")
        return None

    content = payload.get("content")
    text = _extract_text(content).strip()
    if not text:
        log(f"classifier returned empty content: {payload!r}")
        return None

    # Strip any fencing / prose around the JSON
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0 or end <= start:
        log(f"no JSON object in classifier output: {text[:200]!r}")
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        log(f"classifier JSON parse failed ({e}): {text[:200]!r}")
        return None


def main() -> int:
    # Read hook JSON from stdin
    try:
        hook_input = json.loads(sys.stdin.read())
    except Exception as e:
        log(f"stdin parse failed: {e}")
        return 0  # fail open

    # Honor a "don't gate me" escape hatch (future-proofing)
    if os.environ.get("CLAUDE_STOP_GATE_DISABLE") == "1":
        log("CLAUDE_STOP_GATE_DISABLE=1 — skipping")
        return 0

    # stop_hook_active is true when Claude already got blocked once in this cycle;
    # avoid infinite loops — let the second stop through.
    if hook_input.get("stop_hook_active"):
        log("stop_hook_active=true — skipping to avoid loop")
        return 0

    # Use last_assistant_message from stdin (authoritative, no race condition)
    # rather than relying on the transcript which may not be flushed yet.
    last_assistant_msg = hook_input.get("last_assistant_message", "")
    if isinstance(last_assistant_msg, str):
        last_assistant_msg = last_assistant_msg.strip()

    transcript_path_str = hook_input.get("transcript_path")
    if not transcript_path_str:
        if not last_assistant_msg:
            log("no transcript_path and no last_assistant_message — fail open")
            return 0
        messages: list[dict] = [{"role": "assistant", "text": last_assistant_msg[:MAX_MESSAGE_CHARS]}]
    else:
        transcript_path = Path(transcript_path_str)
        messages = read_transcript_messages(transcript_path)

    if last_assistant_msg:
        # Inject/replace the authoritative last assistant message from stdin.
        # The transcript may have a stale or missing version due to flush timing.
        if messages and messages[-1]["role"] == "assistant":
            messages[-1] = {"role": "assistant", "text": last_assistant_msg[:MAX_MESSAGE_CHARS]}
        else:
            messages.append({"role": "assistant", "text": last_assistant_msg[:MAX_MESSAGE_CHARS]})
    elif not messages:
        log("empty transcript and no last_assistant_message — fail open")
        return 0
    elif messages[-1]["role"] != "assistant":
        log(f"last message role={messages[-1]['role']} and no last_assistant_message — skip")
        return 0

    rules = load_rules()
    prompt = build_classifier_prompt(rules, messages)
    result = classify(prompt)
    if not isinstance(result, dict) or "verdict" not in result:
        log(f"classifier returned no usable result — fail open")
        return 0

    verdict = result.get("verdict", "")
    category = result.get("category")
    reason = result.get("reason", "")
    instruction = result.get("instruction", "")

    log(f"verdict={verdict} category={category} reason={reason!r}")

    if verdict == "stall":
        feedback = (
            "[stop-gate] Your turn-end was flagged as a STALL by the autonomy "
            "classifier.\n"
            f"Reason: {reason}\n"
            f"Do this instead: {instruction}\n"
            "Rules file: ~/.claude/autonomy-rules.md\n"
            "If you believe the classifier is wrong, proceed anyway — but do "
            "not repeat the stalling phrase."
        )
        print(feedback, file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
