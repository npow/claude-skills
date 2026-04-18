# Custom harness evaluation for Temporal-native coordination

**Status:** ⚠️ SUPERSEDED by `2026-04-18-pi-dev-harness-adoption-design.md` — kept as history
**Author:** npow + Claude (brainstorming session 2026-04-18)
**Type:** evaluation / spike (P4 in path analysis) — decision made before full eval ran
**Companion:** `2026-04-18-flux-temporal-orchestration-design.md` (P2 build)

> **Why superseded:** after a desk evaluation + architectural discussion in the same brainstorming session,
> user committed to pi.dev as the P4 direction without running the full 3-candidate spike.
> See `2026-04-18-pi-dev-harness-adoption-design.md` for the current plan. This file remains in the repo
> so the reasoning trail for the decision is preserved.

## Context

The brainstorming session that produced the Flux/P2 spec also surfaced a longer-term question: should the orchestration layer live inside Claude Code (P2, keep Claude as orchestrator) or inside a custom harness (P4, own the tool-call loop)?

P2 solves the immediate bug and gives Temporal-grade activity guarantees. P4 buys additional ceiling — cross-session workflows, full Temporal workflow constructs (signals, queries, replay), lower hook latency, ownership of the tool-call loop, and potential shareability as a product. The cost is a 1-3 week migration that touches every skill.

The user wants to run P2 AND evaluate P4 in parallel to make an informed long-term decision. This spec defines that evaluation: a time-boxed spike across 3 harness candidates, producing a decision artifact.

**Not a goal:** commit to P4 migration, port all skills. This spec is purely evaluation — enough work to make a decision, no more.

## Decision this evaluation informs

Within 4 weeks of completion, answer:
- **Migrate to P4** — start porting the remaining coordinator skills to a chosen harness (expected 2-6 more weeks)
- **Stay on P2** — flux adapter is sufficient; close the P4 exploration
- **Hybrid** — keep P2 for most skills; use P4 for specific new skills where its ceiling matters (e.g. cross-session research jobs)
- **Defer** — more real-world flux usage needed before the call makes sense

Decision artifact: `docs/specs/YYYY-MM-DD-harness-migration-decision.md`.

## Evaluation candidates

### C1. goose (block/goose)

Open-source AI agent framework by Block (Square). Rust-based runtime, MCP-first, extensible via "extensions." "Recipe" format close to Claude skills (markdown + frontmatter).

**Why evaluate:**
- Mature (1k+ commits, active development)
- MCP-compatible out of the box
- Recipe format already close to Claude skill format → low-friction port
- Has hook points + observability already
- Native support for multiple LLMs (OpenAI/Anthropic/Gemini/etc.)

**What we'd build:** a goose extension that wraps spawns in Temporal activities. Port one coordinator skill (deep-debug) as a goose recipe; run full lifecycle against the extension.

**Risks:** learning curve for goose internals; recipe format may have non-trivial differences from Claude skills; Rust extension development is higher friction than Python.

### C2. pi.dev

Open-source Python agent framework (to be verified at eval start — flagged by user in brainstorming, needs confirmation of current state). If it exists and is maintained, evaluate similarly to goose.

**If pi.dev is not viable** (abandoned, closed-source, or lacks extensibility), substitute with:

**C2-alt. OpenHands (formerly OpenDevin)** — open-source, Python-first, has runtime controller pattern.

### C3. DIY on Claude Agent SDK

Anthropic's Python SDK gives programmatic control over Claude's tool-call loop. Write a minimal harness (~500 lines) that:
- Reads skill markdown files (same format as Claude Code skills)
- Invokes Claude via the Anthropic API with tool definitions
- Dispatches tool calls (Read/Write/Bash/Agent/etc.) via local handlers
- Wraps sub-agent dispatches in Temporal activities natively

**Why evaluate:**
- Maximum control over the integration
- Natural ergonomic fit — Temporal activities are first-class, no adapter layer
- No dependency on an external harness's development velocity
- Skills-as-markdown can stay; the harness reads them directly

**Risks:** 500 lines is optimistic; real harnesses have edge cases (context compaction, conversation summarization, tool result truncation, error recovery) — realistic is probably 1500-2500 lines for parity with Claude Code. Major surface area to test.

## Evaluation methodology

### Phase 1: Setup (week 1, per candidate)

For each of C1, C2, C3:
1. Install / set up the harness
2. Confirm it can execute a trivial agent flow: "read file X, summarize in Y words, write to Z"
3. Identify extension / integration points for Temporal
4. Document: install steps, prerequisites, runtime footprint, obvious papercuts

### Phase 2: Port one skill (week 2, per candidate)

Port `deep-debug` as the test skill because:
- Newest, smallest scope
- Well-specified (we just wrote it)
- Uses all orchestration patterns: parallel agent spawns, blocking polls, judge batches, retries
- Has natural Temporal-fitting structure (phases as workflows, agents as activities)

For each candidate:
1. Port skill format (SKILL.md + DIMENSIONS.md + EVIDENCE.md + FORMAT.md + STATE.md + TECHNIQUES.md) to harness's native format
2. Implement Temporal integration for background spawns
3. Run full end-to-end against a fabricated bug (same scenario in each)
4. Record: port effort (hours), LOC changes, runtime characteristics, failure modes observed

### Phase 3: Stress + comparison (week 3)

For each successfully ported candidate:
1. Run the failure-injection scenarios from the flux spec (kill agent mid-run, kill coordinator, etc.)
2. Measure: tool-call latency, memory, activity state accuracy under failure
3. Compare against baseline (same deep-debug run via P2/flux)

### Phase 4: Decision write-up (week 4)

Produce `docs/specs/YYYY-MM-DD-harness-migration-decision.md` per the decision framework below.

## Evaluation criteria (rubric)

Score each candidate 1-5 on each axis; weights applied for final recommendation.

| Axis | Weight | 1 (fail) | 3 (middling) | 5 (excellent) |
|---|---|---|---|---|
| **Migration cost (per skill)** | 25% | > 1 week/skill | ~1 day/skill | ~2 hours/skill |
| **Temporal integration ergonomics** | 20% | Requires external glue | Clean SDK integration | Native workflow pattern |
| **Skill format compatibility** | 15% | Total rewrite | Tool-aware migration | Minor annotations |
| **Runtime stability** | 10% | Crashes under stress | Mostly stable | Zero incidents in stress test |
| **Development velocity (iteration time)** | 10% | > 5 min edit-test-loop | ~1 min loop | Sub-second loop |
| **Ecosystem preserved** | 10% | Subagent types, plugins, MCP lost | Some preserved, some reimplementable | All preserved |
| **Community / maintenance risk** | 5% | Single-maintainer, sporadic | Active, mid-size community | Anthropic-backed or > 1k contributors |
| **Cross-session workflow support** | 5% | Not possible | Possible with effort | First-class |

Total weighted score determines P4 viability per-candidate.

## Decision framework

After evaluation completes, the decision goes by these rules:

**Migrate to P4 if:**
- Top candidate scores ≥ 4.0 weighted average
- Per-skill migration cost < 4 hours for remaining skills
- At least one candidate beats P2 on Temporal ergonomics AND keeps ecosystem preserved

**Stay on P2 if:**
- No candidate scores > 3.5 OR
- Best candidate's migration cost > 2 days/skill OR
- Ecosystem loss is critical (e.g. `subagent_type` library usage is > 20% of current coordination surface)

**Hybrid if:**
- A candidate scores well on cross-session workflow support AND we have a concrete skill use case requiring it (e.g. a multi-day research agent)
- AND P2 is sufficient for existing skills (meaning: add P4 for NEW skills, not migrate EXISTING ones)

**Defer if:**
- Evaluation surfaces new questions requiring more real-world flux usage before the call is informed
- Write up the open questions; re-evaluate in 3 months

## Deliverables

At evaluation end:
1. **`docs/specs/YYYY-MM-DD-harness-migration-decision.md`** — the decision artifact
2. **One working port of deep-debug per viable candidate** — kept in a `eval-harness-ports/` branch for reference
3. **Benchmark numbers** in a simple `eval-harness-benchmarks.md`
4. **Writeup of unexpected findings** — things we learned that weren't on the rubric

## Timeline & scope

Total: **4 weeks, part-time** (expected ≤ 20 hours total across all 4 weeks).

- Week 1 (setup): 5 hours
- Week 2 (port deep-debug × 3 candidates): 9 hours
- Week 3 (stress + benchmarks): 4 hours
- Week 4 (writeup + decision): 2 hours

Hard stops:
- If week-1 setup for a candidate takes > 5 hours, drop that candidate (fails the "realistic migration" bar)
- If week-2 port takes > 8 hours for a candidate, note as red flag but continue
- If total hits 25 hours without a clear leader, declare defer and stop

## Risks & mitigations

**Risk: pi.dev may not be the right reference.** User mentioned it casually; it may be a different project or stale. Mitigation: verify at Phase 1 start; substitute OpenHands if needed. If no viable C2 substitute, run with just goose + DIY.

**Risk: evaluating in isolation misses production signal.** The real data is how P2 performs on actual coordinator runs over weeks. Mitigation: the eval's decision threshold is intentionally high; "defer" is a valid outcome that lets real P2 usage accumulate before commitment.

**Risk: DIY harness spike undersells the cost.** 500 lines is optimistic. Mitigation: time-box the DIY port at 8 hours; if parity isn't reachable in that time, the rubric's "migration cost" axis captures it correctly.

**Risk: eval takes longer than 4 weeks.** Classic spike creep. Mitigation: hard-stops in Phase 3; if the eval drifts, defer the decision rather than extend.

## Relationship to P2

P2 ships regardless of P4 evaluation outcome. Nothing in P2 is wasted work even if P4 wins:
- The activity-annotation schema (flux_timeouts, flux_retry_policy) maps directly to any Temporal-based harness
- Skill migrations for P2 (adding those annotations) are forward-compatible with P4 migration
- flux adapter becomes unnecessary under P4, but its call-site API (conceptually) matches any Temporal-wrapping harness's

If evaluation selects P4: plan a staged migration where flux-adapted skills are re-migrated to the chosen harness, with P2 remaining as fallback for skills not yet migrated.

## Open questions for user before evaluation starts

1. **Is pi.dev the right reference?** — needs verification; if not, substitute OK?
2. **Weighting the rubric** — the weights above are my guess; does the user want to adjust (e.g. migration cost matters more/less)?
3. **Single skill port sufficient?** — eval ports only deep-debug. Is that a good-enough signal? Alternative: port deep-debug (smallest) + deep-research (largest) for more coverage at +1 week.
4. **DIY candidate worth it?** — if the user feels strongly about never doing DIY, we can cut C3 and run C1 + C2 only, tightening the timeline to 3 weeks.

---

## Post-spec-review workflow

After user approves this spec:
1. Flag open questions above; await answers or proceed with defaults
2. Evaluation runs over 4 weeks in parallel with P2 build (P2 is the committed path)
3. Decision artifact written at week 4
4. If decision is "migrate to P4": invoke `superpowers:writing-plans` for migration plan
5. If decision is "stay on P2" or "defer": close this thread; revisit in 3-6 months
