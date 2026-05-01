#!/usr/bin/env python3
"""Long-Horizon Coherence (LHC) Goal Manager.

File-persisted goal tracking with atomic writes, drift detection,
and session prompt injection for multi-session objectives.
"""

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(os.environ.get("LHC_WORKSPACE", os.path.expanduser("~/.aimee/workspace")))
GOALS_DIR = WORKSPACE / "goals"
GOALS_MD = WORKSPACE / "GOALS.md"
THREAD_MAP = GOALS_DIR / "thread_map.json"
LHC_META = GOALS_DIR / ".lhc_meta.json"

SCHEMA_VERSION = "1.1"
TOKEN_BUDGET_GOALS = 1500
TOKEN_BUDGET_ALERTS = 300
TOKEN_BUDGET_TOTAL = 2000
STALE_DAYS = 3
VERY_STALE_DAYS = 7
MAJOR_DECISION_THRESHOLD = 3
LOW_CONFIDENCE_THRESHOLD = 0.6
ALERT_COOLDOWN_HOURS = 24
MAX_HIGH_ALERTS_PER_SESSION = 3


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _generate_goal_id():
    ts = int(time.time() * 1000)
    ts_hex = f"{ts:012x}"
    rand = uuid.uuid4().hex[:8]
    return f"g-{ts_hex}{rand}"


def _estimate_tokens(text):
    return max(1, int(len(text.split()) / 0.75))


def _ensure_dirs():
    GOALS_DIR.mkdir(parents=True, exist_ok=True)


def _atomic_write(path, data):
    """Write JSON atomically: temp file -> fsync -> rename."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    content = json.dumps(data, indent=2, default=str)
    with open(tmp, "w") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.rename(tmp, path)


def _read_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default if default is not None else {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default if default is not None else {}


def _read_goal(goal_id):
    path = GOALS_DIR / f"{goal_id}.json"
    if not path.exists():
        return None
    return _read_json(path)


def _write_goal(goal):
    goal["version"] = goal.get("version", 0) + 1
    goal["last_updated_at"] = _now_iso()
    _atomic_write(GOALS_DIR / f"{goal['id']}.json", goal)
    _update_goals_md()
    return goal


def _all_goals():
    _ensure_dirs()
    goals = []
    for p in sorted(GOALS_DIR.glob("g-*.json")):
        g = _read_json(p)
        if g and "id" in g:
            goals.append(g)
    return goals


# --- GOALS.md sentinel block ---

def _update_goals_md():
    goals = _all_goals()
    visible = [g for g in goals if g.get("status") != "abandoned"]
    visible.sort(key=lambda g: g.get("last_updated_at", ""), reverse=True)

    rows = []
    for g in visible:
        threads = len(g.get("thread_ids", []))
        updated = g.get("last_updated_at", "")[:10]
        rows.append(
            f"| {g['id']} | {g['title']} | {g['status']} | {updated} | {g.get('expected_effort', '?')} | {threads} |"
        )

    table = "| ID | Title | Status | Last Updated | Effort | Threads |\n"
    table += "|---|---|---|---|---|---|\n"
    table += "\n".join(rows) if rows else "| — | No active goals | — | — | — | — |"

    content = f"""# Active Goals
<!-- LHC:BEGIN -->
{table}
<!-- LHC:END -->
<!-- DO NOT EDIT between LHC tags. Managed by goal_manager. -->
"""
    GOALS_MD.write_text(content)


# --- Thread Map ---

def _read_thread_map():
    return _read_json(THREAD_MAP, default={})


def _write_thread_map(tmap):
    _atomic_write(THREAD_MAP, tmap)


def _link_thread(thread_id, goal_id):
    if not thread_id:
        return
    tmap = _read_thread_map()
    existing = tmap.get(thread_id, [])
    if goal_id not in existing:
        existing.append(goal_id)
    tmap[thread_id] = existing
    _write_thread_map(tmap)


def _unlink_thread(thread_id, goal_id):
    tmap = _read_thread_map()
    if thread_id in tmap:
        tmap[thread_id] = [g for g in tmap[thread_id] if g != goal_id]
        if not tmap[thread_id]:
            del tmap[thread_id]
        _write_thread_map(tmap)


# --- LHC Metadata ---

def _read_meta():
    return _read_json(LHC_META, default={
        "schema_version": SCHEMA_VERSION,
        "last_drift_check": None,
        "alert_surface_log": {}
    })


def _write_meta(meta):
    meta["schema_version"] = SCHEMA_VERSION
    _atomic_write(LHC_META, meta)


def _can_surface_alert(goal_id):
    meta = _read_meta()
    log = meta.get("alert_surface_log")
    if not isinstance(log, dict):
        return True
    last = log.get(goal_id)
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
        elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
        return elapsed >= ALERT_COOLDOWN_HOURS
    except (ValueError, TypeError):
        return True


def _record_alert_surfaced(goal_id):
    meta = _read_meta()
    log = meta.get("alert_surface_log")
    if not isinstance(log, dict):
        log = {}
    log[goal_id] = _now_iso()
    meta["alert_surface_log"] = log
    meta["last_drift_check"] = _now_iso()
    _write_meta(meta)


# --- Operations ---

def cmd_register(args):
    _ensure_dirs()
    criteria = args.criteria if args.criteria else []
    tags = args.tags if args.tags else []

    goal = {
        "id": _generate_goal_id(),
        "version": 0,
        "status": "active",
        "title": args.title,
        "intent": args.intent or args.title,
        "success_criteria": criteria,
        "expected_effort": args.effort or "days",
        "tags": tags,
        "thread_ids": [args.thread_id] if args.thread_id else [],
        "parent_goal_id": args.parent or None,
        "child_goal_ids": [],
        "sagaflow_run_ids": [],
        "allow_unmapped_work": False,
        "created_at": _now_iso(),
        "created_by": args.triggered_by or "user_message",
        "last_updated_at": _now_iso(),
        "last_session_id": None,
        "progress": [],
        "drift_history": [],
        "completed_at": None,
        "abandoned_at": None,
        "outcome_summary": None,
        "artifacts": []
    }

    if args.parent:
        parent = _read_goal(args.parent)
        if parent:
            if goal["id"] not in parent.get("child_goal_ids", []):
                parent.setdefault("child_goal_ids", []).append(goal["id"])

            _write_goal(goal)
            _write_goal(parent)
        else:
            _write_goal(goal)
    else:
        _write_goal(goal)

    if args.thread_id:
        _link_thread(args.thread_id, goal["id"])

    print(json.dumps({"ok": True, "goal_id": goal["id"]}))


def cmd_update_progress(args):
    goal = _read_goal(args.goal_id)
    if not goal:
        print(json.dumps({"ok": False, "error": "goal_not_found"}))
        return

    if args.run_id:
        for p in goal.get("progress", []):
            if p.get("sagaflow_run_id") == args.run_id:
                print(json.dumps({"ok": True, "skipped": "duplicate_run_id"}))
                return
        goal.setdefault("sagaflow_run_ids", [])
        if args.run_id not in goal["sagaflow_run_ids"]:
            goal["sagaflow_run_ids"].append(args.run_id)

    accomplished = args.accomplished if args.accomplished else []
    remaining = args.remaining if args.remaining else []
    decisions = []
    if args.decisions:
        for d in args.decisions:
            parts = d.split("|", 2)
            decisions.append({
                "description": parts[0].strip(),
                "rationale": parts[1].strip() if len(parts) > 1 else "",
                "scope_impact": parts[2].strip() if len(parts) > 2 else "none"
            })

    entry = {
        "session_id": args.session_id or str(uuid.uuid4())[:8],
        "timestamp": _now_iso(),
        "accomplished": accomplished,
        "remaining": remaining,
        "decisions": decisions,
        "confidence": float(args.confidence) if args.confidence else 0.8,
        "sagaflow_run_id": args.run_id
    }
    goal.setdefault("progress", []).append(entry)
    goal["last_session_id"] = entry["session_id"]
    _write_goal(goal)

    drift_flags = _check_single_goal(goal)
    print(json.dumps({"ok": True, "drift_flags": [d["alert_type"] for d in drift_flags]}))


def cmd_complete(args):
    goal = _read_goal(args.goal_id)
    if not goal:
        print(json.dumps({"ok": False, "error": "goal_not_found"}))
        return

    active_children = [
        cid for cid in goal.get("child_goal_ids", [])
        if (_read_goal(cid) or {}).get("status") == "active"
    ]
    if active_children:
        print(json.dumps({"ok": False, "error": "active_children", "child_ids": active_children}))
        return

    goal["status"] = "completed"
    goal["completed_at"] = _now_iso()
    goal["outcome_summary"] = args.summary or ""
    if args.artifacts:
        goal["artifacts"] = args.artifacts
    _write_goal(goal)
    print(json.dumps({"ok": True, "goal_id": goal["id"], "status": "completed"}))


def cmd_abandon(args):
    goal = _read_goal(args.goal_id)
    if not goal:
        print(json.dumps({"ok": False, "error": "goal_not_found"}))
        return

    goal["status"] = "abandoned"
    goal["abandoned_at"] = _now_iso()
    goal["outcome_summary"] = args.reason or ""
    goal.setdefault("drift_history", []).append({
        "timestamp": _now_iso(),
        "alert_type": "ABANDONED",
        "severity": "LOW",
        "detail": args.reason or "Abandoned by user",
        "surfaced_to_user": False,
        "last_surfaced_at": None
    })
    _write_goal(goal)

    for tid in goal.get("thread_ids", []):
        _unlink_thread(tid, goal["id"])

    for cid in goal.get("child_goal_ids", []):
        child = _read_goal(cid)
        if child and child.get("status") == "active":
            child["status"] = "abandoned"
            child["abandoned_at"] = _now_iso()
            child["outcome_summary"] = f"parent abandoned: {goal['id']}"
            child.setdefault("drift_history", []).append({
                "timestamp": _now_iso(),
                "alert_type": "ABANDONED",
                "severity": "LOW",
                "detail": f"Parent goal {goal['id']} abandoned",
                "surfaced_to_user": False,
                "last_surfaced_at": None
            })
            for tid in child.get("thread_ids", []):
                _unlink_thread(tid, child["id"])
            _write_goal(child)

    print(json.dumps({"ok": True, "goal_id": goal["id"], "status": "abandoned"}))


def cmd_pause(args):
    goal = _read_goal(args.goal_id)
    if not goal:
        print(json.dumps({"ok": False, "error": "goal_not_found"}))
        return
    goal["status"] = "paused"
    goal.setdefault("drift_history", []).append({
        "timestamp": _now_iso(),
        "alert_type": "PAUSED",
        "severity": "LOW",
        "detail": args.reason or "Paused by user",
        "surfaced_to_user": False,
        "last_surfaced_at": None
    })
    _write_goal(goal)
    print(json.dumps({"ok": True, "goal_id": goal["id"], "status": "paused"}))


def cmd_resume(args):
    goal = _read_goal(args.goal_id)
    if not goal:
        print(json.dumps({"ok": False, "error": "goal_not_found"}))
        return
    goal["status"] = "active"
    _write_goal(goal)
    print(json.dumps({"ok": True, "goal_id": goal["id"], "status": "active"}))


def cmd_list(args):
    goals = _all_goals()
    filt = getattr(args, "filter", "active")
    if filt != "all":
        goals = [g for g in goals if g.get("status") == filt]

    goals.sort(key=lambda g: g.get("last_updated_at", ""), reverse=True)
    out = []
    for g in goals:
        last_progress = g["progress"][-1] if g.get("progress") else None
        out.append({
            "id": g["id"],
            "title": g["title"],
            "status": g["status"],
            "last_updated_at": g.get("last_updated_at"),
            "expected_effort": g.get("expected_effort"),
            "thread_count": len(g.get("thread_ids", [])),
            "progress_count": len(g.get("progress", [])),
            "remaining": last_progress.get("remaining", []) if last_progress else [],
            "confidence": last_progress.get("confidence") if last_progress else None,
            "parent_goal_id": g.get("parent_goal_id"),
            "child_count": len(g.get("child_goal_ids", []))
        })
    print(json.dumps({"ok": True, "goals": out, "count": len(out)}))


# --- Drift Detection ---

def _days_since(iso_str):
    if not iso_str:
        return 999
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() / 86400
    except (ValueError, TypeError):
        return 999


def _check_single_goal(goal):
    alerts = []
    if goal.get("status") != "active":
        return alerts

    last_progress_time = None
    if goal.get("progress"):
        last_progress_time = goal["progress"][-1].get("timestamp")
    else:
        last_progress_time = goal.get("created_at")

    days = _days_since(last_progress_time)

    # D-01 STALE
    if days > STALE_DAYS and days <= VERY_STALE_DAYS:
        alerts.append({
            "alert_type": "STALE",
            "severity": "MEDIUM",
            "goal_id": goal["id"],
            "goal_title": goal["title"],
            "detail": f"No progress in {int(days)} days.",
            "recommended_action": "Update progress, pause, or abandon.",
            "surfaced_to_user": False,
            "timestamp": _now_iso()
        })

    # D-02 VERY_STALE
    if days > VERY_STALE_DAYS:
        alerts.append({
            "alert_type": "VERY_STALE",
            "severity": "HIGH",
            "goal_id": goal["id"],
            "goal_title": goal["title"],
            "detail": f"No progress in {int(days)} days.",
            "recommended_action": "Resume, pause, or abandon this goal.",
            "surfaced_to_user": False,
            "timestamp": _now_iso()
        })

    # D-03 SCOPE_CREEP
    major_decisions = 0
    for p in goal.get("progress", []):
        for d in p.get("decisions", []):
            if d.get("scope_impact") == "major":
                major_decisions += 1
    if major_decisions >= MAJOR_DECISION_THRESHOLD:
        alerts.append({
            "alert_type": "SCOPE_CREEP",
            "severity": "HIGH",
            "goal_id": goal["id"],
            "goal_title": goal["title"],
            "detail": f"{major_decisions} major-impact decisions recorded. Original scope may have shifted.",
            "recommended_action": "Review whether success criteria still match original intent.",
            "surfaced_to_user": False,
            "timestamp": _now_iso()
        })

    # D-04 LOW_CONFIDENCE
    if goal.get("progress"):
        latest_confidence = goal["progress"][-1].get("confidence", 1.0)
        if latest_confidence < LOW_CONFIDENCE_THRESHOLD:
            alerts.append({
                "alert_type": "LOW_CONFIDENCE",
                "severity": "HIGH",
                "goal_id": goal["id"],
                "goal_title": goal["title"],
                "detail": f"Latest confidence: {latest_confidence:.0%}. Work may be diverging from intent.",
                "recommended_action": "Re-check alignment with original intent and success criteria.",
                "surfaced_to_user": False,
                "timestamp": _now_iso()
            })

    # D-05 CRITERIA_DRIFT — compare current criteria to original
    # (simplified: if criteria were modified, we'd need a baseline; skip for now)

    # D-06 ORPHANED_THREAD
    if not goal.get("thread_ids"):
        alerts.append({
            "alert_type": "ORPHANED_THREAD",
            "severity": "MEDIUM",
            "goal_id": goal["id"],
            "goal_title": goal["title"],
            "detail": "Goal has no linked threads.",
            "recommended_action": "Link a thread or abandon if no longer relevant.",
            "surfaced_to_user": False,
            "timestamp": _now_iso()
        })

    # D-08 BLOCKED_CHILD
    for cid in goal.get("child_goal_ids", []):
        child = _read_goal(cid)
        if child and child.get("status") == "abandoned":
            alerts.append({
                "alert_type": "BLOCKED_CHILD",
                "severity": "MEDIUM",
                "goal_id": goal["id"],
                "goal_title": goal["title"],
                "detail": f"Child goal {cid} is abandoned but parent is still active.",
                "recommended_action": "Review parent goal status.",
                "surfaced_to_user": False,
                "timestamp": _now_iso()
            })

    return alerts


def cmd_drift_check(args):
    _ensure_dirs()
    goals = _all_goals()
    scope = getattr(args, "scope", "all")

    if scope != "all":
        goals = [g for g in goals if g["id"] == scope]

    all_alerts = []
    for g in goals:
        alerts = _check_single_goal(g)
        for a in alerts:
            g.setdefault("drift_history", []).append(a)
        if alerts:
            _write_goal(g)
        all_alerts.extend(alerts)

    high_alerts = [a for a in all_alerts if a["severity"] == "HIGH"]
    surfaced = []
    for a in sorted(high_alerts, key=lambda x: x.get("detail", "")):
        if len(surfaced) >= MAX_HIGH_ALERTS_PER_SESSION:
            a["severity"] = "MEDIUM"
            a["surfaced_to_user"] = False
            continue
        if _can_surface_alert(a["goal_id"]):
            a["surfaced_to_user"] = True
            _record_alert_surfaced(a["goal_id"])
            surfaced.append(a)

    meta = _read_meta()
    meta["last_drift_check"] = _now_iso()
    _write_meta(meta)

    print(json.dumps({
        "ok": True,
        "alerts": all_alerts,
        "high_count": len(high_alerts),
        "surfaced_count": len(surfaced)
    }))


# --- Context Block Generator ---

def cmd_context_block(args):
    _ensure_dirs()
    goals = _all_goals()
    active = [g for g in goals if g.get("status") == "active"]
    paused = [g for g in goals if g.get("status") == "paused"]

    if not active and not paused:
        print("")
        return

    active.sort(key=lambda g: g.get("last_updated_at", ""), reverse=True)

    drift_results = []
    for g in active:
        drift_results.extend(_check_single_goal(g))

    high_alerts = [a for a in drift_results if a["severity"] == "HIGH"]

    lines = ["=== ACTIVE GOALS (LHC) ==="]

    for a in high_alerts[:MAX_HIGH_ALERTS_PER_SESSION]:
        lines.append(f'[DRIFT ALERT — HIGH] {a["goal_id"]} "{a["goal_title"]}": {a["detail"]}')

    if high_alerts:
        lines.append("")

    lines.append("ACTIVE:")
    for i, g in enumerate(active):
        last_p = g["progress"][-1] if g.get("progress") else None
        updated = g.get("last_updated_at", "?")[:10]
        line = f'• {g["id"]} | "{g["title"]}" | last worked: {updated}'
        lines.append(line)

        if i < 3 and last_p:
            remaining = last_p.get("remaining", [])
            if remaining:
                lines.append(f"  Remaining: {', '.join(remaining[:3])}")
            decisions = last_p.get("decisions", [])
            if decisions:
                d = decisions[-1]
                lines.append(f"  Last decision: {d['description']} ({d.get('scope_impact', 'none')} scope)")
            conf = last_p.get("confidence")
            if conf is not None:
                lines.append(f"  Confidence: {conf:.0%}")
        elif i >= 3:
            pass  # summary line only for goals 4+

        current_tokens = _estimate_tokens("\n".join(lines))
        if current_tokens > TOKEN_BUDGET_GOALS:
            remaining_count = len(active) - i - 1
            if remaining_count > 0:
                lines.append(f"  ... {remaining_count} more active goals not shown")
            break

    if paused:
        lines.append("")
        lines.append("PAUSED:")
        for g in paused[:3]:
            reason = ""
            for dh in reversed(g.get("drift_history", [])):
                if dh.get("alert_type") == "PAUSED":
                    reason = f" | reason: {dh['detail']}"
                    break
            updated = g.get("last_updated_at", "?")[:10]
            lines.append(f'• {g["id"]} | "{g["title"]}" | paused {updated}{reason}')

    thread_id = getattr(args, "thread_id", None)
    if thread_id:
        tmap = _read_thread_map()
        linked = tmap.get(thread_id, [])
        if linked:
            lines.append(f"\nThis session's thread: {thread_id} → linked goals: {', '.join(linked)}")

    lines.append("=========================")

    block = "\n".join(lines)
    total_tokens = _estimate_tokens(block)
    if total_tokens > TOKEN_BUDGET_TOTAL:
        block_lines = block.split("\n")
        while _estimate_tokens("\n".join(block_lines)) > TOKEN_BUDGET_TOTAL and len(block_lines) > 5:
            for j in range(len(block_lines) - 2, 2, -1):
                if block_lines[j].startswith("  Remaining:") or block_lines[j].startswith("  Last decision:"):
                    block_lines.pop(j)
                    break
            else:
                break
        block = "\n".join(block_lines)

    print(block)


# --- Consistency Check ---

def cmd_consistency_check(_args):
    _ensure_dirs()
    goals = _all_goals()
    goal_ids = {g["id"] for g in goals}

    repairs = []

    if GOALS_MD.exists():
        content = GOALS_MD.read_text()
        import re
        md_ids = set(re.findall(r"(g-[a-f0-9]+)", content))
        for mid in md_ids:
            if mid not in goal_ids:
                repairs.append(f"GOALS.md references {mid} but no JSON file exists — removing from index")
        for gid in goal_ids:
            g = _read_goal(gid)
            if g and g.get("status") != "abandoned" and gid not in md_ids:
                repairs.append(f"{gid} exists as JSON but missing from GOALS.md — adding to index")

    tmap = _read_thread_map()
    for thread_id, gids in list(tmap.items()):
        for gid in list(gids):
            if gid not in goal_ids:
                repairs.append(f"thread_map references {gid} for thread {thread_id} but goal doesn't exist — removing")
                gids.remove(gid)
        if not gids:
            del tmap[thread_id]
    _write_thread_map(tmap)

    if repairs:
        _update_goals_md()

    print(json.dumps({"ok": True, "repairs": repairs, "repair_count": len(repairs)}))


# --- Thread operations ---

def cmd_link_thread(args):
    goal = _read_goal(args.goal_id)
    if not goal:
        print(json.dumps({"ok": False, "error": "goal_not_found"}))
        return
    if args.thread_id not in goal.get("thread_ids", []):
        goal.setdefault("thread_ids", []).append(args.thread_id)
        _write_goal(goal)
    _link_thread(args.thread_id, args.goal_id)
    print(json.dumps({"ok": True}))


def cmd_set_unmapped(args):
    goal = _read_goal(args.goal_id)
    if not goal:
        print(json.dumps({"ok": False, "error": "goal_not_found"}))
        return
    goal["allow_unmapped_work"] = args.value.lower() in ("true", "1", "yes")
    _write_goal(goal)
    print(json.dumps({"ok": True, "allow_unmapped_work": goal["allow_unmapped_work"]}))


def cmd_show(args):
    goal = _read_goal(args.goal_id)
    if not goal:
        print(json.dumps({"ok": False, "error": "goal_not_found"}))
        return
    print(json.dumps(goal, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(description="LHC Goal Manager")
    sub = parser.add_subparsers(dest="command")

    # register
    p = sub.add_parser("register")
    p.add_argument("--title", required=True)
    p.add_argument("--intent")
    p.add_argument("--criteria", nargs="*")
    p.add_argument("--effort", choices=["hours", "days", "weeks"])
    p.add_argument("--tags", nargs="*")
    p.add_argument("--thread-id")
    p.add_argument("--parent")
    p.add_argument("--triggered-by", default="user_message")

    # update-progress
    p = sub.add_parser("update-progress")
    p.add_argument("--goal-id", required=True)
    p.add_argument("--accomplished", nargs="*")
    p.add_argument("--remaining", nargs="*")
    p.add_argument("--decisions", nargs="*", help="format: desc|rationale|scope_impact")
    p.add_argument("--confidence")
    p.add_argument("--session-id")
    p.add_argument("--run-id")

    # complete
    p = sub.add_parser("complete")
    p.add_argument("--goal-id", required=True)
    p.add_argument("--summary")
    p.add_argument("--artifacts", nargs="*")

    # abandon
    p = sub.add_parser("abandon")
    p.add_argument("--goal-id", required=True)
    p.add_argument("--reason")

    # pause
    p = sub.add_parser("pause")
    p.add_argument("--goal-id", required=True)
    p.add_argument("--reason")

    # resume
    p = sub.add_parser("resume")
    p.add_argument("--goal-id", required=True)

    # list
    p = sub.add_parser("list")
    p.add_argument("--filter", default="active", choices=["active", "paused", "completed", "abandoned", "all"])

    # drift-check
    p = sub.add_parser("drift-check")
    p.add_argument("--scope", default="all")

    # context-block
    p = sub.add_parser("context-block")
    p.add_argument("--thread-id")

    # consistency-check
    sub.add_parser("consistency-check")

    # show
    p = sub.add_parser("show")
    p.add_argument("--goal-id", required=True)

    # link-thread
    p = sub.add_parser("link-thread")
    p.add_argument("--goal-id", required=True)
    p.add_argument("--thread-id", required=True)

    # set-unmapped-work
    p = sub.add_parser("set-unmapped-work")
    p.add_argument("--goal-id", required=True)
    p.add_argument("--value", required=True)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd_map = {
        "register": cmd_register,
        "update-progress": cmd_update_progress,
        "complete": cmd_complete,
        "abandon": cmd_abandon,
        "pause": cmd_pause,
        "resume": cmd_resume,
        "list": cmd_list,
        "drift-check": cmd_drift_check,
        "context-block": cmd_context_block,
        "consistency-check": cmd_consistency_check,
        "show": cmd_show,
        "link-thread": cmd_link_thread,
        "set-unmapped-work": cmd_set_unmapped,
    }
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
