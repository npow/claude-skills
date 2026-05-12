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
               max_rounds * 5).
  v4.1      — Translation round-trip tracking per direction.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from sagaflow.durable.activities import (
        EmitFindingInput,
        FinalizeManifestInput,
        SpawnSubagentInput,
        WriteArtifactInput,
    )
    from sagaflow.durable.retry_policies import HAIKU_POLICY, SONNET_POLICY
    from sagaflow.slack_progress import DeliverArtifactInput, ReportSlackProgressInput
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
    # Soft gate; override per-launch when a topic warrants more.
    max_rounds: int = 100
    min_rounds: int = 3
    # Directions per round (initial Phase-1 generation + expander cap).
    # 50 covers most topics without bloating fan-out cost.
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
        abs_cap = inp.max_rounds * 5

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
            tier="HAIKU",
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
            run_dir=run_dir,
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
            tier="HAIKU",
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
            run_dir=run_dir,
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
            _vocab_system = (
                "You bootstrap domain vocabulary from Wikipedia using WebFetch. "
                "After completing your research, your FINAL output MUST be ONLY "
                "the structured block below — no prose, no summary, no explanation.\n\n"
                "STRUCTURED_OUTPUT_START\n"
                "CANONICAL_TERMS|<json array of strings>\n"
                "DISCOVERED_SOURCES|<json array of URLs>\n"
                "STRUCTURED_OUTPUT_END"
            )
            await _write(vocab_prompt_path,
                f"Research topic file: {seed_path}\n"
                "Read the file above for the full research topic.\n\n"
                "Build domain vocabulary using Wikipedia WebFetch.\n"
                "1. WebFetch Wikipedia opensearch API for this topic.\n"
                "2. WebFetch top-3 Wikipedia articles.\n"
                "3. Extract bolded terms, H2/H3 headings, See-also, categories.\n\n"
                "Your FINAL output MUST be ONLY this structured block — "
                "no prose before or after:\n"
                "STRUCTURED_OUTPUT_START\n"
                "CANONICAL_TERMS|[\"term1\", \"term2\", ...]\n"
                "DISCOVERED_SOURCES|[\"https://en.wikipedia.org/...\", ...]\n"
                "STRUCTURED_OUTPUT_END"
            )
            vocab_result = await _spawn(
                role="vocab-bootstrap",
                tier="SONNET",
                system_prompt=_vocab_system,
                prompt_path=vocab_prompt_path,
                max_tokens=128000,
                tools_needed=True,
                run_dir=run_dir,
            )
            # Retry once with output_schema (forced JSON at API level) if the
            # subagent returned prose instead of structured output markers.
            if vocab_result.get("_sagaflow_malformed") == "1":
                retry_prompt_path = f"{run_dir}/vocab-bootstrap-retry-prompt.txt"
                raw_prose = vocab_result.get("_raw", "")
                await _write(retry_prompt_path,
                    "Extract canonical terms and source URLs from this research "
                    "output into the JSON schema.\n\n"
                    f"{raw_prose}"
                )
                _vocab_schema = {
                    "type": "object",
                    "properties": {
                        "canonical_terms": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "discovered_sources": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["canonical_terms", "discovered_sources"],
                }
                vocab_result = await _spawn(
                    role="vocab-bootstrap",
                    tier="SONNET",
                    system_prompt="Extract structured data from research output.",
                    prompt_path=retry_prompt_path,
                    max_tokens=32000,
                    tools_needed=False,
                    output_schema=_vocab_schema,
                    run_dir=run_dir,
                )
            raw_terms = vocab_result.get("CANONICAL_TERMS") or vocab_result.get("canonical_terms") or "[]"
            raw_discovered = vocab_result.get("DISCOVERED_SOURCES") or vocab_result.get("discovered_sources") or "[]"
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
            "BALANCE: distribute directions evenly across ALL dimensions. No single "
            f"dimension should have more than {max(inp.max_directions // 8, 5)} directions. "
            "If the topic is an organization or company, also include dimensions for: "
            "COST/EFFICIENCY, ADOPTION/USAGE-METRICS, RISK/GOVERNANCE, INFRASTRUCTURE, "
            "COMPETITIVE-LANDSCAPE.\n"
            "DIVERSITY: each direction must explore a DISTINCT sub-topic. Two directions "
            "that would lead a researcher to the same sources or findings should be merged.\n"
            "STRUCTURED_OUTPUT_START\n"
            'DIRECTIONS|[{"id":"d1","dimension":"HOW","question":"<specific>","priority":"high"}, ...]\n'
            "STRUCTURED_OUTPUT_END"
        )
        dim_result = await _spawn(
            role="dim-discover",
            tier="SONNET",
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
            run_dir=run_dir,
        )
        raw_directions = _parse_json_list(dim_result.get("DIRECTIONS", "[]"))

        if workflow.patched("direction-retry-v1"):
            if not raw_directions:
                workflow.logger.warning(
                    "dim-discover returned 0 parseable directions (raw=%s); retrying",
                    dim_result.get("DIRECTIONS", "")[:500],
                )
                dim_result_retry = await _spawn(
                    role="dim-discover-retry",
                    tier="SONNET",
                    system_prompt=(
                        "You generate research directions. Your previous attempt was not "
                        "parseable. Output ONLY valid JSON — no markdown fences, no prose "
                        "before or after the structured block.\n"
                        "STRUCTURED_OUTPUT_START\n"
                        'DIRECTIONS|[{"id":"d1","dimension":"HOW","question":"...","priority":"high"}, ...]\n'
                        "STRUCTURED_OUTPUT_END"
                    ),
                    prompt_path=dim_prompt_path,
                    max_tokens=128000,
                    tools_needed=True,
                    run_dir=run_dir,
                )
                raw_directions = _parse_json_list(
                    dim_result_retry.get("DIRECTIONS", "[]")
                )

            if not raw_directions:
                workflow.logger.error(
                    "dim-discover returned 0 directions after retry — failing run"
                )
                raise ApplicationError(
                    "dim-discover produced 0 parseable directions after 2 attempts"
                )

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

        if workflow.patched("balanced-dims-v1"):
            _PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
            dims: dict[str, list[Direction]] = {}
            for d in directions:
                dims.setdefault(d.dimension, []).append(d)
            num_dims = max(len(dims), 1)
            max_per_dim = max(inp.max_directions // num_dims + 2, 5)
            balanced: list[Direction] = []
            for _, dim_dirs in dims.items():
                dim_dirs.sort(key=lambda x: _PRIORITY_ORDER.get(x.priority, 1))
                balanced.extend(dim_dirs[:max_per_dim])
            directions = balanced

        await _update_progress(
            phase="directions_done",
            directions_generated=len(directions),
            dimensions=list(set(d.dimension for d in directions)),
        )

        # Initialise cross-cut coverage tracking.
        state.cross_cut_coverage = {dim: [] for dim in CROSS_CUT_DIMS}

        # MCP scoping — only load servers the researchers actually need.
        # Keyword→category mappings come from inp.mcp_categories_json
        # (JSON: {"category": ["kw1","kw2"]}). Unmatched seeds get "web-only".
        mcp_config_path: str | None = None
        if workflow.patched("scoped-mcp-v1"):
            _category_keywords: dict[str, set[str]] = {
                cat: set(kws) for cat, kws in json.loads(inp.mcp_categories_json).items()
            }
            seed_lower = inp.seed.lower()
            mcp_needs: list[str] = []
            for cat, kws in _category_keywords.items():
                if any(kw in seed_lower for kw in kws):
                    mcp_needs.append(cat)
            if not mcp_needs:
                mcp_needs.append("web-only")
            from sagaflow.transport.mcp_registry import resolve_and_generate
            mcp_config_path = resolve_and_generate(mcp_needs, run_dir=run_dir)
            await _update_progress(phase="mcp_scoped", mcp_categories=mcp_needs)

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
                    "Cross-reference findings across multiple sources.\n\n"
                    "EVIDENCE STANDARDS (mandatory):\n"
                    "- Every claim MUST have a source (URL, doc reference, or tool output)\n"
                    "- Name SPECIFIC repos, teams, people, PRs, incidents — never vague references\n"
                    "- When referencing people, verify they are still current when possible\n"
                    "- Include industry comparisons where relevant (peer companies, benchmarks)\n"
                    "- All links must be full clickable URLs, not shorthand\n\n"
                    "SOURCE COVERAGE (mandatory):\n"
                    "- Use ALL available search tools — not just web search and code search\n"
                    "- Search internal document repositories (shared drives, wikis, docs) "
                    "explicitly — strategy docs, architecture specs, and roadmaps often "
                    "live in document stores separate from code or chat\n"
                    "- Fetch full content of high-value documents, not just snippets\n"
                    "- Search chat/messaging archives for recent discussions and decisions\n\n"
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
                "EVIDENCE: Every claim needs a source (URL or citation). Name specific "
                "repos, teams, people, PRs, incidents. Verify people are still current "
                "when possible. Include industry comparisons. Full clickable URLs.\n"
                "SOURCES: Use ALL available search tools. Search internal document "
                "repositories (shared drives, wikis, docs) explicitly — strategy docs "
                "and architecture specs often live separate from code or chat. Fetch "
                "full content of high-value documents. Search chat archives too.\n"
                "CITATION VALIDITY (REQUIRED): For every code/repo URL you cite — "
                "`corp/<repo>` top-level OR `corp/<repo>/<subpath>` monorepo subpath OR "
                "a specific file/blob/tree URL — you MUST verify it resolves before "
                "including it. Top-level repos: call `mcp__sourcegraph-official__list_repos` "
                "with the last path segment as the query. Monorepo subpaths: call "
                "`mcp__sourcegraph-official__list_files` with `repo` and `path` set. If "
                "the call returns 'No files.' or zero matches → the path is invalid. "
                "DO NOT cite invalid paths. If you cited from a grep hit, the grep "
                "result is evidence of a pattern match, NOT evidence the directory "
                "exists — `list_files` is the directory-existence check. This is required "
                "because monorepo subpath conflation (citing `corp/algo/<dir>` from a "
                "filename match without verifying `<dir>` is a real directory) is a "
                "documented defect class.\n"
                "DATA-SOURCE COVERAGE LIMITS (REQUIRED): When you cite a number, count, "
                "or coverage claim drawn from a single table or service (e.g. 'N teams "
                "own M flows per Presto query on table X'), state explicitly what the "
                "data source DOES and DOES NOT include. Tables for scheduled workflows "
                "typically miss ad-hoc/Workbench/dev runs; cost tables typically miss "
                "compute that bypasses the standard scheduler. If you assert a coverage "
                "claim ('N teams use X'), verify whether the underlying table includes "
                "ad-hoc usage — if it does not, state the gap and search for an "
                "ad-hoc-inclusive alternative source before reporting the number as "
                "comprehensive.\n"
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
                        tier="SONNET",
                        system_prompt=_researcher_system,
                        prompt_path=prompt_path,
                        max_tokens=128000,
                        tools_needed=True,
                        mcp_config_path=mcp_config_path,
                        run_dir=run_dir,
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
                findings_path = f"{findings_dir}/{d.id}.md"
                await _write(findings_path, _format_findings_file(d, finding))
                # State-trim contract: after the findings file is on disk, drop
                # the raw text from workflow state. Keeping it inflates Temporal
                # payloads past the 2MB limit (TMPRL1103) once N×25KB findings
                # accumulate. Synthesis re-reads from disk via findings_path
                # (the synth prompt receives the file path, not the text).
                # Keep a short excerpt for the in-state fallback path.
                finding["findings_path"] = findings_path
                # Stored as str so the inner dict stays dict[str, str]; this
                # field is metadata for triage, not arithmetic.
                finding["findings_bytes"] = str(len(findings_text))
                finding["findings_excerpt"] = findings_text[:2000]
                finding["findings"] = ""
                _researchers_pending.discard(d.id)
                _researchers_done.append(d.id)
                # Bump findings_total incrementally so progress.json reflects
                # partial success when some researchers are still running. Prior
                # behavior set findings_total only after asyncio.gather, so a
                # single hung researcher froze the count at 0 indefinitely.
                progress["findings_total"] = (
                    progress.get("findings_total", 0) + 1
                )
                await _update_progress(
                    phase=f"round_{round_num}_researching",
                    researchers_completed=len(_researchers_done),
                    researchers_pending=list(_researchers_pending),
                    findings_total=progress["findings_total"],
                )
                return finding

            if workflow.patched("concurrency-limit-v1"):
                _sem = asyncio.Semaphore(inp.max_concurrent_researchers)
                async def _gated(d: Direction, p: str) -> dict | None:
                    async with _sem:
                        return await _research_and_write(d, p)
                results = await asyncio.gather(
                    *[_gated(d, p) for d, p in research_prompts],
                    return_exceptions=True,
                )
            else:
                results = await asyncio.gather(
                    *[_research_and_write(d, p) for d, p in research_prompts],
                    return_exceptions=True,
                )
            for r in results:
                if isinstance(r, dict):
                    round_findings.append(r)
                    all_findings.append(r)

            progress["researchers_spawned"] += len(current_batch)
            progress["researchers_completed"] += len(current_batch) - r_failed
            progress["researchers_failed"] += r_failed
            progress["researchers_empty"] += r_empty
            # Don't overwrite findings_total here — it's now bumped per
            # researcher inside _research_and_write. Reconcile to len(all_findings)
            # only as a defensive sync (max of the two).
            progress["findings_total"] = max(
                progress.get("findings_total", 0), len(all_findings)
            )
            await _update_progress(
                phase=f"round_{round_num}_researchers_done",
                round=round_num,
                round_batch_size=len(current_batch),
                round_findings=len(round_findings),
                round_failed=r_failed,
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
                tier="HAIKU",
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
                run_dir=run_dir,
            )
            coord_summary = coord_result.get("COORD_SUMMARY", "")
            state.coordinator_summary_count += 1
            separator = "" if state.coordinator_summary_count == 1 else "\n\n---\n\n"
            await _write(
                f"{run_dir}/coordinator-summary.md",
                separator + coord_summary,
                append=state.coordinator_summary_count > 1,
            )
            info_gain = int(coord_result.get("INFO_GAIN_RATE", "50") or "50")
            if "info_gain_rates" not in progress:
                progress["info_gain_rates"] = []
            progress["info_gain_rates"].append({"round": round_num, "rate": info_gain})
            if workflow.patched("relaxed-convergence-v1"):
                _CONVERGENCE_WINDOW = 2
                _CONVERGENCE_THRESHOLD = 10
            else:
                _CONVERGENCE_WINDOW = 3
                _CONVERGENCE_THRESHOLD = 5
            recent_gains = progress["info_gain_rates"][-_CONVERGENCE_WINDOW:]
            info_gain_converged = (
                round_num >= inp.min_rounds
                and len(recent_gains) >= _CONVERGENCE_WINDOW
                and all(g["rate"] < _CONVERGENCE_THRESHOLD for g in recent_gains)
            )

            # Source-based novelty: deterministic, paraphrase-blind. Counts
            # unique URL/source strings in this round's findings vs the
            # cumulative set from prior rounds. Below 20% new sources for
            # _CONVERGENCE_WINDOW rounds = real saturation, not Haiku noise.
            if "all_sources_seen" not in progress:
                progress["all_sources_seen"] = []
            prior_sources = set(progress["all_sources_seen"])
            this_round_sources: set[str] = set()
            for f in round_findings:
                try:
                    srcs = json.loads(f.get("sources", "[]"))
                    if isinstance(srcs, list):
                        for s in srcs:
                            if isinstance(s, str) and s.strip():
                                this_round_sources.add(s.strip())
                except (json.JSONDecodeError, TypeError):
                    pass
            new_sources = this_round_sources - prior_sources
            source_novelty = (
                len(new_sources) / len(this_round_sources)
                if this_round_sources else 0.0
            )
            progress["all_sources_seen"] = sorted(prior_sources | this_round_sources)
            if "source_novelty_rates" not in progress:
                progress["source_novelty_rates"] = []
            progress["source_novelty_rates"].append({
                "round": round_num,
                "new": len(new_sources),
                "total_this_round": len(this_round_sources),
                "novelty_pct": round(source_novelty * 100, 1),
            })
            recent_novelty = progress["source_novelty_rates"][-_CONVERGENCE_WINDOW:]
            _SOURCE_NOVELTY_THRESHOLD = 0.20  # below 20% new sources = saturating
            source_converged = (
                round_num >= inp.min_rounds
                and len(recent_novelty) >= _CONVERGENCE_WINDOW
                and all(r["novelty_pct"] / 100 < _SOURCE_NOVELTY_THRESHOLD for r in recent_novelty)
                and all(r["total_this_round"] > 0 for r in recent_novelty)
            )
            # Default: both signals must agree (avoid premature termination
            # when one is noisy). Tiebreaker: if either has been converged
            # for 2× the window without the other catching up, accept the
            # one signal — escapes stuck-disagreement deadlock.
            _STUCK_WINDOW = _CONVERGENCE_WINDOW * 2  # 6 rounds default
            stuck_recent_gains = progress["info_gain_rates"][-_STUCK_WINDOW:]
            stuck_recent_novelty = progress["source_novelty_rates"][-_STUCK_WINDOW:]
            info_gain_long_converged = (
                round_num >= inp.min_rounds
                and len(stuck_recent_gains) >= _STUCK_WINDOW
                and all(g["rate"] < _CONVERGENCE_THRESHOLD for g in stuck_recent_gains)
            )
            source_long_converged = (
                round_num >= inp.min_rounds
                and len(stuck_recent_novelty) >= _STUCK_WINDOW
                and all(r["novelty_pct"] / 100 < _SOURCE_NOVELTY_THRESHOLD for r in stuck_recent_novelty)
                and all(r["total_this_round"] > 0 for r in stuck_recent_novelty)
            )
            converged = (
                (info_gain_converged and source_converged)
                or info_gain_long_converged
                or source_long_converged
            )
            info_gain_converged = converged  # downstream code reads this
            state.frontier = [d for d in state.frontier if d.status == "frontier"]
            warn_count = len(progress.get("warnings", []))
            if warn_count > 50:
                progress["warnings"] = progress["warnings"][-10:]
                progress["warnings_pruned"] = warn_count - 10

            await _update_progress(
                phase=f"round_{round_num}_coord_done",
                coord_summary_len=len(coord_summary),
                info_gain_rate=info_gain,
                source_novelty_pct=round(source_novelty * 100, 1),
                source_converged=source_converged,
                info_gain_converged=info_gain_converged,
            )

        # -------------------------------------------------------------- #
            # Sub-direction generation: read findings, spawn follow-ups      #
            # -------------------------------------------------------------- #
            if info_gain_converged:
                directions.clear()
                if source_converged and not (
                    round_num >= inp.min_rounds
                    and len(recent_gains) >= _CONVERGENCE_WINDOW
                    and all(g["rate"] < _CONVERGENCE_THRESHOLD for g in recent_gains)
                ):
                    novelty_summary = [r["novelty_pct"] for r in recent_novelty]
                    state.termination_label = (
                        f"Convergence — source novelty below "
                        f"{int(_SOURCE_NOVELTY_THRESHOLD*100)}% for "
                        f"{_CONVERGENCE_WINDOW} consecutive rounds "
                        f"(rates: {novelty_summary})"
                    )
                else:
                    state.termination_label = (
                        f"Convergence — info gain below {_CONVERGENCE_THRESHOLD}% "
                        f"for {_CONVERGENCE_WINDOW} consecutive rounds "
                        f"(rates: {[g['rate'] for g in recent_gains]})"
                )
                break
            explored_questions = {f["question"] for f in all_findings}
            # Build a heavily-cited-source list so the expander avoids
            # proposing more directions that would re-fetch the same docs.
            # In a real AIMS run, 38 of 660 sources were cited 4+ times each;
            # showing the model "this URL was already read by N researchers"
            # encourages it to drill into UNDER-EXPLORED corners instead.
            _src_counts: dict[str, int] = {}
            for f in all_findings:
                try:
                    srcs = json.loads(f.get("sources", "[]"))
                    if isinstance(srcs, list):
                        for s in srcs:
                            if isinstance(s, str) and s.strip():
                                _src_counts[s.strip()] = _src_counts.get(s.strip(), 0) + 1
                except (json.JSONDecodeError, TypeError):
                    pass
            heavy_sources = sorted(
                ((u, n) for u, n in _src_counts.items() if n >= 3),
                key=lambda x: -x[1],
            )[:25]
            heavy_sources_block = ""
            if heavy_sources:
                heavy_sources_block = (
                    f"\nHeavily-cited sources already covered ({len(heavy_sources)} sources, "
                    "cited by 3+ researchers each — DO NOT propose directions that would "
                    "primarily re-fetch these docs; instead drill into adjacent or unmentioned areas):\n"
                    + "\n".join(f"- ({n}×) {u[:160]}" for u, n in heavy_sources) + "\n"
                )
            expand_prompt_path = f"{run_dir}/expand-r{round_num}.txt"
            findings_summary = "\n".join(
                f"- [{f['dimension']}] {f['question']}: {f.get('findings', '')[:500]}"
                for f in round_findings
            )
            await _write(expand_prompt_path,
                f"Research topic file: {seed_path}\n\n"
                f"Round {round_num} just completed. Findings summary:\n{findings_summary}\n\n"
                f"Already explored ({len(explored_questions)} directions):\n"
                + "\n".join(f"- {q}" for q in list(explored_questions)[:30]) + "\n"
                + heavy_sources_block + "\n"
                "Based on these findings, generate NEW follow-up research directions that:\n"
                "1. Drill deeper into surprising or underexplored findings\n"
                "2. Follow up on entities/teams/tools mentioned but not independently researched\n"
                "3. Verify or challenge claims that seem uncertain\n"
                "4. Cover cross-cutting dimensions not yet explored (PRIOR-FAILURE, BASELINE, "
                "ADJACENT-EFFORTS, STRATEGIC-TIMING, ACTUAL-USAGE)\n"
                "5. Identify domain-specific dimensions that emerged from the findings but "
                "weren't explicitly covered (e.g. economics, governance, user experience)\n\n"
                "CRITICAL DIVERSITY RULES:\n"
                "- Each new direction MUST target a DIFFERENT sub-topic than every other new direction.\n"
                "- If two directions would lead a researcher to the same documents or people, MERGE them.\n"
                "- Spread directions across at least 6 different dimensions.\n"
                "- Prioritize directions that explore areas with ZERO prior coverage over drilling deeper into well-covered areas.\n"
                "- Do NOT generate paraphrased variants of already-explored directions.\n\n"
                f"Generate {max(20, min(info_gain * 2, inp.max_directions))} new directions "
                "(more if the topic is broad and underexplored, fewer if nearing exhaustion). "
                "Use tools to discover gaps. "
                "Only return 0 if the topic is truly exhausted.\n\n"
                "STRUCTURED_OUTPUT_START\n"
                'DIRECTIONS|[{"id":"d_r' + str(round_num + 1) + '_1","dimension":"...","question":"...","priority":"high|medium|low"}, ...]\n'
                "STRUCTURED_OUTPUT_END"
            )
            expand_result = await _spawn(
                role="direction-expander",
                tier="SONNET",
                system_prompt=(
                    "You generate follow-up research directions based on prior findings. "
                    "Use all available tools to discover gaps and unexplored areas. "
                    "Generate as many NEW directions as the topic warrants. "
                    "Only return genuinely new directions — not paraphrases. "
                    "Return empty array [] ONLY if the topic is truly exhausted.\n"
                    "STRUCTURED_OUTPUT_START\n"
                    'DIRECTIONS|[{"id":"...","dimension":"...","question":"...","priority":"..."}, ...]\n'
                    "STRUCTURED_OUTPUT_END"
                ),
                prompt_path=expand_prompt_path,
                max_tokens=128000,
                tools_needed=True,
                run_dir=run_dir,
            )
            # Forensic dump: persist the expander's raw response for debugging
            # premature termination. _parse_json_list on missing/malformed
            # output silently coerces to [], which makes "expander returned 0"
            # indistinguishable from "spawn failed" or "model output unparseable".
            await _write(
                f"{run_dir}/expand-r{round_num}-result.json",
                json.dumps(expand_result, indent=2, default=str),
            )
            new_raw = _parse_json_list(expand_result.get("DIRECTIONS", "[]"))
            workflow.logger.info(
                "expand-r%d: explored=%d, prompt_size=%d, raw_keys=%s, "
                "DIRECTIONS_len=%d, parsed_len=%d",
                round_num, len(explored_questions),
                len(expand_result.get("_full_prompt", "")) if isinstance(expand_result, dict) else 0,
                sorted(expand_result.keys()) if isinstance(expand_result, dict) else None,
                len(expand_result.get("DIRECTIONS", "")) if isinstance(expand_result, dict) else 0,
                len(new_raw),
            )
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

            # Recover empty-frontier as long as info_gain still has signal.
            # Below 10% = diminishing returns → let convergence handle exit.
            _SATURATION_GAIN_THRESHOLD = 10
            _saturation_signal_alive = info_gain >= _SATURATION_GAIN_THRESHOLD
            if not directions and (round_num < inp.min_rounds or _saturation_signal_alive):
                gap_prompt_path = f"{run_dir}/gap-r{round_num}.txt"
                covered_dims = {f.get("dimension", "") for f in all_findings}
                all_dims = set(CROSS_CUT_DIMS) | set(d.dimension for d in current_batch)
                uncovered = all_dims - covered_dims
                await _write(gap_prompt_path,
                    f"Research topic file: {seed_path}\n\n"
                    f"CRITICAL: The direction expander returned 0 new directions after round "
                    f"{round_num}, but we have NOT reached saturation (min_rounds={inp.min_rounds}). "
                    f"This is an early exit — the research is INCOMPLETE.\n\n"
                    f"Already explored ({len(explored_questions)} directions):\n"
                    + "\n".join(f"- {q}" for q in list(explored_questions)[:50]) + "\n\n"
                    f"Dimensions with ZERO coverage: {sorted(uncovered) if uncovered else 'none'}\n"
                    f"Dimensions covered: {sorted(covered_dims)}\n\n"
                    "Your job: generate NEW directions that the previous expander missed. "
                    "Strategies:\n"
                    "1. Drill deeper into specific teams/entities mentioned in findings\n"
                    "2. Cover dimensions with zero or thin coverage\n"
                    "3. Cross-reference: find connections between teams that weren't explored\n"
                    "4. Verify/challenge: create directions that test uncertain claims\n"
                    "5. Quantitative: directions targeting metrics, costs, scale numbers\n"
                    "6. Historical: evolution over time, migration stories, deprecation timelines\n\n"
                    f"Generate at least {max(10, inp.max_directions // 3)} new directions. "
                    "DO NOT return 0 — the research is incomplete and needs more rounds.\n\n"
                    "STRUCTURED_OUTPUT_START\n"
                    'DIRECTIONS|[{"id":"d_gap_r' + str(round_num) + '_1","dimension":"...","question":"...","priority":"high"}, ...]\n'
                    "STRUCTURED_OUTPUT_END"
                )
                gap_result = await _spawn(
                    role="gap-analyst",
                    tier="SONNET",
                    system_prompt=(
                        "You are a research gap analyst. The previous direction expander "
                        "returned 0 new directions too early. Find gaps the expander missed. "
                        "Use all available tools to discover underexplored areas. "
                        "NEVER return an empty list — if the topic is broad enough to have "
                        "had a first round of research, there are always follow-up angles.\n"
                        "STRUCTURED_OUTPUT_START\n"
                        'DIRECTIONS|[{"id":"...","dimension":"...","question":"...","priority":"..."}, ...]\n'
                        "STRUCTURED_OUTPUT_END"
                    ),
                    prompt_path=gap_prompt_path,
                    max_tokens=128000,
                    tools_needed=True,
                    run_dir=run_dir,
                )
                # Forensic dump: same rationale as expand-r{N}-result.json above.
                await _write(
                    f"{run_dir}/gap-r{round_num}-result.json",
                    json.dumps(gap_result, indent=2, default=str),
                )
                gap_raw = _parse_json_list(gap_result.get("DIRECTIONS", "[]"))
                workflow.logger.info(
                    "gap-r%d: raw_keys=%s, DIRECTIONS_len=%d, parsed_len=%d",
                    round_num,
                    sorted(gap_result.keys()) if isinstance(gap_result, dict) else None,
                    len(gap_result.get("DIRECTIONS", "")) if isinstance(gap_result, dict) else 0,
                    len(gap_raw),
                )
                gap_added = 0
                for d in gap_raw:
                    q = d.get("question", "")
                    if q and q not in explored_questions:
                        directions.append(
                            Direction(
                                id=d.get("id", f"d_gap_r{round_num}_{gap_added}"),
                                question=q,
                                dimension=d.get("dimension", "HOW"),
                                priority=d.get("priority", "high"),
                            )
                        )
                        gap_added += 1
                progress.setdefault("gap_recoveries", []).append(
                    {"round": round_num, "proposed": len(gap_raw), "added": gap_added}
                )
                workflow.logger.info(
                    "Gap recovery after round %d: proposed=%d, added=%d",
                    round_num, len(gap_raw), gap_added,
                )

                # Deterministic floor: if BOTH the expander and the gap-analyst
                # returned 0 directions but we're below min_rounds, synthesize
                # follow-ups mechanically from the round's findings rather than
                # exit the loop. This is the only mechanism in the workflow that
                # Mechanical fallback when both LLMs return 0 but info_gain
                # says we're still learning. Turns each finding into 2 follow-
                # ups (evidence-drilldown + contradicting-signals search).
                if not directions:
                    fallback_added = 0
                    for f in round_findings:
                        if fallback_added >= max(10, inp.max_directions // 4):
                            break
                        fid = f.get("id", "?")
                        fdim = f.get("dimension", "HOW")
                        fq = f.get("question", "").strip()
                        if not fq:
                            continue
                        for tag, suffix in (
                            ("evidence", "What load-bearing evidence supports the claims in this direction, and which are still single-source?"),
                            ("contradict", "What evidence contradicts or complicates the conclusions reached in this direction?"),
                        ):
                            new_q = f"{fq}\n[{tag}-followup] {suffix}"
                            if new_q in explored_questions:
                                continue
                            directions.append(
                                Direction(
                                    id=f"d_floor_r{round_num}_{fid}_{tag}",
                                    question=new_q,
                                    dimension=fdim,
                                    priority="high",
                                )
                            )
                            fallback_added += 1
                    progress.setdefault("deterministic_floor", []).append(
                        {"round": round_num, "added": fallback_added}
                    )
                    workflow.logger.warning(
                        "Deterministic floor triggered round %d "
                        "(both expander and gap-analyst returned 0): added=%d",
                        round_num, fallback_added,
                    )

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
        elif frontier_empty and round_num >= inp.min_rounds:
            state.termination_label = f"Frontier exhausted after {round_num} rounds — no new directions generated"
        elif frontier_empty:
            state.termination_label = f"Frontier exhausted prematurely at round {round_num} (before min_rounds={inp.min_rounds})"
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
                tier="SONNET",
                system_prompt=(
                    "You are an exhaustive fact verifier. Check EVERY claim using all "
                    "available tools — code search for code claims, documentation search "
                    "for doc claims, chat search for discussion claims. Verify exact "
                    "numbers, team names, repo existence, API details. Be ruthless "
                    "about flagging unverifiable claims. "
                    "CITATION-URL VALIDATION (REQUIRED — backstop for researcher rule): "
                    "Extract all `corp/<repo>` and `corp/<repo>/<subpath>` URLs cited in "
                    "the findings. For a stratified sample of up to 20 URLs (mix of "
                    "top-level repos and monorepo subpaths if both are cited), call "
                    "`mcp__sourcegraph-official__list_repos` for top-level checks and "
                    "`mcp__sourcegraph-official__list_files` for subpath checks. Record "
                    "in UNVERIFIABLE any URL that returns 'No files.' or zero matches — "
                    "those are broken citations and the report must NOT present them as "
                    "valid evidence. The sample budget is 20 calls = ~30s wall-clock "
                    "with parallelism; 9 parallel calls completed in 10s in a probe. "
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
                run_dir=run_dir,
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

        if workflow.patched("refuse-empty-synthesis-v1"):
            if not all_findings:
                workflow.logger.error(
                    "0 findings after all rounds — refusing to synthesize an empty report"
                )
                raise ApplicationError(
                    "Research produced 0 findings — cannot synthesize. "
                    "Check researcher spawn/completion logs."
                )

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

        # Dump the unexplored frontier so the synth subagent can list "what we did
        # NOT cover" — without this the report silently terminates with an unknown
        # blast radius (deep-qa C2/C4: VP-roles unvalidated, queued directions
        # not inventoried).
        unexplored_path = f"{run_dir}/unexplored-frontier.json"
        unexplored = [
            {"id": d.id, "dimension": d.dimension, "question": d.question, "priority": d.priority}
            for d in state.frontier
            if d.status not in ("researched", "duplicate")
        ]
        await _write(unexplored_path, json.dumps(unexplored, indent=2))

        synth_prompt_path = f"{run_dir}/synth-prompt.txt"
        await _write(synth_prompt_path,
            f"Research topic file: {seed_path}\n\n"
            f"Termination: {state.termination_label}\n\n"
            f"Findings index ({len(all_findings)} directions): {findings_index_path}\n"
            f"Findings directory: {findings_dir}/\n"
            f"Coordinator summary: {run_dir}/coordinator-summary.md\n"
            f"Unexplored frontier ({len(unexplored)} unresearched directions): {unexplored_path}\n"
            "Read the coordinator summary and findings files for full content.\n\n"
            f"{cross_cut_section}\n\n"
            f"{verifier_section}\n\n"
            f"Write research-report.md targeting {max(3000, len(all_findings) * 30)} words "
            f"(scaled to {len(all_findings)} findings — broader topics need longer reports).\n"
            "Structure:\n"
            "- Executive Summary\n"
            "- Findings per direction\n"
            "- Cross-cutting analysis (PRIOR-FAILURE, BASELINE, ADJACENT-EFFORTS, "
            "STRATEGIC-TIMING, ACTUAL-USAGE)\n"
            "- Contradictions & Reconciliation (verbatim from coordinator summary, never silently picked)\n"
            "- Fact Verification Results\n"
            "- Coverage & Termination — REQUIRED subsections:\n"
            "    * 'What this report did NOT cover' — enumerate each entry from "
            f"      {unexplored_path} as a bullet, with priority and dimension. "
            "      Required whenever the unexplored frontier is non-empty.\n"
            "    * 'Attribution recency' — for each named manager/IC/team-state "
            "      claim, cite the year of the underlying source. Flag any "
            "      attribution older than 12 months as `[STALE: source from {date}]`.\n"
            "- Sources\n"
            "STRUCTURED_OUTPUT_START\n"
            "REPORT|<full markdown>\n"
            "STRUCTURED_OUTPUT_END"
        )
        synth_result = await _spawn(
            role="synth",
            tier="SONNET",
            system_prompt=(
                "Write the most comprehensive research report possible. Include EVERY "
                "finding from EVERY direction. Include a 'Cross-cutting analysis' "
                "section and a 'Fact Verification Results' section. Do NOT summarize "
                "or truncate — include full detail for each direction. Use all available "
                "tools to verify and enrich the synthesis. "
                "EDITORIAL STANDARDS (mandatory): "
                "1) Every person gets full name on first mention with role/context. "
                "2) Every named system, tool, project, or platform MUST have a clickable "
                "hyperlink on first mention — look up the URL (manual page, GitHub repo, "
                "or reference doc) and add it. This means ADDING links, not just checking "
                "existing ones. "
                "3) If you write 'three X' or 'five Y', the enumeration must match exactly. "
                "4) Every sentence follows logically from the previous — no topic shifts "
                "without paragraph breaks. "
                "5) Every factual claim has a source. "
                "6) Keep source terminology exactly — do not rename proper nouns. "
                "7) ROLE ATTRIBUTION DISCIPLINE: when building any team→people table, "
                "distinguish managers from ICs explicitly. A person is a MANAGER iff their "
                "userid appears in a Pandora `latest_owner_employee_user_id_mgt_chain_array` "
                "tuple `[--, estone, ..., USERID, ...]` with at least one element after them. "
                "CODEOWNERS, commit authors, Slack mentions, and people identified as 'lead "
                "engineer on X' are ICs unless explicit 'Manager of X' phrasing exists in "
                "findings. NEVER place an IC in a column labeled 'Manager' — use 'Lead / IC' "
                "or annotate `(IC)`. If role evidence is missing, write `*(role unknown)*` — "
                "do not guess from proximity, list position, or quote frequency. "
                "8) SOURCE-DOC LINK PRESERVATION: for every claim of the form 'Per the X "
                "doc, ...' or 'X authored Y stating: \"...quote...\"', search the coordinator "
                "summary and mini-syntheses for the URL. If found → hyperlink the doc title "
                "on first mention. If the URL is NOT in findings → either drop the verbatim "
                "quote OR mark it `⚠️ Citation not found in findings — single-source "
                "unverified`. If the URL exists but the doc is access-walled (Google Docs, "
                "Confluence, Notion) → include a `⚠️ Verification note:` that the doc could "
                "not be independently verified. "
                "9) TERMINATION DISCLOSURE: when the unexplored-frontier file passed in your "
                "prompt has entries (any termination label other than `Frontier exhausted "
                "after N rounds`), you MUST include a 'What this report did NOT cover' "
                "subsection in Coverage & Termination that enumerates every unexplored "
                "direction by id, dimension, priority, and question. This is required even "
                "if the list is long. Silently terminating with unexplored frontier hides "
                "the report's blast radius (deep-qa C2/C4: VP-roles unvalidated, queued "
                "directions not inventoried). "
                "10) CONTRADICTION RECONCILIATION: scan the coordinator summary's "
                "'Contradictions / Reconciliation' section. Every contradiction listed there "
                "MUST appear in the final report's 'Contradictions & Reconciliation' section "
                "with both sides quoted verbatim, source attribution for each, and either "
                "(a) an explicit reconciliation if the disagreement is resolvable from "
                "evidence (e.g. different time windows, different scopes), or (b) the label "
                "`UNRESOLVED — both views preserved` if not. Never silently pick one side "
                "(deep-qa C5: Metaboost 'not paved path' vs. documented production usage "
                "across 6+ teams). "
                "11) ATTRIBUTION RECENCY: every named manager/IC/team-state claim must "
                "carry the year/date of the underlying source visible in the report (in a "
                "footnote, parenthetical, or 'as of {date}' phrase). For manager-attribution "
                "claims sourced from material >12 months old, append `[STALE: source from "
                "{date}]` inline. This is required for fast-moving topics like org charts, "
                "platform inventories, and tool adoption — 16+ month-old org-doc snapshots "
                "are routinely wrong by report time (deep-qa C1/C3: managers and individual "
                "attributions stale). "
                "AFTER writing the report, do a VERIFY pass: scan for capitalized proper "
                "nouns not inside markdown links and add links for any you missed; scan for "
                "every 'Manager' column entry and confirm it has Pandora-chain evidence or "
                "an `(IC)` / `*(role unknown)*` annotation; scan for every verbatim quote "
                "from a doc and confirm the doc is linked or marked unverified; verify the "
                "'What this report did NOT cover' subsection exists if the unexplored "
                "frontier was non-empty; verify every contradiction in the coordinator "
                "summary appears in 'Contradictions & Reconciliation'; verify every named "
                "manager has a source-year annotation. "
                "STRUCTURED_OUTPUT_START\n"
                "REPORT|<full markdown>\n"
                "STRUCTURED_OUTPUT_END"
            ),
            prompt_path=synth_prompt_path,
            max_tokens=128000,
            tools_needed=True,
            run_dir=run_dir,
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
        try:
            await workflow.execute_activity(
                "deliver_artifact_to_slack",
                DeliverArtifactInput(run_dir=run_dir, artifact_path=report_path, comment=summary),
                start_to_close_timeout=timedelta(seconds=120),
                retry_policy=HAIKU_POLICY,
            )
        except Exception:
            pass
        await workflow.execute_activity(
            "finalize_manifest",
            FinalizeManifestInput(run_dir=run_dir, status="COMPLETED"),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=HAIKU_POLICY,
        )
        return f"{summary}\nReport: {report_path}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _write(path: str, content: str, *, append: bool = False) -> None:
    await workflow.execute_activity(
        "write_artifact",
        WriteArtifactInput(path=path, content=content, append=append),
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
    run_dir: str,
    mcp_config_path: str | None = None,
    output_schema: dict | None = None,
) -> dict[str, str]:
    # ``run_dir`` is required: sagaflow's ``spawn_subagent`` activity only
    # writes the per-step manifest entry and the ``cost_audit.jsonl`` row
    # when ``inp.run_dir`` is non-empty. Omitting it silently disables
    # ``sagaflow cost runs`` reporting (which then shows $0.0000 / 0 steps
    # for every research run).
    timeout = 7200 if tools_needed else 3600
    result = await workflow.execute_activity(
        "spawn_subagent",
        SpawnSubagentInput(
            role=role,
            tier_name=tier,
            system_prompt=system_prompt,
            user_prompt_path=prompt_path,
            max_tokens=max_tokens,
            tools_needed=tools_needed,
            mcp_config_path=mcp_config_path,
            output_schema=output_schema,
            run_dir=run_dir,
        ),
        start_to_close_timeout=timedelta(seconds=timeout),
        heartbeat_timeout=timedelta(seconds=120),
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
    # Try direct parse first.
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [x for x in parsed if isinstance(x, dict)]
    except json.JSONDecodeError:
        pass
    # Try extracting a JSON array from surrounding text (LLMs often wrap in markdown).
    import re
    for m in re.finditer(r'\[[\s\S]*?\](?=\s*$|\s*```)', raw):
        try:
            parsed = json.loads(m.group())
            if isinstance(parsed, list):
                result = [x for x in parsed if isinstance(x, dict)]
                if result:
                    return result
        except json.JSONDecodeError:
            continue
    # Last resort: find the largest [...] substring.
    bracket_depth = 0
    start = -1
    for i, ch in enumerate(raw):
        if ch == '[' and start == -1:
            start = i
            bracket_depth = 1
        elif ch == '[' and start != -1:
            bracket_depth += 1
        elif ch == ']' and start != -1:
            bracket_depth -= 1
            if bracket_depth == 0:
                try:
                    parsed = json.loads(raw[start:i + 1])
                    if isinstance(parsed, list):
                        result = [x for x in parsed if isinstance(x, dict)]
                        if result:
                            return result
                except json.JSONDecodeError:
                    pass
                start = -1
    workflow.logger.warning("_parse_json_list: all parsing strategies failed for input (first 500 chars): %s", raw[:500])
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
        # State carries only a short excerpt (full text is on disk at
        # f["findings_path"]); fallback uses the excerpt + a pointer.
        body = f.get("findings_excerpt") or f.get("findings", "")
        body = body[:2000]
        if not body and f.get("findings_path"):
            body = f"(see {f['findings_path']})"
        total += len(header) + len(body) + 2
        if total > _MAX_FALLBACK_BYTES:
            lines.append(f"\n\n... truncated ({len(findings)} total findings, see findings directory)")
            break
        lines.append(header)
        lines.append(body)
        lines.append("")
    return "\n".join(lines)
