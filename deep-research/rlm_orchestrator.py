"""Multi-RLM fan-out orchestrator for deep research.

Decomposes a query into orthogonal dimensions, runs parallel RLM instances
per dimension, synthesizes, detects gaps, and verifies.

Architecture:
    Phase 1: Decompose query -> N dimensions (Sonnet, ~30s)
    Phase 2: N parallel RLM runs, one per dimension (~8-15 min wall time)
    Phase 3: Synthesize per-dimension findings (Sonnet, ~30s)
    Phase 4: Gap detection + targeted follow-up RLMs (~5-10 min)
    Phase 5: Verification pass (Haiku, ~30s)
    Phase 6: Final report assembly

Usage:
    RLM_API_BASE=... python deep-research/rlm_orchestrator.py \\
        --query "<seed prompt>" \\
        --run-dir /tmp/rlm-deep-test

The seed prompt should include any tenant-specific context the runners need
(repo hosts, docs hosts, email domains, chat platforms, naming conventions).
The workflow itself is tenant-agnostic — it does not embed any specific
hostname, domain, or product name.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Resolve OpenAI-compatible base URL. Honour explicit RLM_API_BASE first, then
# fall back to whatever the rest of the stack uses (dspy/litellm reads
# OPENAI_BASE_URL natively; some deployments export CRITIC_BASE_URL pointing at
# a model gateway). This keeps the orchestrator usable on a worker that
# inherits a generic OpenAI-compatible env without a sagaflow-specific export.
MGP_BASE = (
    os.environ.get("RLM_API_BASE")
    or os.environ.get("OPENAI_BASE_URL")
    or os.environ.get("CRITIC_BASE_URL")
)
MGP_KEY = (
    os.environ.get("RLM_API_KEY")
    or os.environ.get("OPENAI_API_KEY")
    or os.environ.get("CRITIC_API_KEY")
    or "sk-dummy"
)
# Model names for direct OpenAI SDK calls (no "openai/" prefix — that's a dspy convention)
MAIN_MODEL = os.environ.get("RLM_ORCH_MODEL", "claude-sonnet-4-6")
DIGEST_MODEL = os.environ.get("RLM_DIGEST_MODEL", "claude-haiku-4-5")
# Verifier must not be in the same family as MAIN_MODEL (cross-model
# independence). Haiku-class verifiers over-flag internal-only URLs as
# fabricated because they pattern-match external falsifiability — for
# research about internal infrastructure, that produces a flood of false
# "looks-fabricated" verdicts. Default to a non-Claude frontier model. The
# operator MUST verify the chosen identifier resolves on their gateway;
# override via RLM_VERIFY_MODEL when it does not.
VERIFY_MODEL = os.environ.get("RLM_VERIFY_MODEL", "gpt-5.4")


_FS_SAFE_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def _slugify_name(name: str) -> str:
    """Make a dim name safe to use as a filesystem path component.

    Replaces path separators, whitespace, and any other non-`[A-Za-z0-9._-]`
    char with `_`. Strips leading dots so we never produce hidden directories
    or `..` traversal. Falls back to a fixed sentinel for empty results so
    we never call ``mkdir("")``.
    """
    slug = _FS_SAFE_RE.sub("_", (name or "").strip())
    slug = slug.lstrip(".") or "dim"
    return slug[:80]  # filesystem-safe length cap


def _uniqueify_dimension_names(dims: list["Dimension"]) -> list["Dimension"]:
    """Slugify + dedupe dim names so each gets a unique on-disk directory.

    The decomposer (and the gap synthesizer) is an LLM and can return
    duplicate or path-unsafe dim names. Without this, two dims sharing a
    slug would concurrently write to the same `<run_dir>/dimensions/<slug>/`
    and corrupt each other's findings.
    """
    seen: dict[str, int] = {}
    out: list[Dimension] = []
    for d in dims:
        slug = _slugify_name(d.name)
        if slug in seen:
            seen[slug] += 1
            slug = f"{slug}_{seen[slug]}"
        else:
            seen[slug] = 0
        out.append(Dimension(name=slug, query=d.query, search_strategy=d.search_strategy))
    return out


@dataclass
class Dimension:
    name: str
    query: str
    search_strategy: str


@dataclass
class DimensionResult:
    dimension: Dimension
    findings: str
    iterations: int
    elapsed_seconds: float
    error: str | None = None
    # Raw text of the runner's tool-call trajectory (printed tool output that
    # the LLM saw but did NOT necessarily paste into `findings`). The runner
    # writes a narrative summary; many URLs/emails/IDs that were returned by
    # search_codebase / search_docs / search_slack never make it into the
    # narrative. We regex-extract citations from BOTH `findings` AND
    # `tool_log` so source identifiers seen by the runner are never silently
    # dropped just because the runner's prose was terse. Loaded from
    # `trajectory.json` per dim; empty string if the file is missing.
    tool_log: str = ""


@dataclass
class OrchestratorResult:
    query: str
    dimensions: list[Dimension]
    dimension_results: list[DimensionResult]
    gap_results: list[DimensionResult]
    synthesis: str
    verification: str
    final_report: str
    total_elapsed_seconds: float
    total_iterations: int
    phase_timings: dict[str, float] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def _llm_call(prompt: str, *, model: str | None = None, max_tokens: int = 32000) -> str:
    """OpenAI chat completion via streaming, with deterministic resource cleanup.

    ``max_tokens`` is a SAFETY VALVE, not a target. Setting it high (32K) does
    NOT make the model emit more tokens — the model only emits what the prompt
    asks for. Setting it low DOES truncate output mid-sentence when the prompt
    legitimately needs more space (e.g. a synthesis report that wants 100+
    inline citations). MGP accepts up to 64000 for both Sonnet 4.6 and Haiku
    4.5; we default to 32000 which is well above any normal output and far
    below the upstream cap. Callers should not lower this unless they have a
    specific reason (e.g. enforcing a tweet-length response).

    Streaming is required: long synthesis outputs exceed the default 120s read
    timeout in non-streaming mode. Streaming applies the timeout between
    chunks; Sonnet emits chunks every <1s under normal load.

    Both the HTTP client and the streaming response object are cleaned up
    deterministically — earlier versions left them open per-call which leaked
    sockets in long-lived workers running map-reduce fan-outs.
    """
    import httpx
    from openai import OpenAI

    # MGP proxy requires x-api-key header, not Authorization: Bearer.
    parts: list[str] = []
    with httpx.Client(
        headers={"x-api-key": MGP_KEY},
        timeout=httpx.Timeout(120.0, connect=10.0),
    ) as http_client:
        client = OpenAI(
            base_url=MGP_BASE,
            api_key=MGP_KEY,
            http_client=http_client,
        )
        stream = client.chat.completions.create(
            model=model or MAIN_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            stream=True,
        )
        try:
            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is not None and delta.content:
                    parts.append(delta.content)
        finally:
            close = getattr(stream, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:  # noqa: BLE001
                    pass
    return "".join(parts)


def decompose_query(query: str, max_dimensions: int = 14) -> list[Dimension]:
    """Phase 1: Decompose a research query into enumerative DIRECTIONS.

    Ported from the traditional deep-research workflow
    (deep-research/workflow.py): each direction is
    a SHARP enumerative question across the WHO/WHAT/HOW/WHERE/WHEN/WHY/
    LIMITS dimensions, with required cross-cutting dimensions
    (PRIOR-FAILURE, BASELINE, ADJACENT-EFFORTS, STRATEGIC-TIMING,
    ACTUAL-USAGE). Earlier RLM decompose generated thematic dims
    ("architecture", "adoption") which produce conceptual research; the
    enumerative WHO/WHAT/HOW phrasing produces concrete team/repo/owner
    enumeration. This is the load-bearing difference between baseline's
    45-team breadth and prior RLM runs' 16-team breadth.
    """
    # The traditional pipeline uses up to max_directions (default 12) and
    # caps any one dimension at max_directions // 8 (≥5). We mirror that.
    n_dirs = max(max_dimensions, 8)
    per_dim_cap = max(n_dirs // 8, 5)
    prompt = f"""Generate {n_dirs} research DIRECTIONS for parallel investigation. Each direction is a SHARP enumerative question, not a thematic topic area.

QUERY: {query}

DIMENSIONS — distribute directions across these (WHO/WHAT/HOW/WHERE/WHEN/WHY/LIMITS):
- WHO — which teams/orgs/individuals are involved, who owns, who uses, who decided
- WHAT — which specific systems/services/repos/artifacts exist, what is in scope
- HOW — how to enumerate/discover/measure/verify; concrete tool/query patterns
- WHERE — which infrastructure/region/namespace/cluster/path; deployment locus
- WHEN — timeline; adoption order; migration dates; version cutovers
- WHY — driving requirements; design decisions; alternatives considered
- LIMITS — scale, criticality, classifications; what is OUT of scope

REQUIRED cross-cutting dimensions — include at least ONE direction for EACH:
- PRIOR-FAILURE — who evaluated and abandoned; what didn't work; rollbacks
- BASELINE — authoritative registries; canonical lists; allocation sheets
- ADJACENT-EFFORTS — overlapping/competing/coexisting systems and their boundaries
- STRATEGIC-TIMING — decisions accelerating/blocking adoption right now
- ACTUAL-USAGE — production traffic; active workers; dormant vs alive
- COST-ECONOMICS — annual spend, $/unit, compute cost, fleet utilization,
  waste, savings opportunities; search internal cost dashboards, budget docs,
  and leadership review materials. Without this dim the report skips
  quantitative cost claims that are usually the load-bearing argument for any
  infra investment proposal.
- INDUSTRY-CONTEXT — public/external comparisons: how peers (other large
  industry players, hyperscalers, open-source projects) approach the same
  problem; what canonical benchmarks, papers, or vendor announcements set the
  comparison baseline. Skip ONLY if the question is strictly tenant-internal
  with no externally-comparable shape.

BALANCE: distribute directions evenly. No single dimension > {per_dim_cap} directions.

DIVERSITY: each direction must explore a DISTINCT sub-topic. Two directions that
would lead a researcher to the same sources or findings should be merged.

ENUMERATIVE PHRASING — REQUIRED for WHO/WHAT directions specifically. Bad:
"What consumers use the subject?" (too vague). Good: "Which named consumers
import or depend on the subject in production, with named owners per consumer?"
Bad: "What artifacts depend on the subject?" (too vague). Good: "Enumerate
every repository, dataset, service, or named artifact that depends on the
subject, grouped by owner." Phrase every WHO/WHAT direction so its answer is
a LIST of named entities, not a paragraph of generic description.

For each direction:
1. name: short slug for the on-disk directory (lowercase, no spaces, ≤40 chars,
   distinct across all directions in this batch)
2. query: the SELF-CONTAINED enumerative research question (include the original
   topic context — the researcher sees only this query)
3. search_strategy: concrete tools and query angles, 2-3 sentences. Available
   tools are advertised at runner-spawn time; describe ANGLES (e.g. "search the
   codebase for imports of <subject>'s canonical package", "search docs for
   ownership/onboarding/registry pages mentioning <subject>", "search chat for
   announcement messages by the team that owns <subject>") rather than
   prescribing concrete tool names — the runner picks the tool.

Respond in this EXACT JSON format (no other text):
[
  {{
    "name": "who-imports",
    "query": "[WHO] Which named consumers import or depend on <subject> in production, with named owners per consumer?",
    "search_strategy": "Code search for canonical-package imports across all repos; cross-reference with ownership/app-metadata registries; chat pinned messages and onboarding announcements for adoption events."
  }}
]

RULES:
- Generate {n_dirs} directions. Each must be independently researchable.
- Include the original topic context in EVERY query (researcher sees only their own).
- Prefix every query with its dimension tag in brackets — `[WHO]`, `[WHAT]`,
  `[HOW]`, `[WHERE]`, `[WHEN]`, `[WHY]`, `[LIMITS]`, `[PRIOR-FAILURE]`,
  `[BASELINE]`, `[ADJACENT-EFFORTS]`, `[STRATEGIC-TIMING]`, `[ACTUAL-USAGE]`,
  `[COST-ECONOMICS]`, `[INDUSTRY-CONTEXT]`.
- Each direction's `name` is the directory slug — must be unique within the run.
- Do NOT hardcode tenant- or topic-specific tool names (e.g. specific repo
  hostnames, specific docs hosts, specific chat platforms) into queries or
  search strategies — the runner discovers and selects from the tools
  available in its sandbox."""

    response = _llm_call(prompt)

    try:
        json_start = response.find("[")
        json_end = response.rfind("]") + 1
        if json_start >= 0 and json_end > json_start:
            dims_raw = json.loads(response[json_start:json_end])
        else:
            raise ValueError("No JSON array found")
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Failed to parse dimensions: %s", e)
        dims_raw = [
            {"name": "architecture", "query": f"Architecture and design of: {query}", "search_strategy": "Official docs, code, design docs"},
            {"name": "adoption", "query": f"Team adoption and use cases for: {query}", "search_strategy": "Slack announcements, team pages, changelogs"},
            {"name": "patterns", "query": f"Patterns and best practices for: {query}", "search_strategy": "Docs, code examples, guides, blog posts"},
            {"name": "operations", "query": f"Production operations and monitoring for: {query}", "search_strategy": "Runbooks, monitoring dashboards, incident reports"},
            {"name": "history", "query": f"History, evolution, and key decisions about: {query}", "search_strategy": "Announcements, changelogs, ADRs, Slack history"},
            {"name": "ecosystem", "query": f"Ecosystem, integrations, and alternatives for: {query}", "search_strategy": "Architecture docs, dependency graphs, comparison docs"},
        ]

    dims = [
        Dimension(
            name=d.get("name", f"dim-{i}"),
            query=d.get("query", query),
            search_strategy=d.get("search_strategy", ""),
        )
        for i, d in enumerate(dims_raw)
    ]

    # Verify-and-fix: ensure required cross-cuts present. Sonnet routinely
    # disregards "REQUIRED" prompt directives when generating dims that look
    # complete to it — measured across multiple benches that COST-ECONOMICS
    # and INDUSTRY-CONTEXT got dropped even at max_dimensions=14. Force-add
    # missing cross-cuts as synthesized directions if they're absent.
    REQUIRED_CROSSCUTS = {
        "PRIOR-FAILURE": (
            "Who evaluated and abandoned this approach? What didn't work, "
            "what got rolled back, and what's the post-mortem?"
        ),
        "BASELINE": (
            "What authoritative registries, canonical lists, or allocation "
            "sheets enumerate the entities in scope?"
        ),
        "ADJACENT-EFFORTS": (
            "What overlapping, competing, or coexisting systems exist? "
            "Where are the boundaries between them?"
        ),
        "STRATEGIC-TIMING": (
            "What decisions, deadlines, or events are accelerating or "
            "blocking adoption right now?"
        ),
        "ACTUAL-USAGE": (
            "What's the production traffic shape — active workers vs "
            "dormant vs alive — for the systems in scope?"
        ),
        "COST-ECONOMICS": (
            "Annual or monthly spend per subsystem; $/unit unit costs; "
            "compute fleet utilization rates; identified waste; savings "
            "opportunities. Search internal cost dashboards, cost-attribution "
            "tooling, budget documents, and leadership review materials."
        ),
        "INDUSTRY-CONTEXT": (
            "How do peers (other large industry players, hyperscalers, "
            "open-source projects, vendors) approach the same problem? What "
            "public benchmarks, papers, or announcements set the comparison "
            "baseline? Use web_search for external sources."
        ),
    }

    def _slug(tag: str) -> str:
        return tag.lower().replace("-", "-")

    present_tags: set[str] = set()
    for d in dims:
        m = _re_dim_tag.match(d.query)
        if m:
            present_tags.add(m.group(1).upper())

    missing = [tag for tag in REQUIRED_CROSSCUTS if tag not in present_tags]
    if missing:
        logger.warning(
            "decompose dropped required cross-cuts: %s — force-adding", missing
        )
        for tag in missing:
            dims.append(Dimension(
                name=f"{tag.lower()}-forced",
                query=f"[{tag}] {REQUIRED_CROSSCUTS[tag]} (Topic: {query})",
                search_strategy=(
                    "Generic angles: search internal docs, code, and chat "
                    "for the dimension's keywords; for INDUSTRY-CONTEXT use "
                    "web_search to find external comparisons."
                ),
            ))

    # Trim back to max_dimensions if force-adds pushed us over. Prefer to
    # KEEP the force-added cross-cuts (they're the rare ones); drop excess
    # main-dimension directions if needed.
    if len(dims) > max_dimensions:
        forced = [d for d in dims if d.name.endswith("-forced")]
        non_forced = [d for d in dims if not d.name.endswith("-forced")]
        keep_non_forced = max(0, max_dimensions - len(forced))
        dims = non_forced[:keep_non_forced] + forced

    return dims[:max_dimensions]


# Compiled once at module load — used by decompose post-validation.
_re_dim_tag = __import__("re").compile(r"^\s*\[([A-Z][A-Z-]+)\]")


def _run_dimension_subprocess(
    dim: Dimension,
    dim_dir: str,
    max_iterations: int,
    max_llm_calls: int,
    python_path: str | None = None,
) -> DimensionResult:
    """Run a single dimension's RLM research as a subprocess."""
    python = python_path or sys.executable

    focused_query = (
        f"{dim.query}\n\n"
        f"FOCUS: This is the '{dim.name}' dimension of a larger research effort. "
        f"Be THOROUGH on this dimension specifically.\n"
        f"Search strategy: {dim.search_strategy}\n"
        f"QUALITY BAR: Aim for at least 8 concrete, specific findings with evidence. "
        f"Do not submit early — use all available iterations to deepen coverage. "
        f"If you have found fewer than 5 substantive facts, keep searching with different terms."
    )

    runner_script = Path(__file__).with_name("rlm_runner.py")
    cmd = [
        python, str(runner_script),
        "--query", focused_query,
        "--run-dir", dim_dir,
        "--max-iterations", str(max_iterations),
        "--max-llm-calls", str(max_llm_calls),
    ]
    subprocess_timeout = max(max_iterations * 50, 600)

    # Run in its OWN process group so we can kill the whole tree on timeout.
    # Without this, ``subprocess.run(timeout=...)`` only kills the immediate
    # child — the runner spawns Deno (WASM sandbox) and tool subprocesses
    # that survive the kill and keep consuming CPU/sockets,
    # accumulating zombies across runs on long-lived workers.
    start = time.time()
    proc: subprocess.Popen[str] | None = None
    try:
        _env = os.environ.copy()
        if MGP_BASE:
            # Propagate the resolved base URL so fallback configs on the
            # orchestrator side (OPENAI_BASE_URL, CRITIC_BASE_URL) also reach
            # the per-dimension runner process.
            _env["RLM_API_BASE"] = MGP_BASE
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=_env,
            cwd=str(Path(__file__).resolve().parent),
            start_new_session=True,  # detach: own pgid; kill -- -pgid kills the tree
        )
        try:
            stdout, stderr = proc.communicate(timeout=subprocess_timeout)
            returncode = proc.returncode
            timed_out = False
        except subprocess.TimeoutExpired:
            # Escalate: SIGTERM the whole group, give it 10s to clean up,
            # then SIGKILL anything still alive. Read whatever output it
            # managed to flush before the kill.
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except (ProcessLookupError, OSError) as exc:
                logger.warning("dim '%s' SIGTERM pg failed: %s", dim.name, exc)
            try:
                stdout, stderr = proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except (ProcessLookupError, OSError):
                    pass
                stdout, stderr = proc.communicate()
            returncode = proc.returncode if proc.returncode is not None else 124
            timed_out = True

        elapsed = time.time() - start

        findings_path = Path(dim_dir) / "findings.md"
        findings = findings_path.read_text(encoding="utf-8") if findings_path.exists() else ""

        # Load the runner's tool-call trajectory so the citation extractor can
        # also pull URLs/emails/IDs the runner saw but didn't paste into the
        # narrative findings. trajectory.json is JSON but we read it as raw
        # text — regex extraction works directly on the JSON-encoded blobs.
        traj_path = Path(dim_dir) / "trajectory.json"
        tool_log = traj_path.read_text(encoding="utf-8") if traj_path.exists() else ""

        meta_path = Path(dim_dir) / "rlm_meta.json"
        iterations = 0
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                iterations = int(meta.get("iterations", 0) or 0)
            except (json.JSONDecodeError, OSError, ValueError, TypeError):
                pass

        error: str | None = None
        if timed_out:
            error = f"timeout after {subprocess_timeout}s (process group killed)"
            # Log stdout/stderr tails so we can diagnose hung-at-0-iters
            # situations. Earlier silent timeouts left no record of WHY the
            # subprocess hung — couldn't distinguish LM gateway slowness
            # from Deno sandbox failure from infinite-loop tool calls.
            _stdout_tail = (stdout or "")[-1500:] or "(empty)"
            _stderr_tail = (stderr or "")[-1500:] or "(empty)"
            logger.warning(
                "dim '%s' timeout — stdout tail:\n%s\nstderr tail:\n%s",
                dim.name, _stdout_tail, _stderr_tail,
            )
        elif returncode != 0:
            err_tail = (stderr or "")[-2000:] or f"exit code {returncode}"
            error = err_tail

        return DimensionResult(
            dimension=dim,
            findings=findings,
            iterations=iterations,
            elapsed_seconds=elapsed,
            error=error,
            tool_log=tool_log,
        )
    except Exception as e:  # noqa: BLE001
        # Always try to reclaim the process group even on unexpected errors —
        # silently leaking child processes is exactly the failure mode the
        # process-group changes above are meant to prevent.
        if proc is not None and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass
        return DimensionResult(
            dimension=dim, findings="", iterations=0,
            elapsed_seconds=time.time() - start, error=str(e),
        )


def run_parallel_dimensions(
    dimensions: list[Dimension],
    run_dir: str,
    *,
    max_iterations: int = 30,
    max_llm_calls: int = 60,
    max_workers: int = 6,
    python_path: str | None = None,
    on_dimension_complete: Callable[[DimensionResult], None] | None = None,
) -> list[DimensionResult]:
    """Phase 2: Run parallel RLM instances, one per dimension."""
    results: list[DimensionResult] = []

    with ThreadPoolExecutor(max_workers=min(max_workers, len(dimensions))) as pool:
        futures = {}
        for dim in dimensions:
            dim_dir = f"{run_dir}/dimensions/{dim.name}"
            Path(dim_dir).mkdir(parents=True, exist_ok=True)
            future = pool.submit(
                _run_dimension_subprocess,
                dim, dim_dir, max_iterations, max_llm_calls, python_path,
            )
            futures[future] = dim

        for future in as_completed(futures):
            dim = futures[future]
            try:
                result = future.result()
                results.append(result)
                logger.info(
                    "Dimension '%s': %d iters, %.0fs, %d chars%s",
                    dim.name, result.iterations, result.elapsed_seconds,
                    len(result.findings),
                    f" (error: {result.error})" if result.error else "",
                )
                if on_dimension_complete:
                    on_dimension_complete(result)
            except Exception as e:
                logger.error("Dimension '%s' failed: %s", dim.name, e)
                results.append(DimensionResult(
                    dimension=dim, findings="", iterations=0,
                    elapsed_seconds=0, error=str(e),
                ))

    return results


# Tenant-agnostic citation patterns. These match any URL/email/identifier
# regardless of host or domain. Tenant-specific narrower patterns (e.g. the
# operating org's email domain or repo host) can be appended via the
# `RLM_TENANT_PATTERNS` JSON file at runtime — see `_load_tenant_patterns`.
_CITATION_PATTERNS: dict[str, str] = {
    # Any HTTP/HTTPS URL. Subcategorized by host downstream if needed.
    "url_generic": r"https?://[a-zA-Z0-9.-]+(?:\.[a-zA-Z]{2,})+/[\w./%#?=&+-]+",
    # Bare repo paths in the common `<host>/<org>/<repo>` form used by
    # GitHub/GitHub-Enterprise/GitLab/Bitbucket et al.
    "repo_path_generic": r"\b[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+/[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+",
    # Any email address — tenant config can narrow this to a specific domain.
    "email_generic": r"\b[\w.-]+@[\w.-]+\.[a-zA-Z]{2,}\b",
    # Dates: YYYY-MM-DD, YYYY-MM, "Month YYYY". Capture so synthesis can
    # thread specific dates into the report instead of "early 2025" /
    # "recently." Pool typically has many transient dates (PR/commit
    # timestamps); cap in _PER_KIND_CAP keeps the surfaced subset bounded.
    "date_specific": r"\b20\d{2}-\d{2}-\d{2}\b|\b20\d{2}-\d{2}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(?:uary|ruary|ch|il|e|y|ust|tember|ober|ember)?\s+20\d{2}\b",
    # Version identifiers: vX.Y, vX.Y.Z, X.Y.Z. Same rationale — pool has
    # PR-diff version churn; surface the meaningful SDK/API versions.
    "version_id": r"\bv\d+\.\d+(?:\.\d+)?\b|\b\d+\.\d+\.\d+\b",
    # Quantitative claims: dollar amounts, percentages, large-number counts,
    # human-scale numbers with units. Synth (especially Haiku digest) drops
    # these by default — measured 27 -> 1 dropout on R3 v2. Surfacing them in
    # the cit_index makes them survive map-reduce digestion.
    "quant_claim": (
        r"\$[\d,]+(?:\.\d+)?\s*[KMB]?\b"
        r"|\b\d+(?:\.\d+)?\s*(?:K|M|B|MM|bn)\b"
        r"|\b\d{1,3}(?:,\d{3})+\b"
        r"|\b\d+(?:\.\d+)?\s*%\b"
        r"|\b\d+(?:\.\d+)?\s*x\b"
        r"|\b\d+\s*(?:hours?|days?|weeks?|months?|years?|seconds?|ms|GB|TB|PB|GPU|GPUs|cores?|nodes?|workers?|jobs?)\b"
    ),
}


def _load_tenant_patterns() -> dict[str, str]:
    """Load tenant-specific citation patterns from the path in
    ``RLM_TENANT_PATTERNS``. Expected schema: a JSON object whose keys are
    citation kinds (e.g. ``"docs_url"``, ``"team_email"``, ``"namespace_id"``)
    and whose values are regex patterns specific to the tenant (e.g.
    ``"https://manuals.example.com/..."``, ``"@example.com"``).

    Tenant patterns are MERGED on top of the generic ones — they win on key
    collision. Use this to add tenant-specific extractors WITHOUT modifying
    the orchestrator code. The tenant-pattern file is owned by the operator,
    not by the workflow.
    """
    path = os.environ.get("RLM_TENANT_PATTERNS")
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if isinstance(v, str)}
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        logger.warning("Failed to load RLM_TENANT_PATTERNS at %s: %s", path, exc)
    return {}


_CITATION_PATTERNS.update(_load_tenant_patterns())


def _extract_citations(text: str) -> dict[str, list[str]]:
    """Deterministically extract citation identifiers from raw dim findings.

    Pure-regex; LLM-free; lossless. Each kind of identifier is deduped and
    ordered by first appearance so the synthesizer sees them in the same
    order they show up in the research.

    For ``email_generic`` (and any tenant-defined ``team_email`` override),
    the extractor ALSO captures a short context snippet — the line
    containing the email plus the previous line — and renders the entry as
    ``<email> :: <context>``. This gives the synthesizer a narrative anchor
    so it doesn't skip orphan emails. Without context, synthesis drops
    well-attested team emails simply because the bare email has no story.
    """
    import re as _re

    out: dict[str, list[str]] = {}

    def _context_for(match_start: int, match_end: int) -> str:
        # Capture a window of bytes around the match. Normalize JSON escapes
        # and whitespace so we get a phrase regardless of whether the source
        # is prose markdown or JSON-encoded trajectory. The window is wider
        # (200 chars before, 50 after) because the useful context for an
        # email is usually the page title / repo name / yaml key that
        # precedes the `Owner:` line.
        win = text[max(0, match_start - 200):min(len(text), match_end + 50)]
        win = win.replace("\\n", " ").replace("\\t", " ").replace("\\\"", "\"")
        win = _re.sub(r"\s+", " ", win).strip()
        return win[-220:]

    EMAIL_KINDS = {"email_generic", "team_email"}
    for kind, pattern in _CITATION_PATTERNS.items():
        seen: set[str] = set()
        ordered: list[str] = []
        for m in _re.finditer(pattern, text):
            v = m.group(0).rstrip(").,;:!?'\"")
            if not v or v in seen:
                continue
            seen.add(v)
            if kind in EMAIL_KINDS:
                ctx = _context_for(m.start(), m.end())
                # Strip the email itself out of the context to keep it short.
                ctx_short = ctx.replace(v, "").strip(" |,.;:\"\\")[:140]
                ordered.append(f"{v} :: {ctx_short}" if ctx_short else v)
            else:
                ordered.append(v)
        if ordered:
            out[kind] = ordered
    return out


_PER_KIND_CAP: dict[str, int] = {
    # Per-dim caps. With 8 dims, total citations across dims can be up to
    # 8x these. Caps are sized to (a) stay well above the relevant baseline
    # so the report has citation-density headroom and (b) keep the synthesis
    # prompt well under Sonnet's 200K context after we append per-dim
    # citation indices. The sdk_development trajectory alone surfaced 1020
    # citations — without caps a single dim's index can be 36KB and 8 such
    # dims would overflow context.
    "manuals_url": 60,
    "sourcegraph_url": 60,
    "github_repo_url": 60,
    "github_repo_path": 60,
    "google_doc_url": 25,
    "slack_permalink": 30,
    "slack_channel_id": 40,
    "namespace_id": 60,
    "team_email": 60,
    # Dates and versions have very high pool counts (hundreds-thousands of
    # transient timestamps from PR/commit/file metadata). Cap aggressively
    # to keep the index focused — these are noise-heavy categories so
    # smaller caps surface the highest-prominence values.
    "date_specific": 30,
    "version_id": 25,
    # Quant claims (dollar amounts, percentages, counts with units) — pool
    # typically has 30-80 in pure-narrative dims, 100-200 once a COST-ECONOMICS
    # dim runs execute_query. Cap is high because synth uses these as a
    # checklist; downstream the dedup filter removes URL-encoded artifacts.
    "quant_claim": 120,
}


def _format_citation_index(citations: dict[str, list[str]]) -> str:
    """Render a per-dim citation index as compact markdown for the synthesizer."""
    if not citations:
        return "_(no concrete citations extracted)_"
    lines: list[str] = []
    label_map = {
        "manuals_url": "Manuals URLs",
        "sourcegraph_url": "Sourcegraph URLs",
        "github_repo_url": "GitHub URLs",
        "github_repo_path": "GitHub repo paths",
        "google_doc_url": "Google Doc URLs",
        "slack_permalink": "Slack permalinks",
        "slack_channel_id": "Slack channel IDs",
        "namespace_id": "System-tagged identifiers (e.g. namespace IDs)",
        "team_email": "Team contact emails",
        "date_specific": "Specific dates",
        "version_id": "Version identifiers",
        "quant_claim": "Quantitative claims (dollar amounts, percentages, counts)",
    }
    for kind, items in citations.items():
        cap = _PER_KIND_CAP.get(kind, 100)
        kept = items[:cap]
        suffix = f"  _(+{len(items) - cap} more truncated)_" if len(items) > cap else ""
        lines.append(
            f"- {label_map.get(kind, kind)}: "
            + ", ".join(f"`{x}`" for x in kept)
            + suffix
        )
    return "\n".join(lines)


def _build_merged_email_inventory(results: list["DimensionResult"]) -> str:
    """Build a deterministic cross-dim email roster for the synthesis prompt.

    For each unique team-contact email surfaced across all dimensions, pick
    the longest single context snippet (most-informative source) and emit a
    markdown table row. Synth is then instructed to include every row in its
    final inventory table.

    Why this exists: per-dim citation indices are scanned by synth one at a
    time and emails attested in only one dim get dropped as "minor." A pre-
    merged roster makes the union explicit and shrinks the inventory task
    from discovery to enrichment.
    """
    # Map email -> best context (longest non-empty snippet wins).
    # Filter: keep emails that look like team aliases (dashed local-part, or
    # short acronym local-part ≤8 chars). Drops individual-person addresses
    # (e.g. firstnamelastname@) that pollute the inventory. The baseline
    # adopter-team report had 71% dashed and 29% short-acronym team aliases —
    # this heuristic captures both classes while excluding 95%+ of individuals.
    def _looks_like_team_alias(email: str) -> bool:
        local = email.split("@", 1)[0].lower()
        if not local:
            return False
        # Drop noreply / no-reply / auto patterns
        if any(t in local for t in ("noreply", "no-reply", "donotreply", "do-not-reply", "auto-")):
            return False
        # Dashed local-part — team-like in nearly all cases.
        if "-" in local:
            return True
        # Dotted (firstname.lastname pattern) — drop.
        if "." in local:
            return False
        # Short acronym (≤8 chars and not vowel-heavy "firstname"-like).
        if len(local) <= 8:
            return True
        # Compound-noun team aliases like ``mlplatform`` or ``platformsecurity``
        # — no dash, longer than acronym, but recognizable team keywords.
        TEAM_KEYWORDS = (
            "platform", "team", "ops", "eng", "dev", "sre", "infra", "support",
            "oncall", "admin", "security", "service", "tools", "pipeline",
            "delivery", "engineering",
        )
        if any(kw in local for kw in TEAM_KEYWORDS):
            return True
        return False

    best: dict[str, tuple[str, str]] = {}
    for r in results:
        cits = _extract_citations(r.findings + "\n" + r.tool_log)
        for entry in cits.get("email_generic", []) + cits.get("team_email", []):
            if " :: " in entry:
                email, ctx = entry.split(" :: ", 1)
            else:
                email, ctx = entry, ""
            email = email.strip().rstrip(").,;:!?'\"")
            if not email or "@" not in email or not _looks_like_team_alias(email):
                continue
            prev = best.get(email)
            if prev is None or len(ctx) > len(prev[1]):
                best[email] = (r.dimension.name, ctx)
    if not best:
        return "_(no team-contact emails extracted across dimensions)_"
    rows = [
        "| # | Team email | Source dim | Context (truncated) |",
        "|---|------------|------------|---------------------|",
    ]
    for i, email in enumerate(sorted(best), 1):
        dim_name, ctx = best[email]
        ctx_short = (ctx or "Unspecified").replace("|", "\\|")[:160]
        rows.append(f"| {i} | `{email}` | {dim_name} | {ctx_short} |")
    rows.append(
        f"\n**Roster size: {len(best)} distinct emails.** Every row above MUST appear "
        f"in the report's inventory table — coverage below ~85% (~{int(len(best) * 0.85)} "
        f"rows) is a citation-drop failure. If a row has thin context, populate the "
        f"description column with `Unspecified` rather than omitting the row."
    )
    return "\n".join(rows)


def _build_merged_quant_roster(results: list["DimensionResult"]) -> str:
    """Build a cross-dim quantitative-claim roster for the synthesis prompt.

    Same pattern as `_build_merged_email_inventory` but for numbers:
    dollar amounts, percentages, counts, GPU/job/user counts. Pulls from
    each dim's trajectory (where numbers appear in tool-call results
    verbatim) so synth has a single ground-truth roster of every
    quantitative claim the research surfaced.

    Why this exists: benchmarks show pools commonly hold 60-100 distinct
    numbers while final reports cite under 15 — synth drops 80%+ of pool
    numbers because Haiku's per-dim digest paraphrases them away
    ("approximately <N> users" -> "many users"). Pre-rendering the roster
    forces synth to thread these numbers into the report's narrative.
    """
    import re as _re

    # Match quant_claim pattern with surrounding context. Patterns mirror
    # the citation extractor; capture broader for context.
    quant_pat = _re.compile(
        r"(\$[\d,]+(?:\.\d+)?\s*[KMB]?\b"
        r"|\b\d+(?:\.\d+)?\s*(?:K|M|B|MM|bn)\b"
        r"|\b\d{1,3}(?:,\d{3})+\b"
        r"|\b\d+(?:\.\d+)?\s*%\b"
        r"|\b\d+(?:\.\d+)?\s*x\b)"
    )

    # Map number -> best context (longest snippet wins). Context is what
    # makes the number tellable in the final report.
    best: dict[str, tuple[str, str]] = {}
    for r in results:
        text = (r.findings or "") + "\n" + (r.tool_log or "")
        # Normalize JSON-escaped trajectory artifacts.
        text = text.replace("\\n", " ").replace("\\t", " ")
        text = _re.sub(r"\s+", " ", text)
        for m in quant_pat.finditer(text):
            val = m.group(1).rstrip(").,;:!?'\"")
            if not val:
                continue
            # 200 chars before, 100 after — enough to capture the unit
            # ("$<N>M compute budget"), the actor ("<TEAM> under <PERSON>"),
            # and the time qualifier ("<YEAR> budget").
            ctx_start = max(0, m.start() - 200)
            ctx_end = min(len(text), m.end() + 100)
            ctx = text[ctx_start:ctx_end].strip()
            prev = best.get(val)
            if prev is None or len(ctx) > len(prev[1]):
                best[val] = (r.dimension.name, ctx)

    # Filter out trivial/noise numbers — extract artifacts from logs,
    # character counts, URL-encoded values, vmaf scores etc. Real
    # quantitative claims have a unit context word within ±20 chars.
    UNIT_KEYWORDS = (
        # currency
        "$", "USD", "spend", "cost", "budget", "investment", "revenue",
        "saving", "OPEX", "CAPEX", "yr", "/month", "/yr", "annual",
        # counts of people / orgs / things
        "users", "user", "employees", "engineers", "teams", "team", "people",
        "headcount", "advertisers", "viewers", "streams", "subscribers",
        "members", "customers", "models", "projects", "repos", "clusters",
        "namespaces", "workflows", "executions", "deployments", "patents",
        "filings", "seats", "tokens", "experiments", "GPUs", "GPU", "A100",
        "H100", "H200", "B200", "TPU", "cores", "nodes", "workers", "jobs",
        # rates / throughput / scale
        "QPS", "RPS", "TPS", "/sec", "/min", "/hour", "MoM", "YoY",
        "concurrent", "active", "weekly", "daily", "hourly",
        # magnitudes
        "M", "B", "K", "GB", "TB", "PB", "billion", "million", "thousand",
        # percentages naturally include % which is part of the regex
    )
    # Noise context patterns — clear artifact signals from log/JSON dumps.
    NOISE_PATTERNS = (
        "total findings length", "total length", "characters", "%2", "%25",
        "vmaf", "encodedHarmonic", "Total length:", "p17", "p178",
    )

    def _useful(val: str, ctx: str) -> bool:
        ctx_lower = ctx.lower()
        # Drop URL-encoded noise (`%25`, `%2C`, `%2B` — these masquerade as
        # percentages but are URL-encoded atlas queries).
        if "%25" in ctx or "%2c" in ctx_lower or "%2b" in ctx_lower:
            return False
        # Drop if context has clear noise markers.
        if any(p in ctx_lower for p in NOISE_PATTERNS):
            return False
        # Drop slack timestamps (long integer IDs).
        if "ts=" in ctx_lower or "slack" in ctx_lower and val.replace(",", "").isdigit() and len(val.replace(",", "")) >= 6:
            return False
        # Drop very-large bare numbers (8+ digits with no decimal) — usually
        # IDs / vmaf scores / timestamps masquerading as quant claims.
        bare = val.replace(",", "").lstrip("$").rstrip("%").rstrip("xX")
        if bare.replace(".", "").isdigit() and len(bare.replace(".", "")) >= 8:
            return False
        # Now: $ amounts, %, and Nx ratios are self-marking and trustworthy
        # after URL-encoding filter above.
        if val.startswith("$") or val.endswith("%") or val.lower().endswith("x"):
            return True
        # For bare comma-numbers and K/M/B suffixes, require a unit keyword.
        return any(kw.lower() in ctx_lower for kw in UNIT_KEYWORDS)

    filtered = {v: c for v, c in best.items() if _useful(v, c[1])}
    if not filtered:
        return "_(no quantitative claims extracted across dimensions)_"

    rows = [
        "| # | Value | Source dim | Context (truncated) |",
        "|---|-------|------------|---------------------|",
    ]
    # Sort by descending context-length (most-attested numbers first).
    items = sorted(filtered.items(), key=lambda kv: -len(kv[1][1]))
    # Roster cap is a prompt-size guardrail, not a content limit. Render
    # all distinct quant claims by default; truncate only when the
    # roster would balloon the synth prompt. Tunable per tenant via
    # RLM_SYNTH_ROSTER_CAP. The default is set high enough that typical
    # research runs render the full union; the truncation message tells
    # the synthesizer how many got trimmed if budget ran out.
    roster_cap = int(os.environ.get("RLM_SYNTH_ROSTER_CAP", "250"))
    for i, (val, (dim_name, ctx)) in enumerate(items[:roster_cap], 1):
        ctx_short = ctx.replace("|", "\\|")[:180]
        rows.append(f"| {i} | `{val}` | {dim_name} | {ctx_short} |")
    if len(items) > roster_cap:
        rows.append(f"\n_(+{len(items) - roster_cap} additional values truncated for prompt size)_")
    rows.append(
        f"\n**Roster size: {len(filtered)} distinct quantitative claims "
        f"(showing top {min(len(items), roster_cap)} by context-richness).** "
        f"Thread these numbers into the report's narrative — sweeping "
        f"qualitative claims ('many users', 'high cost', 'fast growth') "
        f"signal under-citation. Use the exact value with its context unit "
        f"(`$<N>M <kind> budget`, `<N>K users`, `<N> QPS`) so claims are "
        f"checkable."
    )
    return "\n".join(rows)


def _build_per_dim_quant_table(findings: str, tool_log: str) -> str:
    """Extract a per-dim quantitative-claims table with context.

    Same pattern as ``_build_merged_quant_roster`` but scoped to one dim's
    text. Returned as a verbatim markdown table appended to the dim's
    digest so the synth layer sees the numbers even when Haiku's prose
    digest paraphrased them away. The table format mirrors the global
    roster so the synthesizer can treat all roster rows uniformly.
    """
    import re as _re
    quant_pat = _re.compile(
        r"(\$[\d,]+(?:\.\d+)?\s*[KMB]?\b"
        r"|\b\d+(?:\.\d+)?\s*(?:K|M|B|MM|bn)\b"
        r"|\b\d{1,3}(?:,\d{3})+\b"
        r"|\b\d+(?:\.\d+)?\s*%\b"
        r"|\b\d+(?:\.\d+)?\s*x\b)"
    )
    text = (findings or "") + "\n" + (tool_log or "")
    text = text.replace("\\n", " ").replace("\\t", " ")
    text = _re.sub(r"\s+", " ", text)
    best: dict[str, str] = {}
    for m in quant_pat.finditer(text):
        val = m.group(1).rstrip(").,;:!?'\"")
        if not val:
            continue
        ctx = text[max(0, m.start() - 120):min(len(text), m.end() + 60)].strip()
        if len(ctx) > len(best.get(val, "")):
            best[val] = ctx
    if not best:
        return ""
    rows = ["| Value | Context (truncated) |", "|-------|---------------------|"]
    items = sorted(best.items(), key=lambda kv: -len(kv[1]))
    for val, ctx in items:
        ctx_safe = ctx.replace("|", "\\|")[:160]
        rows.append(f"| `{val}` | {ctx_safe} |")
    return "\n".join(rows)


def _compress_dimension_findings(
    query: str, dim_name: str, findings: str, tool_log: str = ""
) -> str:
    """Map step: compress one dimension's raw findings into a digest.

    Returns a digest string that is the textual summary AND a deterministically
    extracted citation index. Earlier versions tried to make Haiku itself
    preserve every URL and Slack channel — that lost ~40% of identifiers
    because Haiku paraphrases. Now Haiku owns prose summary only; URLs/IDs
    are extracted with regex (lossless) and appended verbatim.

    The citation index is extracted from BOTH ``findings`` (the runner's
    submitted markdown) AND ``tool_log`` (the runner's raw tool-call
    trajectory). The runner writes a narrative summary that drops 60-80%
    of the URLs returned by search_codebase / search_docs / search_slack;
    we recover them by regex-scraping the trajectory. This is load-bearing
    for citation density — without it, the synthesis layer can only cite
    what the runner happened to paste.

    A per-dim quantitative table is ALSO appended verbatim — same
    rationale as the citation index, but for numbers. Haiku's prose
    summary tends to round / paraphrase / drop specific values; the
    regex-extracted table preserves them losslessly so the synthesizer
    sees both the narrative and the raw values.
    """
    prompt = (
        f"Compress this research finding into a dense narrative digest for a downstream synthesizer.\n\n"
        f"ORIGINAL QUERY (overall research goal): {query}\n"
        f"DIMENSION: {dim_name}\n\n"
        f"RAW FINDINGS:\n{findings}\n\n"
        f"PRODUCE a markdown fact digest with these properties:\n"
        f"- 600-1200 words.\n"
        f"- Focus on CLAIMS, RATIONALE, and CONTRADICTIONS. Direct quotes welcome.\n"
        f"- Use compact headers (`### topic`) and dense bullet lists.\n"
        f"- Preserve person names, specific dates, version numbers, exact metric numbers,\n"
        f"  and direct quotes — these don't survive regex extraction.\n"
        f"- You DO NOT need to preserve every URL/chat-channel/repo path verbatim —\n"
        f"  those are captured separately. Refer to them by short tag (e.g. \"per\n"
        f"  the architecture doc\") and the synthesizer will resolve the citation\n"
        f"  from a separate index.\n"
        f"- If the dimension found contradictions, surface them explicitly.\n"
        f"- If the dimension produced ZERO concrete facts, say so in one line — do not pad.\n"
    )
    # Default safety valve (32K) — Haiku will write the length the prompt
    # asks for (~600-1200 words). Earlier 2048 cap truncated digests of
    # citation-rich dims mid-sentence.
    summary = _llm_call(prompt, model=DIGEST_MODEL)
    # Merge citations from findings + tool_log so URLs the runner saw but
    # didn't paste into findings are still surfaced to synthesis.
    citations = _extract_citations(findings + "\n" + tool_log)
    citation_block = _format_citation_index(citations)
    quant_table = _build_per_dim_quant_table(findings, tool_log)
    quant_section = (
        f"\n### Per-dim quantitative claims (regex-extracted from findings + trajectory — preserve in synthesis)\n{quant_table}\n"
        if quant_table else ""
    )
    return (
        f"{summary}\n\n"
        f"### Citation index (extracted from raw findings AND runner tool-call trajectory — use these for inline links)\n"
        f"{citation_block}\n"
        f"{quant_section}"
    )


def synthesize_findings(
    query: str,
    results: list[DimensionResult],
    *,
    use_map_reduce: bool = True,
    # Sonnet 4.6 has 200K context. Raw 8-dim runs typically come in at
    # 80-160K chars; we now ALSO append a per-dim citation index extracted
    # from findings + tool_log (typically 5-10KB per dim), so total prompt
    # size = raw_findings + 8*cit_index + prompt_template ≈ raw + 50K + 6K.
    # Setting the threshold at 130K means raw above that triggers map-reduce
    # (which uses 600-1200-word digests instead of raw findings, keeping
    # the citation indices manageable). Below this, the direct path runs
    # with raw findings + cit_indexes ≈ 130 + 50 + 6 = ~186K, comfortably
    # under context. Don't lower further — the direct path preserves prose
    # nuance that map-reduce drops.
    map_reduce_threshold_chars: int = 130_000,
) -> tuple[str, list[Dimension]]:
    """Phase 3: Synthesize per-dimension findings and detect gaps.

    By default uses the direct path: raw dim findings concatenated into one
    Sonnet call (preserves all source URLs). Falls back to map-reduce
    (Haiku digest per dim → Sonnet integration) only when raw findings
    exceed ``map_reduce_threshold_chars``, since digesting drops citation
    density.
    """
    successful = [r for r in results if r.findings and not r.error]
    raw_total = sum(len(r.findings) for r in successful)

    if use_map_reduce and raw_total > map_reduce_threshold_chars and len(successful) > 1:
        # Quant-dense dims bypass digest. Measure each dim's quantitative
        # density (count of regex-matched numbers per 1K chars of findings).
        # If density > QUANT_DENSITY_THRESHOLD AND total raw chars stays
        # under the synth context budget, pass that dim's raw findings
        # directly to Sonnet. Rationale: benchmark of R1 v5 showed
        # cost-economics dim's findings had 57 distinct quant claims; Haiku
        # digest at 1200 words paraphrases most of them away (synth went
        # from 57 distinct in findings to 13 distinct in final report).
        # Direct path preserves the numbers.
        import re as _re
        _quant_pat = _CITATION_PATTERNS.get("quant_claim", "")
        def _quant_count(text: str) -> int:
            if not text or not _quant_pat:
                return 0
            return len(_re.findall(_quant_pat, text))

        # Bypass policy: the map-reduce digest is lossy for numbers (Haiku
        # paraphrases ~70% of quant claims away regardless of how many a
        # dim surfaces). Any dim that surfaced quant claims at all is a
        # candidate to skip the digest and pass raw findings directly to
        # the Sonnet synthesizer. A character-budget cap (not a per-dim
        # threshold) bounds the total bypass volume — the synth model has
        # finite context, so we prioritize the dims that produced the
        # most quant content and let the budget gate when to stop.
        counts = {
            r.dimension.name: _quant_count((r.findings or "") + "\n" + (r.tool_log or ""))
            for r in successful
        }

        bypass_set: set[str] = set()
        bypass_chars = 0
        # Budget sized to fit ~3-4 average dim findings without pushing
        # the synth prompt past ~280K tokens for the gateway. Tunable
        # via RLM_SYNTH_BYPASS_CHAR_BUDGET if a tenant has a larger
        # context budget.
        BYPASS_CHAR_BUDGET = int(os.environ.get("RLM_SYNTH_BYPASS_CHAR_BUDGET", "80000"))
        for name in sorted(counts.keys(), key=lambda n: -counts[n]):
            if counts[name] <= 0:
                break  # rest of the dims surfaced no quant claims — digest is fine
            r = next(r for r in successful if r.dimension.name == name)
            if bypass_chars + len(r.findings) > BYPASS_CHAR_BUDGET:
                continue
            bypass_set.add(name)
            bypass_chars += len(r.findings)
            logger.info(
                "synthesize: bypassing digest for quant-bearing dim %s "
                "(count=%d, %d chars)",
                name, counts[name], len(r.findings),
            )

        logger.info(
            "synthesize: map-reduce path (%d dims, %d raw chars, %d dims bypass digest)",
            len(successful), raw_total, len(bypass_set),
        )
        digests: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=min(8, len(successful))) as pool:
            futures = {
                pool.submit(
                    _compress_dimension_findings,
                    query, r.dimension.name, r.findings, r.tool_log,
                ): r
                for r in successful if r.dimension.name not in bypass_set
            }
            for fut in as_completed(futures):
                r = futures[fut]
                try:
                    digests[r.dimension.name] = fut.result()
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "compress failed for dim %s: %s — falling back to truncated raw",
                        r.dimension.name, exc,
                    )
                    # Preserve citation index even on Haiku failure — extract
                    # from findings + tool_log so the synthesizer still gets
                    # the full citation list even when prose digest fails.
                    _fallback = r.findings[:8000]
                    _cit = _format_citation_index(_extract_citations(r.findings + "\n" + r.tool_log))
                    digests[r.dimension.name] = (
                        f"{_fallback}\n\n"
                        f"### Citation index (extracted from raw findings + runner tool-call trajectory"
                        f" — use these for inline links)\n"
                        f"{_cit}\n"
                    )
        # Bypass dims get full raw findings + cit_index inline.
        for r in successful:
            if r.dimension.name in bypass_set:
                _cit = _format_citation_index(_extract_citations(r.findings + "\n" + r.tool_log))
                digests[r.dimension.name] = (
                    f"_(passed raw to synth — quant-dense dim, "
                    f"digest skipped to preserve numbers)_\n\n"
                    f"{r.findings}\n\n"
                    f"### Citation index (extracted from raw findings + runner tool-call trajectory"
                    f" — use these for inline links)\n"
                    f"{_cit}\n"
                )
        findings_text = ""
        for r in successful:
            digest = digests.get(r.dimension.name, "")
            findings_text += f"\n\n---\n## Dimension: {r.dimension.name}\n{digest}"
    else:
        logger.info(
            "synthesize: direct path (%d dims, %d raw chars)",
            len(successful), raw_total,
        )
        findings_text = ""
        for r in successful:
            # Even on the direct path, the runner's prose drops most URLs.
            # Append a regex-extracted citation index from findings + tool_log
            # so the synthesizer has every URL/email/ID the runner ever saw.
            cit_index = _format_citation_index(
                _extract_citations(r.findings + "\n" + r.tool_log)
            )
            findings_text += (
                f"\n\n---\n## Dimension: {r.dimension.name}\n"
                f"{r.findings}\n\n"
                f"### Citation index (extracted from raw findings + runner tool-call trajectory"
                f" — use these for inline links)\n"
                f"{cit_index}\n"
            )

    # Cross-dim merged email inventory: forces synth to include every
    # email-attested team in the inventory table. Earlier runs saw synth
    # capture only 70% of pool-overlap emails because each per-dim cit_index
    # was scanned independently and emails appearing in only one dim were
    # skipped as "minor." Pre-rendering the merged list (with deduped
    # contexts) gives the synth a single ground-truth roster — the inventory
    # table is then a fill-in-the-blanks exercise rather than a discovery one.
    merged_inventory = _build_merged_email_inventory(successful)
    merged_quant_roster = _build_merged_quant_roster(successful)

    prompt = f"""You are synthesizing research from {len(results)} parallel research agents investigating different dimensions of one topic.

ORIGINAL QUERY: {query}

FINDINGS FROM EACH DIMENSION:
{findings_text}

MERGED QUANTITATIVE CLAIMS ROSTER (deterministic, cross-dim union of every
dollar amount, percentage, count, and rate the runners surfaced):
{merged_quant_roster}

MERGED EMAIL ROSTER (deterministic, cross-dim union of every team-contact email surfaced):
{merged_inventory}

TASKS:
1. Produce a unified, comprehensive research report that INTEGRATES findings across dimensions
2. Resolve contradictions (note which source is more authoritative)
3. Cross-reference: when dimension A mentions something dimension B explored in detail, merge the information
4. Identify GAPS — important aspects that NO dimension covered well

OUTPUT FORMAT:

Write the synthesized report in markdown (## sections, specific facts with evidence).

Then output a JSON block identifying gaps:
```json
{{"gaps": [
  {{"name": "gap-name", "query": "focused research question to fill this gap", "search_strategy": "how to search for this"}}
]}}
```

If no significant gaps remain, output: {{"gaps": []}}

QUALITY RULES:
- Every claim must trace back to which dimension found it
- Contradictions must be flagged and resolved with reasoning
- INTEGRATE, don't concatenate — the report should be thematic, not dimension-by-dimension
- Preserve specifics: names, IDs, namespaces, team names, dates, versions
- LENGTH IS UNCAPPED. Do not pre-budget word count or "be concise to save space".
  The right length is whatever it takes to thread every load-bearing claim to a
  citation from the dimension findings below. If that takes 8000 words, write
  8000 words. If it takes 15000, write 15000. The pipeline streams output and
  has no max-tokens ceiling that should constrain you. Under-citing to fit an
  imagined budget is the failure mode being defended against.

REQUIRED ENUMERATION TABLES (defends against narrative-selectivity citation drop):
Prose paragraphs naturally limit how many distinct entities you can mention —
the writer's instinct is to introduce 3-7 examples per topic and skip the rest.
For research questions that ask about MANY named entities (teams, repos,
services, namespaces, datasets, integrations, consumers), this drops 60-80% of
the surfaced identifiers and produces an under-cited report.

DEFEAT THIS by emitting **markdown enumeration tables** for entity-heavy
sections. Whenever the research surfaces more than ~10 named entities of the
same kind, the report MUST include a table that lists ALL of them — not a
narrative paragraph that names 5 and trails off with "and others." Table
structure:

For an "adopters/consumers/teams" question, the table should have columns:
| Owner / Team email | Service or repo (linked) | Identifier (namespace/cluster/job ID) | Use case (one line) | Status |

Every distinct team contact email found in any dimension's citation index
(below) MUST appear as a row in this table, even if you have only a one-line
description from the trajectory. Missing the team_email floor (≥40) because
"the narrative didn't fit it" is exactly the failure being defended against —
the table is the floor's enforcement mechanism. If a pool entry has thin
context, write `Unspecified` in the description column rather than dropping
the row.

For consumer-repo questions, similar tables with columns suited to the
question (repo / owner / namespace / language / branch / status, etc.).

Place the enumeration table(s) in a top-level section called "Inventory" or
similar; the rest of the report can then reference rows by name without
losing the long-tail entities.

CITATION RULES (load-bearing — uncited claims read as hallucination):

The dimension findings below contain a high citation density (typically 10-30
URLs/IDs per dimension across internal docs, repo paths, code-search file URLs,
Slack channels, namespace IDs, and team emails). Selecting only ~20% of these
for the final report — which is what happens by default — produces a report
that LOOKS thorough but cites <30% of the source material. That is itself a
quality failure: it strips the report's verifiability and discards the
research's most valuable artifact.

CITATION DENSITY TARGETS (these are HARD FLOORS, not ceilings):
The "### Citation index" section appended to each dimension above contains
a deterministically-extracted list of every URL, email, channel ID, and
namespace identifier that the dimension's research surfaced. The index is
the ground truth — your report's citations must be drawn from it.

You will be evaluated on whether your report cites the following MINIMUM
counts of distinct identifiers (these floors are designed to make you cite
MORE than your default selectivity instinct allows):

- Total inline markdown links `[label](url)`: aim for **≥250**, NOT 50.
  A report with under 130 links has under-cited badly.
- Code-search URLs cited: **≥120 distinct**. Walk every code-search URL
  in every dimension's citation index and inline-link it next to
  whatever implementation claim it backs. If a code-search URL is in the
  index but you didn't cite it, you're under-citing — find a place to
  anchor it (the file at that URL is a load-bearing source, otherwise
  the research wouldn't have surfaced it). Do NOT pre-filter as "noisy"
  references; the dimension already filtered when it surfaced them.
- Repo paths cited: **≥150 distinct `<org>/<repo>` paths**. Every named
  service, library, fork, or PR mentioned must be hyperlinked to its
  repo URL.
- Team contact emails: **≥40 distinct emails**. When ANY team is named —
  even in passing — link the contact email inline as
  `[<team-name>](mailto:<team>@<domain>)`. The citation index may
  include auto-generated mailing-list patterns; INCLUDE THOSE TOO when
  they appear next to a discussion of who reports to whom or which org
  owns what. Do not pre-filter as "auto-generated"; the cit_index already
  includes them because the research surfaced them as actual evidence.
- Chat-channel identifiers / permalinks: **≥10 distinct channels** with
  code-formatted IDs or markdown permalinks.
- Internal-docs URLs: **≥60 distinct doc URLs** in whatever URL form the
  tenant's docs tool returns.
- System-tagged identifiers (any system-specific instance/scope IDs the
  research surfaced — namespace IDs, account numbers, cluster names,
  region codes, job IDs, etc.): **≥40 distinct identifiers** as
  code-formatted strings.
- Specific dates: **≥15 distinct dated events** (YYYY-MM-DD or "Month YYYY"
  form). Every milestone, incident, GA/Beta release, migration, and
  policy decision MUST carry its specific date inline. The dim findings
  + trajectory have hundreds of dates; cite the load-bearing ones rather
  than abstracting to "in early 2025" / "recently."
- Version identifiers: **≥5 distinct version strings** (SDK versions,
  API versions, semver, dependency versions). When the research
  references a named library/SDK without a version, the pool typically
  has the version from a manifest file or release log; thread the
  specific version inline. Cite the load-bearing ones (cited SDKs,
  blocking-version-of bugs, current-deployed versions).
- Quantitative claims: preserve every row of the MERGED QUANTITATIVE
  CLAIMS ROSTER above that has a meaningful context column. The roster
  is the union of every number the dim runners surfaced — treat it as a
  CHECKLIST you must visibly tick off, not a suggestion. **Walk the
  roster row by row** and ensure every entry with a meaningful context
  column appears somewhere in the report VERBATIM (do not round, do not
  paraphrase "5 million" when the source said `5M`). Roster entries
  with thin context can be grouped (e.g. multiple per-workload costs
  under one workload table), but they cannot be dropped. **THE COMMON
  FAILURE MODE: the model emits a fraction of the roster and stops.
  Count your distinct quant claims before submitting; if it's well
  below the roster size, you have not finished — go back and thread in
  more from the roster.** Strong research reports cite as many specific
  numbers as the roster supplies (in the forms `$<N>M <kind> budget`,
  `<N>K users`, `<N> QPS`, `<N> <hardware-class>`, `+<N>% YoY`); reports
  that surface only a small fraction of the roster read as "high level
  / sweeping" and lose credibility. **Number density beats prose
  density** — for entity
  enumeration questions, the prose paragraph "<SUBJECT> runs production
  workloads on <hardware-class>" is much weaker than "<SUBJECT> runs
  production workloads on ~$<N>M of <hardware-class> budget across <N>
  <model-class-A> and <N> <model-class-B>." Always prefer the form with
  specific numbers and units when the roster supplies them. **For
  quant-dense dimensions whose findings are passed RAW (not digested)
  — recognizable by the `_(passed raw to synth — quant-dense dim,
  digest skipped to preserve numbers)_` marker — preserve every dollar
  amount, percentage, and count from those findings in the report,
  organized into per-workload / per-team tables. The raw pass-through
  exists precisely so those numbers reach the final report.**

HOW TO CITE:
- Each dimension's `### Citation index` section is a verbatim, capped list
  of identifiers extracted from BOTH that dimension's raw findings AND its
  runner tool-call trajectory. Use these AGGRESSIVELY. After drafting each
  section of the report, REVIEW the citation indexes for the dimensions
  that informed that section and verify every identifier in those indexes
  has been cited somewhere in the section — if not, you're dropping
  research that the dimension already vetted.
- Inline as `[label](url)`, never as a trailing references section.
- Direct quotes MUST keep their quotation marks AND link the source doc.
- For repo paths and team emails, mailto/repo links are valid: e.g.
  `[`<repo-name>`](https://<repo-host>/<org>/<repo>)`.
- For raw identifiers without a URL (chat-channel IDs, namespace strings,
  bare `<org>/<repo>` paths), use code-formatted strings next to the claim.
- If a claim has no traceable source identifier, mark `(unsourced)` rather
  than presenting it as fact.

THE FAILURE MODE BEING DEFENDED AGAINST: synthesis at this layer naturally
selects "representative" URLs and drops the rest as noise. That selection
is the bug — the dimension layer has already done that filtering by
deciding which URLs to surface in its findings + trajectory. Your job is
to thread EVERY surfaced identifier into the report as a citation, not to
re-curate. UNDER-CITATION IS WORSE THAN OVER-CITATION. A report with 300
inline links is fine; a report with 100 has dropped most of the research."""

    # Use MGP's full 64K output budget for the main synthesis call.
    # The synth prompt grows with quant_count of the underlying dims (the
    # cost-econ dim's content count=1138 caused R1 v10c to truncate
    # mid-sentence at the 32K default cap, dropping the inventory's tail
    # and the entire revise rewrite to ~50% of normal length — measured
    # specific_numbers distinct=8 vs v9's 84 with the same code at 32K).
    # 64K is MGP's upstream cap for Sonnet 4.6 (per _llm_call docstring).
    response = _llm_call(prompt, max_tokens=64000)

    gaps: list[Dimension] = []
    try:
        json_marker = response.rfind("```json")
        if json_marker >= 0:
            json_text = response[json_marker + 7:]
            json_end = json_text.find("```")
            if json_end >= 0:
                json_text = json_text[:json_end]
            gap_data = json.loads(json_text.strip())
            for i, g in enumerate(gap_data.get("gaps", [])):
                if g.get("query"):
                    gaps.append(Dimension(
                        name=g.get("name", f"gap-{i}"),
                        query=g["query"],
                        search_strategy=g.get("search_strategy", ""),
                    ))
    except (json.JSONDecodeError, ValueError):
        logger.warning("Could not parse gaps from synthesis response")

    report = response
    if "```json" in response:
        report = response[:response.rfind("```json")].strip()

    # Sanitize gap dim names too — they go through the same on-disk fan-out as
    # original dims, so they need the same slug + dedupe treatment.
    gaps = _uniqueify_dimension_names(gaps)

    return report, gaps


def _audit_github_repos(synthesis: str, *, hostname: str | None = None) -> dict:
    """Programmatically verify `<hostname>/<org>/<repo>` citations via gh CLI.

    ``hostname`` is read from ``RLM_REPO_AUDIT_HOSTNAME`` if not passed.
    If neither is set, the audit is skipped — the workflow does not know
    what code-repo host is relevant to the tenant. Returns
    ``{"real": [...], "broken": [...], "total": N}`` on success, or
    ``{"skipped": <reason>}`` so callers degrade gracefully.
    """
    if hostname is None:
        hostname = os.environ.get("RLM_REPO_AUDIT_HOSTNAME", "")
    if not hostname:
        return {"skipped": "no RLM_REPO_AUDIT_HOSTNAME configured", "total": 0}
    import re as _re
    repo_pat = _re.compile(
        rf"{_re.escape(hostname)}/([a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+?)(?=[/)\s\"`,]|$)",
        _re.M,
    )
    repos = sorted({m.group(1).rstrip(".,") for m in repo_pat.finditer(synthesis)})
    repos = [r for r in repos if "/" in r and not r.endswith("/blob") and not r.endswith("/tree")]
    if not repos:
        return {"real": [], "broken": [], "total": 0}

    real: list[str] = []
    broken: list[str] = []
    for r in repos:
        try:
            result = subprocess.run(
                ["gh", "api", f"repos/{r}", "--hostname", hostname],
                capture_output=True, text=True, timeout=8,
            )
            if result.returncode == 0:
                real.append(r)
            else:
                broken.append(r)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return {"skipped": "gh CLI unavailable or timed out", "total": len(repos)}
    return {"real": real, "broken": broken, "total": len(repos)}


def verify_claims(query: str, synthesis: str) -> str:
    """Phase 5: Independent verification pass.

    Two passes:
    (a) Programmatic repo-existence audit — if ``RLM_REPO_AUDIT_HOSTNAME`` is
        set, queries the tenant's code-repo host API for each cited
        ``<org>/<repo>`` path and reports real-vs-broken counts. Catches
        synthesis-introduced typos (e.g. dropping a name prefix) and stale
        references that no longer exist. Generic-skeptic LLM verifiers
        can't do this — they pattern-match plausibility on internal-only
        URLs and produce high false-positive "this looks fabricated"
        verdicts. Skipped silently when not configured.
    (b) LLM consistency check — looks for internal contradictions and
        unsourced claims, calibrated for the assumption that the URLs are
        internal-by-design (NOT externally reachable; that's not a
        fabrication signal).
    """
    # (a) Programmatic citation audit (skipped if no hostname configured)
    audit = _audit_github_repos(synthesis)
    audit_block = ""
    if audit.get("total"):
        if "skipped" in audit:
            audit_block = (
                f"## Citation Audit (programmatic)\n\n"
                f"_Skipped: {audit['skipped']}; {audit['total']} repo paths in report._\n"
            )
        else:
            real, broken = audit["real"], audit["broken"]
            pct = 100 * len(real) / audit["total"]
            broken_block = (
                "### Inaccessible / not at this path\n"
                + "\n".join(f"- `{r}` — returns 404 to verifier (private with no access, "
                            f"renamed, or wrong path)" for r in broken)
                if broken else "_(none)_"
            )
            audit_block = (
                f"## Citation Audit (programmatic repo-existence spot-check)\n\n"
                f"**{len(real)}/{audit['total']} ({pct:.0f}%) of cited repo paths "
                f"are real and accessible.**\n\n"
                f"{broken_block}\n\n"
                f"Note: a 404 from the repo-host API means either nonexistent OR "
                f"private with no read access; the conservative read is 'treat as "
                f"broken citation.' This is a structural URL-existence check only; "
                f"it does NOT verify that the file paths within real repos contain "
                f"the claims attributed to them.\n"
            )

    # (b) LLM consistency / contradiction check — tenant-agnostic
    truncated = synthesis if len(synthesis) <= 80_000 else (
        synthesis[:75_000] + "\n\n[…middle truncated…]\n\n" + synthesis[-5_000:]
    )
    prompt = f"""You are reviewing an internal research report.

CONTEXT: This is research about internal infrastructure within an
organization. The report cites internal URLs (code repository, code search,
internal documentation, chat-channel IDs, and team email aliases) that are
EXPECTED to be inaccessible from outside the organization. The runner agents
who produced the source dimensions had authorized access to those systems;
their tool output is the ground truth. Inaccessibility to an external
verifier is NOT a fabrication signal.

ORIGINAL QUERY: {query}

REPORT TO REVIEW:
{truncated}

TASKS — focus on internal consistency and unsourced claims, NOT external
falsifiability:

1. Find any internal contradictions (claim X in section A vs claim ¬X in
   section B). List them with line/section references.
2. Find any specific claims (numbers, dates, names, version IDs) that lack
   an inline citation OR are not traceable to an obvious source. List up to 10.
3. Find any places where the report makes a generic LLM-knowledge claim
   (something a model would say about the topic generally, not something
   specific to the operating organization's research) presented as if it
   were primary research.
4. Note structural problems: contradictions between dimensions, missing
   sections, or claims that compound suspiciously (e.g. exact dollar
   amounts, exact incident durations, exact use-case counts).

DO NOT flag any URL/channel/identifier as unverifiable solely on the grounds
that it is internal-only — that is the expected shape of internal research.
The programmatic audit above handles URL existence.

OUTPUT: A short list of internal-consistency concerns. No 1-5 quality score —
the programmatic audit above is the load-bearing fact-check; you are
supplementary."""

    consistency_block = _llm_call(prompt, model=VERIFY_MODEL)
    return f"{audit_block}\n## Internal Consistency Review\n\n{consistency_block}\n"


def revise_synthesis(query: str, synthesis: str, verification: str) -> str:
    """Phase 5.5: Verifier-driven revision pass.

    Earlier pipeline ran verifier as informational appendix only — meaning
    user-visible contradictions ("EDPR rejected but listed as production",
    scope violations) shipped in the final report despite being flagged.
    This pass folds the verifier's findings back into synth: the model
    receives both the original synthesis and the verifier's notes and
    produces a revised version that resolves contradictions and removes
    scope violations.
    """
    truncated = synthesis if len(synthesis) <= 75_000 else (
        synthesis[:70_000] + "\n\n[…middle truncated…]\n\n" + synthesis[-5_000:]
    )
    prompt = f"""You wrote the research report below. An independent verifier
reviewed it and flagged internal contradictions, scope violations, and
unsourced claims. Produce a REVISED version that addresses every flagged
issue WITHOUT dropping load-bearing citations, inventory rows, or
section structure.

ORIGINAL QUERY: {query}

VERIFIER FINDINGS:
{verification}

ORIGINAL REPORT:
{truncated}

REVISION RULES:
1. For each contradiction the verifier flagged: reconcile the conflicting
   claims. If both are sourced, present both with explicit reasoning. If
   one is wrong, drop it and note the resolution.
2. For each scope violation: remove the entry from the inventory and any
   detailed profile. If the entry is borderline, mark it explicitly as
   `(out of scope — listed for completeness only)`.
3. For each unsourced quantitative claim or specific number: **PRESERVE
   the number, weaken the claim's language**. Add "approximately",
   "reportedly", "per uncited internal source", or "(unsourced — flagged
   for follow-up)" to acknowledge the gap WITHOUT dropping the number.
   Specific numbers are the highest-value research artifact; dropping
   them on the grounds of weak sourcing strips the report of its
   load-bearing claims. **Default action on unsourced numbers is to KEEP
   them with weakened language, never DROP them.**
4. For each unsourced non-numerical claim (existence claims, status
   claims, version claims): either add an inline citation from the
   citation index, or weaken with "reportedly" / "per uncited internal
   source." Same principle as rule 3 — prefer weakening over dropping.
5. DO NOT shrink the inventory table beyond removing scope violations.
   Every team-alias email that appears in the original inventory MUST
   stay in the revised inventory (unless the verifier flagged it
   specifically as a scope violation).
6. DO NOT drop specific numbers, dollar amounts, percentages, counts,
   dates, or version IDs from the report. If the verifier said a number
   was unsourced, KEEP THE NUMBER and add a weakening qualifier — do not
   replace `$<N>M` with "significant cost" or "$<N>" with "many".
7. DO NOT trim the report's overall length. The revised report should be
   at least as long as the original.
8. Preserve all internal structural sections (Overview, Inventory,
   Detailed Profiles, Namespace Enumeration, etc.).

Output ONLY the revised report markdown — no explanatory preamble, no
listing of what you changed. The revised report goes straight to users."""
    # Revise must be able to write at least as much as synthesis did
    # (rule 7: "DO NOT trim the report's overall length"). Match the
    # synth call's 64K budget.
    revised = _llm_call(prompt, model=MAIN_MODEL, max_tokens=64000)
    return revised


def _load_existing_dim_results(run_dir: str) -> list[DimensionResult]:
    """Resume helper: rebuild DimensionResult list from on-disk dim findings.

    Reads ``<run_dir>/dimensions.json`` for the original dimension definitions,
    plus ANY ``<run_dir>/gap-round-N/dimensions/<name>/`` subdirs from prior
    gap-fill rounds. Each ``findings.md`` + ``rlm_meta.json`` pair becomes a
    ``DimensionResult``. Returns empty list if no dims exist on disk.

    Loading gap-round results is load-bearing for resume correctness — without
    it, re-running synthesis after a crash silently drops the (often most
    targeted) findings from the gap-fill rounds.
    """
    out: list[DimensionResult] = []
    seen_names: set[str] = set()

    def _add_dir(dim: Dimension, base_dir: Path) -> None:
        findings_path = base_dir / "findings.md"
        meta_path = base_dir / "rlm_meta.json"
        traj_path = base_dir / "trajectory.json"
        if not findings_path.exists():
            return
        findings = findings_path.read_text(encoding="utf-8")
        tool_log = traj_path.read_text(encoding="utf-8") if traj_path.exists() else ""
        iterations = 0
        elapsed = 0.0
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                iterations = int(meta.get("iterations", 0) or 0)
                elapsed = float(meta.get("elapsed_seconds", 0) or 0)
            except (json.JSONDecodeError, OSError, ValueError, TypeError):
                pass
        out.append(DimensionResult(
            dimension=dim,
            findings=findings,
            iterations=iterations,
            elapsed_seconds=elapsed,
            tool_log=tool_log,
        ))
        seen_names.add(dim.name)

    # 1. Load originally-decomposed dimensions.
    dims_path = Path(run_dir) / "dimensions.json"
    if dims_path.exists():
        try:
            dims_raw = json.loads(dims_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            dims_raw = []
        for d in dims_raw:
            name = d.get("name")
            if not name:
                continue
            dim = Dimension(
                name=name,
                query=d.get("query", ""),
                search_strategy=d.get("strategy", d.get("search_strategy", "")),
            )
            _add_dir(dim, Path(run_dir) / "dimensions" / name)

    # 2. Load any gap-round-N results that have findings on disk. The dim
    # name is read from the directory; query/strategy aren't persisted so we
    # synthesize a placeholder — synthesis only needs the findings + name.
    for gap_dir in sorted(Path(run_dir).glob("gap-round-*")):
        gap_dims_dir = gap_dir / "dimensions"
        if not gap_dims_dir.is_dir():
            continue
        for dim_dir in sorted(gap_dims_dir.iterdir()):
            if not dim_dir.is_dir():
                continue
            name = dim_dir.name
            if name in seen_names:
                # avoid double-counting if the same name appears in multiple rounds
                name = f"{name} (in {gap_dir.name})"
            dim = Dimension(
                name=name,
                query=f"gap-fill from {gap_dir.name}: {dim_dir.name}",
                search_strategy="",
            )
            _add_dir(dim, dim_dir)

    return out


def run_deep_research(
    query: str,
    *,
    run_dir: str = "/tmp/rlm-deep-research",
    max_dimensions: int = 14,
    iters_per_dimension: int = 100,
    llm_calls_per_dimension: int = 200,
    max_gap_rounds: int = 3,
    max_workers: int = 6,
    python_path: str | None = None,
    verbose: bool = False,
    resume: bool = False,
    on_phase: Callable[[str, str], None] | None = None,
) -> OrchestratorResult:
    """Run multi-RLM fan-out deep research.

    Default iteration budgets are high so termination is convergence-driven
    (RLM submits findings when satisfied) rather than budget-driven.

    When ``resume=True`` and the run_dir already contains successful dim
    findings, the fan-out phase is skipped and synthesis runs against those.
    Lets a single network blip during synthesis not throw away ~30 minutes
    of upstream RLM work.
    """
    if not MGP_BASE:
        raise ValueError("RLM_API_BASE environment variable is required.")

    Path(run_dir).mkdir(parents=True, exist_ok=True)
    phase_timings: dict[str, float] = {}
    errors: list[str] = []
    total_start = time.time()

    def phase(name: str, detail: str = "") -> None:
        logger.info("Phase: %s %s", name, detail)
        if on_phase:
            on_phase(name, detail)

    # --- Phase 1: Decompose (or load from resume state) ---
    # Resume strategy: load EVERY dim definition from dimensions.json (the
    # original plan), then for each one check whether an actual findings.md
    # exists on disk. Dims with findings are kept as-is; dims without
    # findings get re-fanned-out below. The earlier behavior — short-circuit
    # the entire fan-out the moment ANY dim findings exist — silently dropped
    # missing/failed dims from the original plan and surfaced an under-covered
    # report with no warning.
    resumed_with_findings: list[DimensionResult] = []
    dimensions_to_run: list[Dimension] = []  # dims that need fresh fan-out
    dimensions: list[Dimension] = []
    if resume:
        loaded = _load_existing_dim_results(run_dir)
        resumed_with_findings = [r for r in loaded if r.findings]
        # Identify dim NAMES that came from the original plan (not gap-rounds)
        # by matching against dimensions.json.
        dims_path_existing = Path(run_dir) / "dimensions.json"
        original_plan: list[Dimension] = []
        if dims_path_existing.exists():
            try:
                raw = json.loads(dims_path_existing.read_text(encoding="utf-8"))
                original_plan = [
                    Dimension(
                        name=d.get("name", f"dim-{i}"),
                        query=d.get("query", ""),
                        search_strategy=d.get("strategy", d.get("search_strategy", "")),
                    )
                    for i, d in enumerate(raw)
                ]
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("resume: dimensions.json unreadable (%s); proceeding with whatever loaded", exc)
        loaded_names = {r.dimension.name for r in resumed_with_findings}
        dimensions_to_run = [d for d in original_plan if d.name not in loaded_names]
        dimensions = original_plan or [r.dimension for r in resumed_with_findings]
        phase(
            "resume",
            f"loaded {len(resumed_with_findings)} existing findings; "
            f"{len(dimensions_to_run)} original dim(s) still need fan-out",
        )
        if not original_plan and not resumed_with_findings:
            phase("resume", "no plan or findings on disk — falling through to fresh decompose")

    if not resume or (resume and not dimensions and not resumed_with_findings):
        phase("decompose", "breaking query into orthogonal dimensions")
        t0 = time.time()
        dimensions = decompose_query(query, max_dimensions)
        # Sanitize + dedupe names so they're safe to use as filesystem keys
        # and so concurrent dim subprocesses cannot stomp each other.
        dimensions = _uniqueify_dimension_names(dimensions)
        phase_timings["decompose"] = time.time() - t0

        dims_path = Path(run_dir) / "dimensions.json"
        dims_path.write_text(json.dumps(
            [{"name": d.name, "query": d.query, "strategy": d.search_strategy} for d in dimensions],
            indent=2,
        ), encoding="utf-8")
        phase("decompose", f"-> {len(dimensions)} dimensions: {[d.name for d in dimensions]}")
        dimensions_to_run = dimensions

    # --- Phase 2: Parallel fan-out (run only the dims missing findings) ---
    if resume and not dimensions_to_run:
        # All original dims have findings on disk — no fresh fan-out needed.
        dim_results = resumed_with_findings
        phase_timings["fan-out"] = 0.0
        phase("fan-out", "skipped: all original dimensions already have findings")
    else:
        phase(
            "fan-out",
            f"{len(dimensions_to_run)} parallel RLMs, {iters_per_dimension} iters each"
            + (f" (plus {len(resumed_with_findings)} resumed)" if resumed_with_findings else ""),
        )
        t0 = time.time()

        completed_count = 0

        def _on_dim_complete(result: DimensionResult) -> None:
            nonlocal completed_count
            completed_count += 1
            phase("fan-out", f"{completed_count}/{len(dimensions_to_run)} dimensions complete")

        fresh_results = run_parallel_dimensions(
            dimensions_to_run, run_dir,
            max_iterations=iters_per_dimension,
            max_llm_calls=llm_calls_per_dimension,
            max_workers=max_workers,
            python_path=python_path,
            on_dimension_complete=_on_dim_complete,
        )
        # Combine fresh fan-out with any resumed dims so synthesis sees the full set.
        dim_results = resumed_with_findings + fresh_results
        phase_timings["fan-out"] = time.time() - t0

    for r in dim_results:
        if r.error:
            errors.append(f"dimension '{r.dimension.name}': {r.error}")

    successful = [r for r in dim_results if r.findings and not r.error]
    phase("fan-out", f"-> {len(successful)}/{len(dim_results)} dimensions produced findings")

    # --- Phase 3: Synthesize ---
    phase("synthesize", "merging findings across dimensions")
    t0 = time.time()
    synthesis, gaps = synthesize_findings(query, dim_results)
    phase_timings["synthesize"] = time.time() - t0

    synth_path = Path(run_dir) / "synthesis.md"
    synth_path.write_text(f"# Synthesis: {query}\n\n{synthesis}\n", encoding="utf-8")

    # --- Phase 4: Gap-filling ---
    all_gap_results: list[DimensionResult] = []
    for gap_round in range(max_gap_rounds):
        if not gaps:
            break

        phase("gap-fill", f"round {gap_round + 1}: {len(gaps)} gaps identified")
        t0 = time.time()
        gap_dir = f"{run_dir}/gap-round-{gap_round + 1}"
        gap_results = run_parallel_dimensions(
            gaps, gap_dir,
            max_iterations=iters_per_dimension,
            max_llm_calls=llm_calls_per_dimension,
            max_workers=max_workers,
            python_path=python_path,
        )
        phase_timings[f"gap-fill-{gap_round + 1}"] = time.time() - t0
        all_gap_results.extend(gap_results)

        for r in gap_results:
            if r.error:
                errors.append(f"gap '{r.dimension.name}': {r.error}")

        phase("re-synthesize", f"integrating gap-fill round {gap_round + 1}")
        t0 = time.time()
        synthesis, gaps = synthesize_findings(query, dim_results + all_gap_results)
        phase_timings[f"re-synthesize-{gap_round + 1}"] = time.time() - t0
        synth_path.write_text(f"# Synthesis: {query}\n\n{synthesis}\n", encoding="utf-8")

    # --- Phase 5: Verify ---
    phase("verify", "independent claim verification")
    t0 = time.time()
    verification = verify_claims(query, synthesis)
    phase_timings["verify"] = time.time() - t0

    verify_path = Path(run_dir) / "verification.md"
    verify_path.write_text(f"# Verification: {query}\n\n{verification}\n", encoding="utf-8")

    # --- Phase 5.5: Verifier-driven revision ---
    # Run revision when the verifier reports any contradictions or scope
    # violations. The trigger uses a coarse keyword heuristic on the
    # verifier prose (gpt-5.4) rather than parsing structured output —
    # we want false-positive revisions to be cheap (one extra Sonnet call)
    # rather than false-negative ships with contradictions.
    _contradiction_signals = (
        "contradiction", "contradict", "internal-consistency", "scope violation",
        "out of scope", "directly conflict", "inconsistency", "mislabel",
        "unsourced", "lacking inline citation",
    )
    _verif_lower = verification.lower()
    if any(s in _verif_lower for s in _contradiction_signals):
        phase("revise", "verifier-driven synthesis revision")
        t0 = time.time()
        try:
            revised = revise_synthesis(query, synthesis, verification)
            phase_timings["revise"] = time.time() - t0
            if revised and len(revised) >= 0.5 * len(synthesis):
                synthesis = revised
                synth_path.write_text(
                    f"# Synthesis: {query}\n\n{synthesis}\n", encoding="utf-8"
                )
            else:
                logger.warning(
                    "revise produced suspiciously short output (%d vs orig %d); "
                    "keeping original synthesis",
                    len(revised) if revised else 0, len(synthesis),
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("revise failed: %s — keeping original synthesis", exc)

    # --- Phase 6: Final report ---
    phase("report", "assembling final report")

    failed_dims = [r for r in dim_results + all_gap_results if r.error]
    if failed_dims:
        _failed_lines = "\n".join(
            f"> - **{r.dimension.name}**: {r.error}" for r in failed_dims
        )
        _failure_block = (
            f"\n\n> **Warning: {len(failed_dims)} dimension(s) failed and were excluded from this synthesis.**\n"
            f"> The report below is based on partial coverage only.\n"
            f">\n"
            f"{_failed_lines}\n"
        )
    else:
        _failure_block = ""

    final_report = (
        f"# {query}\n\n"
        f"{synthesis}{_failure_block}\n\n"
        f"---\n\n"
        f"## Appendix: Verification Notes\n\n{verification}\n"
    )

    report_path = Path(run_dir) / "report.md"
    report_path.write_text(final_report, encoding="utf-8")

    total_iterations = sum(r.iterations for r in dim_results + all_gap_results)
    total_elapsed = time.time() - total_start

    meta = {
        "query": query,
        "total_elapsed_seconds": round(total_elapsed, 2),
        "total_iterations": total_iterations,
        "dimensions": len(dimensions),
        "dimension_names": [d.name for d in dimensions],
        "gap_rounds": len([k for k in phase_timings if k.startswith("gap-fill")]),
        "phase_timings": {k: round(v, 2) for k, v in phase_timings.items()},
        "dimension_stats": [
            {
                "name": r.dimension.name,
                "iterations": r.iterations,
                "elapsed_s": round(r.elapsed_seconds, 2),
                "findings_chars": len(r.findings),
                "error": r.error,
            }
            for r in dim_results + all_gap_results
        ],
        "errors": errors,
    }
    meta_path = Path(run_dir) / "orchestrator_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    phase("complete", f"{total_iterations} total iterations, {total_elapsed:.0f}s elapsed")

    return OrchestratorResult(
        query=query,
        dimensions=dimensions,
        dimension_results=dim_results,
        gap_results=all_gap_results,
        synthesis=synthesis,
        verification=verification,
        final_report=final_report,
        total_elapsed_seconds=total_elapsed,
        total_iterations=total_iterations,
        phase_timings=phase_timings,
        errors=errors,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-RLM Deep Research Orchestrator")
    parser.add_argument("--query", "-q", required=True)
    parser.add_argument("--run-dir", "-d", default="/tmp/rlm-deep-research")
    parser.add_argument("--max-dimensions", type=int, default=12)
    parser.add_argument("--iters-per-dimension", type=int, default=100)
    parser.add_argument("--llm-calls-per-dimension", type=int, default=200)
    parser.add_argument("--max-gap-rounds", type=int, default=3)
    parser.add_argument("--max-workers", type=int, default=6)
    parser.add_argument("--python-path", default=None)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument(
        "--resume", action="store_true",
        help="Skip fan-out if dim findings already exist in run-dir",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    def on_phase(name: str, detail: str) -> None:
        elapsed = time.time() - _start
        print(f"[{elapsed:6.0f}s] [{name}] {detail}", flush=True)

    _start = time.time()

    result = run_deep_research(
        args.query,
        run_dir=args.run_dir,
        max_dimensions=args.max_dimensions,
        iters_per_dimension=args.iters_per_dimension,
        llm_calls_per_dimension=args.llm_calls_per_dimension,
        max_gap_rounds=args.max_gap_rounds,
        max_workers=args.max_workers,
        python_path=args.python_path,
        verbose=args.verbose,
        resume=args.resume,
        on_phase=on_phase,
    )

    # Exit status is keyed off whether we produced a usable final report — NOT
    # whether any individual dimension failed. The fan-out path is intentionally
    # fault-tolerant: a 1-of-8 timeout still yields a complete synthesis from
    # the other 7. Treating any per-dim error as a process-level failure causes
    # downstream consumers (sagaflow run_shell activity, Temporal workflow) to
    # discard a perfectly good report.md because exit_code != 0.
    report_path = Path(args.run_dir) / "report.md"
    report_ok = report_path.exists() and report_path.stat().st_size > 0
    status = "ok" if report_ok else ("error" if result.errors else "no_report")
    print(json.dumps({
        "status": status,
        "report_path": str(report_path),
        "report_written": report_ok,
        "total_iterations": result.total_iterations,
        "total_elapsed_seconds": round(result.total_elapsed_seconds, 2),
        "dimensions": len(result.dimensions),
        "gap_rounds": len(result.gap_results),
        "dimension_errors": result.errors[:5],
        "phase_timings": {k: round(v, 2) for k, v in result.phase_timings.items()},
    }))

    sys.exit(0 if report_ok else 1)


if __name__ == "__main__":
    main()
