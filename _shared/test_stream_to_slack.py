#!/usr/bin/env python3
"""Unit tests for stream_to_slack.py"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from stream_to_slack import _summarize_input, _short_path, _fmt_duration, StreamAdapter

# _summarize_input tests
assert _summarize_input("Read", {"file_path": "/root/code/foo/bar.py"}) == "`foo/bar.py`"
assert _summarize_input("Write", {"file_path": "/root/docs/test.txt"}) == "`~/docs/test.txt`"
assert _summarize_input("Edit", {"file_path": "/tmp/x.py"}) == "`/tmp/x.py`"
assert _summarize_input("Bash", {"command": "git status"}) == "`git status`"
assert _summarize_input("Bash", {"command": "x" * 100}) == "`" + "x" * 80 + "...`"
assert _summarize_input("Grep", {"pattern": "TODO"}) == "`TODO`"
assert _summarize_input("Glob", {"pattern": "**/*.py"}) == "`**/*.py`"
assert _summarize_input("Agent", {"description": "Search codebase"}) == "Search codebase"
assert _summarize_input("TodoWrite", {"todos": [
    {"status": "in_progress", "activeForm": "Running tests"},
    {"status": "pending", "activeForm": "Deploy"},
]}) == "Running tests"
assert _summarize_input("TodoWrite", {"todos": [
    {"status": "pending", "activeForm": "Deploy"},
    {"status": "pending", "activeForm": "Test"},
]}) == "2 tasks"

# _short_path tests
assert _short_path("/root/code/myrepo/src/main.py") == "myrepo/src/main.py"
assert _short_path("/root/docs/file.txt") == "~/docs/file.txt"
assert _short_path("/tmp/other.py") == "/tmp/other.py"

# _fmt_duration tests
assert _fmt_duration(5) == "5s"
assert _fmt_duration(59.9) == "60s"
assert _fmt_duration(65) == "1m05s"
assert _fmt_duration(3661) == "61m01s"

# StreamAdapter._render smoke test
adapter = StreamAdapter("C123", "1234.5678", "Test Run")
text = adapter._render(final=False)
assert ":arrows_counterclockwise:" in text
assert "Test Run" in text

adapter.tasks.append(type("Task", (), {
    "name": "Read", "detail": "`foo.py`", "tool_use_id": "t1",
    "status": "completed", "elapsed_s": lambda self: 2.5,
})())
adapter.completed_count = 1
text = adapter._render(final=True)
assert ":white_check_mark:" in text
assert "1 completed" in text

# Event processing smoke test
adapter2 = StreamAdapter("C123", None, "Build")
event = {
    "type": "assistant",
    "message": {
        "id": "msg_1",
        "content": [
            {"type": "tool_use", "id": "tu_1", "name": "Read", "input": {"file_path": "/root/code/x/y.py"}}
        ],
    },
}
adapter2._process(event)
assert len(adapter2.tasks) == 1
assert adapter2.tasks[0].name == "Read"
assert "tu_1" in adapter2.pending_tool_ids

# Duplicate tool_use_id ignored
adapter2._process(event)
assert len(adapter2.tasks) == 1

# New message ID completes pending
event2 = {
    "type": "assistant",
    "message": {
        "id": "msg_2",
        "content": [
            {"type": "tool_use", "id": "tu_2", "name": "Bash", "input": {"command": "echo hi"}}
        ],
    },
}
adapter2._process(event2)
assert adapter2.tasks[0].status == "completed"
assert adapter2.completed_count == 1
assert len(adapter2.tasks) == 2

# Result event marks all done
result_event = {"type": "result", "total_cost_usd": 0.05, "result": "done"}
adapter2._process(result_event)
assert all(t.status == "completed" for t in adapter2.tasks)
assert adapter2.total_cost == 0.05

print("All tests passed.")
