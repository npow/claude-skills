"""loop-until-done: PRD generation → falsifiability judge → per-criterion verify loop.

Phases:
  1. PRD planner (Sonnet): generates stories with acceptance criteria.
  2. Falsifiability judge (Haiku): marks each criterion pass/fail for falsifiability.
  3. Executor (Sonnet): for each story, simulates completing the work.
  4. Verifier (Haiku): per-criterion verification (simulated in v0.2).
  5. Reviewer (Sonnet): final verdict.
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
class LoopUntilDoneInput:
    run_id: str
    task: str
    inbox_path: str
    run_dir: str
    max_iter: int = 5
    notify: bool = True
    # Prompts loaded from claude-skills at build_input time.
    prd_system_prompt: str = ""
    prd_user_prompt: str = ""
    falsifiability_system_prompt: str = ""
    falsifiability_user_prompt: str = ""
    executor_system_prompt: str = ""
    executor_user_prompt: str = ""
    verifier_system_prompt: str = ""
    verifier_user_prompt: str = ""
    reviewer_system_prompt: str = ""
    reviewer_user_prompt: str = ""


@workflow.defn(name="LoopUntilDoneWorkflow")
class LoopUntilDoneWorkflow:
    @workflow.run
    async def run(self, inp: LoopUntilDoneInput) -> str:
        prd_prompt_path = f"{inp.run_dir}/prd-prompt.txt"
        summary_path = f"{inp.run_dir}/summary.md"

        # --- Phase 1: PRD planner ---
        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(
                path=prd_prompt_path,
                content=inp.prd_user_prompt,
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        prd_result = await workflow.execute_activity(
            "spawn_subagent",
            SpawnSubagentInput(
                role="prd",
                tier_name="SONNET",
                system_prompt=inp.prd_system_prompt,
                user_prompt_path=prd_prompt_path,
                max_tokens=2048,
                tools_needed=False,
            ),
            start_to_close_timeout=timedelta(seconds=600),
            retry_policy=SONNET_POLICY,
        )
        stories_raw = prd_result.get("STORIES", "[]")
        stories = _parse_stories(stories_raw)

        if not stories:
            verdict = "budget_exhausted"
            summary_text = _build_summary(inp.task, stories, verdict)
            await _write_summary_and_emit(inp, summary_path, summary_text, verdict)
            return verdict

        # --- Phase 2: Falsifiability judge ---
        # Collect all criteria across all stories.
        all_criteria: list[dict[str, str]] = []
        for story in stories:
            for crit in story.get("criteria", []):
                all_criteria.append({
                    "criterion_id": crit.get("id", ""),
                    "criterion": crit.get("criterion", ""),
                    "story_id": story.get("id", ""),
                    "verification_command": crit.get("verification_command", ""),
                    "expected_pattern": crit.get("expected_pattern", ""),
                })

        falsifiability_prompt_path = f"{inp.run_dir}/falsifiability-prompt.txt"
        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(
                path=falsifiability_prompt_path,
                content=inp.falsifiability_user_prompt or _falsifiability_user_prompt(all_criteria),  # runtime-dynamic
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        falsifiability_result = await workflow.execute_activity(
            "spawn_subagent",
            SpawnSubagentInput(
                role="falsifiability",
                tier_name="HAIKU",
                system_prompt=inp.falsifiability_system_prompt,
                user_prompt_path=falsifiability_prompt_path,
                max_tokens=1024,
                tools_needed=False,
            ),
            start_to_close_timeout=timedelta(seconds=600),
            retry_policy=HAIKU_POLICY,
        )
        verdicts_raw = falsifiability_result.get("CRITERION_VERDICTS", "[]")
        verdicts = _parse_verdicts(verdicts_raw)
        # Build a set of criterion IDs that passed falsifiability.
        passing_criterion_ids = {
            v["criterion_id"] for v in verdicts if v.get("pass", False)
        }

        # Filter criteria down to only falsifiable ones.
        falsifiable_criteria = [
            c for c in all_criteria if c["criterion_id"] in passing_criterion_ids
        ]

        # --- Phase 3: Executor (per story) ---
        work_descriptions: dict[str, str] = {}
        for story in stories:
            story_id = story.get("id", "")
            executor_prompt_path = f"{inp.run_dir}/executor-{story_id}.txt"
            await workflow.execute_activity(
                "write_artifact",
                WriteArtifactInput(
                    path=executor_prompt_path,
                    content=inp.executor_user_prompt or _executor_user_prompt(story, inp.task),  # runtime-dynamic
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=HAIKU_POLICY,
            )
            executor_result = await workflow.execute_activity(
                "spawn_subagent",
                SpawnSubagentInput(
                    role="executor",
                    tier_name="SONNET",
                    system_prompt=inp.executor_system_prompt,
                    user_prompt_path=executor_prompt_path,
                    max_tokens=1024,
                    tools_needed=False,
                ),
                start_to_close_timeout=timedelta(seconds=600),
                retry_policy=SONNET_POLICY,
            )
            work_descriptions[story_id] = executor_result.get("WORK_DESCRIPTION", "")

        # --- Phase 4: Per-criterion verification (parallel) ---
        # Only verify falsifiable criteria.
        verify_results: dict[str, bool] = {}
        if falsifiable_criteria:
            verifier_coros = []
            for crit in falsifiable_criteria:
                verifier_prompt_path = f"{inp.run_dir}/verifier-{crit['criterion_id']}.txt"
                verifier_coros.append(
                    _run_verifier(inp, verifier_prompt_path, crit, work_descriptions)
                )
            verification_outcomes = await asyncio.gather(*verifier_coros, return_exceptions=True)
            for crit, outcome in zip(falsifiable_criteria, verification_outcomes):
                if isinstance(outcome, BaseException):
                    verify_results[crit["criterion_id"]] = False
                else:
                    verify_results[crit["criterion_id"]] = bool(outcome)

        # --- Phase 5: Reviewer ---
        reviewer_prompt_path = f"{inp.run_dir}/reviewer-prompt.txt"
        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(
                path=reviewer_prompt_path,
                content=inp.reviewer_user_prompt or _reviewer_user_prompt(  # runtime-dynamic
                    stories=stories,
                    falsifiable_criteria=falsifiable_criteria,
                    verify_results=verify_results,
                    work_descriptions=work_descriptions,
                ),
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        reviewer_result = await workflow.execute_activity(
            "spawn_subagent",
            SpawnSubagentInput(
                role="reviewer",
                tier_name="SONNET",
                system_prompt=inp.reviewer_system_prompt,
                user_prompt_path=reviewer_prompt_path,
                max_tokens=1024,
                tools_needed=False,
            ),
            start_to_close_timeout=timedelta(seconds=600),
            retry_policy=SONNET_POLICY,
        )
        verdict = reviewer_result.get(
            "OVERALL_VERDICT", "all_stories_passed"
        )

        # Write summary and emit finding.
        summary_text = _build_summary(inp.task, stories, verdict)
        await _write_summary_and_emit(inp, summary_path, summary_text, verdict)
        return verdict


async def _run_verifier(
    inp: LoopUntilDoneInput,
    verifier_prompt_path: str,
    crit: dict[str, str],
    work_descriptions: dict[str, str],
) -> bool:
    await workflow.execute_activity(
        "write_artifact",
        WriteArtifactInput(
            path=verifier_prompt_path,
            content=inp.verifier_user_prompt or _verifier_user_prompt(crit, work_descriptions),  # runtime-dynamic
        ),
        start_to_close_timeout=timedelta(seconds=10),
        retry_policy=HAIKU_POLICY,
    )
    result = await workflow.execute_activity(
        "spawn_subagent",
        SpawnSubagentInput(
            role="verifier",
            tier_name="HAIKU",
            system_prompt=inp.verifier_system_prompt,
            user_prompt_path=verifier_prompt_path,
            max_tokens=512,
            tools_needed=False,
        ),
        start_to_close_timeout=timedelta(seconds=600),
        retry_policy=HAIKU_POLICY,
    )
    verified_raw = result.get("VERIFIED", "false")
    return verified_raw.strip().lower() == "true"


async def _write_summary_and_emit(
    inp: LoopUntilDoneInput,
    summary_path: str,
    summary_text: str,
    verdict: str,
) -> None:
    await workflow.execute_activity(
        "write_artifact",
        WriteArtifactInput(path=summary_path, content=summary_text),
        start_to_close_timeout=timedelta(seconds=10),
        retry_policy=HAIKU_POLICY,
    )
    timestamp = workflow.now().isoformat(timespec="seconds")
    await workflow.execute_activity(
        "emit_finding",
        EmitFindingInput(
            inbox_path=inp.inbox_path,
            run_id=inp.run_id,
            skill="loop-until-done",
            status=verdict,
            summary=f"loop-until-done: {verdict}",
            notify=inp.notify,
            timestamp_iso=timestamp,
        ),
        start_to_close_timeout=timedelta(seconds=10),
        retry_policy=HAIKU_POLICY,
    )


# --- prompt templates ---



def _falsifiability_user_prompt(criteria: list[dict[str, str]]) -> str:
    return (
        f"Criteria to evaluate ({len(criteria)} total):\n"
        f"{json.dumps(criteria, indent=2)}\n\n"
        "For each, emit pass=true if concretely verifiable, pass=false if not."
    )



def _executor_user_prompt(story: dict[str, object], task: str) -> str:
    return (
        f"Overall task: {task}\n\n"
        f"Story: {story.get('title', '')}\n"
        f"Criteria:\n{json.dumps(story.get('criteria', []), indent=2)}\n\n"
        "Describe what work was done to complete this story (simulate in v0.2)."
    )



def _verifier_user_prompt(
    crit: dict[str, str], work_descriptions: dict[str, str]
) -> str:
    story_id = crit.get("story_id", "")
    work = work_descriptions.get(story_id, "(no work description)")
    return (
        f"Criterion: {crit.get('criterion', '')}\n"
        f"Verification command: {crit.get('verification_command', '')}\n"
        f"Expected pattern: {crit.get('expected_pattern', '')}\n\n"
        f"Work description:\n{work}\n\n"
        "Does the work description satisfy this criterion? (simulate in v0.2)"
    )



def _reviewer_user_prompt(
    stories: list[dict[str, object]],
    falsifiable_criteria: list[dict[str, str]],
    verify_results: dict[str, bool],
    work_descriptions: dict[str, str],
) -> str:
    lines = [f"Stories ({len(stories)}):", json.dumps(stories, indent=2), ""]
    lines.append(f"Falsifiable criteria ({len(falsifiable_criteria)}):")
    for crit in falsifiable_criteria:
        cid = crit.get("criterion_id", "")
        passed = verify_results.get(cid, False)
        lines.append(f"  {cid}: {'PASS' if passed else 'FAIL'} — {crit.get('criterion', '')}")
    lines.append("")
    lines.append("Work descriptions:")
    for story_id, desc in work_descriptions.items():
        lines.append(f"  {story_id}: {desc}")
    lines.append("\nEmit the appropriate OVERALL_VERDICT label.")
    return "\n".join(lines)


def _build_summary(task: str, stories: list[dict[str, object]], verdict: str) -> str:
    lines = [
        "# loop-until-done Summary",
        "",
        f"**Task:** {task}",
        f"**Verdict:** {verdict}",
        "",
        f"## Stories ({len(stories)})",
        "",
    ]
    for story in stories:
        title = story.get("title", "untitled")
        sid = story.get("id", "?")
        lines.append(f"- [{sid}] {title}")
        for crit in story.get("criteria", []):  # type: ignore[union-attr]
            if isinstance(crit, dict):
                lines.append(f"  - {crit.get('criterion', '')}")
    lines.append("")
    lines.append(f"**Terminal label:** `{verdict}`")
    return "\n".join(lines)


# --- JSON helpers ---


def _parse_stories(raw: str) -> list[dict[str, object]]:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [s for s in parsed if isinstance(s, dict)]
    except json.JSONDecodeError:
        pass
    return []


def _parse_verdicts(raw: str) -> list[dict[str, object]]:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [v for v in parsed if isinstance(v, dict)]
    except json.JSONDecodeError:
        pass
    return []
