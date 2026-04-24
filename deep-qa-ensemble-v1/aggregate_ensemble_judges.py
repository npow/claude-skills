#!/usr/bin/env python3
"""Deterministic aggregator for deep-qa-ensemble-v1 judge panels.

Reads up to 3 per-judge output files for a single batch and produces
one aggregated verdict per defect plus a human-readable summary.

Usage:
    aggregate_ensemble_judges.py \\
        --batch-id batch_1_1 \\
        --pass 1 \\
        --judge-file judge_claude=/path/to/pass1_judge_claude.md \\
        --judge-file judge_openai=/path/to/pass1_judge_openai.md \\
        --judge-file judge_gemini=/path/to/pass1_judge_gemini.md \\
        [--prior-pass1-json /path/to/prior/pass1-aggregated.json] \\
        --out-json /path/to/pass1-aggregated.json \\
        --out-summary-md /path/to/pass1_aggregated.md

Exit codes: 0 success (even partial/failed), 2 bad arguments, 3 no defects
parsed from any file. Stderr gets one line per warning/error.

Aggregation rule (spec'd in SKILL.md "Ensemble Judge Panel"):
  severity: majority vote (>=2 agree). 3-way split -> max (critical > major > minor).
            partial panel of 2: require agreement, else max.
            partial panel of 1: use it, flag partial.
            0 parseable: record as failed, carry prior-severity hint if given.
  confidence: max across judges matching aggregated severity.
  calibration (pass 2): vote + upgrade on 3-way split.
  calibration forced-consistency: if aggregated_pass2_severity > aggregated_pass1_severity
                                  -> 'upgrade'; if less -> 'downgrade'; if equal -> 'confirm'.
  rationale: '[judge_id/model] ...' joined with ' | '.
  agreement_rate: n_matching_majority / n_parseable.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

SEVERITY_RANK = {"minor": 0, "major": 1, "critical": 2}
SEVERITY_NAMES = {v: k for k, v in SEVERITY_RANK.items()}
CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}
CONFIDENCE_NAMES = {v: k for k, v in CONFIDENCE_RANK.items()}

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


@dataclass
class JudgeVerdict:
    judge_id: str
    model: str
    provider: str
    severity: str | None = None  # "critical" | "major" | "minor" | None if missing/unparseable
    confidence: str | None = None
    calibration: str | None = None  # pass-2 only
    rationale: str = ""
    parse_status: str = "ok"  # "ok" | "missing_file" | "unparseable" | "no_matching_defect"


@dataclass
class AggregatedVerdict:
    defect_id: str
    severity: str | None = None
    confidence: str | None = None
    calibration: str | None = None
    rationale: str = ""
    agreement_rate: float = 0.0
    per_model: list[dict] = field(default_factory=list)
    aggregation_status: str = "completed"  # "completed" | "partial" | "failed"
    notes: list[str] = field(default_factory=list)


def parse_judge_file(path: Path, judge_id: str) -> dict[str, JudgeVerdict]:
    """Parse a single judge's output file. Returns {defect_id: JudgeVerdict}.

    If the file is missing/empty, returns a dict with one sentinel entry keyed
    ``"_file_status"`` whose parse_status carries the failure mode; downstream
    logic must handle it.
    """
    model = JUDGE_MODEL_MAP.get(judge_id, judge_id)
    provider = JUDGE_PROVIDER_MAP.get(judge_id, "unknown")

    if not path.exists():
        sentinel = JudgeVerdict(judge_id=judge_id, model=model, provider=provider,
                                parse_status="missing_file")
        return {"_file_status": sentinel}
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        sentinel = JudgeVerdict(judge_id=judge_id, model=model, provider=provider,
                                parse_status="missing_file")
        return {"_file_status": sentinel}

    # Split by --- delimiters; each block is one defect verdict.
    blocks = [b.strip() for b in re.split(r"^-{3,}\s*$", text, flags=re.MULTILINE) if b.strip()]
    out: dict[str, JudgeVerdict] = {}
    for block in blocks:
        defect_id = _extract_field(block, "DEFECT_ID")
        if not defect_id:
            continue
        severity = _normalize_severity(_extract_field(block, "SEVERITY"))
        confidence = _normalize_confidence(_extract_field(block, "CONFIDENCE"))
        calibration = _normalize_calibration(_extract_field(block, "CALIBRATION"))
        rationale = _extract_field(block, "RATIONALE") or ""

        # Unparseable = a block that clearly failed to produce the required fields.
        # Fail-safe: per SYNTHESIS.md, unparseable -> SEVERITY: critical.
        if severity is None:
            out[defect_id] = JudgeVerdict(judge_id=judge_id, model=model, provider=provider,
                                          severity="critical",
                                          confidence=confidence or "low",
                                          calibration=calibration or ("upgrade" if calibration is None else calibration),
                                          rationale=f"[UNPARSEABLE_FAILSAFE] {rationale}".strip(),
                                          parse_status="unparseable")
        else:
            out[defect_id] = JudgeVerdict(judge_id=judge_id, model=model, provider=provider,
                                          severity=severity,
                                          confidence=confidence,
                                          calibration=calibration,
                                          rationale=rationale,
                                          parse_status="ok")
    return out or {"_file_status": JudgeVerdict(judge_id=judge_id, model=model, provider=provider,
                                                parse_status="no_matching_defect")}


def _extract_field(block: str, field_name: str) -> str | None:
    m = re.search(rf"^\s*{re.escape(field_name)}\s*:\s*(.+?)\s*$", block, flags=re.MULTILINE)
    return m.group(1).strip() if m else None


def _normalize_severity(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip().lower()
    s = s.split()[0] if s else s  # tolerate "major -- the artifact..."
    s = s.rstrip(".,;:")
    return s if s in SEVERITY_RANK else None


def _normalize_confidence(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip().lower().split()[0].rstrip(".,;:")
    return s if s in CONFIDENCE_RANK else None


def _normalize_calibration(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip().lower().split()[0].rstrip(".,;:")
    return s if s in {"confirm", "upgrade", "downgrade"} else None


def aggregate_defect(
    defect_id: str,
    verdicts: list[JudgeVerdict],
    prior_pass1_severity: str | None = None,
    is_pass2: bool = False,
) -> AggregatedVerdict:
    parseable = [v for v in verdicts if v.parse_status in ("ok", "unparseable") and v.severity]
    total_judges = 3  # panel size
    n_parseable = len(parseable)
    result = AggregatedVerdict(defect_id=defect_id)

    # Serialize per-model list for every judge slot, even missing ones,
    # so downstream consumers see a uniform shape.
    for v in verdicts:
        result.per_model.append({
            "judge_id": v.judge_id,
            "model": v.model,
            "provider": v.provider,
            "severity": v.severity,
            "confidence": v.confidence,
            "calibration": v.calibration if is_pass2 else None,
            "rationale": v.rationale,
            "parse_status": v.parse_status,
        })

    if n_parseable == 0:
        result.aggregation_status = "failed"
        result.severity = prior_pass1_severity  # best-effort; None if pass 1
        result.confidence = "low"
        result.rationale = "JUDGE_PANEL_TOTAL_FAILURE: all 3 judges missing/unparseable"
        result.agreement_rate = 0.0
        if is_pass2 and prior_pass1_severity:
            result.calibration = "confirm"  # degenerate — no actual comparison possible
        result.notes.append("all_judges_failed")
        return result

    # Severity vote.
    sev_counts: dict[str, int] = {}
    for v in parseable:
        sev_counts[v.severity] = sev_counts.get(v.severity, 0) + 1

    max_count = max(sev_counts.values())
    winners = [s for s, c in sev_counts.items() if c == max_count]

    if len(winners) == 1:
        aggregated_severity = winners[0]
    else:
        # Tie. Fail-safe: take highest-rank severity among tied.
        aggregated_severity = max(winners, key=lambda s: SEVERITY_RANK[s])
        result.notes.append(f"severity_tie_resolved_failsafe_up: winners={winners}")
    result.severity = aggregated_severity

    # Confidence = max across judges whose severity matched the aggregated severity.
    matching = [v for v in parseable if v.severity == aggregated_severity and v.confidence]
    if matching:
        result.confidence = max((v.confidence for v in matching),
                                key=lambda c: CONFIDENCE_RANK[c])
    else:
        result.confidence = "low"

    # Rationale: concat.
    result.rationale = " | ".join(
        f"[{v.judge_id}/{v.model}] {v.rationale}" for v in parseable if v.rationale
    ) or "(no rationale from any judge)"

    # Agreement rate against the majority.
    n_matching_majority = sev_counts[aggregated_severity]
    result.agreement_rate = round(n_matching_majority / n_parseable, 3)

    # Calibration (pass 2 only).
    if is_pass2:
        cals = [v.calibration for v in parseable if v.calibration]
        if not cals:
            result.calibration = "confirm"  # conservative default
            result.notes.append("no_calibration_from_judges")
        else:
            cal_counts: dict[str, int] = {}
            for c in cals:
                cal_counts[c] = cal_counts.get(c, 0) + 1
            max_cal = max(cal_counts.values())
            cal_winners = [c for c, count in cal_counts.items() if count == max_cal]
            if len(cal_winners) == 1:
                result.calibration = cal_winners[0]
            else:
                result.calibration = "upgrade"  # fail-safe per spec
                result.notes.append(f"calibration_tie_resolved_failsafe_upgrade: {cal_winners}")

        # Forced-consistency: aggregated pass-2 severity vs prior pass-1 aggregated severity.
        # This overrides the per-judge vote to maintain the CALIBRATION semantic.
        if prior_pass1_severity:
            p1 = SEVERITY_RANK[prior_pass1_severity]
            p2 = SEVERITY_RANK[aggregated_severity]
            if p2 > p1:
                forced = "upgrade"
            elif p2 < p1:
                forced = "downgrade"
            else:
                forced = "confirm"
            if forced != result.calibration:
                result.notes.append(
                    f"calibration_forced_consistency: {result.calibration}->{forced} "
                    f"(pass1={prior_pass1_severity}, pass2={aggregated_severity})"
                )
                result.calibration = forced

    # Partial/complete status.
    if n_parseable < total_judges:
        result.aggregation_status = "partial"
        result.notes.append(f"partial_panel_{n_parseable}_of_{total_judges}")
    else:
        result.aggregation_status = "completed"

    return result


def write_summary_md(path: Path, batch_id: str, pass_num: int,
                     aggregated: list[AggregatedVerdict]) -> None:
    lines = [
        f"# Ensemble Judge Aggregation — batch {batch_id}, pass {pass_num}",
        "",
        f"**Defects aggregated:** {len(aggregated)}",
        "",
    ]
    for agg in aggregated:
        lines.append(f"## {agg.defect_id}")
        lines.append("")
        lines.append(f"**Aggregated:** severity=`{agg.severity}`  confidence=`{agg.confidence}`  "
                     f"agreement_rate=`{agg.agreement_rate}`  status=`{agg.aggregation_status}`"
                     + (f"  calibration=`{agg.calibration}`" if agg.calibration else ""))
        lines.append("")
        lines.append("| Judge | Model | Severity | Confidence | Calibration | Parse |")
        lines.append("|---|---|---|---|---|---|")
        for pm in agg.per_model:
            lines.append(
                f"| {pm['judge_id']} | {pm['model']} | "
                f"{pm['severity'] or '—'} | {pm['confidence'] or '—'} | "
                f"{pm['calibration'] or '—'} | {pm['parse_status']} |"
            )
        lines.append("")
        if agg.rationale:
            lines.append(f"**Rationale:** {agg.rationale}")
            lines.append("")
        if agg.notes:
            lines.append("**Aggregation notes:**")
            for n in agg.notes:
                lines.append(f"- {n}")
            lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-id", required=True)
    ap.add_argument("--pass", dest="pass_num", type=int, choices=[1, 2], required=True)
    ap.add_argument("--judge-file", action="append", default=[],
                    help="judge_id=path, repeat per judge (up to 3)")
    ap.add_argument("--prior-pass1-json", type=Path, default=None,
                    help="pass-1 aggregated JSON, required for pass 2 to apply calibration")
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--out-summary-md", type=Path, required=True)
    args = ap.parse_args()

    judge_files: dict[str, Path] = {}
    for spec in args.judge_file:
        if "=" not in spec:
            print(f"bad --judge-file (need judge_id=path): {spec}", file=sys.stderr)
            return 2
        jid, p = spec.split("=", 1)
        judge_files[jid] = Path(p)

    if not judge_files:
        print("at least one --judge-file is required", file=sys.stderr)
        return 2

    prior_pass1: dict[str, str] = {}  # defect_id -> severity
    if args.pass_num == 2:
        if not args.prior_pass1_json:
            print("--prior-pass1-json is required for --pass 2", file=sys.stderr)
            return 2
        try:
            prior_data = json.loads(args.prior_pass1_json.read_text(encoding="utf-8"))
            for defect_id, entry in prior_data.get("defects", {}).items():
                sev = entry.get("severity")
                if sev in SEVERITY_RANK:
                    prior_pass1[defect_id] = sev
        except (OSError, json.JSONDecodeError) as exc:
            print(f"could not read prior pass-1 JSON: {exc}", file=sys.stderr)
            return 2

    # Parse each judge file.
    per_judge_verdicts: dict[str, dict[str, JudgeVerdict]] = {}
    for jid, path in judge_files.items():
        per_judge_verdicts[jid] = parse_judge_file(path, jid)

    # Collect the union of defect_ids from all judges (ignoring the sentinel key).
    defect_ids: set[str] = set()
    for jid, parsed in per_judge_verdicts.items():
        for did in parsed.keys():
            if did != "_file_status":
                defect_ids.add(did)

    if not defect_ids:
        print("no defect_ids parsed from any judge file", file=sys.stderr)
        return 3

    aggregated: list[AggregatedVerdict] = []
    for defect_id in sorted(defect_ids):
        verdicts: list[JudgeVerdict] = []
        for jid in sorted(judge_files.keys()):
            parsed = per_judge_verdicts[jid]
            if defect_id in parsed:
                verdicts.append(parsed[defect_id])
            elif "_file_status" in parsed:
                verdicts.append(parsed["_file_status"])
            else:
                verdicts.append(JudgeVerdict(
                    judge_id=jid,
                    model=JUDGE_MODEL_MAP.get(jid, jid),
                    provider=JUDGE_PROVIDER_MAP.get(jid, "unknown"),
                    parse_status="no_matching_defect",
                ))
        aggregated.append(aggregate_defect(
            defect_id=defect_id,
            verdicts=verdicts,
            prior_pass1_severity=prior_pass1.get(defect_id),
            is_pass2=(args.pass_num == 2),
        ))

    # Write JSON.
    out = {
        "batch_id": args.batch_id,
        "pass": args.pass_num,
        "n_defects": len(aggregated),
        "defects": {a.defect_id: asdict(a) for a in aggregated},
        "global_agreement_rate": round(
            sum(a.agreement_rate for a in aggregated) / len(aggregated), 3
        ),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, indent=2), encoding="utf-8")

    # Write MD.
    args.out_summary_md.parent.mkdir(parents=True, exist_ok=True)
    write_summary_md(args.out_summary_md, args.batch_id, args.pass_num, aggregated)

    # Stderr summary (non-fatal warnings only).
    panel_failures = sum(1 for a in aggregated if a.aggregation_status == "failed")
    partials = sum(1 for a in aggregated if a.aggregation_status == "partial")
    if panel_failures or partials:
        print(f"batch {args.batch_id} pass {args.pass_num}: "
              f"failed={panel_failures} partial={partials} total={len(aggregated)}",
              file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
