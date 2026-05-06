#!/usr/bin/env python3
"""Gather open PR status for a GitHub Enterprise user.

Outputs JSON with PR metadata, CI check status, and bot-posted test summaries.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from argparse import ArgumentParser
from typing import Any


def gh(*args: str, host: str = "github.netflix.net") -> Any:
    """Run gh CLI and return parsed JSON, raw string, or None on error."""
    cmd = ["gh", *args]
    env = {**os.environ, "GH_HOST": host}
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30)
    except subprocess.TimeoutExpired:
        print(f"  gh timeout ({' '.join(args[:3])})", file=sys.stderr)
        return None
    if r.returncode != 0:
        print(f"  gh error ({' '.join(args[:3])}): {r.stderr.strip()[:200]}", file=sys.stderr)
        return None
    out = r.stdout.strip()
    if not out:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return out


def summarize_checks(status_check_rollup: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize CI checks from statusCheckRollup (already in PR list data)."""
    checks = []
    for item in status_check_rollup:
        typename = item.get("__typename", "")
        if typename == "CheckRun":
            checks.append({
                "name": item.get("name", "unknown"),
                "status": item.get("status", ""),
                "conclusion": item.get("conclusion", ""),
                "url": item.get("detailsUrl", ""),
                "type": "check_run",
            })
        elif typename == "StatusContext":
            checks.append({
                "name": item.get("context", "unknown"),
                "status": item.get("state", ""),
                "conclusion": item.get("state", ""),
                "url": item.get("targetUrl", ""),
                "type": "status",
            })

    passing = sum(1 for c in checks if c["conclusion"] in ("SUCCESS", "success"))
    failing = sum(1 for c in checks if c["conclusion"] in ("FAILURE", "failure", "ERROR", "error"))
    pending = sum(1 for c in checks if c["conclusion"] in ("PENDING", "pending", "EXPECTED", ""))
    return {"checks": checks, "passing": passing, "failing": failing,
            "pending": pending, "total": len(checks)}


def get_bot_comment(repo: str, pr_number: int, host: str) -> str | None:
    """Get the latest netflix-octocat bot comment (test summary)."""
    result = gh("api", f"repos/{repo}/issues/{pr_number}/comments",
                "--hostname", host,
                "--jq", '[.[] | select(.user.login == "netflix-octocat" or .user.login == "netflix-octobot")] | last | .body // empty',
                host=host)
    if isinstance(result, str) and result and result != "null":
        return result
    return None


def _check_single_pr(repo: str, pr_number: int, host: str,
                      checks: bool, comments: bool) -> None:
    """Fetch and output status for a single PR."""
    print(f"Checking PR #{pr_number} on {repo}...", file=sys.stderr)
    pr = gh("pr", "view", str(pr_number), "--repo", repo,
            "--json", "number,title,headRefName,baseRefName,isDraft,reviewDecision,"
                      "mergeable,statusCheckRollup,createdAt,url,additions,deletions,changedFiles,state",
            host=host)
    if not isinstance(pr, dict):
        print(f"Error: could not fetch PR #{pr_number}", file=sys.stderr)
        sys.exit(1)

    pr["repo"] = repo
    if checks:
        rollup = pr.get("statusCheckRollup") or []
        check_info = summarize_checks(rollup)
        pr["checks"] = check_info["checks"]
        pr["checkSummary"] = {
            "passing": check_info["passing"], "failing": check_info["failing"],
            "pending": check_info["pending"], "total": check_info["total"],
        }
    if comments:
        pr["botComment"] = get_bot_comment(repo, pr_number, host)

    json.dump({"pr": pr}, sys.stdout, indent=2)
    print(file=sys.stdout)


def main() -> None:
    parser = ArgumentParser(description="Check open PR status on GHE")
    parser.add_argument("--user", "-u", help="GitHub username (default: current user)")
    parser.add_argument("--repo", "-r", help="Specific repo (e.g., corp/mli-metaflow-custom)")
    parser.add_argument("--pr", "-p", type=int, help="Specific PR number (requires --repo)")
    parser.add_argument("--host", default="github.netflix.net")
    parser.add_argument("--no-checks", dest="checks", action="store_false", default=True,
                        help="Skip CI check fetching")
    parser.add_argument("--no-comments", dest="comments", action="store_false", default=True,
                        help="Skip bot comment fetching")
    args = parser.parse_args()

    host: str = args.host

    if args.pr:
        if not args.repo:
            print("Error: --pr requires --repo", file=sys.stderr)
            sys.exit(1)
        _check_single_pr(args.repo, args.pr, host, args.checks, args.comments)
        return

    user: str | None = args.user
    if not user:
        whoami = gh("api", "user", "--jq", ".login", host=host)
        if not isinstance(whoami, str) or not whoami:
            print("Error: could not determine username. Use --user USERNAME", file=sys.stderr)
            sys.exit(1)
        user = whoami.strip('"')

    print(f"Checking open PRs for {user}...", file=sys.stderr)

    repos: list[str]
    if args.repo:
        repos = [args.repo]
    else:
        search = gh("search", "prs", "--author", user, "--state", "open",
                     "--limit", "50", "--json", "repository", host=host)
        if not isinstance(search, list) or not search:
            json.dump({"user": user, "prs": [], "summary": "No open PRs found"}, sys.stdout, indent=2)
            print(file=sys.stdout)
            return
        repos = sorted({pr["repository"]["nameWithOwner"] for pr in search})

    print(f"Repos: {', '.join(repos)}", file=sys.stderr)

    all_prs: list[dict[str, Any]] = []
    for repo in repos:
        print(f"  Fetching PRs from {repo}...", file=sys.stderr)
        prs = gh("pr", "list", "--repo", repo, "--author", user, "--state", "open",
                 "--json", "number,title,headRefName,baseRefName,isDraft,reviewDecision,"
                           "mergeable,statusCheckRollup,createdAt,url,additions,deletions,changedFiles",
                 host=host)
        if not isinstance(prs, list) or not prs:
            continue

        for pr in prs:
            pr["repo"] = repo
            num: int = pr["number"]

            if args.checks:
                rollup = pr.get("statusCheckRollup") or []
                check_info = summarize_checks(rollup)
                pr["checks"] = check_info["checks"]
                pr["checkSummary"] = {
                    "passing": check_info["passing"],
                    "failing": check_info["failing"],
                    "pending": check_info["pending"],
                    "total": check_info["total"],
                }

            if args.comments:
                pr["botComment"] = get_bot_comment(repo, num, host)

        all_prs.extend(prs)

    summary = {
        "total_prs": len(all_prs),
        "draft": sum(1 for p in all_prs if p.get("isDraft")),
        "with_failures": sum(1 for p in all_prs
                             if isinstance(p.get("checkSummary"), dict)
                             and p["checkSummary"].get("failing", 0) > 0),
        "pending_ci": sum(1 for p in all_prs
                          if isinstance(p.get("checkSummary"), dict)
                          and p["checkSummary"].get("pending", 0) > 0),
    }

    json.dump({"user": user, "prs": all_prs, "summary": summary}, sys.stdout, indent=2)
    print(file=sys.stdout)


if __name__ == "__main__":
    main()
