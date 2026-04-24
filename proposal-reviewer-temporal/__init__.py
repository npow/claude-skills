"""proposal-reviewer skill registration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sagaflow.durable.activities import emit_finding, spawn_subagent, write_artifact
from sagaflow.prompts import load_claude_skill_prompt
from sagaflow.registry import SkillRegistry, SkillSpec

from .workflow import ProposalReviewInput, ProposalReviewWorkflow

_MIN_WORDS = 200
_SKILL = "proposal-reviewer"


def _build_input(
    *, run_id: str, run_dir: str, inbox_path: str, cli_args: dict[str, Any]
) -> ProposalReviewInput:
    proposal_text = str(cli_args.get("proposal") or "")
    path = cli_args.get("path") or ""

    if not proposal_text and path:
        p = Path(str(path)).expanduser().resolve()
        proposal_text = p.read_text(encoding="utf-8", errors="replace")

    if not proposal_text:
        raise ValueError(
            "proposal-reviewer requires --arg proposal='...' or --path <file>"
        )

    word_count = len(proposal_text.split())
    if word_count < _MIN_WORDS:
        raise ValueError(
            f"Proposal too short: {word_count} words (minimum {_MIN_WORDS})."
        )

    notify = bool(cli_args.get("notify", True))
    return ProposalReviewInput(
        run_id=run_id,
        proposal_text=proposal_text,
        inbox_path=inbox_path,
        run_dir=run_dir,
        notify=notify,
        claim_extraction_system_prompt=load_claude_skill_prompt(_SKILL, "claim_extraction.system"),
        claim_extraction_user_prompt=load_claude_skill_prompt(
            _SKILL, "claim_extraction.user",
            substitutions={
                "proposal_length": str(len(proposal_text)),
                "proposal_text": proposal_text[:20000],
            },
        ),
        critic_system_prompt=load_claude_skill_prompt(_SKILL, "critic.system"),
        critic_user_prompt=load_claude_skill_prompt(_SKILL, "critic.user"),
        fact_check_system_prompt=load_claude_skill_prompt(_SKILL, "fact_check.system"),
        fact_check_user_prompt=load_claude_skill_prompt(_SKILL, "fact_check.user"),
        credibility_judge_system_prompt=load_claude_skill_prompt(_SKILL, "credibility_judge.system"),
        credibility_judge_pass1_prompt=load_claude_skill_prompt(_SKILL, "credibility_judge.pass1"),
        credibility_judge_pass2_prompt=load_claude_skill_prompt(_SKILL, "credibility_judge.pass2"),
        severity_judge_system_prompt=load_claude_skill_prompt(_SKILL, "severity_judge.system"),
        severity_judge_pass1_prompt=load_claude_skill_prompt(_SKILL, "severity_judge.pass1"),
        severity_judge_pass2_prompt=load_claude_skill_prompt(_SKILL, "severity_judge.pass2"),
        landscape_judge_system_prompt=load_claude_skill_prompt(_SKILL, "landscape_judge.system"),
        landscape_judge_user_prompt=load_claude_skill_prompt(_SKILL, "landscape_judge.user"),
        audit_system_prompt=load_claude_skill_prompt(_SKILL, "audit.system"),
        audit_user_prompt=load_claude_skill_prompt(_SKILL, "audit.user"),
        assembly_system_prompt=load_claude_skill_prompt(_SKILL, "assembly.system"),
        assembly_user_prompt=load_claude_skill_prompt(_SKILL, "assembly.user"),
    )


def register(registry: SkillRegistry) -> None:
    registry.register(
        SkillSpec(
            name="proposal-reviewer",
            workflow_cls=ProposalReviewWorkflow,
            activities=[write_artifact, emit_finding, spawn_subagent],
            build_input=_build_input,
        )
    )
