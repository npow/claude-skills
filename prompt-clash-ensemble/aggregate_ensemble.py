#!/usr/bin/env python3
"""Aggregate prompt-clash ensemble outputs into a comparison table.

Reads defender output files, extracts fenced code blocks and security fixes,
and produces a structured comparison for the synthesis agent.

Usage:
    python3 aggregate_ensemble.py --run-dir /tmp/prompt-clash-ensemble-{run_id}
"""
import argparse
import json
import re
import sys
from pathlib import Path


def extract_code_block(text: str) -> str | None:
    m = re.search(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL)
    return m.group(1).strip() if m else None


def count_tokens_approx(text: str) -> int:
    return len(text.split())


def extract_security_fixes(prompt_text: str) -> list[str]:
    fixes: list[str] = []
    in_security = False
    for line in prompt_text.splitlines():
        upper = line.strip().upper()
        if "SECURITY" in upper and ("REQUIREMENT" in upper or ":" in upper):
            in_security = True
            continue
        if in_security:
            stripped = line.strip()
            if not stripped:
                continue
            if re.match(r"^(#{1,3}\s|[A-Z]{3,}\s)", stripped) and "SECURITY" not in stripped.upper():
                break
            if re.match(r"^(\d+[\.\)]\s*|-\s*|\*\s*)", stripped):
                fixes.append(re.sub(r"^(\d+[\.\)]\s*|-\s*|\*\s*)", "", stripped).strip())
            elif stripped:
                fixes.append(stripped)
    return fixes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, help="Path to ensemble run directory")
    parser.add_argument("--out-json", help="Output JSON path (default: {run-dir}/comparison.json)")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"ERROR: {run_dir} is not a directory", file=sys.stderr)
        return 1

    results: list[dict] = []
    for f in sorted(run_dir.glob("defender_*m.md")):
        budget_match = re.search(r"defender_(\d+)m", f.name)
        if not budget_match:
            continue
        budget = int(budget_match.group(1))
        text = f.read_text()
        code_block = extract_code_block(text)
        prompt_text = code_block if code_block else text
        fixes = extract_security_fixes(prompt_text)
        results.append({
            "budget_minutes": budget,
            "file": str(f),
            "token_count": count_tokens_approx(prompt_text),
            "security_fixes": fixes,
            "fix_count": len(fixes),
            "prompt_text": prompt_text,
        })

    all_fixes: set[str] = set()
    for r in results:
        all_fixes.update(r["security_fixes"])

    for r in results:
        unique = [f for f in r["security_fixes"] if sum(1 for other in results if f in other["security_fixes"]) == 1]
        r["unique_fixes"] = unique
        r["unique_fix_count"] = len(unique)

    comparison = {
        "defenders": results,
        "total_unique_fixes_across_all": len(all_fixes),
        "defender_count": len(results),
    }

    out_path = Path(args.out_json) if args.out_json else run_dir / "comparison.json"
    out_path.write_text(json.dumps(comparison, indent=2))
    print(json.dumps(comparison, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
