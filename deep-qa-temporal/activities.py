"""Skill-specific activities for deep-qa-temporal.

Only adds one activity beyond the framework base: read_text_file, used to
snapshot the artifact under QA at workflow start. Everything else reuses
write_artifact, spawn_subagent, and emit_finding from sagaflow.durable.
"""

from __future__ import annotations

from pathlib import Path

from temporalio import activity


@activity.defn(name="read_text_file")
async def read_text_file(path: str) -> str:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"artifact not found: {p}")
    if not p.is_file():
        raise IsADirectoryError(f"artifact is not a regular file: {p}")
    return p.read_text(encoding="utf-8", errors="replace")
