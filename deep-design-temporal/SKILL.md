---
name: deep-design-temporal
description: Use when designing, specifying, architecting, or drafting a design via a durable Temporal-backed workflow that survives session crashes. Trigger phrases include "deep-design temporal", "sagaflow design", "durable design", "temporal design review". DFS-based flaw-finding with parallel critic agents that stress-test until coverage saturates. Output is a battle-tested design document with an honest coverage report. Fire-and-forget while you do other work.
user_invocable: true
argument: |
  Concept to design (a product, system, feature, protocol, workflow). Optional flags:
    --arg max_rounds=N          iteration cap for stress-test loop (default 2)
  Example: /deep-design-temporal "multi-tenant rate limiter with per-tenant quotas" --arg max_rounds=3
---

# deep-design-temporal

Launches the `deep-design` workflow on sagaflow. DFS-based adversarial design with parallel critic agents that stress-test the draft design until coverage saturates or max_rounds is hit.

## How to invoke

```
Bash(
  run_in_background=true,
  command="sagaflow launch deep-design --arg concept='<CONCEPT>' --arg max_rounds=<N> --await"
)
```

Substitute `<CONCEPT>` with the design brief (what to design) and `<N>` with the stress-test round budget (1-5; default 2).

Tell the user: "Launched deep-design on <concept>. Running in the background — I'll surface the design + coverage report when the workflow completes."

## Termination labels

`Coverage saturated — design hardened` · `Max rounds reached` · `User-stopped at round N` · `Hard stop at round N`

## Result surfacing

Report at `~/.sagaflow/runs/<run_id>/design-report.md` with the battle-tested design, per-round flaw inventory, unresolved risks, and an honest coverage table (what was stress-tested vs what wasn't). Surface the coverage label + top remaining risks to the user.
