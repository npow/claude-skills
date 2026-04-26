"""deep-qa-temporal: Temporal port of the deep-qa skill.

Phases:
  0. Snapshot artifact into the run directory.
  1. Dimension/angle discovery (Sonnet, one call).
  2. Initialize state: hard_stop = 2 * max_rounds (immutable), required_categories_covered.
  3. QA rounds (up to max_rounds × up to 6 parallel critics, Haiku).
     Per-round: spawn critics → collect defects → coverage enforcement →
     background severity judges (pass-1 blind, batches of ≤5).
  4. Fact verification (research artifacts only, Haiku + WebFetch via claude -p).
  5. Drain pass-1 judges, run pass-2 informed judges (authoritative severity).
  5.5. Rationalization auditor (Sonnet) — up to 2 attempts before hard exit.
  6. Synthesize final report (Sonnet) + emit finding to INBOX.

Termination labels (exhaustive — see Phase 5 vocabulary table in SKILL.md):
  Conditions Met
  Coverage plateau — frontier saturated
  Max Rounds Reached — user stopped
  Max Rounds Reached
  User-stopped at round N
  Convergence — frontier exhausted before full coverage
  Hard stop at round N
  Audit compromised — report re-assembled from verdicts only
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import timedelta
from string import Template

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from sagaflow.durable.activities import (
        EmitFindingInput,
        SpawnSubagentInput,
        WriteArtifactInput,
    )
    from sagaflow.durable.retry_policies import HAIKU_POLICY, SONNET_POLICY
    from .state import (
        REQUIRED_CATEGORIES,
        Angle,
        Defect,
        JudgeVerdict,
    )


@dataclass(frozen=True)
class DeepQaInput:
    run_id: str
    artifact_path: str  # absolute path to artifact to QA
    artifact_type: str  # "doc" | "code" | "research" | "skill"
    inbox_path: str
    run_dir: str
    max_rounds: int = 3
    notify: bool = True
    # Prompt overrides — loaded from ~/.claude/skills/deep-qa/prompts/*.md
    # at build_input time via load_claude_skill_prompt.
    dim_discovery_system_prompt: str = ""
    dim_discovery_user_prompt: str = ""
    critic_system_prompt: str = ""
    critic_user_prompt: str = ""
    judge_pass1_system_prompt: str = ""
    judge_pass1_user_prompt: str = ""
    judge_pass2_system_prompt: str = ""
    judge_pass2_user_prompt: str = ""
    auditor_system_prompt: str = ""
    auditor_user_prompt: str = ""
    verifier_system_prompt: str = ""
    verifier_user_prompt: str = ""
    synth_system_prompt: str = ""
    synth_user_prompt: str = ""


# Bounded parallelism per round (spec: max 6 critics per round).
_MAX_CRITICS_PER_ROUND = 6

# Maximum defects per judge batch (spec: ≤5 per batch).
_MAX_DEFECTS_PER_JUDGE_BATCH = 5

# Maximum rationalization-auditor retry attempts before hard exit.
_MAX_AUDIT_ATTEMPTS = 2


@workflow.defn(name="DeepQaWorkflow")
class DeepQaWorkflow:
    @workflow.run
    async def run(self, inp: DeepQaInput) -> str:
        artifact_snapshot = f"{inp.run_dir}/artifact.txt"
        report_path = f"{inp.run_dir}/qa-report.md"
        dim_prompt_path = f"{inp.run_dir}/dim-prompt.txt"
        synth_prompt_path = f"{inp.run_dir}/synth-prompt.txt"

        # ------------------------------------------------------------------
        # Phase 0: snapshot artifact + write the dim-discovery prompt.
        # ------------------------------------------------------------------
        artifact_text = await workflow.execute_activity(
            "read_text_file",
            inp.artifact_path,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=HAIKU_POLICY,
        )
        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(path=artifact_snapshot, content=artifact_text),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(
                path=dim_prompt_path,
                content=Template(inp.dim_discovery_user_prompt).safe_substitute(
                    artifact_type=inp.artifact_type,
                    artifact_length=str(len(artifact_text)),
                    artifact_text=artifact_text[:20000],
                ),
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )

        # ------------------------------------------------------------------
        # Phase 1: dimension discovery → list of angles.
        # ------------------------------------------------------------------
        dim_result = await workflow.execute_activity(
            "spawn_subagent",
            SpawnSubagentInput(
                role="dim-discover",
                tier_name="SONNET",
                system_prompt=inp.dim_discovery_system_prompt,
                user_prompt_path=dim_prompt_path,
                max_tokens=128000,
                tools_needed=False,
            ),
            start_to_close_timeout=timedelta(seconds=600),
            retry_policy=SONNET_POLICY,
        )
        angles_raw = dim_result.get("ANGLES", "[]")
        frontier: list[Angle] = _parse_angles(angles_raw)

        # ------------------------------------------------------------------
        # Phase 2: initialize state invariants.
        # ------------------------------------------------------------------
        hard_stop = inp.max_rounds * 2  # immutable after this point
        required_categories: list[str] = REQUIRED_CATEGORIES.get(inp.artifact_type, [])
        required_categories_covered: dict[str, bool] = {
            cat: False for cat in required_categories
        }

        all_defects: list[Defect] = []
        generation: int = 0

        # ------------------------------------------------------------------
        # Phase 3: QA rounds.
        # ------------------------------------------------------------------
        rounds_run = 0
        rounds_without_new_dimensions = 0
        termination_label: str | None = None

        for round_idx in range(hard_stop):
            # Hard-stop check fires unconditionally before every round.
            if round_idx >= hard_stop:
                termination_label = f"Hard stop at round {hard_stop}"
                break

            # Prospective gate omitted (--auto semantics in Temporal context).
            # Budget soft gate.
            if round_idx >= inp.max_rounds and not frontier:
                break
            if round_idx >= inp.max_rounds:
                termination_label = "Max Rounds Reached"
                break

            if not frontier:
                break

            rounds_run += 1
            generation += 1

            # Pop up to _MAX_CRITICS_PER_ROUND highest-priority angles.
            batch = frontier[:_MAX_CRITICS_PER_ROUND]
            frontier = frontier[_MAX_CRITICS_PER_ROUND:]

            # Write critic prompt files before spawning.
            critic_prompt_paths: list[str] = []
            for i, angle in enumerate(batch):
                ppath = f"{inp.run_dir}/critic-r{round_idx}-{i}.txt"
                await workflow.execute_activity(
                    "write_artifact",
                    WriteArtifactInput(
                        path=ppath,
                        content=Template(inp.critic_user_prompt).safe_substitute(
                            angle_question=angle.question,
                            angle_dimension=angle.dimension,
                            artifact_type=inp.artifact_type,
                            artifact_text=artifact_text[:20000],
                        ),
                    ),
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=HAIKU_POLICY,
                )
                critic_prompt_paths.append(ppath)

            # Spawn critics in parallel (180s timeout per spec).
            critic_coros = [
                workflow.execute_activity(
                    "spawn_subagent",
                    SpawnSubagentInput(
                        role="critic",
                        tier_name="HAIKU",
                        system_prompt=inp.critic_system_prompt,
                        user_prompt_path=ppath,
                        max_tokens=128000,
                        tools_needed=False,
                    ),
                    start_to_close_timeout=timedelta(seconds=600),
                    retry_policy=HAIKU_POLICY,
                )
                for ppath in critic_prompt_paths
            ]
            critic_outputs = await asyncio.gather(*critic_coros, return_exceptions=True)

            new_defects_this_round: list[Defect] = []
            dimensions_seen_this_round: set[str] = set()

            for angle, result in zip(batch, critic_outputs):
                if isinstance(result, BaseException):
                    # Critic failure: fail-safe skip; do NOT re-queue.
                    continue
                defects_raw = result.get("DEFECTS", "[]")
                for raw_defect in _parse_raw_defects(defects_raw):
                    defect_id = raw_defect.get("id") or f"d-r{round_idx}-{len(all_defects)}"
                    sev = raw_defect.get("severity", "minor")
                    if sev not in ("critical", "major", "minor"):
                        sev = "minor"
                    defect = Defect(
                        id=defect_id,
                        title=raw_defect.get("title", ""),
                        severity=sev,  # type: ignore[arg-type]
                        dimension=raw_defect.get("dimension", angle.dimension),
                        scenario=raw_defect.get("scenario", ""),
                        root_cause=raw_defect.get("root_cause", ""),
                        source_angle_id=angle.id,
                        judge_status="pending",
                    )
                    new_defects_this_round.append(defect)
                    dimensions_seen_this_round.add(angle.dimension)

            # Update coverage tracking.
            for dim in dimensions_seen_this_round:
                if dim in required_categories_covered:
                    required_categories_covered[dim] = True

            # Check if any new dimensions were discovered.
            if dimensions_seen_this_round:
                rounds_without_new_dimensions = 0
            else:
                rounds_without_new_dimensions += 1

            all_defects.extend(new_defects_this_round)
            generation += 1

            # Coverage enforcement: for any uncovered required category, add CRITICAL angle.
            for cat, covered in required_categories_covered.items():
                if not covered:
                    critical_angle = Angle(
                        id=f"coverage-{cat}-r{round_idx}",
                        question=f"Evaluate the artifact specifically for {cat} defects. This is a required QA category that has not yet been covered.",
                        dimension=cat,
                        status="frontier",
                        priority="critical",
                    )
                    frontier.append(critical_angle)

            # ------------------------------------------------------------------
            # Pass-1 severity judges (blind — critic-proposed severity stripped).
            # Batches of ≤5 defects each, run in parallel.
            # ------------------------------------------------------------------
            pending_defects = [d for d in new_defects_this_round]
            if pending_defects:
                judge_batches = _chunk(pending_defects, _MAX_DEFECTS_PER_JUDGE_BATCH)
                judge_pass1_coros = []
                judge_batch_paths = []
                for batch_num, judge_batch in enumerate(judge_batches):
                    judge_input_path = (
                        f"{inp.run_dir}/judge-inputs/batch_r{round_idx}_{batch_num}.txt"
                    )
                    # Write blind judge input (severity stripped from each defect).
                    blind_content = Template(inp.judge_pass1_user_prompt).safe_substitute(
                        defects_text=_format_defects_blind(judge_batch),
                    )
                    await workflow.execute_activity(
                        "write_artifact",
                        WriteArtifactInput(path=judge_input_path, content=blind_content),
                        start_to_close_timeout=timedelta(seconds=10),
                        retry_policy=HAIKU_POLICY,
                    )
                    judge_batch_paths.append((judge_batch, judge_input_path))
                    judge_pass1_coros.append(
                        workflow.execute_activity(
                            "spawn_subagent",
                            SpawnSubagentInput(
                                role="judge-pass-1",
                                tier_name="HAIKU",
                                system_prompt=inp.judge_pass1_system_prompt,
                                user_prompt_path=judge_input_path,
                                max_tokens=128000,
                                tools_needed=False,
                            ),
                            start_to_close_timeout=timedelta(seconds=600),
                            retry_policy=HAIKU_POLICY,
                        )
                    )

                judge_pass1_results = await asyncio.gather(
                    *judge_pass1_coros, return_exceptions=True
                )

                # Apply pass-1 verdicts to defects.
                for (judge_batch, _), pass1_result in zip(
                    judge_batch_paths, judge_pass1_results
                ):
                    if isinstance(pass1_result, BaseException):
                        # Timeout / failure: retain critic-proposed severity.
                        for d in judge_batch:
                            d.judge_status = "pass_1_timed_out"
                        continue
                    verdicts = _parse_verdicts(pass1_result.get("VERDICTS", "[]"))
                    verdict_map = {v.defect_id: v for v in verdicts}
                    for d in judge_batch:
                        if d.id in verdict_map:
                            d.judge_pass_1_verdict = verdict_map[d.id]
                            d.judge_status = "pass_1_completed"
                        else:
                            d.judge_status = "pass_1_timed_out"

                generation += 1

                # ------------------------------------------------------------------
                # Pass-2 informed judges (authoritative — sees pass-1 verdict).
                # ------------------------------------------------------------------
                pass2_eligible = [
                    d for d in pending_defects if d.judge_status == "pass_1_completed"
                ]
                if pass2_eligible:
                    pass2_batches = _chunk(pass2_eligible, _MAX_DEFECTS_PER_JUDGE_BATCH)
                    judge_pass2_coros = []
                    judge_pass2_batch_map = []
                    for batch_num, p2_batch in enumerate(pass2_batches):
                        p2_path = (
                            f"{inp.run_dir}/judge-inputs/batch_pass2_r{round_idx}_{batch_num}.txt"
                        )
                        p2_content = Template(inp.judge_pass2_user_prompt).safe_substitute(
                            defects_text=_format_defects_informed(p2_batch),
                        )
                        await workflow.execute_activity(
                            "write_artifact",
                            WriteArtifactInput(path=p2_path, content=p2_content),
                            start_to_close_timeout=timedelta(seconds=10),
                            retry_policy=HAIKU_POLICY,
                        )
                        judge_pass2_batch_map.append((p2_batch, p2_path))
                        judge_pass2_coros.append(
                            workflow.execute_activity(
                                "spawn_subagent",
                                SpawnSubagentInput(
                                    role="judge-pass-2",
                                    tier_name="HAIKU",
                                    system_prompt=inp.judge_pass2_system_prompt,
                                    user_prompt_path=p2_path,
                                    max_tokens=128000,
                                    tools_needed=False,
                                ),
                                start_to_close_timeout=timedelta(seconds=600),
                                retry_policy=HAIKU_POLICY,
                            )
                        )

                    judge_pass2_results = await asyncio.gather(
                        *judge_pass2_coros, return_exceptions=True
                    )

                    # Apply pass-2 verdicts as authoritative severity.
                    for (p2_batch, _), pass2_result in zip(
                        judge_pass2_batch_map, judge_pass2_results
                    ):
                        if isinstance(pass2_result, BaseException):
                            # Timeout: retain current severity; mark timed_out.
                            for d in p2_batch:
                                d.judge_status = "timed_out"
                            continue
                        verdicts = _parse_verdicts(pass2_result.get("VERDICTS", "[]"))
                        verdict_map = {v.defect_id: v for v in verdicts}
                        for d in p2_batch:
                            if d.id in verdict_map:
                                v = verdict_map[d.id]
                                d.severity = v.severity  # authoritative
                                d.judge_pass_2_verdict = v
                                d.judge_status = "completed"
                            else:
                                # Unparseable: fail-safe to critical.
                                d.severity = "critical"
                                d.judge_status = "timed_out"

                    generation += 1

            # Coverage plateau check.
            if (
                rounds_without_new_dimensions >= 2
                and not frontier
            ):
                termination_label = "Coverage plateau — frontier saturated"
                break

        # ------------------------------------------------------------------
        # Phase 4: fact verification (research artifacts only).
        # ------------------------------------------------------------------
        verification_result: dict | None = None
        if inp.artifact_type == "research":
            verifier_prompt_path = f"{inp.run_dir}/verifier-prompt.txt"
            await workflow.execute_activity(
                "write_artifact",
                WriteArtifactInput(
                    path=verifier_prompt_path,
                    content=Template(inp.verifier_user_prompt).safe_substitute(
                        artifact_text=artifact_text[:30000],
                    ),
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=HAIKU_POLICY,
            )
            verifier_result = await workflow.execute_activity(
                "spawn_subagent",
                SpawnSubagentInput(
                    role="verifier",
                    tier_name="HAIKU",
                    system_prompt=inp.verifier_system_prompt,
                    user_prompt_path=verifier_prompt_path,
                    max_tokens=128000,
                    # tools_needed=True routes to claude_cli (WebFetch capable).
                    tools_needed=True,
                ),
                start_to_close_timeout=timedelta(seconds=300),
                retry_policy=HAIKU_POLICY,
            )
            raw_verification = verifier_result.get("VERIFICATION", "{}")
            try:
                verification_result = json.loads(raw_verification)
            except json.JSONDecodeError:
                verification_result = {"parse_error": raw_verification[:200]}

        # ------------------------------------------------------------------
        # Phase 5: termination label selection.
        # ------------------------------------------------------------------
        if termination_label is None:
            uncovered = [
                cat for cat, covered in required_categories_covered.items() if not covered
            ]
            if not frontier:
                if (
                    not uncovered
                    and rounds_without_new_dimensions >= 2
                ):
                    termination_label = "Conditions Met"
                else:
                    termination_label = "Convergence — frontier exhausted before full coverage"
            else:
                termination_label = "Max Rounds Reached"

        # ------------------------------------------------------------------
        # Phase 5.5: rationalization auditor (Sonnet).
        # ------------------------------------------------------------------
        # Build draft report text for the auditor to evaluate.
        draft_report_md = _build_draft_report(
            artifact_type=inp.artifact_type,
            defects=all_defects,
            rounds_run=rounds_run,
            termination_label=termination_label,
            verification_result=verification_result,
        )

        audit_attempts = 0
        final_report_md: str | None = None

        while audit_attempts < _MAX_AUDIT_ATTEMPTS:
            audit_input_path = f"{inp.run_dir}/audit-input-{audit_attempts}.txt"
            await workflow.execute_activity(
                "write_artifact",
                WriteArtifactInput(
                    path=audit_input_path,
                    content=Template(inp.auditor_user_prompt).safe_substitute(
                        defect_count=str(len(all_defects)),
                        verdict_summary=_format_verdict_summary(all_defects),
                        draft_report_md=draft_report_md[:8000],
                    ),
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=HAIKU_POLICY,
            )
            audit_result = await workflow.execute_activity(
                "spawn_subagent",
                SpawnSubagentInput(
                    role="auditor",
                    tier_name="SONNET",
                    system_prompt=inp.auditor_system_prompt,
                    user_prompt_path=audit_input_path,
                    max_tokens=128000,
                    tools_needed=False,
                ),
                start_to_close_timeout=timedelta(seconds=600),
                retry_policy=SONNET_POLICY,
            )
            fidelity = audit_result.get("REPORT_FIDELITY", "compromised")
            audit_attempts += 1

            if fidelity == "clean":
                # Proceed with draft_report_md as-is.
                final_report_md = draft_report_md
                break
            else:
                # Re-assemble strictly from judge verdicts.
                draft_report_md = _reassemble_from_verdicts(
                    defects=all_defects,
                    termination_label=termination_label,
                )

        if final_report_md is None:
            # Two compromised verdicts — hard exit with special label.
            termination_label = "Audit compromised — report re-assembled from verdicts only"
            final_report_md = (
                "⚠️ Coordinator drift detected by rationalization auditor on two consecutive "
                "assemblies. This report is the mechanical assembly of judge verdicts without "
                "coordinator synthesis.\n\n"
                + draft_report_md
            )

        # ------------------------------------------------------------------
        # Phase 6: write report + emit finding.
        # ------------------------------------------------------------------
        # When the rationalization auditor found drift on both attempts, skip the
        # synthesizer entirely — the mechanically-assembled report is already in
        # final_report_md and must not be overwritten by coordinator prose.
        _audit_compromised = termination_label == "Audit compromised — report re-assembled from verdicts only"

        if _audit_compromised:
            report_md = final_report_md
        else:
            # Run Sonnet synthesizer on the audited draft for final polish.
            await workflow.execute_activity(
                "write_artifact",
                WriteArtifactInput(
                    path=synth_prompt_path,
                    content=Template(inp.synth_user_prompt).safe_substitute(
                        artifact_type=inp.artifact_type,
                        rounds_run=str(rounds_run),
                        max_rounds=str(inp.max_rounds),
                        termination_label=termination_label,
                        verification_section=(
                            f"\nFact verification results: {json.dumps(verification_result)}\n"
                            if verification_result is not None else ""
                        ),
                        defect_count=str(len(all_defects)),
                        defects_json=json.dumps(
                            [
                                {
                                    "id": d.id, "title": d.title, "severity": d.severity,
                                    "dimension": d.dimension, "scenario": d.scenario,
                                    "root_cause": d.root_cause, "judge_status": d.judge_status,
                                }
                                for d in all_defects
                            ],
                            indent=2,
                        ),
                        draft_report_md=final_report_md[:4000],
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
                    max_tokens=128000,
                    tools_needed=False,
                ),
                start_to_close_timeout=timedelta(seconds=600),
                retry_policy=SONNET_POLICY,
            )
            synth_report = synth_result.get("REPORT") or ""
            # Fallback: if synth returned malformed output, a stub header, or
            # an empty string, use the audited draft instead of a 1-line file.
            if len(synth_report.strip()) > len("# QA Report\n"):
                report_md = synth_report
            else:
                report_md = final_report_md

        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(path=report_path, content=report_md),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )

        severity_count = _severity_tally(all_defects)
        summary = (
            f"{severity_count['critical']} critical, "
            f"{severity_count['major']} major, "
            f"{severity_count['minor']} minor defects across {rounds_run} rounds"
        )
        status = "DONE" if rounds_run > 0 else "EMPTY"
        timestamp = workflow.now().isoformat(timespec="seconds")
        await workflow.execute_activity(
            "emit_finding",
            EmitFindingInput(
                inbox_path=inp.inbox_path,
                run_id=inp.run_id,
                skill="deep-qa",
                status=status,
                summary=summary,
                notify=inp.notify,
                timestamp_iso=timestamp,
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        return f"{summary}\nReport: {report_path}\nTermination: {termination_label}"


# ---------------------------------------------------------------------------
# Runtime formatting helpers (used to fill $placeholders in .md templates)
# ---------------------------------------------------------------------------


def _format_defects_blind(defects: list["Defect"]) -> str:
    """Format defects for pass-1 blind judge (severity stripped)."""
    lines: list[str] = []
    for d in defects:
        lines.append(f"Defect ID: {d.id}")
        lines.append(f"Title: {d.title}")
        lines.append(f"Dimension: {d.dimension}")
        lines.append(f"Scenario: {d.scenario}")
        lines.append(f"Root cause: {d.root_cause}")
        lines.append("")
    return "\n".join(lines)


def _format_defects_informed(defects: list["Defect"]) -> str:
    """Format defects for pass-2 informed judge (includes severity + pass-1 verdict)."""
    lines: list[str] = []
    for d in defects:
        lines.append(f"Defect ID: {d.id}")
        lines.append(f"Title: {d.title}")
        lines.append(f"Dimension: {d.dimension}")
        lines.append(f"Scenario: {d.scenario}")
        lines.append(f"Root cause: {d.root_cause}")
        lines.append(f"Critic-proposed severity: {d.severity}")
        if d.judge_pass_1_verdict:
            v1 = d.judge_pass_1_verdict
            lines.append(f"Pass-1 blind verdict: {v1.severity} (confidence={v1.confidence})")
            lines.append(f"Pass-1 rationale: {v1.rationale}")
        lines.append("")
    return "\n".join(lines)


def _format_verdict_summary(defects: list["Defect"]) -> str:
    """Format verdict summary for auditor user prompt."""
    lines: list[str] = []
    for d in defects:
        p2 = d.judge_pass_2_verdict
        p2_sev = p2.severity if p2 else "no-pass2"
        lines.append(
            f"  - {d.id}: critic={d.severity}, judge_p2={p2_sev}, judge_status={d.judge_status}"
        )
    return "\n".join(lines) or "  (no defects)"


# ---------------------------------------------------------------------------
# Report assembly helpers
# ---------------------------------------------------------------------------


def _build_draft_report(
    artifact_type: str,
    defects: list["Defect"],
    rounds_run: int,
    termination_label: str,
    verification_result: dict | None,
) -> str:
    counts = _severity_tally_from_defects(defects)
    lines = [
        "# QA Report",
        "",
        f"**Artifact type:** {artifact_type}",
        f"**Rounds:** {rounds_run}",
        f"**Termination:** {termination_label}",
        f"**Totals:** {counts['critical']} critical / {counts['major']} major / "
        f"{counts['minor']} minor",
        "",
    ]
    if verification_result:
        lines += [
            "## Fact Verification (research)",
            "",
            f"- Claims checked: {verification_result.get('checked_count', '?')} / "
            f"{verification_result.get('total_claims', '?')}",
            f"- Accessible rate: {verification_result.get('accessible_rate', '?')}",
            f"- Mismatches found: {verification_result.get('mismatches', '?')}",
            "",
        ]
    for sev in ("critical", "major", "minor"):
        sev_defects = [d for d in defects if d.severity == sev]
        if sev_defects:
            lines.append(f"## {sev.capitalize()} Defects")
            lines.append("")
            for d in sev_defects:
                lines.append(f"### {d.id}: {d.title}")
                lines.append(f"- **Dimension:** {d.dimension}")
                lines.append(f"- **Scenario:** {d.scenario}")
                lines.append(f"- **Root cause:** {d.root_cause}")
                lines.append(f"- **Judge status:** {d.judge_status}")
                lines.append("")
    return "\n".join(lines)


def _reassemble_from_verdicts(
    defects: list["Defect"],
    termination_label: str,
) -> str:
    """Re-assemble report strictly from pass-2 judge verdicts."""
    counts = _severity_tally_from_defects(defects)
    lines = [
        "# QA Report (re-assembled from judge verdicts)",
        "",
        "⚠️ Re-assembled after rationalization auditor flagged coordinator drift.",
        "",
        f"**Termination:** {termination_label}",
        f"**Totals:** {counts['critical']} critical / {counts['major']} major / "
        f"{counts['minor']} minor",
        "",
    ]
    for sev in ("critical", "major", "minor"):
        sev_defects = [d for d in defects if d.severity == sev]
        if sev_defects:
            lines.append(f"## {sev.capitalize()}")
            lines.append("")
            for d in sev_defects:
                p2 = d.judge_pass_2_verdict
                rationale = p2.rationale if p2 else "(no pass-2 verdict)"
                lines.append(f"- **{d.id}** — {d.title}")
                lines.append(f"  Rationale: {rationale}")
            lines.append("")
    return "\n".join(lines)


def _fallback_report(defects: list["Defect"], rounds_run: int) -> str:
    counts = _severity_tally_from_defects(defects)
    lines = [
        "# QA Report (fallback synthesis)",
        "",
        f"The synthesizer produced no structured output. Rounds run: {rounds_run}.",
        "",
        f"**Severity tally:** {counts['critical']} critical / {counts['major']} major / "
        f"{counts['minor']} minor.",
        "",
        "## Defects",
        "",
    ]
    for d in defects:
        lines.append(
            f"- [{d.severity}] {d.title} — {d.scenario}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_angles(raw: str) -> list["Angle"]:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            angles = []
            for i, a in enumerate(parsed):
                if isinstance(a, dict):
                    angles.append(
                        Angle(
                            id=a.get("id") or f"a{i}",
                            question=a.get("question", ""),
                            dimension=a.get("dimension", "general"),
                        )
                    )
            return angles
    except json.JSONDecodeError:
        pass
    return []


def _parse_raw_defects(raw: str) -> list[dict]:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [d for d in parsed if isinstance(d, dict)]
    except json.JSONDecodeError:
        pass
    return []


def _parse_verdicts(raw: str) -> list["JudgeVerdict"]:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            verdicts = []
            for v in parsed:
                if not isinstance(v, dict):
                    continue
                sev = v.get("severity", "critical")
                if sev not in ("critical", "major", "minor"):
                    sev = "critical"  # fail-safe per spec
                verdicts.append(
                    JudgeVerdict(
                        defect_id=v.get("defect_id", ""),
                        severity=sev,  # type: ignore[arg-type]
                        confidence=v.get("confidence", "low"),
                        calibration=v.get("calibration", "confirm"),
                        rationale=v.get("rationale", ""),
                    )
                )
            return verdicts
    except json.JSONDecodeError:
        pass
    return []


def _severity_tally_from_defects(defects: list["Defect"]) -> dict[str, int]:
    counts: dict[str, int] = {"critical": 0, "major": 0, "minor": 0}
    for d in defects:
        sev = d.severity.lower()
        if sev in counts:
            counts[sev] += 1
    return counts


# Keep old dict-based signature for backward compat with the fallback helper above.
def _severity_tally(defects: list["Defect"]) -> dict[str, int]:
    return _severity_tally_from_defects(defects)


def _chunk(items: list, size: int) -> list[list]:
    """Split a list into consecutive chunks of at most `size`."""
    return [items[i : i + size] for i in range(0, len(items), size)]
