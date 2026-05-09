#!/usr/bin/env python3
"""find-skill: search the cached skill index for matches.

Reuses the index built by ~/.claude/hooks/inject-skill-hints.py. If the index
is stale or missing, rebuilds it by importing the hook module.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
INDEX_PATH = HOME / ".cache" / "claude-skill-index.json"
HOOK_PATH = HOME / ".claude" / "hooks" / "inject-skill-hints.py"
INDEX_TTL_SEC = 24 * 3600


def load_index_module():
    spec = importlib.util.spec_from_file_location("inject_skill_hints", HOOK_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load hook module at {HOOK_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def get_index() -> list[dict]:
    if INDEX_PATH.exists():
        age = time.time() - INDEX_PATH.stat().st_mtime
        if age < INDEX_TTL_SEC:
            try:
                return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
    mod = load_index_module()
    skills = mod.build_index()
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(skills), encoding="utf-8")
    return skills


def main() -> int:
    ap = argparse.ArgumentParser(description="Search the Claude Code skill index.")
    ap.add_argument("query", nargs="+", help="search terms")
    ap.add_argument("--limit", type=int, default=10, help="max results (default 10)")
    ap.add_argument("--full", action="store_true", help="show full descriptions")
    ap.add_argument("--rebuild", action="store_true", help="force index rebuild")
    args = ap.parse_args()

    if args.rebuild and INDEX_PATH.exists():
        INDEX_PATH.unlink()

    skills = get_index()

    mod = load_index_module()
    query_text = " ".join(args.query).lower()
    keywords = mod.extract_keywords(query_text)
    if not keywords:
        print("No usable search terms (all stopwords).", file=sys.stderr)
        return 1

    scored = []
    seen_leaves: set[str] = set()
    for s in skills:
        leaf = s["name"].rsplit(":", 1)[-1]
        if leaf in seen_leaves:
            continue
        sc = mod.score(keywords, set(s["tokens"]))
        # Also boost direct substring matches in name/description
        name_l = s["name"].lower()
        desc_l = s["description"].lower()
        for kw in keywords:
            if kw in name_l:
                sc += 3
            elif kw in desc_l:
                sc += 1
        if sc > 0:
            scored.append((sc, s))
            seen_leaves.add(leaf)

    if not scored:
        print(f"No skills matched: {query_text}")
        return 0

    scored.sort(key=lambda x: (-x[0], x[1]["name"]))
    print(f"Found {len(scored)} matches (showing top {min(args.limit, len(scored))}):\n")
    for sc, s in scored[: args.limit]:
        desc = s["description"] if args.full else s["description"][:200]
        print(f"[{sc:3d}] {s['name']}")
        print(f"      {desc}")
        print(f"      path: {s['path']}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
