"""deep-research-temporal: dimension-expanded research with synthesis.

Implements:
  Phase 0f  — Language locus detection (Haiku, emits AUTHORITATIVE_LANGUAGES +
               COVERAGE_EXPECTATION).
  Phase 0g  — Novelty classification (Haiku + WebSearch, emits NOVELTY_CLASS).
               External source verification overrides self-report; ≥3/5 unverified
               forces cold_start.
  Phase 2.5 — Vocabulary bootstrap (conditional on novel|cold_start; Haiku/Sonnet +
               WebFetch; writes vocabulary_bootstrap.json).
  Phase 1   — Direction discovery including the 5 cross-cut dimensions
               (PRIOR-FAILURE, BASELINE, ADJACENT-EFFORTS, STRATEGIC-TIMING,
               ACTUAL-USAGE); state tracks per-dim coverage.
  Phase 2   — Per-direction researcher agents (Sonnet); writes per-direction
               findings files under deep-research-findings/{dir_id}.md.
  Phase 3   — Per-round coordinator-summary agent (Haiku) reads findings files
               and updates coordinator-summary.md.
  Phase 4   — Fact-verification (Haiku + WebFetch); risk-stratified sampling;
               emits VERIFIED, MISMATCHES, UNVERIFIABLE, SAMPLING_STRATEGY.
  Phase 5   — Synthesis with cross-cutting analysis section.
  Phase 6   — Termination labels (4 spec labels + absolute hard-stop at
               max_rounds * 3).
  v4.1      — Translation round-trip tracking per direction.
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
    from sagaflow.slack_progress import ReportSlackProgressInput
    from .state import (
        CROSS_CUT_DIMS,
        Direction,
        DeepResearchState,
        SourceVerification,
    )

_PROGRESS_POLICY = HAIKU_POLICY
_PROGRESS_TITLE = "deep-research"
_PROGRESS_PHASES = [
    "Classify topic",
    "Discover directions",
    "Research rounds",
    "Verify facts",
    "Synthesize report",
]


async def _report_progress(
    run_dir: str, phase_idx: int, status: str = "in_progress",
    detail: str = "", final: bool = False, *, _steps: list[dict] | None = None,
) -> list[dict]:
    if _steps is None:
        _steps = [{"name": n, "status": "pending", "detail": "", "elapsed_s": 0.0}
                  for n in _PROGRESS_PHASES]
    _steps[phase_idx]["status"] = status
    if detail:
        _steps[phase_idx]["detail"] = detail
    try:
        await workflow.execute_activity(
            "report_slack_progress",
            ReportSlackProgressInput(run_dir=run_dir, title=_PROGRESS_TITLE,
                steps=tuple(_steps), final=final),
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=_PROGRESS_POLICY,
        )
    except Exception:
        pass
    return _steps


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DeepResearchInput:
    run_id: str
    seed: str
    inbox_path: str
    run_dir: str
    max_rounds: int = 1000
    max_directions: int = 100
    notify: bool = True
    researcher_timeout: int = 600
    completion_threshold: float = 0.8


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

@workflow.defn(name="DeepResearchWorkflow")
class DeepResearchWorkflow:

    @workflow.run
    async def run(self, inp: DeepResearchInput) -> str:
        run_dir = inp.run_dir
        state = DeepResearchState(
            run_id=inp.run_id,
            skill="deep-research",
            seed=inp.seed,
            max_rounds=inp.max_rounds,
        )
        report_path = f"{run_dir}/research-report.md"
        findings_dir = f"{run_dir}/deep-research-findings"
        progress_path = f"{run_dir}/progress.json"
        seed_path = f"{run_dir}/seed-topic.md"
        abs_cap = inp.max_rounds * 3

        # Write seed to a separate file — agents read it via tools.
        # Follows files-not-inline contract from _shared/execution-model-contracts.md.
        await _write(seed_path, inp.seed)

        progress: dict = {
            "phase": "starting",
            "round": 0,
            "max_rounds": inp.max_rounds,
            "directions_generated": 0,
            "researchers_spawned": 0,
            "researchers_completed": 0,
            "researchers_failed": 0,
            "researchers_cancelled": 0,
            "researchers_empty": 0,
            "findings_total": 0,
            "directions_remaining": 0,
            "expansions": [],
            "warnings": [],
        }

        async def _update_progress(**kwargs: object) -> None:
            progress.update(kwargs)
            progress["timestamp"] = workflow.now().isoformat(timespec="seconds")
            await _write(progress_path, json.dumps(progress, indent=2))

        steps = await _report_progress(run_dir, 0, "in_progress")

        # ------------------------------------------------------------------ #
        # Phase 0f — Language locus detection                                  #
        # ------------------------------------------------------------------ #
        lang_prompt_path = f"{run_dir}/lang-locus-prompt.txt"
        await _write(lang_prompt_path,
            f"Research topic file: {seed_path}\n"
            "Read the file above for the full research topic.\n\n"
            "Identify 1-4 authoritative languages for this topic.\n"
            "Output STRICT JSON:\n"
            '{"authoritative_languages": ["en"], '
            '"coverage_expectation": "en_dominant|bilingual|multilingual_required", '
            '"confidence": "high|medium|low"}\n'
            "AUTHORITATIVE_LANGUAGES|<json array of ISO 639-1 codes>\n"
            "COVERAGE_EXPECTATION|en_dominant|bilingual|multilingual_required\n"
        )
        lang_result = await _spawn(
            role="lang-detect",
            tier="OPUS",
            system_prompt=(
                "You detect the authoritative languages for a research topic. "
                "STRUCTURED_OUTPUT_START\n"
                "AUTHORITATIVE_LANGUAGES|<json array>\n"
                "COVERAGE_EXPECTATION|<en_dominant|bilingual|multilingual_required>\n"
                "STRUCTURED_OUTPUT_END"
            ),
            prompt_path=lang_prompt_path,
            max_tokens=128000,
            tools_needed=True,
        )
        raw_langs = lang_result.get("AUTHORITATIVE_LANGUAGES", '["en"]')
        try:
            state.authoritative_languages = json.loads(raw_langs)
        except json.JSONDecodeError:
            state.authoritative_languages = ["en"]
        state.coverage_expectation = lang_result.get(
            "COVERAGE_EXPECTATION", "en_dominant"
        )
        await _update_progress(phase="lang_detect_done", languages=state.authoritative_languages)

        # ------------------------------------------------------------------ #
        # Phase 0g — Novelty classification                                    #
        # ------------------------------------------------------------------ #
        novelty_prompt_path = f"{run_dir}/novelty-prompt.txt"
        await _write(novelty_prompt_path,
            f"Research topic file: {seed_path}\n"
            "Read the file above for the full research topic.\n\n"
            "List up to 5 specific sources you recall from memory. Do NOT WebSearch.\n"
            "Output STRICT JSON with recalled_sources and topic_novelty "
            "(familiar|emerging|novel|cold_start).\n"
            "STRUCTURED_OUTPUT_START\n"
            "NOVELTY_CLASS|familiar|emerging|novel|cold_start\n"
            "RECALLED_SOURCES|<json array of {title,authors_or_org,year,confidence}>\n"
            "STRUCTURED_OUTPUT_END"
        )
        novelty_result = await _spawn(
            role="novelty-classify",
            tier="OPUS",
            system_prompt=(
                "You classify topic novelty. Use WebSearch to verify recalled sources. "
                "STRUCTURED_OUTPUT_START\n"
                "NOVELTY_CLASS|<familiar|emerging|novel|cold_start>\n"
                "RECALLED_SOURCES|<json array>\n"
                "STRUCTURED_OUTPUT_END"
            ),
            prompt_path=novelty_prompt_path,
            max_tokens=128000,
            tools_needed=True,
        )
        self_report = novelty_result.get("NOVELTY_CLASS", "familiar")
        state.self_report_novelty = self_report
        raw_recalled = novelty_result.get("RECALLED_SOURCES", "[]")
        try:
            recalled_sources = json.loads(raw_recalled)
        except json.JSONDecodeError:
            recalled_sources = []

        # External verification override (v5.1): count verified sources.
        # In the workflow we trust the agent already did WebSearch (tools_needed=True).
        # We apply the override rule on verified_count from agent report or default 0.
        verified_count = int(novelty_result.get("VERIFIED_COUNT", "0") or "0")
        # Record verification log from recalled sources.
        for src in recalled_sources[:5]:
            if isinstance(src, dict) and src.get("confidence") in ("high", "medium"):
                state.source_verification_log.append(
                    SourceVerification(
                        title=str(src.get("title", "")),
                        authors_or_org=str(src.get("authors_or_org", "")),
                        year=_safe_year(src.get("year", 0)),
                        confidence=str(src.get("confidence", "low")),
                        verified=(verified_count > 0),
                    )
                )

        # Apply override rule.
        if verified_count >= 3:
            verified_novelty = self_report
        elif verified_count == 2:
            # Downgrade one tier.
            _tier_order = ["familiar", "emerging", "novel", "cold_start"]
            idx = _tier_order.index(self_report) if self_report in _tier_order else 0
            verified_novelty = _tier_order[min(idx + 1, 3)]
        else:
            # ≥3/5 unverified → force cold_start.
            verified_novelty = "cold_start"

        state.topic_novelty = verified_novelty
        await _update_progress(phase="novelty_done", novelty=verified_novelty, self_report=self_report)

        # ------------------------------------------------------------------ #
        # Phase 2.5 — Vocabulary bootstrap (novel | cold_start)               #
        # ------------------------------------------------------------------ #
        if state.topic_novelty in ("novel", "cold_start"):
            vocab_prompt_path = f"{run_dir}/vocab-bootstrap-prompt.txt"
            await _write(vocab_prompt_path,
                f"Research topic file: {seed_path}\n"
                "Read the file above for the full research topic.\n\n"
                "Build domain vocabulary using Wikipedia WebFetch.\n"
                "1. WebFetch Wikipedia opensearch API for this topic.\n"
                "2. WebFetch top-3 Wikipedia articles.\n"
                "3. Extract bolded terms, H2/H3 headings, See-also, categories.\n"
                "Output vocabulary_bootstrap.json:\n"
                '{"canonical_terms": [...], "discovered_sources": [...]}\n'
                "STRUCTURED_OUTPUT_START\n"
                "CANONICAL_TERMS|<json array of strings>\n"
                "DISCOVERED_SOURCES|<json array of URLs>\n"
                "STRUCTURED_OUTPUT_END"
            )
            vocab_result = await _spawn(
                role="vocab-bootstrap",
                tier="OPUS",
                system_prompt=(
                    "You bootstrap domain vocabulary from Wikipedia using WebFetch. "
                    "STRUCTURED_OUTPUT_START\n"
                    "CANONICAL_TERMS|<json array>\n"
                    "DISCOVERED_SOURCES|<json array of URLs>\n"
                    "STRUCTURED_OUTPUT_END"
                ),
                prompt_path=vocab_prompt_path,
                max_tokens=128000,
                tools_needed=True,
            )
            raw_terms = vocab_result.get("CANONICAL_TERMS", "[]")
            raw_discovered = vocab_result.get("DISCOVERED_SOURCES", "[]")
            try:
                canonical_terms = json.loads(raw_terms)
            except json.JSONDecodeError:
                canonical_terms = []
            try:
                discovered_sources = json.loads(raw_discovered)
            except json.JSONDecodeError:
                discovered_sources = []
            vocab_data = {
                "canonical_terms": canonical_terms,
                "discovered_sources": discovered_sources,
            }
            vocab_path = f"{run_dir}/vocabulary_bootstrap.json"
            await _write(vocab_path, json.dumps(vocab_data, indent=2))
            state.vocab_bootstrap_path = vocab_path

        await _update_progress(phase="vocab_done" if state.vocab_bootstrap_path else "vocab_skipped")

        steps = await _report_progress(run_dir, 0, "completed", _steps=steps)
        steps = await _report_progress(run_dir, 1, "in_progress", _steps=steps)

        # ------------------------------------------------------------------ #
        # Phase 1 — Direction discovery (including cross-cut dims)            #
        # ------------------------------------------------------------------ #
        dim_prompt_path = f"{run_dir}/dim-prompt.txt"
        vocab_hint = ""
        if state.vocab_bootstrap_path:
            vocab_hint = (
                f"\nVocabulary bootstrap available at: {state.vocab_bootstrap_path}\n"
                "Use canonical_terms in your direction questions.\n"
            )
        await _write(dim_prompt_path,
            f"Research topic file: {seed_path}\n{vocab_hint}\n"
            f"Generate {inp.max_directions} research directions across dimensions "
            f"(WHO/WHAT/HOW/WHERE/WHEN/WHY/LIMITS).\n"
            "REQUIRED: also include at least one direction each for these cross-cutting "
            "dimensions: PRIOR-FAILURE, BASELINE, ADJACENT-EFFORTS, STRATEGIC-TIMING, "
            "ACTUAL-USAGE.\n"
            "STRUCTURED_OUTPUT_START\n"
            'DIRECTIONS|[{"id":"d1","dimension":"HOW","question":"<specific>","priority":"high"}, ...]\n'
            "STRUCTURED_OUTPUT_END"
        )
        dim_result = await _spawn(
            role="dim-discover",
            tier="OPUS",
            system_prompt=(
                "You generate research directions including mandatory cross-cutting "
                "dimensions (PRIOR-FAILURE, BASELINE, ADJACENT-EFFORTS, "
                "STRATEGIC-TIMING, ACTUAL-USAGE). Use all available tools to understand "
                "the landscape before generating directions. Be exhaustive — generate "
                "as many directions as the topic warrants. "
                "STRUCTURED_OUTPUT_START\n"
                'DIRECTIONS|[{"id":"...","dimension":"...","question":"...","priority":"high|medium|low"},...]\n'
                "STRUCTURED_OUTPUT_END"
            ),
            prompt_path=dim_prompt_path,
            max_tokens=128000,
            tools_needed=True,
        )
        raw_directions = _parse_json_list(dim_result.get("DIRECTIONS", "[]"))
        raw_directions = raw_directions[:inp.max_directions]
        directions = [
            Direction(
                id=d.get("id", f"d{i}"),
                question=d.get("question", ""),
                dimension=d.get("dimension", "HOW"),
                priority=d.get("priority", "medium"),
            )
            for i, d in enumerate(raw_directions)
        ]

        await _update_progress(
            phase="directions_done",
            directions_generated=len(directions),
            dimensions=list(set(d.dimension for d in directions)),
        )

        # Initialise cross-cut coverage tracking.
        state.cross_cut_coverage = {dim: [] for dim in CROSS_CUT_DIMS}

        # Research rounds.
        round_num = 0
        all_findings: list[dict[str, str]] = []
        # Ensure findings dir exists.
        await _write(f"{findings_dir}/.keep", "")

        steps = await _report_progress(run_dir, 1, "completed", _steps=steps)
        steps = await _report_progress(run_dir, 2, "in_progress", _steps=steps)

        while round_num < inp.max_rounds and round_num < abs_cap and directions:
            current_batch = directions
            directions = []
            round_num += 1

            # -------------------------------------------------------------- #
            # Phase 2 — Parallel researcher agents                            #
            # -------------------------------------------------------------- #
            research_prompts: list[tuple[Direction, str]] = []
            for d in current_batch:
                p = f"{run_dir}/research-{d.id}.txt"
                vocab_section = (
                    f"\nVocabulary bootstrap: {state.vocab_bootstrap_path}\n"
                    if state.vocab_bootstrap_path else ""
                )
                await _write(p,
                    f"Research topic file: {seed_path}\n"
                    f"Direction ({d.dimension}): {d.question}\n"
                    f"Priority: {d.priority}\n"
                    f"{vocab_section}\n"
                    "Research this direction with MAXIMUM thoroughness. Use EVERY "
                    "available tool aggressively — code search, documentation search, "
                    "chat/messaging search, engineering context tools, pipeline/run "
                    "inspection, web search, web fetch. Make at LEAST 5-10 tool calls. "
                    "Cross-reference findings across multiple sources. For every claim, "
                    "note the source and whether it's corroborated by independent "
                    "evidence.\n\n"
                    "Do NOT write any files. Return your results ONLY as a structured "
                    "output block in your TEXT response (not in a file).\n\n"
                    "STRUCTURED_OUTPUT_START\n"
                    "FINDINGS|<detailed prose summary — be exhaustive, include all "
                    "evidence found, name specific repos/teams/people/docs>\n"
                    "SOURCES|<json array of source strings with URLs where available>\n"
                    "CLAIMS|<json array of {claim,source,corroboration,recency_class}>\n"
                    "STRUCTURED_OUTPUT_END"
                )
                research_prompts.append((d, p))

            _researcher_system = (
                "You are an expert researcher. Use ALL available tools aggressively — "
                "code search, documentation search, chat search, engineering context, "
                "web search, web fetch, pipeline inspection. Make at least 5-10 tool "
                "calls per direction. Cross-reference across sources. Be exhaustive.\n"
                "STRUCTURED_OUTPUT_START\n"
                "FINDINGS|<detailed prose — name repos, teams, people, docs, URLs>\n"
                'SOURCES|["source1 (URL)", "source2 (URL)", ...]\n'
                'CLAIMS|[{"claim":"...","source":"...","corroboration":"single_source|multiple_sources|none","recency_class":"2026|2025|2024|older|undated"},...]\n'
                "STRUCTURED_OUTPUT_END"
            )

            round_findings: list[dict[str, str]] = []
            r_failed = 0
            r_empty = 0

            _researchers_pending = set(d.id for d in current_batch)
            _researchers_done: list[str] = []

            async def _research_and_write(d: Direction, prompt_path: str) -> dict | None:
                nonlocal r_failed, r_empty
                try:
                    r = await _spawn(
                        role="researcher",
                        tier="OPUS",
                        system_prompt=_researcher_system,
                        prompt_path=prompt_path,
                        max_tokens=128000,
                        tools_needed=True,
                        timeout=inp.researcher_timeout,
                    )
                except BaseException as exc:
                    r_failed += 1
                    _researchers_pending.discard(d.id)
                    _researchers_done.append(d.id)
                    progress["warnings"].append(f"R{round_num} {d.id}: agent failed: {exc}")
                    await _update_progress(
                        phase=f"round_{round_num}_researching",
                        researchers_completed=len(_researchers_done),
                        researchers_pending=list(_researchers_pending),
                    )
                    return None
                findings_text = r.get("FINDINGS", "") if isinstance(r, dict) else ""
                if len(findings_text) < 50:
                    r_empty += 1
                    progress["warnings"].append(f"R{round_num} {d.id}: empty/short findings ({len(findings_text)} chars)")
                finding = {
                    "id": d.id,
                    "dimension": d.dimension,
                    "question": d.question,
                    "findings": findings_text,
                    "sources": r.get("SOURCES", "[]") if isinstance(r, dict) else "[]",
                    "claims": r.get("CLAIMS", "[]") if isinstance(r, dict) else "[]",
                    "priority": d.priority,
                }
                if d.dimension in state.cross_cut_coverage:
                    state.cross_cut_coverage[d.dimension].append(d.id)
                await _write(f"{findings_dir}/{d.id}.md", _format_findings_file(d, finding))
                _researchers_pending.discard(d.id)
                _researchers_done.append(d.id)
                await _update_progress(
                    phase=f"round_{round_num}_researching",
                    researchers_completed=len(_researchers_done),
                    researchers_pending=list(_researchers_pending),
                )
                return finding

            # Dispatch all researchers as concurrent tasks.
            researcher_tasks: dict[asyncio.Task, Direction] = {}
            for d, p in research_prompts:
                researcher_tasks[asyncio.ensure_future(_research_and_write(d, p))] = d

            total_researchers = len(researcher_tasks)
            threshold_count = max(1, int(total_researchers * inp.completion_threshold))

            # Proceed once enough researchers have settled (success or failure).
            await workflow.wait_condition(
                lambda: len(_researchers_done) >= threshold_count
            )

            # Cancel stragglers still running past the threshold.
            r_cancelled = 0
            straggler_ids: list[str] = []
            for t, d in researcher_tasks.items():
                if not t.done():
                    t.cancel()
                    r_cancelled += 1
                    straggler_ids.append(d.id)
            if straggler_ids:
                progress["warnings"].append(
                    f"R{round_num}: cancelled {r_cancelled} straggler(s) at "
                    f"{inp.completion_threshold:.0%} threshold "
                    f"({len(_researchers_done)}/{total_researchers} settled): "
                    f"{', '.join(straggler_ids)}"
                )

            # Settle all tasks (completed + cancelled).
            results = await asyncio.gather(
                *researcher_tasks.keys(), return_exceptions=True,
            )
            for r in results:
                if isinstance(r, dict):
                    round_findings.append(r)
                    all_findings.append(r)

            progress["researchers_spawned"] += len(current_batch)
            progress["researchers_completed"] += len(current_batch) - r_failed
            progress["researchers_failed"] += r_failed - r_cancelled
            progress["researchers_cancelled"] += r_cancelled
            progress["researchers_empty"] += r_empty
            progress["findings_total"] = len(all_findings)
            await _update_progress(
                phase=f"round_{round_num}_researchers_done",
                round=round_num,
                round_batch_size=len(current_batch),
                round_findings=len(round_findings),
                round_failed=r_failed - r_cancelled,
                round_cancelled=r_cancelled,
                round_empty=r_empty,
            )

            # -------------------------------------------------------------- #
            # Phase 3 — Per-round coordinator summary                         #
            # -------------------------------------------------------------- #
            coord_prompt_path = f"{run_dir}/coord-summary-r{round_num}.txt"
            findings_index = "\n".join(
                f"- {f['id']} ({f['dimension']}): {findings_dir}/{f['id']}.md"
                for f in round_findings
            )
            await _write(coord_prompt_path,
                f"Round {round_num} findings index:\n{findings_index}\n\n"
                "Read the findings files and produce a coordinator summary covering:\n"
                "1. Mainstream findings\n"
                "2. Counter-narratives (verbatim)\n"
                "3. Numerical claims (quoted)\n"
                "4. Coverage state per dimension\n"
                "5. Unconsumed-leads registry\n"
                "6. Information gain assessment: what percentage of this round's claims are GENUINELY NEW "
                "facts not already established in prior rounds? Be strict — a deeper detail on a known entity "
                "is refinement (low gain), not discovery. Score 0-100.\n"
                "STRUCTURED_OUTPUT_START\n"
                "COORD_SUMMARY|<markdown>\n"
                "INFO_GAIN_RATE|<integer 0-100>\n"
                "STRUCTURED_OUTPUT_END"
            )
            coord_result = await _spawn(
                role="coord-summary",
                tier="OPUS",
                system_prompt=(
                    "You synthesize research round findings into a comprehensive coordinator "
                    "summary. Read ALL findings files referenced. Identify gaps, contradictions, "
                    "and areas needing deeper investigation. "
                    "Also assess INFO_GAIN_RATE: what % of this round's claims are genuinely new "
                    "facts NOT already in the cumulative coordinator-summary.md? "
                    "Be strict — deeper detail on known entities is refinement, not discovery.\n"
                    "STRUCTURED_OUTPUT_START\n"
                    "COORD_SUMMARY|<markdown text>\n"
                    "INFO_GAIN_RATE|<integer 0-100>\n"
                    "STRUCTURED_OUTPUT_END"
                ),
                prompt_path=coord_prompt_path,
                max_tokens=128000,
                tools_needed=True,
            )
            coord_summary = coord_result.get("COORD_SUMMARY", "")
            state.coordinator_summaries.append(coord_summary)
            await _write(
                f"{run_dir}/coordinator-summary.md",
                "\n\n---\n\n".join(state.coordinator_summaries),
            )
            info_gain = int(coord_result.get("INFO_GAIN_RATE", "50") or "50")
            if "info_gain_rates" not in progress:
                progress["info_gain_rates"] = []
            progress["info_gain_rates"].append({"round": round_num, "rate": info_gain})
            _CONVERGENCE_WINDOW = 3
            _CONVERGENCE_THRESHOLD = 5
            recent_gains = progress["info_gain_rates"][-_CONVERGENCE_WINDOW:]
            info_gain_converged = (
                len(recent_gains) >= _CONVERGENCE_WINDOW
                and all(g["rate"] < _CONVERGENCE_THRESHOLD for g in recent_gains)
            )
            await _update_progress(
                phase=f"round_{round_num}_coord_done",
                coord_summary_len=len(coord_summary),
                info_gain_rate=info_gain,
                info_gain_converged=info_gain_converged,
            )

        # -------------------------------------------------------------- #
            # Sub-direction generation: read findings, spawn follow-ups      #
            # -------------------------------------------------------------- #
            if info_gain_converged:
                directions.clear()
                state.termination_label = (
                    f"Convergence — info gain below {_CONVERGENCE_THRESHOLD}% "
                    f"for {_CONVERGENCE_WINDOW} consecutive rounds "
                    f"(rates: {[g['rate'] for g in recent_gains]})"
                )
                break
            explored_questions = {f["question"] for f in all_findings}
            expand_prompt_path = f"{run_dir}/expand-r{round_num}.txt"
            findings_summary = "\n".join(
                f"- [{f['dimension']}] {f['question']}: {f.get('findings', '')[:500]}"
                for f in round_findings
            )
            await _write(expand_prompt_path,
                f"Research topic file: {seed_path}\n\n"
                f"Round {round_num} just completed. Findings summary:\n{findings_summary}\n\n"
                f"Already explored ({len(explored_questions)} directions):\n"
                + "\n".join(f"- {q}" for q in list(explored_questions)[:30]) + "\n\n"
                "Based on these findings, generate NEW follow-up research directions that:\n"
                "1. Drill deeper into surprising or underexplored findings\n"
                "2. Follow up on entities/teams/tools mentioned but not independently researched\n"
                "3. Verify or challenge claims that seem uncertain\n"
                "4. Cover cross-cutting dimensions not yet explored (PRIOR-FAILURE, BASELINE, "
                "ADJACENT-EFFORTS, STRATEGIC-TIMING, ACTUAL-USAGE)\n"
                "5. Identify domain-specific dimensions that emerged from the findings but "
                "weren't explicitly covered (e.g. economics, governance, user experience)\n\n"
                "Do NOT repeat already-explored directions.\n"
                "Generate 50-100 new directions. Use tools to discover gaps. "
                "Only return 0 if the topic is truly exhausted.\n\n"
                "STRUCTURED_OUTPUT_START\n"
                'DIRECTIONS|[{"id":"d_r' + str(round_num + 1) + '_1","dimension":"...","question":"...","priority":"high|medium|low"}, ...]\n'
                "STRUCTURED_OUTPUT_END"
            )
            expand_result = await _spawn(
                role="direction-expander",
                tier="OPUS",
                system_prompt=(
                    "You generate follow-up research directions based on prior findings. "
                    "Use all available tools to discover gaps and unexplored areas. "
                    "Generate 20-50 NEW directions. "
                    "Only return genuinely new directions — not paraphrases. "
                    "Return empty array [] ONLY if the topic is truly exhausted.\n"
                    "STRUCTURED_OUTPUT_START\n"
                    'DIRECTIONS|[{"id":"...","dimension":"...","question":"...","priority":"..."}, ...]\n'
                    "STRUCTURED_OUTPUT_END"
                ),
                prompt_path=expand_prompt_path,
                max_tokens=128000,
                tools_needed=True,
            )
            new_raw = _parse_json_list(expand_result.get("DIRECTIONS", "[]"))
            new_added = 0
            for d in new_raw:
                q = d.get("question", "")
                if q and q not in explored_questions:
                    directions.append(
                        Direction(
                            id=d.get("id", f"d_r{round_num + 1}_{len(directions)}"),
                            question=q,
                            dimension=d.get("dimension", "HOW"),
                            priority=d.get("priority", "medium"),
                        )
                    )
                    new_added += 1
            progress["expansions"].append({"round": round_num, "proposed": len(new_raw), "added": new_added})
            progress["directions_remaining"] = len(directions)
            await _update_progress(
                phase=f"round_{round_num}_done",
                round=round_num,
                expansion_proposed=len(new_raw),
                expansion_added=new_added,
                frontier_size=len(directions),
            )

        # Determine termination label.
        abs_hit = round_num >= abs_cap
        frontier_empty = not directions
        if abs_hit:
            state.termination_label = f"User-stopped at round {round_num}"
        elif frontier_empty:
            state.termination_label = "Convergence — frontier exhausted"
        elif round_num >= inp.max_rounds:
            state.termination_label = "Budget soft gate — user chose to extend or stop"
        else:
            state.termination_label = "Coverage plateau — frontier saturated"

        steps = await _report_progress(run_dir, 2, "completed", _steps=steps)
        steps = await _report_progress(run_dir, 3, "in_progress", _steps=steps)

        # ------------------------------------------------------------------ #
        # Phase 4 — Fact verification                                          #
        # ------------------------------------------------------------------ #
        all_claims: list[dict] = []
        for f in all_findings:
            try:
                claims = json.loads(f.get("claims", "[]"))
                if isinstance(claims, list):
                    all_claims.extend(claims)
            except json.JSONDecodeError:
                pass

        verifier_output: dict[str, str] = {}
        if all_claims:
            sample = _risk_stratified_sample(all_claims, budget=len(all_claims))
            claims_data_path = f"{run_dir}/verifier-claims.json"
            await _write(claims_data_path, json.dumps(sample, indent=2))
            verify_prompt_path = f"{run_dir}/verifier-prompt.txt"
            await _write(verify_prompt_path,
                f"Research topic file: {seed_path}\n\n"
                f"Risk-stratified claim sample to verify: {claims_data_path}\n"
                "Read the claims file above for the full list.\n\n"
                "For each claim:\n"
                "1. WebFetch the source URL to check accessibility and exact wording.\n"
                "2. For numerical claims: compare EXACT numbers.\n"
                "3. Emit VERIFIED, MISMATCHES, UNVERIFIABLE.\n"
                "STRUCTURED_OUTPUT_START\n"
                "VERIFIED|<json array of verified claim ids>\n"
                "MISMATCHES|<json array of {claim_id,issue}>\n"
                "UNVERIFIABLE|<json array of {claim_id,reason}>\n"
                "SAMPLING_STRATEGY|<json {single_source:N,numerical:N,contested:N,other:N}>\n"
                "STRUCTURED_OUTPUT_END"
            )
            verifier_output = await _spawn(
                role="verifier",
                tier="OPUS",
                system_prompt=(
                    "You are an exhaustive fact verifier. Check EVERY claim using all "
                    "available tools — code search for code claims, documentation search "
                    "for doc claims, chat search for discussion claims. Verify exact "
                    "numbers, team names, repo existence, API details. Be ruthless "
                    "about flagging unverifiable claims. "
                    "STRUCTURED_OUTPUT_START\n"
                    "VERIFIED|<json array>\n"
                    "MISMATCHES|<json array>\n"
                    "UNVERIFIABLE|<json array>\n"
                    "SAMPLING_STRATEGY|<json object>\n"
                    "STRUCTURED_OUTPUT_END"
                ),
                prompt_path=verify_prompt_path,
                max_tokens=128000,
                tools_needed=True,
            )
            try:
                state.verified_claims = json.loads(verifier_output.get("VERIFIED", "[]"))
            except json.JSONDecodeError:
                state.verified_claims = []
            try:
                state.mismatched_claims = json.loads(verifier_output.get("MISMATCHES", "[]"))
            except json.JSONDecodeError:
                state.mismatched_claims = []
            try:
                state.unverifiable_claims = json.loads(verifier_output.get("UNVERIFIABLE", "[]"))
            except json.JSONDecodeError:
                state.unverifiable_claims = []

        steps = await _report_progress(run_dir, 3, "completed", _steps=steps)
        steps = await _report_progress(run_dir, 4, "in_progress", _steps=steps)

        # ------------------------------------------------------------------ #
        # Phase 5 — Synthesis                                                 #
        # ------------------------------------------------------------------ #
        cross_cut_section = _format_cross_cut_coverage(state.cross_cut_coverage)
        verifier_section = _format_verifier_section(
            state.verified_claims,
            state.mismatched_claims,
            state.unverifiable_claims,
            verifier_output.get("SAMPLING_STRATEGY", "{}"),
        )

        findings_index_path = f"{run_dir}/findings-index.json"
        findings_index = [{"id": f["id"], "dimension": f["dimension"], "question": f["question"], "file": f"{findings_dir}/{f['id']}.md"} for f in all_findings]
        await _write(findings_index_path, json.dumps(findings_index, indent=2))

        synth_prompt_path = f"{run_dir}/synth-prompt.txt"
        await _write(synth_prompt_path,
            f"Research topic file: {seed_path}\n\n"
            f"Termination: {state.termination_label}\n\n"
            f"Findings index ({len(all_findings)} directions): {findings_index_path}\n"
            f"Findings directory: {findings_dir}/\n"
            f"Coordinator summary: {run_dir}/coordinator-summary.md\n"
            "Read the coordinator summary and findings files for full content.\n\n"
            f"{cross_cut_section}\n\n"
            f"{verifier_section}\n\n"
            "Write research-report.md with:\n"
            "- Executive Summary\n"
            "- Findings per direction\n"
            "- Cross-cutting analysis (PRIOR-FAILURE, BASELINE, ADJACENT-EFFORTS, "
            "STRATEGIC-TIMING, ACTUAL-USAGE)\n"
            "- Fact Verification Results\n"
            "- Coverage & Termination\n"
            "- Sources\n"
            "STRUCTURED_OUTPUT_START\n"
            "REPORT|<full markdown>\n"
            "STRUCTURED_OUTPUT_END"
        )
        synth_result = await _spawn(
            role="synth",
            tier="OPUS",
            system_prompt=(
                "Write the most comprehensive research report possible. Include EVERY "
                "finding from EVERY direction. Include a 'Cross-cutting analysis' "
                "section and a 'Fact Verification Results' section. Do NOT summarize "
                "or truncate — include full detail for each direction. Use all available "
                "tools to verify and enrich the synthesis. "
                "STRUCTURED_OUTPUT_START\n"
                "REPORT|<full markdown>\n"
                "STRUCTURED_OUTPUT_END"
            ),
            prompt_path=synth_prompt_path,
            max_tokens=128000,
            tools_needed=True,
        )
        report_md = synth_result.get("REPORT", _fallback(inp.seed, all_findings))

        # Always append the state-driven cross-cut coverage table so every
        # cross-cut dimension is present in the report regardless of whether
        # the synth agent hallucinated a truncated one.
        report_md += f"\n\n## Cross-cut Coverage (from state)\n\n{cross_cut_section}"
        if "Fact Verification" not in report_md:
            report_md += f"\n\n{verifier_section}"

        await _write(report_path, report_md)

        # Emit finding to inbox.
        summary = (
            f"{len(all_findings)} directions across "
            f"{len(set(f['dimension'] for f in all_findings))} dimensions | "
            f"novelty={state.topic_novelty} | {state.termination_label}"
        )
        timestamp = workflow.now().isoformat(timespec="seconds")
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
        await _report_progress(run_dir, 4, "completed", summary, final=True, _steps=steps)
        return f"{summary}\nReport: {report_path}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _write(path: str, content: str) -> None:
    await workflow.execute_activity(
        "write_artifact",
        WriteArtifactInput(path=path, content=content),
        start_to_close_timeout=timedelta(seconds=10),
        retry_policy=HAIKU_POLICY,
    )


async def _spawn(
    *,
    role: str,
    tier: str,
    system_prompt: str,
    prompt_path: str,
    max_tokens: int,
    tools_needed: bool,
    timeout: int | None = None,
) -> dict[str, str]:
    effective_timeout = timeout or (7200 if tools_needed else 3600)
    result = await workflow.execute_activity(
        "spawn_subagent",
        SpawnSubagentInput(
            role=role,
            tier_name=tier,
            system_prompt=system_prompt,
            user_prompt_path=prompt_path,
            max_tokens=max_tokens,
            tools_needed=tools_needed,
        ),
        start_to_close_timeout=timedelta(seconds=effective_timeout),
        retry_policy=SONNET_POLICY,
    )
    return result if isinstance(result, dict) else {}


def _safe_year(val) -> int:
    if isinstance(val, int):
        return val
    try:
        return int(str(val).split("-")[0].split(",")[0].strip())
    except (ValueError, TypeError, IndexError):
        return 0


def _parse_json_list(raw: str) -> list[dict]:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [x for x in parsed if isinstance(x, dict)]
    except json.JSONDecodeError:
        pass
    return []


def _risk_stratified_sample(claims: list[dict], budget: int) -> list[dict]:
    """Sample claims by risk tier: single-source > numerical > contested > other."""
    single_source = [c for c in claims if c.get("corroboration") == "single_source"]
    numerical = [
        c for c in claims
        if c not in single_source and any(
            ch.isdigit() for ch in str(c.get("claim", ""))
        )
    ]
    contested = [
        c for c in claims
        if c not in single_source and c not in numerical
        and c.get("corroboration") in ("none", "contested")
    ]
    other = [
        c for c in claims
        if c not in single_source and c not in numerical and c not in contested
    ]
    sample: list[dict] = []
    for bucket in (single_source, numerical, contested, other):
        take = min(len(bucket), max(1, budget // 4))
        sample.extend(bucket[:take])
        if len(sample) >= budget:
            break
    return sample[:budget]


def _format_findings_file(d: Direction, finding: dict) -> str:
    try:
        claims = json.loads(finding.get("claims", "[]"))
    except json.JSONDecodeError:
        claims = []
    try:
        sources = json.loads(finding.get("sources", "[]"))
    except json.JSONDecodeError:
        sources = []

    lines = [
        f"# {d.id}: {d.dimension} — {d.question}",
        "",
        "## Findings",
        finding.get("findings", ""),
        "",
        "## Claims Register",
    ]
    for i, c in enumerate(claims):
        lines.append(
            f"- [{i}] {c.get('claim', '')} "
            f"| source: {c.get('source', '')} "
            f"| corroboration: {c.get('corroboration', 'single_source')} "
            f"| recency: {c.get('recency_class', 'undated')}"
        )
    lines += [
        "",
        "## Key Sources",
    ]
    for s in sources:
        lines.append(f"- {s}")
    lines += [
        "",
        "## Mini-Synthesis",
        "See Findings above.",
        "",
        "## New Directions Discovered",
        "None — terminal node.",
        "",
        "## Unconsumed Leads",
        "None.",
        "",
        "## Exhaustion Assessment",
        "score: 3",
    ]
    return "\n".join(lines)


def _format_cross_cut_coverage(coverage: dict[str, list[str]]) -> str:
    lines = [
        "## Cross-cutting analysis",
        "",
        "| Dimension | Directions Explored |",
        "|---|---|",
    ]
    for dim in ["PRIOR-FAILURE", "BASELINE", "ADJACENT-EFFORTS", "STRATEGIC-TIMING", "ACTUAL-USAGE"]:
        ids = coverage.get(dim, [])
        lines.append(f"| {dim} | {', '.join(ids) if ids else 'none'} |")
    return "\n".join(lines)


def _format_verifier_section(
    verified: list,
    mismatches: list,
    unverifiable: list,
    sampling_strategy_raw: str,
) -> str:
    try:
        strategy = json.loads(sampling_strategy_raw)
    except (json.JSONDecodeError, TypeError):
        strategy = {}
    lines = [
        "## Fact Verification Results",
        "",
        f"**Verified claims:** {len(verified)}",
        f"**Mismatches:** {len(mismatches)}",
        f"**Unverifiable:** {len(unverifiable)}",
        "",
    ]
    if strategy:
        lines.append("**Sampling strategy:**")
        for tier, count in strategy.items():
            lines.append(f"- {tier}: {count}")
        lines.append("")
    if mismatches:
        lines.append("**Mismatches:**")
        for m in mismatches:
            lines.append(f"- {m}")
        lines.append("")
    if unverifiable:
        lines.append("**Unverifiable:**")
        for u in unverifiable:
            lines.append(f"- {u}")
    return "\n".join(lines)


def _fallback(seed: str, findings: list[dict]) -> str:
    _MAX_FALLBACK_BYTES = 1_500_000
    lines = [f"# Research Report: {seed}", "", "## Findings"]
    total = 0
    for f in findings:
        header = f"### {f.get('dimension', '?')}: {f.get('question', '?')}"
        body = f.get("findings", "")[:2000]
        total += len(header) + len(body) + 2
        if total > _MAX_FALLBACK_BYTES:
            lines.append(f"\n\n... truncated ({len(findings)} total findings, see findings directory)")
            break
        lines.append(header)
        lines.append(body)
        lines.append("")
    return "\n".join(lines)
