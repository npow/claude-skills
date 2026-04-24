#!/usr/bin/env python3
"""Deterministic aggregator for deep-debug-ensemble-v1 hypothesis judge panels.

Reads up to 3 per-judge output files for a single batch and produces one
aggregated plausibility verdict per hypothesis plus a human-readable summary.

Adapted from deep-qa-ensemble-v1's aggregator for the deep-debug protocol:
  - Label set: leading | plausible | disputed | rejected | deferred  (NOT severity)
  - Field names: HYP_ID, PLAUSIBILITY, FALSIFIABLE, EVIDENCE_TIER, PASS2_VERDICT
  - Input files include STRUCTURED_OUTPUT_START/END markers
  - Tie-break fail-safe: `disputed` (flag for scrutiny, NOT max-rank) — unlike
    severity where fail-up = critical makes sense, for plausibility "leading on tie"
    would promote unvetted hypotheses to Phase 4 probe generation.

Usage:
    aggregate_ensemble_judges_debug.py \\
        --batch-id batch_1_1 \\
        --judge-file judge_claude=/path/to/judge_claude.md \\
        --judge-file judge_openai=/path/to/judge_openai.md \\
        --judge-file judge_gemini=/path/to/judge_gemini.md \\
        --out-json /path/to/aggregated.json \\
        --out-summary-md /path/to/aggregated.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

PLAUSIBILITY_RANK = {
    "rejected": 0,
    "deferred": 1,
    "disputed": 2,
    "plausible": 3,
    "leading": 4,
}

JUDGE_MODEL_MAP = {
    "judge_claude": "sonnet-4.6",
    "judge_openai": "gpt-5.4",
    "judge_gemini": "gemini-2.5-pro",
}
JUDGE_PROVIDER_MAP = {
    "judge_claude": "anthropic",
    "judge_openai": "pal-custom",
    "judge_gemini": "pal-custom",
}
TIE_BREAK_PLAUSIBILITY = "disputed"


@dataclass
class JudgeVerdict:
    judge_id: str
    model: str
    provider: str
    plausibility: str | None = None
    falsifiable: bool | None = None
    evidence_tier: int | None = None
    pass2_verdict: str | None = None
    parse_status: str = "ok"


@dataclass
class AggregatedVerdict:
    hyp_id: str
    plausibility: str | None = None
    evidence_tier: int | None = None
    all_falsifiable: bool | None = None
    pass2_majority: str | None = None
    agreement_rate: float = 0.0
    per_model: list[dict] = field(default_factory=list)
    aggregation_status: str = "completed"
    notes: list[str] = field(default_factory=list)


def parse_judge_file(path: Path, judge_id: str) -> dict[str, JudgeVerdict]:
    model = JUDGE_MODEL_MAP.get(judge_id, judge_id)
    provider = JUDGE_PROVIDER_MAP.get(judge_id, "unknown")
    if not path.exists():
        return {"_file_status": JudgeVerdict(judge_id=judge_id, model=model, provider=provider, parse_status="missing_file")}
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return {"_file_status": JudgeVerdict(judge_id=judge_id, model=model, provider=provider, parse_status="missing_file")}

    m = re.search(r"STRUCTURED_OUTPUT_START\s*\n(.+?)\nSTRUCTURED_OUTPUT_END", text, flags=re.DOTALL)
    structured = m.group(1) if m else text

    blocks = [b.strip() for b in re.split(r"^-{3,}\s*$", structured, flags=re.MULTILINE) if b.strip()]
    out: dict[str, JudgeVerdict] = {}
    for block in blocks:
        hyp_id = _extract(block, "HYP_ID")
        if not hyp_id:
            continue
        plaus = _norm(_extract(block, "PLAUSIBILITY"), PLAUSIBILITY_RANK.keys())
        fals_raw = _extract(block, "FALSIFIABLE")
        falsifiable = None
        if fals_raw:
            f = fals_raw.strip().lower()
            if f in ("true", "yes", "y"):
                falsifiable = True
            elif f in ("false", "no", "n"):
                falsifiable = False
        et_raw = _extract(block, "EVIDENCE_TIER")
        et = None
        if et_raw:
            try:
                et = int(et_raw.strip().split()[0])
            except (ValueError, IndexError):
                pass
        p2_raw = _extract(block, "PASS2_VERDICT")
        p2 = None
        if p2_raw:
            p = p2_raw.strip().upper().split()[0].rstrip(".,;:")
            if p in ("CONFIRM", "UPGRADE", "DOWNGRADE"):
                p2 = p

        status = "ok" if plaus else "unparseable"
        out[hyp_id] = JudgeVerdict(
            judge_id=judge_id, model=model, provider=provider,
            plausibility=plaus or "disputed",
            falsifiable=falsifiable, evidence_tier=et, pass2_verdict=p2,
            parse_status=status,
        )

    return out or {"_file_status": JudgeVerdict(judge_id=judge_id, model=model, provider=provider, parse_status="no_matching_hyp")}


def _extract(block: str, field_name: str) -> str | None:
    m = re.search(rf"^\s*{re.escape(field_name)}\s*:\s*(.+?)\s*$", block, flags=re.MULTILINE)
    return m.group(1).strip() if m else None


def _norm(s: str | None, allowed) -> str | None:
    if not s:
        return None
    t = s.strip().lower().split()[0].rstrip(".,;:")
    return t if t in allowed else None


def aggregate_hypothesis(hyp_id: str, verdicts: list[JudgeVerdict]) -> AggregatedVerdict:
    parseable = [v for v in verdicts if v.parse_status in ("ok", "unparseable") and v.plausibility]
    total = 3
    n = len(parseable)
    result = AggregatedVerdict(hyp_id=hyp_id)

    for v in verdicts:
        result.per_model.append({
            "judge_id": v.judge_id, "model": v.model, "provider": v.provider,
            "plausibility": v.plausibility, "falsifiable": v.falsifiable,
            "evidence_tier": v.evidence_tier, "pass2_verdict": v.pass2_verdict,
            "parse_status": v.parse_status,
        })

    if n == 0:
        result.aggregation_status = "failed"
        result.plausibility = "disputed"
        result.notes.append("all_judges_failed")
        return result

    counts: dict[str, int] = {}
    for v in parseable:
        counts[v.plausibility] = counts.get(v.plausibility, 0) + 1
    max_c = max(counts.values())
    winners = [p for p, c in counts.items() if c == max_c]
    if len(winners) == 1:
        result.plausibility = winners[0]
        result.agreement_rate = round(counts[result.plausibility] / n, 3)
    else:
        result.plausibility = TIE_BREAK_PLAUSIBILITY
        result.notes.append(f"plausibility_tie_to_disputed: winners={winners}")
        result.agreement_rate = 0.0

    tiers = [v.evidence_tier for v in parseable if v.evidence_tier is not None]
    if tiers:
        result.evidence_tier = min(tiers)

    fals = [v.falsifiable for v in parseable if v.falsifiable is not None]
    if fals:
        result.all_falsifiable = all(fals)

    p2s = [v.pass2_verdict for v in parseable if v.pass2_verdict]
    if p2s:
        pc: dict[str, int] = {}
        for p in p2s:
            pc[p] = pc.get(p, 0) + 1
        mc = max(pc.values())
        p2w = [p for p, c in pc.items() if c == mc]
        if len(p2w) == 1:
            result.pass2_majority = p2w[0]
        else:
            result.pass2_majority = "CONFIRM"
            result.notes.append(f"pass2_tie_to_confirm: {p2w}")

    if n < total:
        result.aggregation_status = "partial"
        result.notes.append(f"partial_panel_{n}_of_{total}")
    return result


def write_summary_md(path: Path, batch_id: str, aggregated: list[AggregatedVerdict]) -> None:
    lines = [f"# Ensemble Hypothesis-Judge Aggregation — batch {batch_id}", "",
             f"**Hypotheses aggregated:** {len(aggregated)}", ""]
    for agg in aggregated:
        lines.append(f"## {agg.hyp_id}")
        lines.append("")
        extras = []
        if agg.evidence_tier is not None:
            extras.append(f"evidence_tier=`{agg.evidence_tier}`")
        if agg.all_falsifiable is not None:
            extras.append(f"all_falsifiable=`{agg.all_falsifiable}`")
        if agg.pass2_majority is not None:
            extras.append(f"pass2_majority=`{agg.pass2_majority}`")
        summary = (f"**Aggregated:** plausibility=`{agg.plausibility}`  "
                   f"agreement_rate=`{agg.agreement_rate}`  "
                   f"status=`{agg.aggregation_status}`")
        if extras:
            summary += "  " + "  ".join(extras)
        lines.append(summary)
        lines.append("")
        lines.append("| Judge | Model | Plausibility | Tier | Falsifiable | Pass2 | Parse |")
        lines.append("|---|---|---|---|---|---|---|")
        for pm in agg.per_model:
            lines.append(
                f"| {pm['judge_id']} | {pm['model']} | {pm['plausibility'] or '—'} | "
                f"{pm['evidence_tier'] if pm['evidence_tier'] is not None else '—'} | "
                f"{pm['falsifiable'] if pm['falsifiable'] is not None else '—'} | "
                f"{pm['pass2_verdict'] or '—'} | {pm['parse_status']} |"
            )
        lines.append("")
        if agg.notes:
            for note in agg.notes:
                lines.append(f"- {note}")
            lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-id", required=True)
    ap.add_argument("--judge-file", action="append", default=[])
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--out-summary-md", type=Path, required=True)
    args = ap.parse_args()

    judge_files: dict[str, Path] = {}
    for spec in args.judge_file:
        if "=" not in spec:
            print(f"bad --judge-file: {spec}", file=sys.stderr)
            return 2
        jid, p = spec.split("=", 1)
        judge_files[jid] = Path(p)
    if not judge_files:
        return 2

    per_judge = {jid: parse_judge_file(p, jid) for jid, p in judge_files.items()}
    hyp_ids: set[str] = set()
    for parsed in per_judge.values():
        for k in parsed:
            if k != "_file_status":
                hyp_ids.add(k)
    if not hyp_ids:
        print("no HYP_ID parsed from any file", file=sys.stderr)
        return 3

    aggregated: list[AggregatedVerdict] = []
    for hyp_id in sorted(hyp_ids):
        verdicts = []
        for jid in sorted(judge_files.keys()):
            parsed = per_judge[jid]
            if hyp_id in parsed:
                verdicts.append(parsed[hyp_id])
            elif "_file_status" in parsed:
                verdicts.append(parsed["_file_status"])
            else:
                verdicts.append(JudgeVerdict(
                    judge_id=jid,
                    model=JUDGE_MODEL_MAP.get(jid, jid),
                    provider=JUDGE_PROVIDER_MAP.get(jid, "unknown"),
                    parse_status="no_matching_hyp",
                ))
        aggregated.append(aggregate_hypothesis(hyp_id, verdicts))

    out = {
        "batch_id": args.batch_id,
        "n_hypotheses": len(aggregated),
        "hypotheses": {a.hyp_id: asdict(a) for a in aggregated},
        "global_agreement_rate": round(sum(a.agreement_rate for a in aggregated) / len(aggregated), 3),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, indent=2), encoding="utf-8")
    args.out_summary_md.parent.mkdir(parents=True, exist_ok=True)
    write_summary_md(args.out_summary_md, args.batch_id, aggregated)

    return 0


if __name__ == "__main__":
    sys.exit(main())
