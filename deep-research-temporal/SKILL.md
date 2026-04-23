---
name: deep-research-temporal
description: Use when researching, investigating, or exploring a topic systematically via a durable Temporal-backed workflow. Trigger phrases include "deep-research temporal", "sagaflow research", "durable research", "temporal research". Spawns parallel researchers across WHO/WHAT/HOW/WHERE/WHEN/WHY/LIMITS plus cross-cut dimensions (PRIOR-FAILURE, BASELINE, ADJACENT-EFFORTS, STRATEGIC-TIMING, ACTUAL-USAGE). Fact-verification, novelty classification, vocabulary bootstrap for cold-start topics. Fire-and-forget while you do other work.
user_invocable: true
argument: |
  Research seed (a question or topic). Optional flags:
    --arg max_directions=N       number of research directions (default 5, max ~15)
    --arg topic_velocity=fast_moving|stable   recency threshold
  Example: /deep-research-temporal "How are teams adopting Temporal for LLM orchestration?" --arg max_directions=8
---

# deep-research-temporal

Launches the `deep-research` workflow on sagaflow. Language locus detection → novelty classification → (conditional) vocabulary bootstrap → dimension discovery with 5 cross-cuts → parallel researchers → per-round coordinator summary → fact verifier → synthesis.

## How to invoke

```
Bash(
  run_in_background=true,
  command="sagaflow launch deep-research --arg seed='<SEED>' --arg max_directions=<N> --await"
)
```

Substitute `<SEED>` with the research topic/question and `<N>` with the direction budget.

Tell the user: "Launched deep-research on <seed>. Running in the background — I'll surface findings when the workflow completes."

## Termination labels

`User-stopped at round N` · `Coverage plateau — frontier saturated` · `Convergence — frontier exhausted` · `Budget soft gate — user chose to extend or stop`

## Result surfacing

Report at `~/.sagaflow/runs/<run_id>/research-report.md` with executive summary, per-direction findings, cross-cutting analysis, fact-verification spot-checks, coverage, sources, termination label. Surface the summary + any time-sensitive findings to the user.
