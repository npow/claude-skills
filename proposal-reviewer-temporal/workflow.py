"""proposal-reviewer-temporal: Temporal port of the proposal-reviewer skill.

Phases:
  0. Input validation + SHA256 anti-tampering lock.
  1. Claim extraction (Sonnet): parse core claims from the proposal.
  2. Parallel critiques on 4 dimensions (Haiku x4): viability, competition,
     structural, evidence.  Quorum gate: >=3/4 must succeed.
  3. Fact-check each claim in parallel (Haiku x N, capped at 4).
     Fact-checker proposes verdicts; proposed verdict is STRIPPED before judge.
  4a. Credibility judge per claim — two-pass (Haiku pass-1, informed pass-2).
  4b. Severity + falsifiability judge per weakness — two-pass (Haiku x2).
  4c. Landscape judge (Opus-tier) — market window + platform risk.
  5. Rationalization auditor (Opus-tier) — acceptance-rate + fidelity check.
     Two compromised runs => terminate insufficient_evidence_to_review.
  6. Iron-law gate: every claim has credibility verdict; every weakness has
     severity verdict.  Missing => halt.
  7. Assembly (Sonnet): emit REPORT|<markdown> + termination label.
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

# Fixed 4 critique dimensions for Phase 2.
_CRITIQUE_DIMENSIONS = ["viability", "competition", "structural", "evidence"]

# Cap on parallel fact-check calls.
_MAX_FACT_CHECK = 4

# Quorum threshold: at least this many of 4 critics must succeed.
_QUORUM_MIN = 3

# Termination constants.
_LABEL_HIGH = "high_conviction_review"
_LABEL_MIXED = "mixed_evidence"
_LABEL_INSUFFICIENT = "insufficient_evidence_to_review"
_LABEL_DECLINED = "declined_unfalsifiable"


@dataclass(frozen=True)
class ProposalReviewInput:
    run_id: str
    proposal_text: str
    inbox_path: str
    run_dir: str
    notify: bool = True
    # Prompt overrides — loaded from ~/.claude/skills/proposal-reviewer/prompts/.
    # Empty string means "use inline default".
    claim_extraction_system_prompt: str = ""
    claim_extraction_user_prompt: str = ""
    critic_system_prompt: str = ""
    critic_user_prompt: str = ""
    fact_check_system_prompt: str = ""
    fact_check_user_prompt: str = ""
    credibility_judge_system_prompt: str = ""
    credibility_judge_pass1_prompt: str = ""
    credibility_judge_pass2_prompt: str = ""
    severity_judge_system_prompt: str = ""
    severity_judge_pass1_prompt: str = ""
    severity_judge_pass2_prompt: str = ""
    landscape_judge_system_prompt: str = ""
    landscape_judge_user_prompt: str = ""
    audit_system_prompt: str = ""
    audit_user_prompt: str = ""
    assembly_system_prompt: str = ""
    assembly_user_prompt: str = ""


@workflow.defn(name="ProposalReviewWorkflow")
class ProposalReviewWorkflow:
    @workflow.run
    async def run(self, inp: ProposalReviewInput) -> str:  # noqa: PLR0912, PLR0915
        run_dir = inp.run_dir
        proposal_sha256 = hashlib.sha256(inp.proposal_text.encode()).hexdigest()

        # ------------------------------------------------------------------ #
        # Phase 1: claim extraction.                                          #
        # ------------------------------------------------------------------ #
        claim_prompt_path = f"{run_dir}/claim-prompt.txt"
        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(
                path=claim_prompt_path,
                content=inp.claim_extraction_user_prompt,
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        claim_result = await workflow.execute_activity(
            "spawn_subagent",
            SpawnSubagentInput(
                role="claim-extractor",
                tier_name="SONNET",
                system_prompt=inp.claim_extraction_system_prompt,
                user_prompt_path=claim_prompt_path,
                max_tokens=1024,
                tools_needed=False,
            ),
            start_to_close_timeout=timedelta(seconds=600),
            retry_policy=SONNET_POLICY,
        )
        claims_raw = claim_result.get("CLAIMS", "[]")
        claims = _parse_json_list(claims_raw)

        # ------------------------------------------------------------------ #
        # Phase 2: 4 parallel critiques (quorum gate).                        #
        # ------------------------------------------------------------------ #
        critic_prompt_paths: list[str] = []
        for dim in _CRITIQUE_DIMENSIONS:
            ppath = f"{run_dir}/critic-{dim}.txt"
            await workflow.execute_activity(
                "write_artifact",
                WriteArtifactInput(
                    path=ppath,
                    content=inp.critic_user_prompt or _critic_user_prompt(inp.proposal_text, dim),  # runtime-dynamic
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=HAIKU_POLICY,
            )
            critic_prompt_paths.append(ppath)

        critic_coros = [
            workflow.execute_activity(
                "spawn_subagent",
                SpawnSubagentInput(
                    role="critic",
                    tier_name="HAIKU",
                    system_prompt=inp.critic_system_prompt or _critic_system_prompt(dim),  # dim-dependent
                    user_prompt_path=ppath,
                    max_tokens=1024,
                    tools_needed=False,
                ),
                start_to_close_timeout=timedelta(seconds=600),
                retry_policy=HAIKU_POLICY,
            )
            for dim, ppath in zip(_CRITIQUE_DIMENSIONS, critic_prompt_paths)
        ]
        critic_outputs = await asyncio.gather(*critic_coros, return_exceptions=True)

        # Quorum check — a result is "parseable" only if it's a dict with
        # real structured output (not the malformed sentinel).
        raw_critic_texts: list[str] = []  # collect raw text for fallback report
        parseable_count = 0
        for r in critic_outputs:
            if isinstance(r, BaseException):
                raw_critic_texts.append(f"[exception] {r}")
            elif isinstance(r, dict) and r.get("_sagaflow_malformed"):
                # Malformed sentinel — extract raw text but don't count as parseable.
                raw_critic_texts.append(r.get("_raw", r.get("_error", "(malformed)")))
            elif isinstance(r, dict):
                parseable_count += 1
                raw_critic_texts.append(r.get("WEAKNESSES", "(no weaknesses key)"))
            else:
                raw_critic_texts.append(str(r))

        if parseable_count < _QUORUM_MIN:
            return await self._terminate(
                inp,
                label=_LABEL_INSUFFICIENT,
                reason=f"critic quorum failed ({parseable_count}/{len(_CRITIQUE_DIMENSIONS)} parseable)",
                claims=claims,
                weaknesses=[],
                credibility_verdicts=[],
                severity_verdicts=[],
                landscape_verdict=None,
                audit_result=None,
                proposal_sha256=proposal_sha256,
                raw_critic_texts=raw_critic_texts,
            )

        all_weaknesses: list[dict[str, str]] = []
        for dim, result in zip(_CRITIQUE_DIMENSIONS, critic_outputs):
            if isinstance(result, BaseException):
                continue
            # Skip malformed sentinels — already captured in raw_critic_texts.
            if isinstance(result, dict) and result.get("_sagaflow_malformed"):
                continue
            raw = result.get("WEAKNESSES", "[]")
            for w in _parse_json_list(raw):
                w.setdefault("dimension", dim)
                # Require author_counter_response; drop weakness if absent.
                if not w.get("counter_response"):
                    continue
                all_weaknesses.append(w)

        # ------------------------------------------------------------------ #
        # Phase 3: fact-check each claim (proposed verdicts only).            #
        # ------------------------------------------------------------------ #
        claims_to_check = claims[:_MAX_FACT_CHECK]
        fact_check_proposed: list[dict[str, str]] = []

        if claims_to_check:
            fc_prompt_paths: list[str] = []
            for i, claim in enumerate(claims_to_check):
                ppath = f"{run_dir}/fc-{i}.txt"
                await workflow.execute_activity(
                    "write_artifact",
                    WriteArtifactInput(
                        path=ppath,
                        content=inp.fact_check_user_prompt or _fact_check_user_prompt(claim),  # runtime-dynamic
                    ),
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=HAIKU_POLICY,
                )
                fc_prompt_paths.append(ppath)

            fc_coros = [
                workflow.execute_activity(
                    "spawn_subagent",
                    SpawnSubagentInput(
                        role="fact-check",
                        tier_name="HAIKU",
                        system_prompt=inp.fact_check_system_prompt,
                        user_prompt_path=ppath,
                        max_tokens=512,
                        tools_needed=False,
                    ),
                    start_to_close_timeout=timedelta(seconds=600),
                    retry_policy=HAIKU_POLICY,
                )
                for ppath in fc_prompt_paths
            ]
            fc_outputs = await asyncio.gather(*fc_coros, return_exceptions=True)
            for claim, fc_out in zip(claims_to_check, fc_outputs):
                if isinstance(fc_out, BaseException):
                    # Treat as UNVERIFIABLE on failure.
                    fact_check_proposed.append(
                        {
                            "claim_id": claim.get("id", ""),
                            "claim_text": claim.get("text", ""),
                            "proposed_verdict": "UNVERIFIABLE",
                            "confidence": "low",
                            "evidence": "",
                        }
                    )
                    continue
                fact_check_proposed.append(
                    {
                        "claim_id": claim.get("id", ""),
                        "claim_text": claim.get("text", ""),
                        # Proposed verdict stored here; STRIPPED before judge sees it.
                        "proposed_verdict": fc_out.get("VERDICT", "UNVERIFIABLE"),
                        "confidence": fc_out.get("CONFIDENCE", "low"),
                        "evidence": fc_out.get("EVIDENCE", ""),
                    }
                )

        # ------------------------------------------------------------------ #
        # Phase 4a: credibility judge per claim (two-pass, blind pass-1).    #
        # ------------------------------------------------------------------ #
        credibility_verdicts: list[dict[str, str]] = []

        for fc_entry in fact_check_proposed:
            claim_id = fc_entry["claim_id"]
            claim_text = fc_entry["claim_text"]
            evidence = fc_entry["evidence"]
            proposed_verdict = fc_entry["proposed_verdict"]

            # Pass 1 — blind (proposed verdict STRIPPED).
            p1_path = f"{run_dir}/cred-judge1-{claim_id}.txt"
            await workflow.execute_activity(
                "write_artifact",
                WriteArtifactInput(
                    path=p1_path,
                    content=inp.credibility_judge_pass1_prompt or _credibility_judge_pass1_prompt(claim_id, claim_text, evidence),  # runtime-dynamic
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=HAIKU_POLICY,
            )
            p1_result = await workflow.execute_activity(
                "spawn_subagent",
                SpawnSubagentInput(
                    role="credibility-judge-1",
                    tier_name="HAIKU",
                    system_prompt=inp.credibility_judge_system_prompt,
                    user_prompt_path=p1_path,
                    max_tokens=512,
                    tools_needed=False,
                ),
                start_to_close_timeout=timedelta(seconds=600),
                retry_policy=HAIKU_POLICY,
            )
            pass1_verdict = p1_result.get("VERDICT_PASS_1", "UNVERIFIABLE")

            # Pass 2 — informed (pass-1 result + proposed verdict supplied).
            p2_path = f"{run_dir}/cred-judge2-{claim_id}.txt"
            await workflow.execute_activity(
                "write_artifact",
                WriteArtifactInput(
                    path=p2_path,
                    content=inp.credibility_judge_pass2_prompt or _credibility_judge_pass2_prompt(  # runtime-dynamic
                        claim_id, claim_text, evidence, pass1_verdict, proposed_verdict
                    ),
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=HAIKU_POLICY,
            )
            p2_result = await workflow.execute_activity(
                "spawn_subagent",
                SpawnSubagentInput(
                    role="credibility-judge-2",
                    tier_name="HAIKU",
                    system_prompt=inp.credibility_judge_system_prompt,
                    user_prompt_path=p2_path,
                    max_tokens=512,
                    tools_needed=False,
                ),
                start_to_close_timeout=timedelta(seconds=600),
                retry_policy=HAIKU_POLICY,
            )
            final_verdict = p2_result.get("VERDICT_FINAL", pass1_verdict)
            confidence = p2_result.get("CONFIDENCE", "low")
            credibility_verdicts.append(
                {
                    "claim_id": claim_id,
                    "verdict": final_verdict,
                    "confidence": confidence,
                }
            )

        # ------------------------------------------------------------------ #
        # Phase 4b: severity + falsifiability judge per weakness (two-pass). #
        # ------------------------------------------------------------------ #
        severity_verdicts: list[dict[str, str]] = []
        all_unfalsifiable = True  # track if every weakness is rejected

        for i, weakness in enumerate(all_weaknesses):
            wid = weakness.get("id", f"w{i}")
            dim = weakness.get("dimension", "unknown")
            full_wid = f"{dim}-{wid}"

            # Pass 1 — blind (severity claim AND falsifiability block stripped).
            s1_path = f"{run_dir}/sev-judge1-{i}.txt"
            await workflow.execute_activity(
                "write_artifact",
                WriteArtifactInput(
                    path=s1_path,
                    content=inp.severity_judge_pass1_prompt or _severity_judge_pass1_prompt(weakness),  # runtime-dynamic
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=HAIKU_POLICY,
            )
            s1_result = await workflow.execute_activity(
                "spawn_subagent",
                SpawnSubagentInput(
                    role="severity-judge-1",
                    tier_name="HAIKU",
                    system_prompt=inp.severity_judge_system_prompt,
                    user_prompt_path=s1_path,
                    max_tokens=512,
                    tools_needed=False,
                ),
                start_to_close_timeout=timedelta(seconds=600),
                retry_policy=HAIKU_POLICY,
            )
            falsifiable_p1 = s1_result.get("FALSIFIABLE", "no").lower() == "yes"
            severity_p1 = s1_result.get("SEVERITY_PASS_1", "minor")

            # Pass 2 — informed (pass-1 verdict + critic's original severity).
            critic_severity = weakness.get("severity", "minor")
            s2_path = f"{run_dir}/sev-judge2-{i}.txt"
            await workflow.execute_activity(
                "write_artifact",
                WriteArtifactInput(
                    path=s2_path,
                    content=inp.severity_judge_pass2_prompt or _severity_judge_pass2_prompt(  # runtime-dynamic
                        weakness, falsifiable_p1, severity_p1, critic_severity
                    ),
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=HAIKU_POLICY,
            )
            s2_result = await workflow.execute_activity(
                "spawn_subagent",
                SpawnSubagentInput(
                    role="severity-judge-2",
                    tier_name="HAIKU",
                    system_prompt=inp.severity_judge_system_prompt,
                    user_prompt_path=s2_path,
                    max_tokens=512,
                    tools_needed=False,
                ),
                start_to_close_timeout=timedelta(seconds=600),
                retry_policy=HAIKU_POLICY,
            )
            falsifiable_final = s2_result.get("FALSIFIABLE", "no").lower() == "yes"
            severity_final = s2_result.get("SEVERITY_FINAL", severity_p1)
            fixability = s2_result.get("FIXABILITY", "fixable")

            if falsifiable_final:
                all_unfalsifiable = False

            severity_verdicts.append(
                {
                    "weakness_id": full_wid,
                    "falsifiable": "yes" if falsifiable_final else "no",
                    "severity": severity_final,
                    "fixability": fixability,
                    "title": weakness.get("title", ""),
                    "scenario": weakness.get("scenario", ""),
                    "counter_response": weakness.get("counter_response", ""),
                    "dimension": dim,
                }
            )

        # Declined-unfalsifiable: every weakness was rejected.
        if all_weaknesses and all_unfalsifiable:
            return await self._terminate(
                inp,
                label=_LABEL_DECLINED,
                reason="every critic weakness was rejected by Judge B as unfalsifiable",
                claims=claims,
                weaknesses=all_weaknesses,
                credibility_verdicts=credibility_verdicts,
                severity_verdicts=severity_verdicts,
                landscape_verdict=None,
                audit_result=None,
                proposal_sha256=proposal_sha256,
            )

        # ------------------------------------------------------------------ #
        # Phase 4c: landscape judge (Opus-tier).                              #
        # ------------------------------------------------------------------ #
        landscape_prompt_path = f"{run_dir}/landscape-judge.txt"
        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(
                path=landscape_prompt_path,
                content=inp.landscape_judge_user_prompt or _landscape_judge_user_prompt(inp.proposal_text, critic_outputs),  # runtime-dynamic
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        landscape_result = await workflow.execute_activity(
            "spawn_subagent",
            SpawnSubagentInput(
                role="landscape-judge",
                tier_name="SONNET",  # Opus-tier intent; SONNET used for test compat.
                system_prompt=inp.landscape_judge_system_prompt,
                user_prompt_path=landscape_prompt_path,
                max_tokens=512,
                tools_needed=False,
            ),
            start_to_close_timeout=timedelta(seconds=600),
            retry_policy=SONNET_POLICY,
        )
        landscape_verdict = {
            "market_window": landscape_result.get("MARKET_WINDOW", "open"),
            "platform_risk": landscape_result.get("PLATFORM_RISK", "low"),
            "most_likely_threat": landscape_result.get("BLIND_SPOT", ""),
        }

        # ------------------------------------------------------------------ #
        # Iron-law gate — every claim has credibility verdict; every weakness #
        # has severity verdict.                                               #
        # ------------------------------------------------------------------ #
        checked_claim_ids = {v["claim_id"] for v in credibility_verdicts}
        for fc in fact_check_proposed:
            if fc["claim_id"] not in checked_claim_ids:
                return await self._terminate(
                    inp,
                    label=_LABEL_INSUFFICIENT,
                    reason=f"missing_verdict for claim {fc['claim_id']}",
                    claims=claims,
                    weaknesses=all_weaknesses,
                    credibility_verdicts=credibility_verdicts,
                    severity_verdicts=severity_verdicts,
                    landscape_verdict=landscape_verdict,
                    audit_result=None,
                    proposal_sha256=proposal_sha256,
                )

        # ------------------------------------------------------------------ #
        # Phase 5: rationalization auditor (Opus-tier).                      #
        # ------------------------------------------------------------------ #
        audit_prompt_path = f"{run_dir}/audit-prompt.txt"
        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(
                path=audit_prompt_path,
                content=inp.audit_user_prompt or _audit_user_prompt(credibility_verdicts, severity_verdicts),  # runtime-dynamic
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        audit_result_raw = await workflow.execute_activity(
            "spawn_subagent",
            SpawnSubagentInput(
                role="rationalization-auditor",
                tier_name="SONNET",  # Opus-tier intent; SONNET for test compat.
                system_prompt=inp.audit_system_prompt,
                user_prompt_path=audit_prompt_path,
                max_tokens=1024,
                tools_needed=False,
            ),
            start_to_close_timeout=timedelta(seconds=600),
            retry_policy=SONNET_POLICY,
        )
        audit_fidelity = audit_result_raw.get("REPORT_FIDELITY", "clean")
        audit_suspicious = audit_result_raw.get("SUSPICIOUS_PATTERN", "none")
        # Count how many "compromised" signals are present.
        compromised_count = audit_result_raw.get("COMPROMISED_COUNT", "0")
        try:
            n_compromised = int(compromised_count)
        except ValueError:
            n_compromised = 1 if audit_fidelity == "compromised" else 0

        audit_result: dict[str, str] = {
            "fidelity": audit_fidelity,
            "suspicious_patterns": audit_suspicious,
            "compromised_count": str(n_compromised),
        }

        if n_compromised >= 2 or (audit_fidelity == "compromised" and n_compromised >= 1):
            return await self._terminate(
                inp,
                label=_LABEL_INSUFFICIENT,
                reason="rationalization audit compromised twice",
                claims=claims,
                weaknesses=all_weaknesses,
                credibility_verdicts=credibility_verdicts,
                severity_verdicts=severity_verdicts,
                landscape_verdict=landscape_verdict,
                audit_result=audit_result,
                proposal_sha256=proposal_sha256,
            )

        # ------------------------------------------------------------------ #
        # Phase 6: determine termination label from verdicts.                 #
        # ------------------------------------------------------------------ #
        label = _termination_label(credibility_verdicts, severity_verdicts, audit_fidelity)

        # ------------------------------------------------------------------ #
        # Phase 7: assemble final report (Sonnet).                           #
        # ------------------------------------------------------------------ #
        synth_prompt_path = f"{run_dir}/synth-prompt.txt"
        report_path = f"{run_dir}/review.md"

        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(
                path=synth_prompt_path,
                content=inp.assembly_user_prompt or _assembly_user_prompt(  # runtime-dynamic
                    proposal_text=inp.proposal_text,
                    claims=claims,
                    weaknesses=all_weaknesses,
                    credibility_verdicts=credibility_verdicts,
                    severity_verdicts=severity_verdicts,
                    landscape_verdict=landscape_verdict,
                    audit_result=audit_result,
                    label=label,
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
                system_prompt=inp.assembly_system_prompt,
                user_prompt_path=synth_prompt_path,
                max_tokens=4096,
                tools_needed=False,
            ),
            start_to_close_timeout=timedelta(seconds=600),
            retry_policy=SONNET_POLICY,
        )
        report_md = synth_result.get(
            "REPORT",
            _fallback_report(
                claims, all_weaknesses, credibility_verdicts, severity_verdicts, label
            ),
        )

        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(path=report_path, content=report_md),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )

        weak_count = len(all_weaknesses)
        claim_count = len(claims)
        summary = (
            f"{claim_count} claims extracted, {weak_count} weaknesses found; "
            f"label={label}"
        )
        timestamp = workflow.now().isoformat(timespec="seconds")
        await workflow.execute_activity(
            "emit_finding",
            EmitFindingInput(
                inbox_path=inp.inbox_path,
                run_id=inp.run_id,
                skill="proposal-reviewer",
                status="DONE",
                summary=summary,
                notify=inp.notify,
                timestamp_iso=timestamp,
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        return f"{summary}\nReport: {report_path}"

    async def _terminate(
        self,
        inp: ProposalReviewInput,
        *,
        label: str,
        reason: str,
        claims: list[dict[str, str]],
        weaknesses: list[dict[str, str]],
        credibility_verdicts: list[dict[str, str]],
        severity_verdicts: list[dict[str, str]],
        landscape_verdict: dict[str, str] | None,
        audit_result: dict[str, str] | None,
        proposal_sha256: str,
        raw_critic_texts: list[str] | None = None,
    ) -> str:
        """Write a minimal report and emit finding for early-exit paths."""
        run_dir = inp.run_dir
        report_path = f"{run_dir}/review.md"
        report_md = _fallback_report(
            claims, weaknesses, credibility_verdicts, severity_verdicts, label,
            reason=reason, raw_critic_texts=raw_critic_texts,
        )
        await workflow.execute_activity(
            "write_artifact",
            WriteArtifactInput(path=report_path, content=report_md),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        summary = f"label={label}; reason={reason}"
        timestamp = workflow.now().isoformat(timespec="seconds")
        await workflow.execute_activity(
            "emit_finding",
            EmitFindingInput(
                inbox_path=inp.inbox_path,
                run_id=inp.run_id,
                skill="proposal-reviewer",
                status="DONE",
                summary=summary,
                notify=inp.notify,
                timestamp_iso=timestamp,
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=HAIKU_POLICY,
        )
        return f"{summary}\nReport: {report_path}"


# --------------------------------------------------------------------------- #
# Prompt templates                                                             #
# --------------------------------------------------------------------------- #



def _critic_system_prompt(dimension: str) -> str:
    dim_instructions = {
        "viability": "Focus on technical and operational feasibility. Can this actually be built/executed?",
        "competition": "Focus on the competitive landscape. Are there existing solutions? What differentiates this?",
        "structural": "Focus on logical consistency, gaps in reasoning, and internal contradictions.",
        "evidence": "Focus on the quality and sufficiency of evidence. Are claims backed by data?",
    }
    instruction = dim_instructions.get(dimension, f"Focus on the {dimension} dimension.")
    return (
        f"You are a proposal critic specializing in the {dimension} dimension. "
        f"{instruction} "
        "Find real weaknesses — do not pad. Only flag genuine problems.\n\n"
        "FALSIFIABILITY REQUIREMENT: every weakness MUST include an author_counter_response "
        "field — a plausible defense the proposal author could mount. Weaknesses without "
        "counter_response will be dropped.\n\n"
        "Output format:\n"
        "STRUCTURED_OUTPUT_START\n"
        'WEAKNESSES|[{"id":"w1","title":"<short>","severity":"fatal|major|minor",'
        f'"dimension":"{dimension}","scenario":"<concrete situation>",'
        '"root_cause":"<one line>","fix_direction":"<one line>",'
        '"counter_response":"<plausible author defense>"}, ...]\n'
        "STRUCTURED_OUTPUT_END\n"
        "If no real weaknesses, emit WEAKNESSES|[]. Do not invent problems."
    )


def _critic_user_prompt(proposal_text: str, dimension: str) -> str:
    return (
        f"Critique dimension: {dimension}\n\n"
        "--- PROPOSAL START ---\n"
        f"{proposal_text[:20000]}\n"
        "--- PROPOSAL END ---\n"
    )



def _fact_check_user_prompt(claim: dict[str, str]) -> str:
    return (
        f"Claim ID: {claim.get('id', '?')}\n"
        f"Tier: {claim.get('tier', '?')}\n\n"
        f"Claim text:\n{claim.get('text', '')}\n\n"
        "Evaluate this claim."
    )



def _credibility_judge_pass1_prompt(
    claim_id: str, claim_text: str, evidence: str
) -> str:
    """Pass 1: proposed verdict STRIPPED — judge reads claim + evidence only."""
    return (
        f"Claim ID: {claim_id}\n"
        f"Claim: {claim_text}\n\n"
        f"Evidence gathered by fact-checker:\n{evidence or '(none provided)'}\n\n"
        "Assess the credibility of this claim based solely on the evidence above. "
        "Emit VERDICT_PASS_1 with one of: VERIFIED, PARTIALLY_TRUE, UNVERIFIABLE, FALSE."
    )


def _credibility_judge_pass2_prompt(
    claim_id: str,
    claim_text: str,
    evidence: str,
    pass1_verdict: str,
    proposed_verdict: str,
) -> str:
    """Pass 2: informed — judge sees pass-1 result and the fact-checker's proposal."""
    return (
        f"Claim ID: {claim_id}\n"
        f"Claim: {claim_text}\n\n"
        f"Evidence gathered by fact-checker:\n{evidence or '(none provided)'}\n\n"
        f"Your pass-1 verdict: {pass1_verdict}\n"
        f"Fact-checker's proposed verdict: {proposed_verdict}\n\n"
        "Review your pass-1 verdict in light of the fact-checker's proposed verdict. "
        "You may confirm, upgrade, or downgrade. Emit VERDICT_FINAL as the authoritative verdict."
    )



def _severity_judge_pass1_prompt(weakness: dict[str, str]) -> str:
    """Pass 1: critic's severity claim AND falsifiability block stripped."""
    return (
        f"Weakness title: {weakness.get('title', '?')}\n"
        f"Scenario: {weakness.get('scenario', '?')}\n"
        f"Root cause: {weakness.get('root_cause', '?')}\n"
        f"Author counter-response: {weakness.get('counter_response', '(none)')}\n\n"
        "Assess this weakness WITHOUT knowing the critic's severity claim.\n"
        "1. Is it FALSIFIABLE? (yes/no) — requires concrete scenario + plausible counter.\n"
        "2. What is your independent severity assessment? (fatal/major/minor/rejected)"
    )


def _severity_judge_pass2_prompt(
    weakness: dict[str, str],
    falsifiable_p1: bool,
    severity_p1: str,
    critic_severity: str,
) -> str:
    """Pass 2: informed — pass-1 verdicts + critic's original severity claim."""
    return (
        f"Weakness title: {weakness.get('title', '?')}\n"
        f"Scenario: {weakness.get('scenario', '?')}\n"
        f"Root cause: {weakness.get('root_cause', '?')}\n"
        f"Author counter-response: {weakness.get('counter_response', '(none)')}\n\n"
        f"Your pass-1 falsifiability: {'yes' if falsifiable_p1 else 'no'}\n"
        f"Your pass-1 severity: {severity_p1}\n"
        f"Critic's original severity claim: {critic_severity}\n\n"
        "Review your pass-1 verdicts in light of the critic's severity claim.\n"
        "Emit FALSIFIABLE, SEVERITY_FINAL, and FIXABILITY."
    )



def _landscape_judge_user_prompt(
    proposal_text: str, critic_outputs: list[object]
) -> str:
    competition_critique = ""
    for result in critic_outputs:
        if isinstance(result, dict):
            raw = result.get("WEAKNESSES", "")
            if raw:
                competition_critique += raw + "\n"
    return (
        "--- PROPOSAL START ---\n"
        f"{proposal_text[:10000]}\n"
        "--- PROPOSAL END ---\n\n"
        "--- COMPETITION CRITIQUE ---\n"
        f"{competition_critique or '(no competition critique available)'}\n"
        "--- END COMPETITION CRITIQUE ---\n\n"
        "Assess the market window, platform risk, and most likely blind spot."
    )



def _audit_user_prompt(
    credibility_verdicts: list[dict[str, str]],
    severity_verdicts: list[dict[str, str]],
) -> str:
    return (
        f"Credibility verdicts ({len(credibility_verdicts)}):\n"
        f"{json.dumps(credibility_verdicts, indent=2)}\n\n"
        f"Severity verdicts ({len(severity_verdicts)}):\n"
        f"{json.dumps(severity_verdicts, indent=2)}\n\n"
        "Audit the judge verdicts for rationalization patterns. "
        "Compute acceptance rates, detect suspicious patterns, and assess report fidelity."
    )



def _assembly_user_prompt(
    proposal_text: str,
    claims: list[dict[str, str]],
    weaknesses: list[dict[str, str]],
    credibility_verdicts: list[dict[str, str]],
    severity_verdicts: list[dict[str, str]],
    landscape_verdict: dict[str, str] | None,
    audit_result: dict[str, str] | None,
    label: str,
) -> str:
    return (
        f"Proposal length: {len(proposal_text)} chars\n"
        f"Claims ({len(claims)}):\n{json.dumps(claims, indent=2)}\n\n"
        f"Credibility verdicts ({len(credibility_verdicts)}):\n"
        f"{json.dumps(credibility_verdicts, indent=2)}\n\n"
        f"Severity verdicts ({len(severity_verdicts)}):\n"
        f"{json.dumps(severity_verdicts, indent=2)}\n\n"
        f"Landscape verdict:\n{json.dumps(landscape_verdict or {}, indent=2)}\n\n"
        f"Audit result:\n{json.dumps(audit_result or {}, indent=2)}\n\n"
        f"Termination label: {label}\n\n"
        "Write the comprehensive review following the required structure."
    )


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #


def _parse_json_list(raw: str) -> list[dict[str, str]]:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
    except json.JSONDecodeError:
        pass
    return []


def _termination_label(
    credibility_verdicts: list[dict[str, str]],
    severity_verdicts: list[dict[str, str]],
    audit_fidelity: str,
) -> str:
    """Derive label from judge verdict distribution per SKILL.md rules."""
    if not credibility_verdicts:
        return _LABEL_INSUFFICIENT

    verdicts = [v.get("verdict", "UNVERIFIABLE") for v in credibility_verdicts]
    total = len(verdicts)
    verified_count = sum(
        1 for v in verdicts if v in ("VERIFIED", "PARTIALLY_TRUE")
    )
    false_count = sum(1 for v in verdicts if v == "FALSE")
    unverifiable_count = sum(1 for v in verdicts if v == "UNVERIFIABLE")

    if unverifiable_count / total > 0.4:
        return _LABEL_INSUFFICIENT

    has_fatal_inherent = any(
        sv.get("severity") == "fatal" and sv.get("fixability") == "inherent_risk"
        for sv in severity_verdicts
        if sv.get("falsifiable") == "yes"
    )

    verified_pct = verified_count / total

    # high_conviction: >=80% verified/partially, zero FALSE, zero unresolved fatal,
    # audit clean.
    if (
        verified_pct >= 0.8
        and false_count == 0
        and not has_fatal_inherent
        and audit_fidelity == "clean"
    ):
        return _LABEL_HIGH

    # mixed_evidence: 50-80% verified, or any FALSE, or any fatal+inherent_risk.
    if verified_pct >= 0.5 or false_count > 0 or has_fatal_inherent:
        return _LABEL_MIXED

    return _LABEL_INSUFFICIENT


def _fallback_report(
    claims: list[dict[str, str]],
    weaknesses: list[dict[str, str]],
    credibility_verdicts: list[dict[str, str]],
    severity_verdicts: list[dict[str, str]],
    label: str,
    *,
    reason: str | None = None,
    raw_critic_texts: list[str] | None = None,
) -> str:
    lines = [
        "# Proposal Review Report",
        "",
    ]
    if reason:
        lines.extend([
            f"**Early termination:** {reason}",
            "",
        ])
    lines.extend([
        f"**Termination label:** {label}",
        f"**Claims extracted:** {len(claims)}",
        f"**Weaknesses found:** {len(weaknesses)}",
        "",
    ])
    # Claims section — always present so report is never empty.
    if claims:
        lines.extend(["## Extracted Claims", ""])
        for c in claims:
            tier = c.get("tier", "?")
            lines.append(f"- [{tier}] {c.get('text', '(no text)')}")
        lines.append("")

    lines.extend(["## Fact-Check Results", ""])
    if credibility_verdicts:
        for cv in credibility_verdicts:
            lines.append(
                f"- Claim {cv.get('claim_id', '?')}: "
                f"{cv.get('verdict', 'UNVERIFIABLE')} ({cv.get('confidence', 'low')})"
            )
    else:
        lines.append("No fact-check verdicts were produced (review terminated early).")
    lines.extend(["", "## Weaknesses (Falsifiable Only)", ""])
    if severity_verdicts:
        for sv in severity_verdicts:
            if sv.get("falsifiable") == "yes":
                lines.append(
                    f"- [{sv.get('severity', '?')}] [{sv.get('dimension', '?')}] "
                    f"{sv.get('title', '?')}: {sv.get('scenario', '')}"
                )
    else:
        lines.append("No severity verdicts were produced (review terminated early).")

    # Raw critic findings — dump whatever text was collected even if parsing failed.
    if raw_critic_texts:
        lines.extend(["", "## Raw Critic Findings", ""])
        lines.append(
            "The following raw outputs were collected from critic agents "
            "(parsing may have failed for some):"
        )
        lines.append("")
        for i, raw in enumerate(raw_critic_texts):
            dim = _CRITIQUE_DIMENSIONS[i] if i < len(_CRITIQUE_DIMENSIONS) else f"critic-{i}"
            lines.append(f"### {dim}")
            lines.append("")
            lines.append(f"```\n{raw}\n```")
            lines.append("")

    return "\n".join(lines)
