"""Temporal wrapper for the deep-research RLM backend."""

from __future__ import annotations

import json
import shlex
import sys
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from temporalio import workflow
from temporalio.common import RetryPolicy

from sagaflow.durable.activities import RunShellInput, RunShellResult

ACTIVITY_TIMEOUT = timedelta(hours=2)
HEARTBEAT_TIMEOUT = timedelta(seconds=120)
DEFAULT_PYTHON = sys.executable
ORCHESTRATOR_PATH = Path(__file__).resolve().with_name("rlm_orchestrator.py")


@dataclass(frozen=True)
class DeepResearchInput:
    run_id: str
    seed: str
    inbox_path: str
    run_dir: str
    max_dimensions: int = 8
    iters_per_dimension: int = 25
    llm_calls_per_dimension: int = 60
    max_gap_rounds: int = 2
    max_workers: int = 8
    verbose: bool = False
    notify: bool = True


@workflow.defn(name="DeepResearchRLMWorkflow")
class DeepResearchWorkflow:
    """Run the deep-research-owned multi-RLM orchestrator as a heartbeat shell activity."""

    @workflow.run
    async def run(self, inp: DeepResearchInput) -> str:
        cmd_parts = [
            "export PATH=$HOME/.deno/bin:$PATH &&",
            shlex.quote(DEFAULT_PYTHON),
            shlex.quote(str(ORCHESTRATOR_PATH)),
            "--query", shlex.quote(inp.seed),
            "--run-dir", shlex.quote(inp.run_dir),
            "--max-dimensions", str(inp.max_dimensions),
            "--iters-per-dimension", str(inp.iters_per_dimension),
            "--llm-calls-per-dimension", str(inp.llm_calls_per_dimension),
            "--max-gap-rounds", str(inp.max_gap_rounds),
            "--max-workers", str(inp.max_workers),
            "--python-path", shlex.quote(DEFAULT_PYTHON),
        ]
        if inp.verbose:
            cmd_parts.append("--verbose")
        cmd = " ".join(cmd_parts)

        result: RunShellResult = await workflow.execute_activity(
            "run_shell",
            RunShellInput(
                command=cmd,
                cwd=str(ORCHESTRATOR_PATH.parent),
                timeout_seconds=ACTIVITY_TIMEOUT.total_seconds() - 60,
                label=f"rlm-research: {inp.seed[:60]}",
            ),
            start_to_close_timeout=ACTIVITY_TIMEOUT,
            heartbeat_timeout=HEARTBEAT_TIMEOUT,
            retry_policy=RetryPolicy(maximum_attempts=1),
            result_type=RunShellResult,
        )

        if result.exit_code != 0:
            error_detail = (result.stderr or "")[-1000:] or "unknown error"
            return f"RLM research failed: {error_detail[-200:]}"

        try:
            last_line = result.stdout.strip().split("\n")[-1]
            output = json.loads(last_line)
            iters = output.get("total_iterations", "?")
            elapsed = output.get("total_elapsed_seconds", "?")
            dims = output.get("dimensions", output.get("dimension_count", "?"))
            gap_rounds = output.get("gap_rounds", 0)
            err_count = len(output.get("errors", []))
            summary = (
                f"Research complete: {dims} dimensions, {iters} total iters, "
                f"{elapsed}s elapsed"
            )
            if gap_rounds:
                summary += f", {gap_rounds} gap-fill round(s)"
            if err_count:
                summary += f" ({err_count} dimension error(s))"
            return summary
        except (json.JSONDecodeError, IndexError, KeyError):
            return f"Research complete (raw output: {result.stdout[-200:]})"
