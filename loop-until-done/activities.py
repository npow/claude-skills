"""loop-until-done: subprocess activity for running verification commands."""

from __future__ import annotations

import re
import subprocess
import time

from temporalio import activity


@activity.defn(name="run_verification_command")
async def run_verification_command(
    command: str,
    expected_pattern: str,
    timeout: int = 60,
) -> dict[str, object]:
    """Execute *command* in a subprocess, capture stdout/stderr, check pattern.

    Returns a dict with keys:
        stdout        str  — captured stdout
        stderr        str  — captured stderr
        exit_code     int  — process exit code
        matched       bool — True if expected_pattern found in stdout
        duration_ms   int  — wall-clock ms for the subprocess
    """
    started = time.monotonic()
    try:
        completed = subprocess.run(  # noqa: S603
            command,
            shell=True,  # noqa: S602
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        exit_code = completed.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"").decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = (exc.stderr or b"").decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        exit_code = -1
    except Exception as exc:  # noqa: BLE001
        stdout = ""
        stderr = str(exc)
        exit_code = -1

    duration_ms = int((time.monotonic() - started) * 1000)

    # Pattern match: treat as regex if surrounded by '/', else substring.
    if expected_pattern.startswith("/") and expected_pattern.endswith("/") and len(expected_pattern) > 1:
        inner = expected_pattern[1:-1]
        try:
            matched = bool(re.search(inner, stdout))
        except re.error:
            matched = inner in stdout
    else:
        matched = expected_pattern in stdout

    return {
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "matched": matched,
        "duration_ms": duration_ms,
    }
