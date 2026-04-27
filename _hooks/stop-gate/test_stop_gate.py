"""Comprehensive tests for stop-gate.py — the autonomy-enforcement hook.

Run: python3 -m pytest ~/.claude/hooks/test_stop_gate.py -v
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from io import StringIO
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

# Import the hook as a module from its file path
_HOOK_PATH = Path(__file__).parent / "stop-gate.py"
_spec = importlib.util.spec_from_file_location("stop_gate", _HOOK_PATH)
assert _spec and _spec.loader
stop_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stop_gate)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _jsonl_line(role: str, content: Any) -> str:
    return json.dumps({"message": {"role": role, "content": content}})


def _make_transcript(tmp: Path, lines: list[str]) -> Path:
    p = tmp / "transcript.jsonl"
    p.write_text("\n".join(lines) + "\n")
    return p


def _hook_stdin(
    transcript_path: str | None = None,
    stop_hook_active: bool = False,
    last_assistant_message: str = "",
) -> str:
    d: dict[str, Any] = {"stop_hook_active": stop_hook_active}
    if transcript_path is not None:
        d["transcript_path"] = transcript_path
    if last_assistant_message:
        d["last_assistant_message"] = last_assistant_message
    return json.dumps(d)


# ---------------------------------------------------------------------------
# _extract_text
# ---------------------------------------------------------------------------

class TestExtractText:
    def test_string_content(self):
        assert stop_gate._extract_text("hello world") == "hello world"

    def test_empty_string(self):
        assert stop_gate._extract_text("") == ""

    def test_none(self):
        assert stop_gate._extract_text(None) == ""

    def test_integer(self):
        assert stop_gate._extract_text(42) == ""

    def test_text_blocks(self):
        content = [
            {"type": "text", "text": "First paragraph."},
            {"type": "text", "text": "Second paragraph."},
        ]
        result = stop_gate._extract_text(content)
        assert "First paragraph." in result
        assert "Second paragraph." in result

    def test_tool_use_blocks(self):
        content = [
            {"type": "text", "text": "Let me check."},
            {"type": "tool_use", "name": "Bash"},
            {"type": "tool_use", "name": "Read"},
        ]
        result = stop_gate._extract_text(content)
        assert "Let me check." in result
        assert "[Tool calls: Bash, Read]" in result

    def test_tool_use_only(self):
        content = [
            {"type": "tool_use", "name": "Bash"},
        ]
        result = stop_gate._extract_text(content)
        assert result == "[Tool calls: Bash]"

    def test_tool_use_missing_name(self):
        content = [{"type": "tool_use"}]
        result = stop_gate._extract_text(content)
        assert "unknown" in result

    def test_empty_list(self):
        assert stop_gate._extract_text([]) == ""

    def test_non_dict_blocks_skipped(self):
        content = ["not a dict", {"type": "text", "text": "ok"}]
        assert stop_gate._extract_text(content) == "ok"

    def test_block_without_type(self):
        content = [{"text": "no type field"}]
        assert stop_gate._extract_text(content) == ""


# ---------------------------------------------------------------------------
# read_transcript_messages
# ---------------------------------------------------------------------------

class TestReadTranscriptMessages:
    def test_basic_transcript(self, tmp_path):
        lines = [
            _jsonl_line("user", "do the thing"),
            _jsonl_line("assistant", "I did the thing."),
        ]
        p = _make_transcript(tmp_path, lines)
        msgs = stop_gate.read_transcript_messages(p)
        assert len(msgs) == 2
        assert msgs[0] == {"role": "user", "text": "do the thing"}
        assert msgs[1] == {"role": "assistant", "text": "I did the thing."}

    def test_nonexistent_file(self, tmp_path):
        assert stop_gate.read_transcript_messages(tmp_path / "nope.jsonl") == []

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.jsonl"
        p.write_text("")
        assert stop_gate.read_transcript_messages(p) == []

    def test_corrupt_json_lines_skipped(self, tmp_path):
        lines = [
            "not json at all",
            _jsonl_line("user", "valid line"),
            "{broken json",
        ]
        p = _make_transcript(tmp_path, lines)
        msgs = stop_gate.read_transcript_messages(p)
        assert len(msgs) == 1
        assert msgs[0]["text"] == "valid line"

    def test_non_user_assistant_roles_skipped(self, tmp_path):
        lines = [
            json.dumps({"message": {"role": "system", "content": "sys prompt"}}),
            _jsonl_line("user", "hello"),
            json.dumps({"message": {"role": "tool", "content": "tool result"}}),
            _jsonl_line("assistant", "hi"),
        ]
        p = _make_transcript(tmp_path, lines)
        msgs = stop_gate.read_transcript_messages(p)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"

    def test_truncation_to_recent_n(self, tmp_path):
        lines = []
        for i in range(20):
            role = "user" if i % 2 == 0 else "assistant"
            lines.append(_jsonl_line(role, f"msg {i}"))
        p = _make_transcript(tmp_path, lines)
        msgs = stop_gate.read_transcript_messages(p)
        assert len(msgs) == stop_gate.RECENT_MESSAGES_TO_SEND

    def test_max_message_chars_truncation(self, tmp_path):
        long_text = "x" * (stop_gate.MAX_MESSAGE_CHARS + 1000)
        lines = [_jsonl_line("assistant", long_text)]
        p = _make_transcript(tmp_path, lines)
        msgs = stop_gate.read_transcript_messages(p)
        assert len(msgs[0]["text"]) == stop_gate.MAX_MESSAGE_CHARS

    def test_empty_text_messages_skipped(self, tmp_path):
        lines = [
            _jsonl_line("assistant", ""),
            _jsonl_line("assistant", []),
            _jsonl_line("user", "real message"),
        ]
        p = _make_transcript(tmp_path, lines)
        msgs = stop_gate.read_transcript_messages(p)
        assert len(msgs) == 1
        assert msgs[0]["text"] == "real message"

    def test_structured_content_blocks(self, tmp_path):
        content = [
            {"type": "text", "text": "I will check."},
            {"type": "tool_use", "name": "Bash"},
        ]
        lines = [_jsonl_line("assistant", content)]
        p = _make_transcript(tmp_path, lines)
        msgs = stop_gate.read_transcript_messages(p)
        assert len(msgs) == 1
        assert "I will check." in msgs[0]["text"]
        assert "[Tool calls: Bash]" in msgs[0]["text"]

    def test_lines_without_message_key_skipped(self, tmp_path):
        lines = [
            json.dumps({"type": "event", "data": "something"}),
            _jsonl_line("user", "real"),
        ]
        p = _make_transcript(tmp_path, lines)
        msgs = stop_gate.read_transcript_messages(p)
        assert len(msgs) == 1

    def test_tail_read_on_large_file(self, tmp_path):
        lines = []
        for i in range(500):
            role = "user" if i % 2 == 0 else "assistant"
            lines.append(_jsonl_line(role, f"message number {i} " + "x" * 200))
        p = _make_transcript(tmp_path, lines)
        msgs = stop_gate.read_transcript_messages(p)
        assert len(msgs) == stop_gate.RECENT_MESSAGES_TO_SEND
        assert msgs[-1]["text"].startswith("message number 499")

    def test_binary_content_handled(self, tmp_path):
        p = tmp_path / "binary.jsonl"
        p.write_bytes(b'\x80\x81\x82' + b'\n' + _jsonl_line("user", "ok").encode())
        msgs = stop_gate.read_transcript_messages(p)
        assert len(msgs) == 1
        assert msgs[0]["text"] == "ok"


# ---------------------------------------------------------------------------
# load_rules
# ---------------------------------------------------------------------------

class TestLoadRules:
    def test_reads_rules_file(self, tmp_path, monkeypatch):
        rules_file = tmp_path / "rules.md"
        rules_file.write_text("custom rules here")
        monkeypatch.setattr(stop_gate, "RULES_FILE", rules_file)
        assert stop_gate.load_rules() == "custom rules here"

    def test_fallback_on_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stop_gate, "RULES_FILE", tmp_path / "nope.md")
        result = stop_gate.load_rules()
        assert "DEFAULT = execute" in result


# ---------------------------------------------------------------------------
# build_classifier_prompt
# ---------------------------------------------------------------------------

class TestBuildClassifierPrompt:
    def test_includes_rules_and_messages(self):
        rules = "Rule 1: do stuff"
        messages = [
            {"role": "user", "text": "do it"},
            {"role": "assistant", "text": "want me to?"},
        ]
        prompt = stop_gate.build_classifier_prompt(rules, messages)
        assert "Rule 1: do stuff" in prompt
        assert "### USER\ndo it" in prompt
        assert "### ASSISTANT\nwant me to?" in prompt
        assert "STALL" in prompt
        assert "LEGITIMATE_COMPLETION" in prompt

    def test_json_output_format_described(self):
        prompt = stop_gate.build_classifier_prompt("rules", [{"role": "assistant", "text": "x"}])
        assert '"verdict"' in prompt
        assert '"category"' in prompt
        assert '"reason"' in prompt


# ---------------------------------------------------------------------------
# classify (mocked HTTP)
# ---------------------------------------------------------------------------

class TestClassify:
    def _mock_response(self, body: dict) -> mock.MagicMock:
        resp = mock.MagicMock()
        resp.read.return_value = json.dumps(body).encode()
        resp.__enter__ = mock.MagicMock(return_value=resp)
        resp.__exit__ = mock.MagicMock(return_value=False)
        return resp

    def test_successful_classification(self):
        verdict = {"verdict": "stall", "category": None, "reason": "stalling", "instruction": "keep going"}
        api_response = {"content": [{"type": "text", "text": json.dumps(verdict)}]}
        with mock.patch("urllib.request.urlopen", return_value=self._mock_response(api_response)):
            result = stop_gate.classify("test prompt")
        assert result == verdict

    def test_legitimate_completion(self):
        verdict = {"verdict": "legitimate_completion", "category": None, "reason": "done"}
        api_response = {"content": [{"type": "text", "text": json.dumps(verdict)}]}
        with mock.patch("urllib.request.urlopen", return_value=self._mock_response(api_response)):
            result = stop_gate.classify("test prompt")
        assert result["verdict"] == "legitimate_completion"

    def test_json_with_surrounding_prose(self):
        text = 'Here is my analysis:\n{"verdict":"stall","category":null,"reason":"x","instruction":"y"}\nDone.'
        api_response = {"content": [{"type": "text", "text": text}]}
        with mock.patch("urllib.request.urlopen", return_value=self._mock_response(api_response)):
            result = stop_gate.classify("test")
        assert result is not None
        assert result["verdict"] == "stall"

    def test_http_error_returns_none(self):
        import urllib.error
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
            assert stop_gate.classify("test") is None

    def test_timeout_returns_none(self):
        with mock.patch("urllib.request.urlopen", side_effect=TimeoutError()):
            assert stop_gate.classify("test") is None

    def test_invalid_json_response_returns_none(self):
        resp = mock.MagicMock()
        resp.read.return_value = b"not json"
        resp.__enter__ = mock.MagicMock(return_value=resp)
        resp.__exit__ = mock.MagicMock(return_value=False)
        with mock.patch("urllib.request.urlopen", return_value=resp):
            assert stop_gate.classify("test") is None

    def test_empty_content_returns_none(self):
        api_response = {"content": []}
        with mock.patch("urllib.request.urlopen", return_value=self._mock_response(api_response)):
            assert stop_gate.classify("test") is None

    def test_no_json_object_in_text(self):
        api_response = {"content": [{"type": "text", "text": "no json here"}]}
        with mock.patch("urllib.request.urlopen", return_value=self._mock_response(api_response)):
            assert stop_gate.classify("test") is None


# ---------------------------------------------------------------------------
# main() end-to-end (mocked stdin + HTTP)
# ---------------------------------------------------------------------------

class TestMain:
    _SENTINEL = object()

    def _run_main(self, stdin_data: str, classify_result: dict | None = _SENTINEL) -> int:
        with mock.patch("sys.stdin", StringIO(stdin_data)):
            if classify_result is not self._SENTINEL:
                with mock.patch.object(stop_gate, "classify", return_value=classify_result):
                    return stop_gate.main()
            else:
                return stop_gate.main()

    def test_invalid_stdin_fails_open(self):
        assert self._run_main("not json") == 0

    def test_disable_env_var(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_STOP_GATE_DISABLE", "1")
        assert self._run_main(_hook_stdin()) == 0

    def test_stop_hook_active_skips(self):
        assert self._run_main(_hook_stdin(stop_hook_active=True)) == 0

    def test_no_transcript_no_last_msg_fails_open(self):
        assert self._run_main(_hook_stdin(transcript_path=None)) == 0

    def test_last_assistant_message_used_without_transcript(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stop_gate, "RULES_FILE", tmp_path / "rules.md")
        (tmp_path / "rules.md").write_text("rules")
        stdin = _hook_stdin(
            transcript_path=None,
            last_assistant_message="Want me to continue?",
        )
        verdict = {"verdict": "stall", "category": None, "reason": "stall", "instruction": "just do it"}
        rc = self._run_main(stdin, classify_result=verdict)
        assert rc == 2

    def test_last_assistant_message_overrides_transcript(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stop_gate, "RULES_FILE", tmp_path / "rules.md")
        (tmp_path / "rules.md").write_text("rules")
        transcript = _make_transcript(tmp_path, [
            _jsonl_line("user", "do the thing"),
            _jsonl_line("assistant", "OLD assistant message from transcript"),
        ])
        stdin = _hook_stdin(
            transcript_path=str(transcript),
            last_assistant_message="NEW authoritative message from stdin",
        )
        captured_prompt = []
        def mock_classify(prompt):
            captured_prompt.append(prompt)
            return {"verdict": "legitimate_completion", "category": None, "reason": "done"}
        with mock.patch("sys.stdin", StringIO(stdin)):
            with mock.patch.object(stop_gate, "classify", side_effect=mock_classify):
                stop_gate.main()
        assert "NEW authoritative message from stdin" in captured_prompt[0]
        assert "OLD assistant message from transcript" not in captured_prompt[0]

    def test_race_condition_fixed_last_msg_user_in_transcript(self, tmp_path, monkeypatch):
        """The race condition: transcript's last message is from user, but
        last_assistant_message in stdin has the real assistant message."""
        monkeypatch.setattr(stop_gate, "RULES_FILE", tmp_path / "rules.md")
        (tmp_path / "rules.md").write_text("rules")
        transcript = _make_transcript(tmp_path, [
            _jsonl_line("user", "do it"),
            _jsonl_line("assistant", "doing it"),
            _jsonl_line("user", "more context"),
            # NOTE: no assistant message at end — race condition!
        ])
        stdin = _hook_stdin(
            transcript_path=str(transcript),
            last_assistant_message="I finished the work. Want me to also do X?",
        )
        captured = []
        def mock_classify(prompt):
            captured.append(prompt)
            return {"verdict": "stall", "category": None, "reason": "stall", "instruction": "do X"}
        with mock.patch("sys.stdin", StringIO(stdin)):
            with mock.patch.object(stop_gate, "classify", side_effect=mock_classify):
                rc = stop_gate.main()
        assert rc == 2
        assert "I finished the work" in captured[0]

    def test_stall_returns_2_with_stderr(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stop_gate, "RULES_FILE", tmp_path / "rules.md")
        (tmp_path / "rules.md").write_text("rules")
        transcript = _make_transcript(tmp_path, [
            _jsonl_line("user", "do it"),
            _jsonl_line("assistant", "Want me to proceed?"),
        ])
        stdin = _hook_stdin(
            transcript_path=str(transcript),
            last_assistant_message="Want me to proceed?",
        )
        verdict = {"verdict": "stall", "category": None, "reason": "permission seeking", "instruction": "just do it"}
        stderr_capture = StringIO()
        with mock.patch("sys.stdin", StringIO(stdin)):
            with mock.patch("sys.stderr", stderr_capture):
                with mock.patch.object(stop_gate, "classify", return_value=verdict):
                    rc = stop_gate.main()
        assert rc == 2
        err = stderr_capture.getvalue()
        assert "[stop-gate]" in err
        assert "permission seeking" in err

    def test_legitimate_completion_returns_0(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stop_gate, "RULES_FILE", tmp_path / "rules.md")
        (tmp_path / "rules.md").write_text("rules")
        transcript = _make_transcript(tmp_path, [
            _jsonl_line("user", "do it"),
            _jsonl_line("assistant", "Done. All changes committed."),
        ])
        stdin = _hook_stdin(
            transcript_path=str(transcript),
            last_assistant_message="Done. All changes committed.",
        )
        verdict = {"verdict": "legitimate_completion", "category": None, "reason": "task complete"}
        rc = self._run_main(stdin, classify_result=verdict)
        assert rc == 0

    def test_legitimate_ask_returns_0(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stop_gate, "RULES_FILE", tmp_path / "rules.md")
        (tmp_path / "rules.md").write_text("rules")
        transcript = _make_transcript(tmp_path, [
            _jsonl_line("user", "push to main"),
            _jsonl_line("assistant", "Ready to push to main — confirm?"),
        ])
        stdin = _hook_stdin(
            transcript_path=str(transcript),
            last_assistant_message="Ready to push to main — confirm?",
        )
        verdict = {"verdict": "legitimate_ask", "category": "A2", "reason": "push to main"}
        rc = self._run_main(stdin, classify_result=verdict)
        assert rc == 0

    def test_classifier_failure_fails_open(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stop_gate, "RULES_FILE", tmp_path / "rules.md")
        (tmp_path / "rules.md").write_text("rules")
        transcript = _make_transcript(tmp_path, [
            _jsonl_line("user", "go"),
            _jsonl_line("assistant", "doing it"),
        ])
        stdin = _hook_stdin(
            transcript_path=str(transcript),
            last_assistant_message="doing it",
        )
        rc = self._run_main(stdin, classify_result=None)
        assert rc == 0

    def test_classifier_returns_no_verdict_fails_open(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stop_gate, "RULES_FILE", tmp_path / "rules.md")
        (tmp_path / "rules.md").write_text("rules")
        transcript = _make_transcript(tmp_path, [
            _jsonl_line("user", "go"),
            _jsonl_line("assistant", "doing"),
        ])
        stdin = _hook_stdin(
            transcript_path=str(transcript),
            last_assistant_message="doing",
        )
        rc = self._run_main(stdin, classify_result={"no_verdict_key": True})
        assert rc == 0

    def test_empty_transcript_with_last_msg(self, tmp_path, monkeypatch):
        """Empty transcript but last_assistant_message present — should classify."""
        monkeypatch.setattr(stop_gate, "RULES_FILE", tmp_path / "rules.md")
        (tmp_path / "rules.md").write_text("rules")
        transcript = _make_transcript(tmp_path, [])
        stdin = _hook_stdin(
            transcript_path=str(transcript),
            last_assistant_message="Shall I proceed?",
        )
        verdict = {"verdict": "stall", "category": None, "reason": "stall", "instruction": "do it"}
        rc = self._run_main(stdin, classify_result=verdict)
        assert rc == 2


# ---------------------------------------------------------------------------
# Config resolution
# ---------------------------------------------------------------------------

class TestConfigResolution:
    def test_api_url_explicit_override(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_STOP_GATE_API_URL", "https://custom.api/v1/messages")
        assert stop_gate._resolve_api_url() == "https://custom.api/v1/messages"

    def test_api_url_from_anthropic_base(self, monkeypatch):
        monkeypatch.delenv("CLAUDE_STOP_GATE_API_URL", raising=False)
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://proxy.example.com")
        assert stop_gate._resolve_api_url() == "https://proxy.example.com/v1/messages"

    def test_api_url_strips_trailing_slash(self, monkeypatch):
        monkeypatch.delenv("CLAUDE_STOP_GATE_API_URL", raising=False)
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://proxy.example.com/")
        assert stop_gate._resolve_api_url() == "https://proxy.example.com/v1/messages"

    def test_api_url_default(self, monkeypatch):
        monkeypatch.delenv("CLAUDE_STOP_GATE_API_URL", raising=False)
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        assert "api.anthropic.com" in stop_gate._resolve_api_url()

    def test_api_key_explicit_override(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_STOP_GATE_API_KEY", "sk-override")
        assert stop_gate._resolve_api_key() == "sk-override"

    def test_api_key_from_anthropic(self, monkeypatch):
        monkeypatch.delenv("CLAUDE_STOP_GATE_API_KEY", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic")
        assert stop_gate._resolve_api_key() == "sk-anthropic"

    def test_api_key_fallback_dummy(self, monkeypatch):
        monkeypatch.delenv("CLAUDE_STOP_GATE_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        assert stop_gate._resolve_api_key() == "sk-dummy"


# ---------------------------------------------------------------------------
# log()
# ---------------------------------------------------------------------------

class TestLog:
    def test_log_writes_to_file(self, tmp_path, monkeypatch):
        log_file = tmp_path / "test.log"
        monkeypatch.setattr(stop_gate, "LOG_FILE", log_file)
        stop_gate.log("test message")
        content = log_file.read_text()
        assert "test message" in content

    def test_log_silent_on_unwritable(self, monkeypatch):
        monkeypatch.setattr(stop_gate, "LOG_FILE", Path("/nonexistent/dir/test.log"))
        stop_gate.log("should not crash")
