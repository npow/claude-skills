"""deep-research workflow backed by the RLM multi-RLM orchestrator.

Replaces the DFS-style deep-research-temporal workflow (preserved in
``workflow.py`` for rollback) with a thin wrapper around
``sagaflow.rlm.orchestrator`` — the same engine that powers
``rlm-research``. The motivation is cost: the DFS pipeline runs phases
0f, 0g, 1, 2 (researcher fan-out), 3 (coordinator summaries), 4
(verification), and 5 (synthesis) — each round costs tens of Sonnet
calls and the loop runs up to ``max_rounds`` times. RLM runs a single
fan-out across ~14 dims and one synthesis + verify + revise pass.

The replacement keeps the externally-observable contract:
  - Input dataclass field names match ``DeepResearchInput`` so callers
    don't need updating.
  - Output: ``{run_dir}/research-report.md`` (renamed from orchestrator
    default ``report.md``).
  - Side effects: ``emit_finding`` to the inbox + ``finalize_manifest``
    matching the DFS workflow's ending.
  - Workflow name: ``DeepResearchWorkflow`` so the registry binding
    stays valid.

To roll back, edit ``__init__.py`` to import from ``workflow`` instead
of ``workflow_rlm``.
"""

from __future__ import annotations

import json
import shlex
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from sagaflow.durable.activities import (
        EmitFindingInput,
        FinalizeManifestInput,
        RunShellInput,
        RunShellResult,
    )
    from sagaflow.durable.retry_policies import HAIKU_POLICY


# Activity ceiling. RLM orchestrator wall time scales with
# ``max_dimensions * iters_per_dimension``. At 14 dims × 50 iters the
# measured end-to-end is 60-75 min; we cap the activity at 2h with
# heartbeats every 60s so a hung Trino query or slow LM gateway can't
# silently consume budget.
ACTIVITY_TIMEOUT = timedelta(hours=2)
HEARTBEAT_TIMEOUT = timedelta(seconds=120)
DEFAULT_PYTHON = "/apps/default-python/bin/python3"


# ---------------------------------------------------------------------------
# Input — field names match the original DFS workflow so __init__.py
# build_input doesn't change.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DeepResearchInput:
    run_id: str
    seed: str
    inbox_path: str
    run_dir: str
    max_rounds: int = 100
    min_rounds: int = 3
    max_directions: int = 50
    max_concurrent_researchers: int = 20
    notify: bool = True
    mcp_categories_json: str = "{}"


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

@workflow.defn(name="DeepResearchWorkflow")
class DeepResearchWorkflow:

    @workflow.run
    async def run(self, inp: DeepResearchInput) -> str:
        run_dir = inp.run_dir
        report_path = f"{run_dir}/research-report.md"

        # Map DFS knobs to RLM knobs.
        # max_directions in DFS is total directions across all rounds; in
        # RLM there's a single fan-out, so cap at 14 to match the
        # benchmarks where this score was demonstrated.
        max_dimensions = min(int(inp.max_directions or 14), 14) or 14
        # iters_per_dimension defaults to 50 — measured convergence
        # sweet spot for R1/R2/R3 benches. max_rounds in DFS sense maps
        # to RLM's max_gap_rounds (additional fan-out after the initial
        # synth flagged gaps); 0 by default since revise covers most gaps.
        max_gap_rounds = 0

        cmd_parts = [
            "export PATH=$HOME/.deno/bin:$PATH &&",
            DEFAULT_PYTHON,
            "-m",
            "sagaflow.rlm.orchestrator",
            "--query",
            shlex.quote(inp.seed),
            "--run-dir",
            shlex.quote(run_dir),
            "--max-dimensions",
            str(max_dimensions),
            "--iters-per-dimension",
            "50",
            "--llm-calls-per-dimension",
            "100",
            "--max-gap-rounds",
            str(max_gap_rounds),
            "--max-workers",
            "8",
            "--python-path",
            DEFAULT_PYTHON,
        ]
        cmd = " ".join(cmd_parts)

        # Inherit env from the worker. The orchestrator reads RLM_API_BASE
        # (or falls back to OPENAI_BASE_URL) and optionally SAGAFLOW_RLM_TOOLS
        # — operators configure those on the worker process to point at
        # their tenant's LM gateway and tool inventory. Never hardcode
        # tenant-specific URLs or tool module paths in this generic
        # workflow.
        result: RunShellResult = await workflow.execute_activity(
            "run_shell",
            RunShellInput(
                command=cmd,
                cwd="/root/projects/sagaflow",
                timeout_seconds=ACTIVITY_TIMEOUT.total_seconds() - 60,
                label=f"deep-research-rlm: {inp.seed[:60]}",
            ),
            start_to_close_timeout=ACTIVITY_TIMEOUT,
            heartbeat_timeout=HEARTBEAT_TIMEOUT,
            retry_policy=RetryPolicy(maximum_attempts=1),
            result_type=RunShellResult,
        )

        timestamp = workflow.now().isoformat(timespec="seconds")

        if result.exit_code != 0:
            error_tail = (result.stderr or "")[-1000:] or "unknown error"
            summary = f"deep-research failed (exit {result.exit_code}): {error_tail[-200:]}"
            await workflow.execute_activity(
                "emit_finding",
                EmitFindingInput(
                    inbox_path=inp.inbox_path,
                    run_id=inp.run_id,
                    skill="deep-research",
                    status="FAILED",
                    summary=summary,
                    notify=inp.notify,
                    timestamp_iso=timestamp,
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=HAIKU_POLICY,
            )
            await workflow.execute_activity(
                "finalize_manifest",
                FinalizeManifestInput(run_dir=run_dir, status="FAILED", error=error_tail[-500:]),
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=HAIKU_POLICY,
            )
            return summary

        # RLM orchestrator writes ``{run_dir}/report.md``; the deep-research
        # convention is ``research-report.md``. Rename via run_shell so the
        # workflow stays deterministic.
        await workflow.execute_activity(
            "run_shell",
            RunShellInput(
                command=f"mv {shlex.quote(run_dir)}/report.md {shlex.quote(report_path)} 2>/dev/null || true",
                cwd="/",
                timeout_seconds=10,
                label="rename report.md -> research-report.md",
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=1),
            result_type=RunShellResult,
        )

        # Pull summary stats from orchestrator stdout (last line is JSON).
        iters = elapsed = dims = "?"
        err_count = 0
        try:
            last_line = result.stdout.strip().split("\n")[-1]
            output = json.loads(last_line)
            iters = output.get("total_iterations", "?")
            elapsed = output.get("total_elapsed_seconds", "?")
            dims = output.get("dimensions", "?")
            err_count = len(output.get("dimension_errors", []) or output.get("errors", []) or [])
        except (json.JSONDecodeError, IndexError, KeyError):
            pass

        summary = (
            f"deep-research complete: {dims} dimensions, {iters} total iters, "
            f"{elapsed}s elapsed"
        )
        if err_count:
            summary += f" ({err_count} dimension error(s))"
        summary += f". Report: {report_path}"

        await workflow.execute_activity(
            "emit_finding",
            EmitFindingInput(
                inbox_path=inp.inbox_path,
                run_id=inp.run_id,
                skill="deep-research",
                status="DONE",
                summary=summary,
                notify=inp.notify,
                timestamp_iso=timestamp,
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        await workflow.execute_activity(
            "finalize_manifest",
            FinalizeManifestInput(run_dir=run_dir, status="COMPLETED"),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=HAIKU_POLICY,
        )
        return summary
