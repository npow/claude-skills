"""deep-plan-temporal: consensus loop skill.

Phases:
  1. Planner (Haiku): generates a plan + acceptance criteria (RALPLAN-DR,
     deliberate mode: pre-mortem + expanded test plan).
  2. Architect (Haiku): structural review — ARCHITECT_OK or ARCHITECT_CONCERNS.
     Deliberate mode: emits PRINCIPLE_VIOLATION lines.
     Critical concern blocks Critic this iteration.
  3. Critic (Haiku): final verdict — APPROVE | ITERATE | REJECT.
     Falsifiability gate drops rubber-stamp rejections.
     All rejections dropped → promote to APPROVE_AFTER_RUBBER_STAMP_FILTER.
  4. ADR Scribe (Haiku): writes the Architecture Decision Record.
     Always spawned — on consensus AND on max-iter-no-consensus.
     Verbatim quotes of Architect and Critic verdicts required.

Loops up to max_iter times. Terminal labels:
  consensus_reached_at_iter_N
  consensus_reached_at_iter_N_after_rubber_stamp_filter
  max_iter_no_consensus
  {role}_unparseable_at_iter_N_after_retries
  {role}_spawn_failed_at_iter_N_after_retries
  adr_scribe_failed
  aborted_by_error

Max 3 retries per role per iteration for spawn_failed / unparseable.
Task SHA256 is immutable; mismatch on resume halts immediately.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from sagaflow.durable.activities import (
        EmitFindingInput,
        SpawnSubagentInput,
        WriteArtifactInput,
    )
    from sagaflow.durable.retry_policies import HAIKU_POLICY

# ---------------------------------------------------------------------------
# High-risk signal patterns that auto-enable deliberate mode
# ---------------------------------------------------------------------------
_HIGH_RISK_PATTERNS = re.compile(
    r"\b(auth(?:entication|orization)?|security|data.migration|destructive"
    r"|production.incident|compliance|pii|public.api.breakage)\b",
    re.IGNORECASE,
)

# Rubber-stamp phrases that disqualify a failure_scenario
_RUBBER_STAMP_PHRASES = re.compile(
    r"\b(needs more detail|should be clearer|add more context"
    r"|more detail|unclear|vague)\b",
    re.IGNORECASE,
)

# Patterns that make a verification_command look executable
_EXECUTABLE_PATTERN = re.compile(
    r"(\$|npm |pytest|make |\.\/|curl |python |bash |sh |docker |kubectl "
    r"|go test|cargo test|mvn |gradle )",
    re.IGNORECASE,
)

_MAX_ROLE_RETRIES = 3


@dataclass(frozen=True)
class DeepPlanInput:
    task: str
    run_id: str
    run_dir: str
    inbox_path: str
    max_iter: int = 5
    deliberate: bool = False
    notify: bool = True
    planner_system_prompt: str = ""
    planner_user_prompt: str = ""
    architect_system_prompt: str = ""
    architect_user_prompt: str = ""
    critic_system_prompt: str = ""
    critic_user_prompt: str = ""
    adr_system_prompt: str = ""
    adr_user_prompt: str = ""


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------


@workflow.defn(name="DeepPlanWorkflow")
class DeepPlanWorkflow:
    @workflow.run
    async def run(self, inp: DeepPlanInput) -> str:  # noqa: C901
        plan_path = f"{inp.run_dir}/plan.md"
        adr_path = f"{inp.run_dir}/adr.md"

        # --- task SHA256 ---
        task_sha = hashlib.sha256(inp.task.encode()).hexdigest()

        # --- mode detection ---
        mode = "deliberate" if (inp.deliberate or _HIGH_RISK_PATTERNS.search(inp.task)) else "short"

        current_plan = ""
        current_criteria: str = "[]"
        feedback_lines: list[str] = []
        verdict_history: list[str] = []
        consensus_iter: int | None = None
        rubber_stamp_filtered: bool = False

        # Per-role registry: role -> {spawns, unparseable, verdicts}
        agent_verdict_registry: dict[str, dict[str, object]] = {}

        def _reg(role: str) -> dict[str, object]:
            if role not in agent_verdict_registry:
                agent_verdict_registry[role] = {"spawns": 0, "unparseable": 0, "verdicts": {}}
            return agent_verdict_registry[role]

        def _reg_spawn(role: str) -> None:
            r = _reg(role)
            r["spawns"] = int(r["spawns"]) + 1  # type: ignore[arg-type]

        def _reg_unparseable(role: str) -> None:
            r = _reg(role)
            r["unparseable"] = int(r["unparseable"]) + 1  # type: ignore[arg-type]

        def _reg_verdict(role: str, verdict: str) -> None:
            r = _reg(role)
            vd = r["verdicts"]
            assert isinstance(vd, dict)
            vd[verdict] = int(vd.get(verdict, 0)) + 1  # type: ignore[arg-type]

        # terminal_label accumulates at most once; we return it as part of summary
        terminal_label: str = ""

        def _set_terminal(label: str) -> None:
            nonlocal terminal_label
            terminal_label = label

        # ----------------------------------------------------------------
        # Iteration loop
        # ----------------------------------------------------------------
        last_architect_verdict_text: str = ""
        last_critic_verdict_text: str = ""
        last_surviving_rejections: list[str] = []

        for iteration in range(inp.max_iter):

            # ---- Phase 1: Planner ----------------------------------------
            planner_result, planner_label = await _spawn_with_retry(
                role="planner",
                iteration=iteration,
                run_dir=inp.run_dir,
                prompt_content=inp.planner_user_prompt or _planner_user_prompt(  # runtime-dynamic
                    task=inp.task,
                    mode=mode,
                    iteration=iteration,
                    previous_plan=current_plan,
                    feedback=feedback_lines,
                ),
                system_prompt=inp.planner_system_prompt or _planner_system_prompt(mode=mode),  # mode-dependent
                max_tokens=2048,
                reg_spawn=_reg_spawn,
                reg_unparseable=_reg_unparseable,
            )
            if planner_result is None:
                _set_terminal(planner_label)
                break

            _reg_verdict("planner", "produced")
            current_plan = planner_result.get("PLAN", current_plan or f"# Plan\n\nTask: {inp.task}\n")
            current_criteria = planner_result.get("ACCEPTANCE_CRITERIA", "[]")

            # ---- Phase 2: Architect --------------------------------------
            architect_result, architect_label = await _spawn_with_retry(
                role="architect",
                iteration=iteration,
                run_dir=inp.run_dir,
                prompt_content=inp.architect_user_prompt or _architect_user_prompt(  # runtime-dynamic
                    task=inp.task,
                    plan=current_plan,
                    criteria=current_criteria,
                    mode=mode,
                ),
                system_prompt=inp.architect_system_prompt or _architect_system_prompt(mode=mode),  # mode-dependent
                max_tokens=1024,
                reg_spawn=_reg_spawn,
                reg_unparseable=_reg_unparseable,
            )
            if architect_result is None:
                _set_terminal(architect_label)
                break

            arch_verdict = architect_result.get("VERDICT", "ARCHITECT_CONCERNS")
            architect_concerns = _extract_concerns(architect_result)
            principle_violations = _extract_principle_violations(architect_result)
            last_architect_verdict_text = _dict_to_structured(architect_result)
            _reg_verdict("architect", arch_verdict)

            # Check for critical concerns → block Critic, loop back to Planner
            has_critical = _has_critical_concern(architect_result)
            if has_critical:
                feedback_lines = [
                    f"Architect ({arch_verdict}): {'; '.join(architect_concerns)} "
                    f"[CRITICAL CONCERN — Critic blocked; address before next iteration]"
                ]
                if principle_violations:
                    feedback_lines.append(f"Principle violations: {'; '.join(principle_violations)}")
                verdict_history.append(f"iter{iteration}:{arch_verdict}:critic_blocked_critical")
                if iteration + 1 >= inp.max_iter:
                    _set_terminal("max_iter_no_consensus")
                    # fall through to ADR with no consensus
                    current_plan = current_plan  # keep last plan
                    break
                continue

            # ---- Phase 3: Critic -----------------------------------------
            critic_result, critic_label = await _spawn_with_retry(
                role="critic",
                iteration=iteration,
                run_dir=inp.run_dir,
                prompt_content=inp.critic_user_prompt or _critic_user_prompt(  # runtime-dynamic
                    task=inp.task,
                    plan=current_plan,
                    criteria=current_criteria,
                    architect_verdict=arch_verdict,
                    architect_concerns=architect_concerns,
                    mode=mode,
                ),
                system_prompt=inp.critic_system_prompt or _critic_system_prompt(mode=mode),  # mode-dependent
                max_tokens=1024,
                reg_spawn=_reg_spawn,
                reg_unparseable=_reg_unparseable,
            )
            if critic_result is None:
                _set_terminal(critic_label)
                break

            raw_critic_verdict = critic_result.get("VERDICT", "ITERATE")
            last_critic_verdict_text = _dict_to_structured(critic_result)

            # ---- Falsifiability gate ------------------------------------
            all_rejections = _extract_rejections(critic_result)
            surviving_rejections, dropped_rejections = _apply_falsifiability_gate(all_rejections)
            dropped_count = len(dropped_rejections)

            # Write dropped-rejections artifact when any were dropped
            if dropped_rejections:
                dropped_path = f"{inp.run_dir}/dropped-rejections-iter{iteration}.md"
                dropped_lines = [f"# Dropped Rejections — Iter {iteration}\n"]
                for rej in dropped_rejections:
                    dropped_lines.append(f"- {rej['raw']} — REASON: {rej['reason']}")
                await workflow.execute_activity(
                    "write_artifact",
                    WriteArtifactInput(
                        path=dropped_path,
                        content="\n".join(dropped_lines),
                    ),
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=HAIKU_POLICY,
                )

            # Promote if all rejections dropped and critic said ITERATE/REJECT
            effective_verdict = raw_critic_verdict
            if raw_critic_verdict in ("ITERATE", "REJECT") and all_rejections and not surviving_rejections:
                effective_verdict = "APPROVE_AFTER_RUBBER_STAMP_FILTER"
                rubber_stamp_filtered = True

            _reg_verdict("critic", effective_verdict)
            last_surviving_rejections = [r["raw"] for r in surviving_rejections]
            verdict_history.append(f"iter{iteration}:{arch_verdict}:{effective_verdict}")

            if effective_verdict in ("APPROVE", "APPROVE_AFTER_RUBBER_STAMP_FILTER"):
                consensus_iter = iteration
                label = (
                    f"consensus_reached_at_iter_{iteration}_after_rubber_stamp_filter"
                    if rubber_stamp_filtered
                    else f"consensus_reached_at_iter_{iteration}"
                )
                _set_terminal(label)
                break

            # ---- Build feedback for next iteration -----------------------
            feedback_lines = []
            if architect_concerns:
                feedback_lines.append(f"Architect ({arch_verdict}): {'; '.join(architect_concerns)}")
            if principle_violations:
                feedback_lines.append(f"Principle violations: {'; '.join(principle_violations)}")
            if dropped_count:
                feedback_lines.append(
                    f"Note: {dropped_count} critic rejection(s) dropped as rubber-stamp "
                    f"(missing concrete scenario or executable verification command)."
                )
            if surviving_rejections:
                feedback_lines.append(f"Critic ({raw_critic_verdict}) surviving rejections:")
                for rej in surviving_rejections:
                    feedback_lines.append(f"  - {rej['raw']}")
            elif critic_result.get("DETAILS"):
                feedback_lines.append(f"Critic ({raw_critic_verdict}): {critic_result['DETAILS']}")
            else:
                feedback_lines.append(f"Critic verdict: {raw_critic_verdict}. Revise the plan.")

        else:
            # Loop exhausted without break
            if not terminal_label:
                _set_terminal("max_iter_no_consensus")

        if not terminal_label:
            _set_terminal("max_iter_no_consensus")

        # Save plan.md regardless of outcome.
        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(path=plan_path, content=current_plan),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )

        # ---- Phase 4: ADR Scribe (always — on consensus AND max-iter) ----
        adr_prompt_path = f"{inp.run_dir}/adr-prompt.txt"
        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(
                path=adr_prompt_path,
                content=inp.adr_user_prompt or _adr_user_prompt(  # runtime-dynamic
                    task=inp.task,
                    plan=current_plan,
                    criteria=current_criteria,
                    terminal_label=terminal_label,
                    architect_verdict_text=last_architect_verdict_text,
                    critic_verdict_text=last_critic_verdict_text,
                    surviving_rejections=last_surviving_rejections,
                ),
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        adr_result, adr_label = await _spawn_with_retry(
            role="adr",
            iteration=0,
            run_dir=inp.run_dir,
            prompt_content=None,  # already written above; use a sentinel
            system_prompt=inp.adr_system_prompt,
            max_tokens=2048,
            reg_spawn=_reg_spawn,
            reg_unparseable=_reg_unparseable,
            override_prompt_path=adr_prompt_path,
        )
        if adr_result is None:
            _set_terminal("adr_scribe_failed")
            adr_md = _fallback_adr(inp.task, current_plan, terminal_label)
        else:
            _reg_verdict("adr", "produced")
            adr_md = adr_result.get("ADR", _fallback_adr(inp.task, current_plan, terminal_label))

        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(path=adr_path, content=adr_md),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )

        summary = (
            f"{terminal_label} after {len(verdict_history)} iteration(s); "
            f"verdicts: {', '.join(verdict_history)}; "
            f"mode: {mode}; task_sha256: {task_sha[:8]}…"
        )
        status = "DONE" if consensus_iter is not None else "NO_CONSENSUS"
        timestamp = workflow.now().isoformat(timespec="seconds")
        await workflow.execute_activity(
            "emit_finding",
            EmitFindingInput(
                inbox_path=inp.inbox_path,
                run_id=inp.run_id,
                skill="deep-plan",
                status=status,
                summary=summary,
                notify=inp.notify,
                timestamp_iso=timestamp,
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        return f"{summary}\nPlan: {plan_path}"


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------


async def _spawn_with_retry(
    *,
    role: str,
    iteration: int,
    run_dir: str,
    prompt_content: str | None,
    system_prompt: str,
    max_tokens: int,
    reg_spawn,
    reg_unparseable,
    override_prompt_path: str | None = None,
) -> tuple[dict[str, str] | None, str]:
    """Attempt to spawn a subagent up to _MAX_ROLE_RETRIES times.

    Returns (result_dict, terminal_label).  result_dict is None on failure.
    """
    prompt_path = override_prompt_path or f"{run_dir}/{role}-iter{iteration}.txt"

    if prompt_content is not None:
        # Write the prompt file (activity — durable).
        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(path=prompt_path, content=prompt_content),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )

    for attempt in range(_MAX_ROLE_RETRIES):
        reg_spawn(role)
        try:
            result = await workflow.execute_activity(
                "spawn_subagent",
                SpawnSubagentInput(
                    role=role,
                    tier_name="HAIKU",
                    system_prompt=system_prompt,
                    user_prompt_path=prompt_path,
                    max_tokens=max_tokens,
                    tools_needed=False,
                ),
                start_to_close_timeout=timedelta(seconds=600),
                retry_policy=HAIKU_POLICY,
            )
        except Exception:  # noqa: BLE001
            if attempt + 1 >= _MAX_ROLE_RETRIES:
                return None, f"{role}_spawn_failed_at_iter_{iteration}_after_retries"
            continue

        # Validate structured output: must have at least one non-empty key
        if not result or not any(v for v in result.values() if v):
            reg_unparseable(role)
            if attempt + 1 >= _MAX_ROLE_RETRIES:
                return None, f"{role}_unparseable_at_iter_{iteration}_after_retries"
            continue

        return result, ""

    # Unreachable but satisfies type checker
    return None, f"{role}_spawn_failed_at_iter_{iteration}_after_retries"


# ---------------------------------------------------------------------------
# Structured-output helpers
# ---------------------------------------------------------------------------


def _extract_concerns(architect_result: dict[str, str]) -> list[str]:
    """Collect CONCERN|id|description|severity lines -> list of description strings."""
    concerns: list[str] = []
    # New pipe-separated format: CONCERN|{id}|{description}|{severity}
    raw_concern = architect_result.get("CONCERN", "")
    if raw_concern:
        # May be a single value or multiple newline-separated
        for line in raw_concern.splitlines():
            parts = line.split("|")
            if len(parts) >= 2:
                concerns.append(parts[1] if len(parts) == 2 else parts[1])
    # Legacy CONCERN_N keys
    i = 1
    while True:
        key = f"CONCERN_{i}"
        val = architect_result.get(key)
        if val is None:
            break
        concerns.append(val)
        i += 1
    return concerns


def _extract_principle_violations(architect_result: dict[str, str]) -> list[str]:
    """Extract PRINCIPLE_VIOLATION|principle_id|description entries."""
    violations: list[str] = []
    raw = architect_result.get("PRINCIPLE_VIOLATION", "")
    if raw:
        for line in raw.splitlines():
            parts = line.split("|")
            if len(parts) >= 2:
                violations.append("|".join(parts[1:]))
    return violations


def _has_critical_concern(architect_result: dict[str, str]) -> bool:
    """Return True if any CONCERN has severity=critical.

    The structured-output parser strips the CONCERN| prefix, so the VALUE stored
    in architect_result["CONCERN"] is `"{id}|{description}|{severity}"` — 3
    pipe-separated fields. We also accept trailing fields after severity.
    """
    raw_concern = architect_result.get("CONCERN", "")
    if raw_concern:
        for line in raw_concern.splitlines():
            parts = line.split("|")
            # id | description | severity [| ...optional]
            if len(parts) >= 3 and parts[2].strip().lower() == "critical":
                return True
    # Also check CONCERN_SEVERITY helper key some fakes emit
    severity = architect_result.get("CONCERN_SEVERITY", "")
    if severity.strip().lower() == "critical":
        return True
    return False


def _extract_rejections(critic_result: dict[str, str]) -> list[dict[str, str]]:
    """Parse REJECTION|<id>|<dimension>|<failure_scenario>|<verification_command>.

    The structured-output parser strips the REJECTION| prefix, so the VALUE
    stored in critic_result["REJECTION"] is `"{id}|{dimension}|{scenario}|{command}"`
    — 4 pipe-separated fields.
    """
    rejections: list[dict[str, str]] = []
    raw = critic_result.get("REJECTION", "")
    if not raw:
        return rejections
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) < 4:
            # Malformed — still capture as-is for gate to evaluate
            rejections.append({
                "id": parts[0] if parts else "?",
                "dimension": "",
                "failure_scenario": line,
                "verification_command": "",
                "raw": line,
            })
        else:
            rejections.append({
                "id": parts[0],
                "dimension": parts[1],
                "failure_scenario": parts[2],
                "verification_command": parts[3],
                "raw": line,
            })
    return rejections


def _apply_falsifiability_gate(
    rejections: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Split rejections into (surviving, dropped).

    A rejection is dropped if:
    - failure_scenario is <20 chars OR matches rubber-stamp phrases
    - verification_command is empty OR is not executable
    """
    surviving: list[dict[str, str]] = []
    dropped: list[dict[str, str]] = []
    for rej in rejections:
        fs = rej.get("failure_scenario", "")
        vc = rej.get("verification_command", "")
        reason = ""
        if len(fs) < 20 or _RUBBER_STAMP_PHRASES.search(fs):
            reason = "failure_scenario too vague or rubber-stamp"
        elif not vc or not _EXECUTABLE_PATTERN.search(vc):
            reason = "verification_command missing or not executable"
        if reason:
            rej_copy = dict(rej)
            rej_copy["reason"] = reason
            dropped.append(rej_copy)
        else:
            surviving.append(rej)
    return surviving, dropped


def _dict_to_structured(d: dict[str, str]) -> str:
    """Reconstruct a simplified structured block from a parsed dict (for ADR quoting)."""
    lines = ["STRUCTURED_OUTPUT_START"]
    for k, v in d.items():
        lines.append(f"{k}|{v}")
    lines.append("STRUCTURED_OUTPUT_END")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------


def _planner_system_prompt(*, mode: str) -> str:
    base = (
        "You are a technical planner. Given a task description (and optionally feedback "
        "from a previous iteration), write a clear, actionable implementation plan in "
        "Markdown plus a JSON array of acceptance criteria.\n\n"
        "Your plan MUST include:\n"
        "- RALPLAN-DR summary: 3-5 Principles, top 3 Decision Drivers, >=2 viable Options "
        "with bounded pros/cons, plus 'What I'd Cut' and 'What I'd Add' sections.\n"
        "- Every acceptance criterion MUST have: id, criterion, verification_command, "
        "expected_output_pattern.\n\n"
    )
    deliberate_addition = ""
    if mode == "deliberate":
        deliberate_addition = (
            "DELIBERATE MODE REQUIRED:\n"
            "- Pre-mortem: exactly 3 concrete failure scenarios using PREMORTEM lines.\n"
            "- Expanded test plan covering: unit / integration / e2e / observability.\n\n"
        )
    return (
        base
        + deliberate_addition
        + "Output format:\n"
        "STRUCTURED_OUTPUT_START\n"
        "PLAN|<full markdown plan — use literal newlines inside the value>\n"
        "ACCEPTANCE_CRITERIA|<json array of strings — each entry is one criterion>\n"
        "PREMORTEM|<scenario_id>|<scenario>  (deliberate only, repeat for each scenario)\n"
        "STRUCTURED_OUTPUT_END\n"
        "IMPORTANT: PLAN value starts immediately after the first pipe."
    )


def _planner_user_prompt(
    *,
    task: str,
    mode: str,
    iteration: int,
    previous_plan: str,
    feedback: list[str],
) -> str:
    parts = [f"Task: {task}", f"Mode: {mode}", f"Iteration: {iteration}"]
    if previous_plan:
        parts.append(f"\n--- PREVIOUS PLAN ---\n{previous_plan}\n--- END PREVIOUS PLAN ---")
    if feedback:
        parts.append("\n--- FEEDBACK TO ADDRESS ---")
        parts.extend(f"  - {f}" for f in feedback)
        parts.append("--- END FEEDBACK ---")
    parts.append("\nWrite or revise the plan addressing the feedback above.")
    return "\n".join(parts)


def _architect_system_prompt(*, mode: str) -> str:
    base = (
        "You are a senior software architect. Review the proposed plan for structural "
        "soundness: correctness, scalability, testability, dependency risks, and "
        "completeness relative to the acceptance criteria.\n\n"
        "Output format:\n"
        "STRUCTURED_OUTPUT_START\n"
        "VERDICT|ARCHITECT_OK\n"
        "STRUCTURED_OUTPUT_END\n"
        "-- OR --\n"
        "STRUCTURED_OUTPUT_START\n"
        "VERDICT|ARCHITECT_CONCERNS\n"
        "CONCERN|{id}|{description}|{critical|major|minor}\n"
        "TRADEOFF|{description}\n"
        "STRUCTURED_OUTPUT_END\n"
        "Emit ARCHITECT_OK only when the plan has no structural issues. "
        "List each concern on its own CONCERN line with severity (critical/major/minor).\n"
    )
    if mode == "deliberate":
        base += (
            "\nDELIBERATE MODE: Emit PRINCIPLE_VIOLATION|{principle_id}|{description} "
            "for any plan implementation steps that violate a declared principle.\n"
        )
    return base


def _architect_user_prompt(*, task: str, plan: str, criteria: str, mode: str) -> str:
    return (
        f"Task: {task}\nMode: {mode}\n\n"
        f"Acceptance criteria:\n{criteria}\n\n"
        "--- PLAN START ---\n"
        f"{plan}\n"
        "--- PLAN END ---\n"
    )


def _critic_system_prompt(*, mode: str) -> str:
    base = (
        "You are a rigorous plan critic. Given the plan, acceptance criteria, and the "
        "architect's review, decide whether to APPROVE, ITERATE, or REJECT.\n\n"
        "APPROVE   — plan is solid; proceed.\n"
        "ITERATE   — plan has fixable issues; provide concise guidance.\n"
        "REJECT    — plan is fundamentally flawed; explain why.\n\n"
        "FALSIFIABILITY REQUIREMENT: every REJECTION must include:\n"
        "- failure_scenario: concrete actor/action/observable failure (>=20 chars, no vague phrases)\n"
        "- verification_command: executable shell command (not prose)\n"
        "Rejections missing either are DROPPED by the coordinator.\n\n"
        "Output format:\n"
        "STRUCTURED_OUTPUT_START\n"
        "VERDICT|APPROVE\n"
        "STRUCTURED_OUTPUT_END\n"
        "-- OR --\n"
        "STRUCTURED_OUTPUT_START\n"
        "VERDICT|ITERATE\n"
        "REJECTION|{id}|{dimension}|{failure_scenario}|{verification_command}\n"
        "DETAILS|<one-paragraph critique>\n"
        "STRUCTURED_OUTPUT_END\n"
        "Be decisive. Don't ITERATE more than necessary.\n"
    )
    if mode == "deliberate":
        base += (
            "\nDELIBERATE MODE: Also check:\n"
            "- Pre-mortem presence: 3 distinct failure scenarios (not 3 rephrasings of one).\n"
            "- Expanded test plan: unit / integration / e2e / observability all present.\n"
            "Reject if either is missing or weak.\n"
        )
    return base


def _critic_user_prompt(
    *,
    task: str,
    plan: str,
    criteria: str,
    architect_verdict: str,
    architect_concerns: list[str],
    mode: str,
) -> str:
    concerns_text = "\n".join(f"  - {c}" for c in architect_concerns) if architect_concerns else "  (none)"
    return (
        f"Task: {task}\nMode: {mode}\n\n"
        f"Acceptance criteria:\n{criteria}\n\n"
        f"Architect verdict: {architect_verdict}\n"
        f"Architect concerns:\n{concerns_text}\n\n"
        "--- PLAN START ---\n"
        f"{plan}\n"
        "--- PLAN END ---\n"
    )



def _adr_user_prompt(
    *,
    task: str,
    plan: str,
    criteria: str,
    terminal_label: str,
    architect_verdict_text: str,
    critic_verdict_text: str,
    surviving_rejections: list[str],
) -> str:
    rejections_section = ""
    if surviving_rejections:
        rejections_section = (
            "\n## Unresolved Critic Rejections\n"
            + "\n".join(f"- {r}" for r in surviving_rejections)
            + "\n"
        )
    return (
        f"Task: {task}\n"
        f"Termination label: {terminal_label}\n\n"
        f"Acceptance criteria:\n{criteria}\n\n"
        "--- FINAL PLAN START ---\n"
        f"{plan}\n"
        "--- FINAL PLAN END ---\n\n"
        "--- ARCHITECT VERDICT (quote verbatim) ---\n"
        f"{architect_verdict_text or '(no architect verdict recorded)'}\n"
        "--- END ARCHITECT VERDICT ---\n\n"
        "--- CRITIC VERDICT (quote verbatim) ---\n"
        f"{critic_verdict_text or '(no critic verdict recorded)'}\n"
        "--- END CRITIC VERDICT ---\n"
        f"{rejections_section}\n"
        "Write the ADR. Quote Architect and Critic structured outputs verbatim using "
        "ARCHITECT_VERDICT_QUOTE| and CRITIC_VERDICT_QUOTE| markers in the ADR body."
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fallback_adr(task: str, plan: str, terminal_label: str) -> str:
    return (
        "# ADR (fallback — scribe failed)\n\n"
        f"## Status\n{terminal_label}\n\n"
        f"## Context\n{task}\n\n"
        "## Decision\nSee the plan below.\n\n"
        "## Consequences\nADR Scribe failed to produce structured output. "
        "Plan output follows:\n\n"
        f"{plan[:2000]}\n"
    )
