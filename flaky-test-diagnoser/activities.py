"""Skill-specific activities for the flaky-test-diagnoser skill.

Adds one activity beyond the framework base: run_test_subprocess, used to
execute the test command and capture pass/fail + timing.
Everything else reuses write_artifact, spawn_subagent, and emit_finding
from sagaflow.durable.
"""

from __future__ import annotations

import asyncio
import time

from temporalio import activity


@activity.defn(name="run_test_subprocess")
async def run_test_subprocess(command: str, timeout: int = 60) -> dict[str, int]:
    """Run a shell command and return exit code + duration in milliseconds.

    Args:
        command: Shell command to execute (passed to asyncio.create_subprocess_shell).
        timeout: Seconds before the subprocess is killed (default 60).

    Returns:
        {"exit_code": int, "duration_ms": int}
    """
    start_ms = int(time.monotonic() * 1000)
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        await asyncio.wait_for(proc.communicate(), timeout=float(timeout))
    except TimeoutError:
        proc.kill()
        await proc.wait()
    end_ms = int(time.monotonic() * 1000)
    exit_code = proc.returncode if proc.returncode is not None else 1
    return {"exit_code": exit_code, "duration_ms": end_ms - start_ms}
