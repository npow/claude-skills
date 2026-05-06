---
name: loop-until-done
description: The single loop skill for ALL recurring and drive-to-completion work. Subsumes the built-in loop (periodic polling), ralph (iterative completion with verification), and loop-until-done (PRD-driven execution). Durable Temporal-backed — survives session crashes. Trigger phrases include "loop", "loop until done", "keep trying", "fix until", "until X passes", "check every N minutes", "keep checking", "poll for", "don't stop until", "ralph", "persist until done", "sagaflow loop", "durable loop".
user_invocable: true
argument: |
  Task to loop on. Modes auto-detected from context:
    --poll <interval>              Periodic polling mode (e.g., --poll 5m)
    --arg max_iter=N               Iteration cap per story (default 5)
    --critic=architect|critic      Reviewer for completion verification
    --no-deslop                    Skip post-review cleanup pass
  Examples:
    /loop-until-done "all tests pass and coverage >= 80%"
    /loop-until-done --poll 5m "check PR #1807 CI results"
    /loop-until-done "fix all setup failures" --critic=architect
---

# loop-until-done

The canonical loop skill. Two modes, one entry point:

## Mode 1: Drive-to-completion (default)

PRD-driven execution — breaks work into stories with acceptance criteria, iterates story-by-story with independent verification, terminates only when every criterion has fresh passing evidence.

**Phases:**
1. **PRD planner** — generates stories with testable acceptance criteria
2. **Falsifiability judge** — marks each criterion pass/fail for falsifiability
3. **Executor** — completes each story, runs verification
4. **Verifier** — per-criterion evidence check
5. **Reviewer** — final verdict with configurable reviewer (--critic)

**From ralph:** session persistence, structured story tracking (prd.json), progress tracking across iterations, reviewer verification before completion.

**From autopilot:** autopilot should invoke this skill for its Phase 3 verify loop rather than implementing its own.

## Mode 2: Periodic polling (--poll)

Recurring check on a schedule — fires the same probe on an interval, stops when a condition is met or the user cancels.

**From built-in loop:** ScheduleWakeup-based recurring execution, CronCreate for fixed intervals, Monitor for event-driven waking.

When `--poll <interval>` is present, skip PRD generation and run the task as a recurring check.

## Execution routing (sagaflow-first)

This skill runs on sagaflow's Temporal backend by default. The workflow is in `workflow.py` in this directory. Sagaflow provides durable execution, heartbeat monitoring, and crash recovery.

**Routing sequence:**
1. Run `sagaflow doctor` to verify worker is running
2. If healthy → launch via sagaflow (fire-and-forget, durable)
3. If worker unavailable → fall back to in-session ralph-style loop (degraded, not crash-safe)

## Engineering gaps (TODO)

These features exist in ralph but aren't yet in the temporal workflow:

- [ ] **Periodic polling mode** — workflow.py only handles drive-to-completion; needs a poll-mode branch that uses Temporal timers instead of ScheduleWakeup
- [ ] **Reviewer selection** — workflow.py hardcodes Sonnet reviewer; needs --critic flag routing to architect/critic/codex
- [ ] **Deslop pass** — post-review cleanup pass from ralph not yet in temporal workflow
- [ ] **Ultrawork integration** — parallel fan-out for independent stories not yet wired
- [ ] **Progress.txt tracking** — ralph's cross-iteration learning file not yet in temporal state

Until these gaps are closed, the in-session fallback uses ralph's implementation. The temporal workflow handles the core PRD→verify loop.
