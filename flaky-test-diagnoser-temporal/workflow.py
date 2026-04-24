"""flaky-test-diagnoser: run a test N times, hypothesize flakiness, report.

Phases:
  1. Run test N times (run_test_subprocess activity) → compute fail_rate.
     Early-exit if not_reproduced (fail_rate == 0) or consistently_broken (fail_rate == 1.0).
  2. Hypothesis generation (Sonnet): 3-5 hypotheses across known flakiness categories.
  3. Hypothesis ranking (Haiku): rank by plausibility.
  4. Synthesis (Sonnet): write markdown report + termination label.
  5. Emit finding to INBOX + desktop notification.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from sagaflow.durable.activities import (
        EmitFindingInput,
        SpawnSubagentInput,
        WriteArtifactInput,
    )
    from sagaflow.durable.retry_policies import HAIKU_POLICY, SONNET_POLICY


@dataclass(frozen=True)
class FlakyTestInput:
    run_id: str
    test_identifier: str
    run_dir: str
    inbox_path: str
    run_command: str
    n_runs: int = 10
    notify: bool = True
    # Prompts loaded from claude-skills at build_input time. Empty string means
    # fall back to inline default.
    hyp_system_prompt: str = ""
    hyp_user_prompt: str = ""
    judge_system_prompt: str = ""
    judge_user_prompt: str = ""
    synth_system_prompt: str = ""
    synth_user_prompt: str = ""


@workflow.defn(name="FlakyTestWorkflow")
class FlakyTestWorkflow:
    @workflow.run
    async def run(self, inp: FlakyTestInput) -> str:
        report_path = f"{inp.run_dir}/report.md"
        hyp_prompt_path = f"{inp.run_dir}/hyp-prompt.txt"
        judge_prompt_path = f"{inp.run_dir}/judge-prompt.txt"
        synth_prompt_path = f"{inp.run_dir}/synth-prompt.txt"

        # ── Phase 1: run test N times ──────────────────────────────────────────
        run_coros = [
            workflow.execute_activity(
                "run_test_subprocess",
                args=[inp.run_command, 60],
                start_to_close_timeout=timedelta(seconds=600),
                retry_policy=HAIKU_POLICY,
            )
            for _ in range(inp.n_runs)
        ]
        results = await asyncio.gather(*run_coros, return_exceptions=True)

        run_records: list[dict[str, int]] = []
        for r in results:
            if isinstance(r, BaseException):
                run_records.append({"exit_code": 1, "duration_ms": 0})
            else:
                run_records.append(r)  # type: ignore[arg-type]

        failures = sum(1 for r in run_records if r["exit_code"] != 0)
        fail_rate = failures / max(len(run_records), 1)

        timestamp = workflow.now().isoformat(timespec="seconds")

        if fail_rate == 0.0:
            summary = f"Test passed all {inp.n_runs} runs — not reproduced."
            await workflow.execute_activity(
                "write_artifact",
                WriteArtifactInput(
                    path=report_path,
                    content=_not_reproduced_report(inp.test_identifier, inp.n_runs),
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=HAIKU_POLICY,
            )
            await workflow.execute_activity(
                "emit_finding",
                EmitFindingInput(
                    inbox_path=inp.inbox_path,
                    run_id=inp.run_id,
                    skill="flaky-test-diagnoser",
                    status="not_reproduced",
                    summary=summary,
                    notify=inp.notify,
                    timestamp_iso=timestamp,
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=HAIKU_POLICY,
            )
            return summary

        if fail_rate == 1.0:
            summary = f"Test failed all {inp.n_runs} runs — consistently broken, not flaky."
            await workflow.execute_activity(
                "write_artifact",
                WriteArtifactInput(
                    path=report_path,
                    content=_consistently_broken_report(inp.test_identifier, inp.n_runs),
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=HAIKU_POLICY,
            )
            await workflow.execute_activity(
                "emit_finding",
                EmitFindingInput(
                    inbox_path=inp.inbox_path,
                    run_id=inp.run_id,
                    skill="flaky-test-diagnoser",
                    status="consistently_broken",
                    summary=summary,
                    notify=inp.notify,
                    timestamp_iso=timestamp,
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=HAIKU_POLICY,
            )
            return summary

        # ── Phase 2: hypothesis generation ────────────────────────────────────
        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(
                path=hyp_prompt_path,
                content=inp.hyp_user_prompt or _hyp_user_prompt(inp.test_identifier, run_records, fail_rate),  # runtime-dynamic
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        hyp_result = await workflow.execute_activity(
            "spawn_subagent",
            SpawnSubagentInput(
                role="hypothesis-gen",
                tier_name="SONNET",
                system_prompt=inp.hyp_system_prompt,
                user_prompt_path=hyp_prompt_path,
                max_tokens=2048,
                tools_needed=False,
            ),
            start_to_close_timeout=timedelta(seconds=600),
            retry_policy=SONNET_POLICY,
        )
        hypotheses = _parse_hypotheses(hyp_result.get("HYPOTHESES", "[]"))

        # ── Phase 3: judge / rank hypotheses ──────────────────────────────────
        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(
                path=judge_prompt_path,
                content=inp.judge_user_prompt or _judge_user_prompt(inp.test_identifier, hypotheses, fail_rate),  # runtime-dynamic
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        judge_result = await workflow.execute_activity(
            "spawn_subagent",
            SpawnSubagentInput(
                role="judge",
                tier_name="HAIKU",
                system_prompt=inp.judge_system_prompt,
                user_prompt_path=judge_prompt_path,
                max_tokens=1024,
                tools_needed=False,
            ),
            start_to_close_timeout=timedelta(seconds=600),
            retry_policy=HAIKU_POLICY,
        )
        rankings = _parse_rankings(judge_result.get("RANKINGS", "[]"))

        # ── Phase 4: synthesis ────────────────────────────────────────────────
        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(
                path=synth_prompt_path,
                content=inp.synth_user_prompt or _synth_user_prompt(  # runtime-dynamic
                    inp.test_identifier, hypotheses, rankings, run_records, fail_rate, inp.n_runs
                ),
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        synth_result = await workflow.execute_activity(
            "spawn_subagent",
            SpawnSubagentInput(
                role="synth",
                tier_name="SONNET",
                system_prompt=inp.synth_system_prompt,
                user_prompt_path=synth_prompt_path,
                max_tokens=4096,
                tools_needed=False,
            ),
            start_to_close_timeout=timedelta(seconds=600),
            retry_policy=SONNET_POLICY,
        )
        report_md = synth_result.get(
            "REPORT",
            _fallback_report(inp.test_identifier, hypotheses, rankings, fail_rate, inp.n_runs),
        )
        termination_label = synth_result.get("TERMINATION_LABEL", "inconclusive_after_N_runs")

        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(path=report_path, content=report_md),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )

        # ── Phase 5: emit finding ─────────────────────────────────────────────
        summary = (
            f"fail_rate={fail_rate:.0%} over {inp.n_runs} runs; "
            f"{len(hypotheses)} hypotheses; label={termination_label}"
        )
        await workflow.execute_activity(
            "emit_finding",
            EmitFindingInput(
                inbox_path=inp.inbox_path,
                run_id=inp.run_id,
                skill="flaky-test-diagnoser",
                status=termination_label,
                summary=summary,
                notify=inp.notify,
                timestamp_iso=timestamp,
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        return f"{summary}\nReport: {report_path}"


# ── prompt templates ───────────────────────────────────────────────────────────



def _hyp_user_prompt(
    test_identifier: str,
    run_records: list[dict[str, int]],
    fail_rate: float,
) -> str:
    passes = sum(1 for r in run_records if r["exit_code"] == 0)
    failures = sum(1 for r in run_records if r["exit_code"] != 0)
    avg_pass_ms = (
        sum(r["duration_ms"] for r in run_records if r["exit_code"] == 0) // max(passes, 1)
    )
    avg_fail_ms = (
        sum(r["duration_ms"] for r in run_records if r["exit_code"] != 0) // max(failures, 1)
    )
    return (
        f"Test: {test_identifier}\n"
        f"Fail rate: {fail_rate:.1%} ({failures}/{len(run_records)} runs failed)\n"
        f"Avg duration (pass): {avg_pass_ms}ms\n"
        f"Avg duration (fail): {avg_fail_ms}ms\n\n"
        "Generate 3-5 independent hypotheses explaining the flakiness. "
        "Cover different categories — don't duplicate mechanisms."
    )



def _judge_user_prompt(
    test_identifier: str,
    hypotheses: list[dict[str, str]],
    fail_rate: float,
) -> str:
    return (
        f"Test: {test_identifier}\n"
        f"Fail rate: {fail_rate:.1%}\n\n"
        f"Hypotheses:\n{json.dumps(hypotheses, indent=2)}\n\n"
        "Rank these hypotheses from most to least plausible. "
        "Consider the fail rate as a clue about timing vs state issues."
    )



def _synth_user_prompt(
    test_identifier: str,
    hypotheses: list[dict[str, str]],
    rankings: list[dict[str, str]],
    run_records: list[dict[str, int]],
    fail_rate: float,
    n_runs: int,
) -> str:
    return (
        f"Test: {test_identifier}\n"
        f"Runs: {len(run_records)} (requested: {n_runs})\n"
        f"Fail rate: {fail_rate:.1%}\n\n"
        f"Hypotheses:\n{json.dumps(hypotheses, indent=2)}\n\n"
        f"Rankings:\n{json.dumps(rankings, indent=2)}\n\n"
        "Write the flakiness diagnosis report."
    )


def _not_reproduced_report(test_identifier: str, n_runs: int) -> str:
    return (
        f"# Flaky Test Diagnosis: Not Reproduced\n\n"
        f"**Test:** {test_identifier}\n"
        f"**Runs:** {n_runs}\n"
        f"**Result:** Passed all {n_runs} runs — flakiness not reproduced in this run.\n\n"
        "Consider increasing `n_runs` or checking environment differences.\n"
    )


def _consistently_broken_report(test_identifier: str, n_runs: int) -> str:
    return (
        f"# Flaky Test Diagnosis: Consistently Broken\n\n"
        f"**Test:** {test_identifier}\n"
        f"**Runs:** {n_runs}\n"
        f"**Result:** Failed all {n_runs} runs — this is not flaky, it is consistently broken.\n\n"
        "Fix the underlying test failure before investigating flakiness.\n"
    )


def _fallback_report(
    test_identifier: str,
    hypotheses: list[dict[str, str]],
    rankings: list[dict[str, str]],
    fail_rate: float,
    n_runs: int,
) -> str:
    rank_map = {r["hyp_id"]: r["rank"] for r in rankings if "hyp_id" in r and "rank" in r}
    sorted_hyps = sorted(hypotheses, key=lambda h: rank_map.get(h.get("id", ""), 999))
    lines = [
        "# Flaky Test Diagnosis (fallback synthesis)",
        "",
        f"**Test:** {test_identifier}",
        f"**Fail rate:** {fail_rate:.1%} over {n_runs} runs",
        "",
        "## Ranked Hypotheses",
        "",
    ]
    for h in sorted_hyps:
        rank = rank_map.get(h.get("id", ""), "?")
        lines.append(
            f"1. [rank {rank}] **{h.get('category', '?')}** — {h.get('mechanism', '?')}"
        )
    return "\n".join(lines)


# ── parsers ────────────────────────────────────────────────────────────────────


def _parse_hypotheses(raw: str) -> list[dict[str, str]]:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [h for h in parsed if isinstance(h, dict)]
    except json.JSONDecodeError:
        pass
    return []


def _parse_rankings(raw: str) -> list[dict[str, str]]:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [r for r in parsed if isinstance(r, dict)]
    except json.JSONDecodeError:
        pass
    return []
