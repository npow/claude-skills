#!/usr/bin/env python3
"""Stream Claude Code progress to a live-updating Slack message.

Usage:
    claude -p "do something" --output-format stream-json --verbose | \\
        python stream_to_slack.py --channel C123 --thread-ts 1234.5678

    # Or post a new thread message (returns thread_ts on stderr):
    claude -p "do something" --output-format stream-json --verbose | \\
        python stream_to_slack.py --channel C123 --title "Building feature X"

Reads newline-delimited JSON events from stdin and maintains a Slack message
showing tool call progress, elapsed time, and cost.

Requires SLACK_SCRIPT env var or uses the default path to slack_request.py.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field

SLACK_SCRIPT = os.environ.get(
    "SLACK_SCRIPT",
    os.path.expanduser(
        "~/ws/ngp-skills/plugins/slack-interactions-plugin/"
        "skills/slack-interactions/scripts/slack_request.py"
    ),
)

UPDATE_INTERVAL_S = 2.5
MAX_DISPLAY_TASKS = 20


@dataclass
class Task:
    name: str
    detail: str
    tool_use_id: str
    status: str = "in_progress"
    started: float = field(default_factory=time.time)

    def elapsed_s(self) -> float:
        return time.time() - self.started


class StreamAdapter:
    def __init__(self, channel: str, thread_ts: str | None, title: str):
        self.channel = channel
        self.thread_ts = thread_ts
        self.msg_ts: str | None = None
        self.title = title
        self.tasks: list[Task] = []
        self.current_msg_id: str | None = None
        self.pending_tool_ids: set[str] = set()
        self.completed_count = 0
        self.total_cost = 0.0
        self.start_time = time.time()
        self.last_update = 0.0
        self.final_result: str | None = None

    def run(self) -> None:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            self._process(event)
        self._finish()

    def _process(self, event: dict) -> None:
        t = event.get("type")
        if t == "assistant":
            self._handle_assistant(event)
        elif t == "result":
            self.total_cost = event.get("total_cost_usd", 0)
            self.final_result = event.get("result", "")
            self._mark_all_done()
            self._push(force=True, final=True)

    def _handle_assistant(self, event: dict) -> None:
        message = event.get("message", {})
        msg_id = message.get("id", "")
        content = message.get("content", [])
        if not isinstance(content, list):
            return

        if msg_id and msg_id != self.current_msg_id:
            self._complete_pending()
            self.current_msg_id = msg_id

        for item in content:
            item_type = item.get("type")
            if item_type == "tool_use":
                self._on_tool_use(item)

    def _on_tool_use(self, item: dict) -> None:
        name = item.get("name", "?")
        tool_use_id = item.get("id", "")
        if tool_use_id in self.pending_tool_ids:
            return
        if any(t.tool_use_id == tool_use_id for t in self.tasks):
            return
        detail = _summarize_input(name, item.get("input", {}))
        self.tasks.append(Task(name, detail, tool_use_id))
        self.pending_tool_ids.add(tool_use_id)
        self._push()

    def _complete_pending(self) -> None:
        for task in self.tasks:
            if task.status == "in_progress" and task.tool_use_id in self.pending_tool_ids:
                task.status = "completed"
                self.completed_count += 1
        self.pending_tool_ids.clear()
        self._push()

    def _mark_all_done(self) -> None:
        for task in self.tasks:
            if task.status == "in_progress":
                task.status = "completed"
                self.completed_count += 1
        self.pending_tool_ids.clear()

    def _push(self, *, force: bool = False, final: bool = False) -> None:
        now = time.time()
        if not force and (now - self.last_update) < UPDATE_INTERVAL_S:
            return
        self.last_update = now
        text = self._render(final)
        if self.msg_ts:
            _slack_update(self.channel, self.msg_ts, text)
        else:
            self.msg_ts = _slack_post(self.channel, self.thread_ts, text)
            if self.msg_ts and not self.thread_ts:
                self.thread_ts = self.msg_ts
                print(self.msg_ts, file=sys.stderr)

    def _finish(self) -> None:
        self._mark_all_done()
        self._push(force=True, final=True)

    def _render(self, final: bool = False) -> str:
        elapsed = time.time() - self.start_time
        cost_str = f"${self.total_cost:.2f}" if self.total_cost else ""
        header_parts = [f"*{self.title}*", f"({_fmt_duration(elapsed)}"]
        if cost_str:
            header_parts[-1] += f", {cost_str}"
        header_parts[-1] += ")"

        status_icon = ":white_check_mark:" if final else ":arrows_counterclockwise:"
        lines = [f"{status_icon} {' '.join(header_parts)}", ""]

        visible = self.tasks[-MAX_DISPLAY_TASKS:]
        hidden_completed = len(self.tasks) - len(visible)

        if hidden_completed > 0:
            lines.append(f"_...{hidden_completed} earlier steps completed_")

        for task in visible:
            if task.status == "completed":
                icon = ":white_check_mark:"
                suffix = f" ({_fmt_duration(task.elapsed_s())})"
            elif task.status == "error":
                icon = ":x:"
                suffix = ""
            else:
                suffix = f" ({_fmt_duration(task.elapsed_s())})"
                icon = ":hourglass_flowing_sand:"
            lines.append(f"{icon} {task.name}: {task.detail}{suffix}")

        lines.append("")
        in_progress = sum(1 for t in self.tasks if t.status == "in_progress")
        footer = f"_{self.completed_count} completed"
        if in_progress:
            footer += f" · {in_progress} running"
        footer += "_"
        lines.append(footer)

        return "\n".join(lines)


def _summarize_input(name: str, inp: dict) -> str:
    if name == "Read":
        return f"`{_short_path(inp.get('file_path', '?'))}`"
    if name == "Write":
        return f"`{_short_path(inp.get('file_path', '?'))}`"
    if name == "Edit":
        return f"`{_short_path(inp.get('file_path', '?'))}`"
    if name == "Bash":
        cmd = inp.get("command", "")
        return f"`{cmd[:80]}{'...' if len(cmd) > 80 else ''}`"
    if name == "Grep":
        return f"`{inp.get('pattern', '?')}`"
    if name == "Glob":
        return f"`{inp.get('pattern', '?')}`"
    if name == "Agent":
        return inp.get("description", inp.get("prompt", "?")[:60])
    if name == "LSP":
        op = inp.get("operation", "?")
        fp = _short_path(inp.get("filePath", "?"))
        return f"{op} `{fp}`"
    if name == "TodoWrite":
        todos = inp.get("todos", [])
        active = [t for t in todos if isinstance(t, dict) and t.get("status") == "in_progress"]
        if active:
            return active[0].get("activeForm", "updating tasks")
        return f"{len(todos)} tasks"
    if name == "WebFetch":
        return f"`{inp.get('url', '?')[:60]}`"
    if name == "WebSearch":
        return f"`{inp.get('query', '?')[:60]}`"
    desc = json.dumps(inp)
    return desc[:60] + ("..." if len(desc) > 60 else "")


def _short_path(path: str) -> str:
    if path.startswith("/root/code/"):
        return path[len("/root/code/"):]
    home = os.path.expanduser("~")
    if path.startswith(home):
        return "~" + path[len(home):]
    return path


def _fmt_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m}m{s:02d}s"


def _slack_post(channel: str, thread_ts: str | None, text: str) -> str | None:
    body: dict = {"channel": channel, "text": text}
    if thread_ts:
        body["thread_ts"] = thread_ts
    result = _slack_api("chat.postMessage", body)
    return result.get("ts")


def _slack_update(channel: str, ts: str, text: str) -> None:
    _slack_api("chat.update", {"channel": channel, "ts": ts, "text": text})


def _slack_api(method: str, body: dict) -> dict:
    try:
        result = subprocess.run(
            [
                SLACK_SCRIPT,
                "--endpoint", f"/api/{method}",
                "-X", "POST",
                "--body", json.dumps(body),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    return {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Stream Claude Code progress to Slack")
    parser.add_argument("--channel", required=True, help="Slack channel ID")
    parser.add_argument("--thread-ts", help="Thread timestamp to reply in")
    parser.add_argument("--title", default="Claude Code", help="Title for the progress message")
    args = parser.parse_args()

    adapter = StreamAdapter(args.channel, args.thread_ts, args.title)
    adapter.run()


if __name__ == "__main__":
    main()
