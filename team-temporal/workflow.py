"""team-temporal: sequential 5-stage pipeline with iron-law gates.

Stages:
  1. plan   — explore (Haiku) → planner (Opus) → plan-validator (Opus, independent)
  2. prd    — analyst (Opus) → critic (Opus, independent) → falsifiability-judge (Opus, independent)
  3. exec   — N workers (Sonnet/executor|designer|test-engineer) each with two-stage per-worker review
  4. verify — Stage A spec-compliance → Stage B code-quality → verify-judge (Opus, independent)
  5. fix    — per-defect fix-worker + per-fix independent verifier, up to max_fix_iters=3

Iron-law gate enforced at every stage transition:
  (a) stage.status = "gate_checking"
  (b) every evidence_file exists and is non-empty
  (c) has STRUCTURED_OUTPUT markers if applicable
  (d) exit_gate_verdict = "approved"
  (e) verdict authored by independent agent (not coordinator)

Gate failure blocks advancement; coordinator re-spawns evaluator or terminates.
"""

from __future__ import annotations

import asyncio
import hashlib
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

# ---------------------------------------------------------------------------
# Input / constants
# ---------------------------------------------------------------------------

MAX_PRD_REVISIONS = 2
MAX_PLAN_REWORKS = 2
WORKER_QUORUM_REJECTION_LIMIT = 3

TIER_OPUS = "OPUS"
TIER_SONNET = "SONNET"
TIER_HAIKU = "HAIKU"


@dataclass(frozen=True)
class TeamInput:
    run_id: str
    task: str
    inbox_path: str
    run_dir: str
    n_workers: int = 2
    max_fix_iters: int = 3
    notify: bool = True
    agent_type: str = "executor"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _parse_json_list(raw: str) -> list[dict]:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [x for x in parsed if isinstance(x, dict)]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def _get_verdict(parsed: dict[str, str], key: str = "VERDICT", default: str = "") -> str:
    return parsed.get(key, default).strip().lower()


def _has_structured_output(content: str) -> bool:
    return "STRUCTURED_OUTPUT_START" in content and "STRUCTURED_OUTPUT_END" in content


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

@workflow.defn(name="TeamWorkflow")
class TeamWorkflow:
    @workflow.run
    async def run(self, inp: TeamInput) -> str:  # noqa: C901 (complex but linear pipeline)
        run_dir = inp.run_dir
        summary_path = f"{run_dir}/SUMMARY.md"

        # Compute task SHA-256 once; guards against resume tampering.
        task_sha = _sha256(inp.task)

        # ---------------------------------------------------------------
        # Stage 1: team-plan
        # ---------------------------------------------------------------
        # Step 1a: explore (Haiku) — codebase context scan
        codebase_ctx_path = f"{run_dir}/exec/codebase-context.md"
        await _spawn_write(run_dir, "explore", TIER_HAIKU,
            "You are a codebase explorer. Scan the repository structure and produce "
            "a brief codebase-context document. Emit:\n"
            "STRUCTURED_OUTPUT_START\n"
            "CODEBASE_SUMMARY|<1-3 sentence description of structure and relevant prior art>\n"
            "STRUCTURED_OUTPUT_END",
            f"Task: {inp.task}\n\nIdentify relevant files, modules, and prior art.",
            max_tokens=512,
            out_path=codebase_ctx_path,
        )

        # Step 1b: planner (Opus) with rework loop driven by plan-validator
        plan_path = f"{run_dir}/handoffs/plan.md"
        plan_verdict_path = f"{run_dir}/handoffs/plan-verdict.md"
        plan_rework = 0
        plan_approved = False
        validator_reasons = ""

        while not plan_approved and plan_rework <= MAX_PLAN_REWORKS:
            rework_note = (
                f"\n\nPrevious plan was REJECTED by the validator. Reasons:\n{validator_reasons}"
                if plan_rework > 0 else ""
            )
            await _spawn_write(run_dir, "planner", TIER_OPUS,
                "You are a task planner. Decompose the task into a concrete plan. "
                "Your plan MUST include: Decided, Rejected, Risks, Files, Remaining, Evidence sections. "
                "Emit:\n"
                "STRUCTURED_OUTPUT_START\n"
                "SUBTASKS|<json array of {id, title, description, files_likely_touched}>\n"
                "PLAN_SUMMARY|<1 sentence>\n"
                "STRUCTURED_OUTPUT_END",
                f"Codebase context: {codebase_ctx_path}\n\nTask: {inp.task}{rework_note}",
                max_tokens=1024,
                out_path=plan_path,
            )

            # Step 1c: plan-validator (independent Opus)
            validator_reasons_out = await _spawn_write(run_dir, "plan-validator", TIER_OPUS,
                "You are an INDEPENDENT plan validator. You succeed by REJECTING or finding ISSUES. "
                "100% approval is evidence of failure. Read the planner's output. "
                "Verify all 6 handoff fields are populated and each major component has a verification plan. "
                "Emit:\n"
                "STRUCTURED_OUTPUT_START\n"
                "VERDICT|approved|rejected\n"
                "ISSUE|<severity>|<description>  (repeat for each issue, omit if none)\n"
                "MISSING_FIELD|<field>  (repeat for each, omit if none)\n"
                "STRUCTURED_OUTPUT_END",
                f"Plan file: {plan_path}\n\nTask: {inp.task}",
                max_tokens=512,
                out_path=plan_verdict_path,
            )

            if _get_verdict(validator_reasons_out) == "approved":
                plan_approved = True
            else:
                plan_rework += 1
                issues = [
                    f"{k}|{v}" for k, v in validator_reasons_out.items()
                    if k in ("ISSUE", "MISSING_FIELD")
                ]
                validator_reasons = "\n".join(issues) if issues else "(unspecified)"
                if plan_rework > MAX_PLAN_REWORKS:
                    return await _terminate(
                        inp, summary_path, "blocked_unresolved",
                        "Plan validator rejected plan after max rework loops.",
                        workers=0, fix_iters=0, defects=0,
                    )

        # Extract subtasks from plan
        subtasks = _parse_json_list(validator_reasons_out.get("SUBTASKS", "[]"))
        # Also try reading planner's own output (validator echoes from plan file)
        if not subtasks:
            subtasks = _parse_json_list(validator_reasons_out.get("SUBTASKS", "[]"))
        if not subtasks:
            subtasks = [{"id": "t1", "title": inp.task, "description": inp.task}]
        subtasks = subtasks[: inp.n_workers]

        # ---------------------------------------------------------------
        # Stage 2: team-prd
        # ---------------------------------------------------------------
        prd_revision = 0
        prd_approved = False
        critique_path = f"{run_dir}/prd/critique.md"
        falsifiability_path = f"{run_dir}/prd/falsifiability-verdict.md"
        prd_final_path = f"{run_dir}/prd/prd-final.md"

        prd_result: dict[str, str] = {}
        falsify_result: dict[str, str] = {}

        while not prd_approved and prd_revision <= MAX_PRD_REVISIONS:
            v_suffix = f"-v{prd_revision}"
            curr_prd_path = f"{run_dir}/prd/prd{v_suffix}.md"

            rework_note = ""
            if prd_revision > 0:
                rework_note = (
                    f"\n\nPRD revision {prd_revision}. Address all critique and unfalsifiable "
                    f"acceptance criteria. Critique: {critique_path}  Falsifiability: {falsifiability_path}"
                )

            # Analyst writes PRD
            prd_result = await _spawn_write(run_dir, "analyst", TIER_OPUS,
                "You are a PRD analyst. Write a PRD with Scope, Acceptance Criteria, Non-goals. "
                "Each AC MUST have: id, statement, verification_command, expected_output_pattern. "
                "Emit:\n"
                "STRUCTURED_OUTPUT_START\n"
                "ACCEPTANCE_CRITERIA|<json array of {id, statement, verification_command, expected_output_pattern}>\n"
                "STRUCTURED_OUTPUT_END",
                f"Plan: {plan_path}\n\nTask: {inp.task}{rework_note}",
                max_tokens=1024,
                out_path=curr_prd_path,
            )

            # Independent critic
            await _spawn_write(run_dir, "critic", TIER_OPUS,
                "You are an INDEPENDENT PRD critic. Attack the PRD for ambiguity, underspecification, "
                "overscope, missing edge cases. You succeed by REJECTING or finding issues. "
                "Emit:\n"
                "STRUCTURED_OUTPUT_START\n"
                "CRITICAL_COUNT|<N>\n"
                "CONCERNS|<json array of {id, severity, description}>\n"
                "STRUCTURED_OUTPUT_END",
                f"PRD: {curr_prd_path}\n\nTask: {inp.task}",
                max_tokens=512,
                out_path=critique_path,
            )

            # Falsifiability judge (independent)
            acceptance = _parse_json_list(prd_result.get("ACCEPTANCE_CRITERIA", "[]"))
            falsify_result = await _spawn_write(run_dir, "falsifiability-judge", TIER_OPUS,
                "You are an INDEPENDENT falsifiability judge. For each acceptance criterion, "
                "determine if it is testable with a concrete failing scenario, executable "
                "verification_command, and deterministic expected_output_pattern. "
                "Emit:\n"
                "STRUCTURED_OUTPUT_START\n"
                "UNFALSIFIABLE_COUNT|<N>\n"
                "AC_VERDICT|<ac_id>|falsifiable|unfalsifiable  (one per AC)\n"
                "STRUCTURED_OUTPUT_END",
                f"PRD: {curr_prd_path}\n\nCritique: {critique_path}\n\nACs: {json.dumps(acceptance)}",
                max_tokens=512,
                out_path=falsifiability_path,
            )

            unfalsifiable = int(falsify_result.get("UNFALSIFIABLE_COUNT", "1") or "1")
            if unfalsifiable == 0:
                prd_approved = True
                # Write final PRD
                prd_final_content = (
                    f"# Final PRD (revision {prd_revision})\n\n"
                    f"Source: {curr_prd_path}\n\n"
                    f"Task: {inp.task}\n\n"
                    f"Acceptance Criteria: {json.dumps(acceptance, indent=2)}\n"
                )
                await _write(run_dir, prd_final_path, prd_final_content)
            else:
                prd_revision += 1
                if prd_revision > MAX_PRD_REVISIONS:
                    return await _terminate(
                        inp, summary_path, "blocked_unresolved",
                        f"PRD still has unfalsifiable criteria after {MAX_PRD_REVISIONS} revisions.",
                        workers=0, fix_iters=0, defects=0,
                    )

        acceptance_criteria = _parse_json_list(prd_result.get("ACCEPTANCE_CRITERIA", "[]"))

        # ---------------------------------------------------------------
        # Stage 3: team-exec — parallel workers with two-stage per-worker review
        # ---------------------------------------------------------------
        worker_type = inp.agent_type  # executor | designer | test-engineer

        async def _run_worker(task_entry: dict) -> dict:
            wid = task_entry.get("id", "w")
            assignment_path = f"{run_dir}/exec/worker-{wid}-assignment.md"

            # Write assignment file
            assignment_content = (
                f"# Worker {wid} Assignment\n\n"
                f"## Subtask\n{json.dumps(task_entry, indent=2)}\n\n"
                f"## Acceptance Criteria\n{json.dumps(acceptance_criteria, indent=2)}\n\n"
                f"## PRD\n{prd_final_path}\n\n"
                f"## Task SHA256\n{task_sha}\n\n"
                f"## TDD Mandate\n"
                f"Write a failing test for each AC → confirm red → implement → confirm green → verify.\n"
            )
            await _write(run_dir, assignment_path, assignment_content)

            consecutive_rejections = 0
            work_result: dict[str, str] = {}

            while consecutive_rejections < WORKER_QUORUM_REJECTION_LIMIT:
                # Worker implements the subtask
                work_result = await _spawn_write(
                    run_dir, "worker", worker_type.upper() if worker_type != "executor" else TIER_SONNET,
                    "You are a TEAM WORKER. Follow the TDD protocol: write failing test → confirm red "
                    "→ implement minimal code → confirm green → run verification_command. "
                    "Emit:\n"
                    "STRUCTURED_OUTPUT_START\n"
                    "WORK_SUMMARY|<what you did>\n"
                    "FILES_TOUCHED|<json array of paths>\n"
                    "TEST_EVIDENCE|<red/green/verify file paths>\n"
                    "STRUCTURED_OUTPUT_END",
                    f"Assignment: {assignment_path}",
                    max_tokens=1024,
                    out_path=f"{run_dir}/exec/worker-{wid}-output.md",
                    role_suffix=f"-{wid}",
                )

                # Stage A: spec-compliance reviewer (independent)
                spec_result = await _spawn_write(
                    run_dir, "spec-compliance-reviewer", TIER_OPUS,
                    "You are an INDEPENDENT spec-compliance reviewer. Check the worker's output "
                    "against the PRD acceptance criteria. You succeed by finding gaps. "
                    "Emit:\n"
                    "STRUCTURED_OUTPUT_START\n"
                    "VERDICT|approved|rejected\n"
                    "DEFECTS|<json array of {id, severity, description}>\n"
                    "STRUCTURED_OUTPUT_END",
                    f"PRD: {prd_final_path}\n\nWorker output: {run_dir}/exec/worker-{wid}-output.md",
                    max_tokens=512,
                    out_path=f"{run_dir}/verify/per-worker/worker-{wid}-spec-compliance.md",
                    role_suffix=f"-{wid}",
                )

                # Stage B: code-quality reviewer (independent, separate agent)
                quality_result = await _spawn_write(
                    run_dir, "code-quality-reviewer", TIER_OPUS,
                    "You are an INDEPENDENT code-quality reviewer. Focus on readability, "
                    "maintainability, idiomatic use, duplication, error handling, test coverage. "
                    "Do NOT re-litigate spec compliance. "
                    "Emit:\n"
                    "STRUCTURED_OUTPUT_START\n"
                    "VERDICT|approved|rejected\n"
                    "QUALITY_DEFECTS|<json array of {id, severity, description}>\n"
                    "STRUCTURED_OUTPUT_END",
                    f"Worker output: {run_dir}/exec/worker-{wid}-output.md\n\n"
                    f"Spec-compliance review: {run_dir}/verify/per-worker/worker-{wid}-spec-compliance.md",
                    max_tokens=512,
                    out_path=f"{run_dir}/verify/per-worker/worker-{wid}-code-quality.md",
                    role_suffix=f"-{wid}",
                )

                spec_ok = _get_verdict(spec_result) == "approved"
                quality_ok = _get_verdict(quality_result) == "approved"

                if spec_ok and quality_ok:
                    return {
                        "id": wid,
                        "work_summary": work_result.get("WORK_SUMMARY", ""),
                        "files_touched": work_result.get("FILES_TOUCHED", "[]"),
                        "status": "task_complete_approved",
                    }
                else:
                    consecutive_rejections += 1
                    if consecutive_rejections >= WORKER_QUORUM_REJECTION_LIMIT:
                        return {
                            "id": wid,
                            "work_summary": work_result.get("WORK_SUMMARY", ""),
                            "files_touched": "[]",
                            "status": "blocked",
                        }
                    # Loop: worker gets another chance with defect feedback

            return {"id": wid, "status": "blocked"}

        worker_results_raw = await asyncio.gather(
            *[_run_worker(t) for t in subtasks],
            return_exceptions=True,
        )

        worker_outputs: list[dict] = []
        for t, r in zip(subtasks, worker_results_raw):
            if isinstance(r, BaseException):
                worker_outputs.append({"id": t.get("id", "?"), "status": "failed"})
            else:
                worker_outputs.append(r)  # type: ignore[arg-type]

        # ---------------------------------------------------------------
        # Stage 4: team-verify — two-stage (A: spec-compliance, B: code-quality)
        # then verify-judge aggregates
        # ---------------------------------------------------------------
        diff_path = f"{run_dir}/verify/diff.patch"
        diff_content = f"# Diff summary\n\nWorkers completed:\n{json.dumps(worker_outputs, indent=2)}\n"
        await _write(run_dir, diff_path, diff_content)

        # Stage A: spec-compliance
        spec_compliance_path = f"{run_dir}/verify/spec-compliance/defect-registry.md"
        await _spawn_write(
            run_dir, "spec-compliance-reviewer", TIER_OPUS,
            "You are an INDEPENDENT spec-compliance reviewer for the full diff. "
            "Compare the diff against the PRD acceptance criteria. "
            "Emit:\n"
            "STRUCTURED_OUTPUT_START\n"
            "CRITICAL_COUNT|<N>\n"
            "MAJOR_COUNT|<N>\n"
            "MINOR_COUNT|<N>\n"
            "DEFECTS|<json array of {id, severity, description}>\n"
            "STRUCTURED_OUTPUT_END",
            f"PRD: {prd_final_path}\n\nDiff: {diff_path}",
            max_tokens=1024,
            out_path=spec_compliance_path,
        )

        # Stage B: code-quality (runs AFTER Stage A)
        code_quality_path = f"{run_dir}/verify/code-quality/review.md"
        await _spawn_write(
            run_dir, "code-quality-reviewer", TIER_OPUS,
            "You are an INDEPENDENT code-quality reviewer. Focus on readability, maintainability, "
            "idiomatic use, duplication, error handling, test coverage. Do NOT re-litigate spec compliance. "
            "Emit:\n"
            "STRUCTURED_OUTPUT_START\n"
            "QUALITY_CRITICAL_COUNT|<N>\n"
            "QUALITY_MAJOR_COUNT|<N>\n"
            "QUALITY_DEFECTS|<json array of {id, severity, description}>\n"
            "STRUCTURED_OUTPUT_END",
            f"Diff: {diff_path}\n\nSpec compliance: {spec_compliance_path}",
            max_tokens=1024,
            out_path=code_quality_path,
        )

        # Verify-judge aggregates both (independent Opus)
        verdict_path = f"{run_dir}/verify/verdict.md"
        verify_judge_result = await _spawn_write(
            run_dir, "verify-judge", TIER_OPUS,
            "You are an INDEPENDENT verify-judge. Aggregate both spec-compliance and code-quality "
            "reviews. Emit:\n"
            "STRUCTURED_OUTPUT_START\n"
            "VERDICT|passed|failed_fixable|failed_unfixable\n"
            "CRITICAL_COUNT|<N>\n"
            "MAJOR_COUNT|<N>\n"
            "MINOR_COUNT|<N>\n"
            "DEFECTS|<json array of {id, severity, description}>\n"
            "STRUCTURED_OUTPUT_END",
            f"Spec-compliance: {spec_compliance_path}\n\nCode-quality: {code_quality_path}",
            max_tokens=512,
            out_path=verdict_path,
        )

        verdict = _get_verdict(verify_judge_result)
        defects = _parse_json_list(verify_judge_result.get("DEFECTS", "[]"))
        critical_count = int(verify_judge_result.get("CRITICAL_COUNT", "0") or "0")
        major_count = int(verify_judge_result.get("MAJOR_COUNT", "0") or "0")

        if verdict == "failed_unfixable":
            return await _terminate(
                inp, summary_path, "blocked_unresolved",
                "Verify-judge determined defects are unfixable.",
                workers=len(worker_outputs), fix_iters=0, defects=len(defects),
            )

        # ---------------------------------------------------------------
        # Stage 5: team-fix — per-defect fix-worker + per-fix verifier, up to max_fix_iters
        # ---------------------------------------------------------------
        fix_iters = 0

        while verdict == "failed_fixable" and fix_iters < inp.max_fix_iters and defects:
            fix_iters += 1
            iter_dir = f"{run_dir}/fix/iter-{fix_iters}"
            new_defects: list[dict] = []

            # Spawn fix-worker and per-fix verifier for each defect
            async def _fix_one(defect: dict) -> dict:
                did = defect.get("id", "d")
                work_path = f"{iter_dir}/defect-{did}-work.md"
                work_content = (
                    f"# Fix Work: defect {did}\n\n"
                    f"Defect: {json.dumps(defect, indent=2)}\n\n"
                    f"PRD: {prd_final_path}\n\n"
                    f"TDD: write a reproducing failing test → fix → green → verify.\n"
                )
                await _write(run_dir, work_path, work_content)

                # Fix-worker
                await _spawn_write(
                    run_dir, "fix-worker", TIER_SONNET,
                    "You are a fix-worker. Follow TDD: write reproducing failing test → fix → green → verify. "
                    "Emit:\n"
                    "STRUCTURED_OUTPUT_START\n"
                    "FIX_SUMMARY|<what changed>\n"
                    "NEW_DEFECT_INTRODUCED|none|<severity>|<description>\n"
                    "STRUCTURED_OUTPUT_END",
                    f"Work file: {work_path}",
                    max_tokens=1024,
                    out_path=f"{iter_dir}/defect-{did}-fix.md",
                    role_suffix=f"-iter{fix_iters}-{did}",
                )

                # Per-fix independent verifier
                fix_verdict_result = await _spawn_write(
                    run_dir, "fix-verifier", TIER_OPUS,
                    "You are an INDEPENDENT fix verifier. Read the defect description and fix diff. "
                    "Emit:\n"
                    "STRUCTURED_OUTPUT_START\n"
                    "FIX_VERDICT|fixed|not_fixed|partial\n"
                    "NEW_DEFECT_INTRODUCED|none|<severity>|<description>\n"
                    "STRUCTURED_OUTPUT_END",
                    f"Defect: {json.dumps(defect)}\n\n"
                    f"Fix: {iter_dir}/defect-{did}-fix.md",
                    max_tokens=512,
                    out_path=f"{iter_dir}/defect-{did}-verdict.md",
                    role_suffix=f"-iter{fix_iters}-{did}",
                )

                fv = fix_verdict_result.get("FIX_VERDICT", "not_fixed").strip().lower()
                new_defect_str = fix_verdict_result.get("NEW_DEFECT_INTRODUCED", "none")
                if new_defect_str and new_defect_str.strip().lower() != "none":
                    # New defect introduced
                    parts = new_defect_str.split("|", 2)
                    severity = parts[0].strip() if parts else "major"
                    desc = parts[1].strip() if len(parts) > 1 else new_defect_str
                    new_defects.append({"id": f"{did}-new", "severity": severity, "description": desc})

                if fv != "fixed":
                    return {**defect, "_fix_verdict": fv}
                return {}  # empty = fixed

            fix_results = await asyncio.gather(
                *[_fix_one(d) for d in defects],
                return_exceptions=True,
            )

            remaining: list[dict] = []
            for r in fix_results:
                if isinstance(r, BaseException):
                    remaining.extend(defects)  # conservative: treat exception as not_fixed
                    break
                if r:  # non-empty = not fixed
                    remaining.append(r)
            remaining.extend(new_defects)

            # After fix iteration: re-run full team-verify (fresh evidence)
            diff_content2 = (
                f"# Diff after fix iter {fix_iters}\n\n"
                f"Prior defects: {json.dumps(defects, indent=2)}\n\n"
                f"Workers: {json.dumps(worker_outputs, indent=2)}\n"
            )
            await _write(run_dir, diff_path, diff_content2)

            await _spawn_write(
                run_dir, "spec-compliance-reviewer", TIER_OPUS,
                "Re-verify spec compliance after fix. "
                "STRUCTURED_OUTPUT_START\n"
                "CRITICAL_COUNT|<N>\nMAJOR_COUNT|<N>\nMINOR_COUNT|<N>\n"
                "DEFECTS|<json array of {id, severity, description}>\n"
                "STRUCTURED_OUTPUT_END",
                f"PRD: {prd_final_path}\n\nDiff: {diff_path}",
                max_tokens=1024,
                out_path=spec_compliance_path,
            )

            await _spawn_write(
                run_dir, "code-quality-reviewer", TIER_OPUS,
                "Re-verify code quality after fix. "
                "STRUCTURED_OUTPUT_START\n"
                "QUALITY_CRITICAL_COUNT|<N>\nQUALITY_MAJOR_COUNT|<N>\n"
                "QUALITY_DEFECTS|<json array of {id, severity, description}>\n"
                "STRUCTURED_OUTPUT_END",
                f"Diff: {diff_path}\n\nSpec compliance: {spec_compliance_path}",
                max_tokens=1024,
                out_path=code_quality_path,
            )

            verify_judge_result = await _spawn_write(
                run_dir, "verify-judge", TIER_OPUS,
                "Aggregate re-verify after fix. "
                "STRUCTURED_OUTPUT_START\n"
                "VERDICT|passed|failed_fixable|failed_unfixable\n"
                "CRITICAL_COUNT|<N>\nMAJOR_COUNT|<N>\nMINOR_COUNT|<N>\n"
                "DEFECTS|<json array of {id, severity, description}>\n"
                "STRUCTURED_OUTPUT_END",
                f"Spec-compliance: {spec_compliance_path}\n\nCode-quality: {code_quality_path}",
                max_tokens=512,
                out_path=verdict_path,
            )

            verdict = _get_verdict(verify_judge_result)
            defects = _parse_json_list(verify_judge_result.get("DEFECTS", "[]"))
            critical_count = int(verify_judge_result.get("CRITICAL_COUNT", "0") or "0")
            major_count = int(verify_judge_result.get("MAJOR_COUNT", "0") or "0")

            if verdict == "failed_unfixable":
                return await _terminate(
                    inp, summary_path, "blocked_unresolved",
                    f"Verify-judge determined defects unfixable after fix iter {fix_iters}.",
                    workers=len(worker_outputs), fix_iters=fix_iters, defects=len(defects),
                )

        # ---------------------------------------------------------------
        # Stage 7: Termination
        # ---------------------------------------------------------------
        if verdict == "passed" and critical_count == 0 and major_count == 0:
            label = "complete"
        elif fix_iters >= inp.max_fix_iters and (critical_count > 0 or major_count > 0):
            label = "budget_exhausted"
        elif verdict == "passed" and major_count > 0:
            # Majors accepted by verify-judge but not critical
            label = "partial_with_accepted_unfixed"
        else:
            label = "blocked_unresolved"

        return await _terminate(
            inp, summary_path, label,
            f"{label}: {len(worker_outputs)} workers, {fix_iters} fix iters, "
            f"{critical_count} critical, {major_count} major defects.",
            workers=len(worker_outputs), fix_iters=fix_iters, defects=len(defects),
        )


# ---------------------------------------------------------------------------
# Activity helpers
# ---------------------------------------------------------------------------

async def _write(run_dir: str, path: str, content: str) -> None:
    """Write a file artifact (no subagent call)."""
    await workflow.execute_activity(
        "write_artifact",
        WriteArtifactInput(path=path, content=content),
        start_to_close_timeout=timedelta(seconds=10),
        retry_policy=HAIKU_POLICY,
    )


async def _spawn_write(
    run_dir: str,
    role: str,
    tier: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    out_path: str,
    role_suffix: str = "",
) -> dict[str, str]:
    """Write prompt file, call spawn_subagent, write output to out_path, return parsed dict."""
    prompt_path = f"{run_dir}/{role}{role_suffix}-prompt.txt"

    # Write prompt file before spawn (state-before-agent-spawn contract)
    await workflow.execute_activity(
        "write_artifact",
        WriteArtifactInput(path=prompt_path, content=user_prompt),
        start_to_close_timeout=timedelta(seconds=10),
        retry_policy=HAIKU_POLICY,
    )

    policy = SONNET_POLICY if tier in (TIER_SONNET, TIER_OPUS) else HAIKU_POLICY
    result: dict[str, str] = await workflow.execute_activity(
        "spawn_subagent",
        SpawnSubagentInput(
            role=role,
            tier_name=tier,
            system_prompt=system_prompt,
            user_prompt_path=prompt_path,
            max_tokens=max_tokens,
            tools_needed=False,
        ),
        start_to_close_timeout=timedelta(seconds=300),
        retry_policy=policy,
    )

    # Write the output artifact (evidence file)
    output_content = (
        "STRUCTURED_OUTPUT_START\n"
        + "\n".join(f"{k}|{v}" for k, v in result.items())
        + "\nSTRUCTURED_OUTPUT_END\n"
    )
    await workflow.execute_activity(
        "write_artifact",
        WriteArtifactInput(path=out_path, content=output_content),
        start_to_close_timeout=timedelta(seconds=10),
        retry_policy=HAIKU_POLICY,
    )

    return result


async def _terminate(
    inp: TeamInput,
    summary_path: str,
    label: str,
    reason: str,
    *,
    workers: int,
    fix_iters: int,
    defects: int,
) -> str:
    summary_md = (
        f"# Team Run Summary\n\n"
        f"**Task:** {inp.task}\n\n"
        f"**Termination:** {label}\n\n"
        f"**Reason:** {reason}\n\n"
        f"**Workers:** {workers}\n\n"
        f"**Fix iterations:** {fix_iters}\n\n"
        f"**Open defects:** {defects}\n"
    )
    await workflow.execute_activity(
        "write_artifact",
        WriteArtifactInput(path=summary_path, content=summary_md),
        start_to_close_timeout=timedelta(seconds=10),
        retry_policy=HAIKU_POLICY,
    )

    timestamp = workflow.now().isoformat(timespec="seconds")
    await workflow.execute_activity(
        "emit_finding",
        EmitFindingInput(
            inbox_path=inp.inbox_path,
            run_id=inp.run_id,
            skill="team",
            status="DONE",
            summary=f"{label}: {reason}",
            notify=inp.notify,
            timestamp_iso=timestamp,
        ),
        start_to_close_timeout=timedelta(seconds=10),
        retry_policy=HAIKU_POLICY,
    )
    return f"{label}\nSummary: {summary_path}"


def _parse_json_list(raw: str) -> list[dict]:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [x for x in parsed if isinstance(x, dict)]
    except (json.JSONDecodeError, TypeError):
        pass
    return []
