# pi.dev harness adoption + Temporal-native coordination

**Status:** design, approved direction — pending user spec review
**Author:** npow + Claude (brainstorming session 2026-04-18)
**Type:** committed migration (P4 in path analysis; supersedes `2026-04-18-custom-harness-evaluation-design.md`)
**Companion:** `2026-04-18-flux-temporal-orchestration-design.md` (P2, ships first)

## Context

The brainstorming session produced a harness-eval spec designed to compare goose / pi.dev / DIY-Agent-SDK over 4 weeks. After a desk evaluation + architectural discussion, the user committed to pi.dev as the P4 direction before running the full 3-candidate spike.

Rationale (from session):
- **Zero migration cost concern.** User is willing to port skill content regardless; this removes goose's main disadvantage (skill format mismatch) but doesn't help it vs pi.dev.
- **Temporal integration ergonomics.** pi.dev's TypeScript + in-process lifecycle-event extension model gives the cleanest Temporal integration path. goose requires MCP protocol hops.
- **Architecturally, pi.dev is closer to the "combined / best-of-both" shape** — in-process lifecycle events + opinionated minimalism + single-language coherence. Its missing pieces (MCP ecosystem, governance, distribution) are additive; goose's architectural commitments (Rust core, MCP-first, LF governance cadence) are harder to strip back.
- **pi.dev follows the Agent Skills standard** — skill files should port with near-zero structural edits.

Known risks (accepted):
- **Single-maintainer bus factor.** pi-mono is authored by Mario Zechner (badlogic). If he stops maintaining, we inherit the code. Mitigated by: pi.dev is TypeScript + small + opinionated; forking is cheap.
- **Smaller ecosystem than goose.** Accepted — we're not using the MCP extension catalog; our need is the framework, not the plugins.
- **Less mature / less production-tested.** Accepted — POC validates this concretely.

**This spec replaces the 3-candidate evaluation with a focused pi.dev adoption plan.**

## Goal

Port the coordinator skill suite (deep-debug, deep-qa, deep-research, deep-design, deep-idea, consensus-plan) onto pi.dev with a native Temporal integration. Produces a harness-owned coordination platform where Temporal-grade activity guarantees are a first-class primitive, not an adapter layer.

**Non-goals:**
- Evaluate alternatives (decision locked)
- Migrate non-coordinator skills (those stay in Claude Code or move independently)
- Replace Claude Code for day-to-day use (pi.dev is for the coordinator-skill use case)

## Strategy

Two tracks running concurrently:

**Track A (ships this week): flux/P2.** Temporal-backed adapter for Claude Code skills. Solves the 18-hour-silent-death bug immediately. Spec: `2026-04-18-flux-temporal-orchestration-design.md`.

**Track B (starts week 2): pi.dev adoption.** Phased migration of coordinator skills off Claude Code onto pi.dev. Each skill migrates when pi.dev's platform reaches parity for that skill's patterns. Until a skill migrates, flux keeps it safe.

Both tracks converge: once a skill is migrated to pi.dev with native Temporal, its flux wrapper in Claude Code becomes obsolete. Flux sunsets per-skill as migration completes.

## Phased plan

### Phase 1: POC (week 2, ~8 hours)

**Deliverable:** deep-debug running end-to-end on pi.dev with Temporal-backed activity dispatch.

**Steps:**
1. Install pi-coding-agent and related pi-mono packages locally
2. Port `deep-debug/SKILL.md` + supporting files to pi.dev's format (expected near-direct copy given Agent Skills standard conformance)
3. Write a TypeScript extension `pi-temporal-activity` that:
   - Subscribes to agent lifecycle events
   - Wraps sub-agent dispatches as Temporal activities (via `temporalio` TS SDK)
   - Implements heartbeat + retry + timeout semantics natively
4. Run a full deep-debug cycle on a fabricated bug
5. Stress test: same failure-injection scenarios from the flux spec (kill agent mid-run, kill Temporal, kill coordinator)

**POC decision gate at end of week 2:**
- ✅ **Ship-worthy:** deep-debug runs correctly; Temporal integration is as clean as predicted; extension pattern scales. → advance to Phase 2.
- ⚠️ **Surprises that matter:** lifecycle events don't cover the spawning pattern you need, OR skill format has non-trivial edits, OR pi.dev has an unfixable defect. → pause migration, document findings, revisit goose OR stay on flux.
- ❌ **Catastrophic:** pi.dev doesn't work at all. → abort P4; flux/P2 becomes the permanent answer.

Worst-case work wasted if POC fails: ~8 hours. Track A (flux/P2) ships regardless, so the primary bug is still fixed.

### Phase 2: Platform hardening (weeks 3-4, ~12 hours)

Once POC passes, flesh out the pi.dev + Temporal platform for reuse across skills:

1. **Formalize the `pi-temporal-activity` extension** as a shared package — one extension, used by every migrated skill
2. **Build a pi.dev coordinator template** — skeleton for new coordinator skills (state.json schema, run-directory structure, hypothesis/critique/judge patterns)
3. **Docs** — migration guide for moving a Claude Code coordinator skill to pi.dev
4. **Testing infrastructure** — unit + integration tests for the extension; contract tests for the coordinator template

### Phase 3: Migration (weeks 5-8, ~20 hours total)

Migrate in this order, ~2-4 hours each:

1. **deep-debug** — already ported in POC; promote from POC to production quality
2. **deep-idea** — smaller scope, simpler coordination pattern
3. **consensus-plan** — sequential, not parallel; simpler
4. **deep-qa** — uses pipelined judges; good exercise for extension patterns
5. **deep-design** — larger coordinator loops; tests scalability
6. **deep-research** — largest / longest-running coordinator; last because riskiest

After each migration:
- Run skill end-to-end on a representative task
- Decommission that skill's flux wrapper in Claude Code
- Commit migration

At the end of Phase 3: all coordinators live on pi.dev. Flux's role narrows to "transitional adapter, no longer in active use."

### Phase 4: Sunset flux (week 9, ~4 hours)

1. Verify no skills depend on flux
2. Move `~/.claude/skills/.shared/flux/` to `archived/flux-*/` with a note explaining the migration
3. Remove hook entries from `~/.claude/settings.json`
4. Update `2026-04-18-flux-temporal-orchestration-design.md` with a superseded-by notice

## Total effort

~8 weeks elapsed; ~48 hours part-time. Compare to original harness-eval spec's 20 hours for eval-only + TBD migration. Net: same "decision-plus-execution" time, but we've cut the "compare alternatives" overhead by committing early.

## Success criteria

1. All 6 coordinator skills run on pi.dev with Temporal-backed activities
2. A deliberately-hung sub-agent is detected within heartbeat_timeout and auto-retried
3. Coordinator session crash resumes cleanly from state (Temporal retains activity history)
4. No skill regresses in functionality or observable output format vs. its Claude Code version
5. Flux is archived, not deleted (so flux is recoverable if pi.dev surprises us later)
6. A new coordinator skill can be authored on pi.dev from the template in ≤1 day

## Dependencies / risks

**Dependencies:**
- `@mariozechner/pi-coding-agent` + `pi-agent-core` + `pi-ai` (npm packages)
- `@temporalio/client` + `@temporalio/worker` (Temporal TS SDK)
- Node.js 20+
- Temporal CLI (same as flux/P2)

**Risks & mitigations:**

| Risk | Probability | Mitigation |
|---|---|---|
| pi.dev's skill format isn't as compatible as advertised | Medium | POC's skill port is the explicit test; fail fast at week 2 |
| Lifecycle events don't cover all sub-agent dispatch patterns | Medium | POC exercises the orchestration patterns used in deep-debug; if gap, assess whether to patch pi.dev or abandon |
| Mario Zechner becomes unresponsive mid-migration | Low-medium | Fork is cheap; pin specific versions; our POC extension runs against a specific commit |
| Temporal TypeScript SDK has bugs we hit | Low | SDK is production-grade; pin version; fall back to Python SDK via subprocess if needed |
| pi.dev's CLI has rough edges for long-running coordinator patterns | Medium | POC reveals this; may need to upstream fixes or maintain a fork |
| Single-maintainer upstream stops accepting PRs | Low | Fork and maintain our own branch |

## Relationship to flux (P2)

**During migration:** flux and pi.dev coexist. Skills that haven't migrated yet stay in Claude Code with flux hardening them. Skills that have migrated run natively on pi.dev.

**After migration:** flux is archived. The pi-temporal-activity extension is the permanent integration.

**If migration fails (any phase):** flux remains in Claude Code, handling what it can. The P4 spec marks that phase's scope as "superseded, migration paused — flux is the permanent answer until reassessed."

## Open questions (for user review before Phase 1)

1. **pi.dev version pin** — pin to a specific commit SHA, or track `main`? Proposal: pin to a commit at POC start; bump deliberately.
2. **Where to host the `pi-temporal-activity` extension** — in the pi-mono monorepo (upstream contribution) or private repo? Proposal: private repo first; upstream only if the extension is generally useful AND pi.dev maintainer welcomes it.
3. **Skill format port automation** — write a one-time converter script, or hand-port each skill? Proposal: hand-port deep-debug in POC; if patterns are consistent, automate before Phase 3.
4. **Fallback if POC fails** — is goose still on the table as backup, or are we fully committed to "flux or pi.dev, nothing else"? Proposal: flux-only as permanent fallback; goose is off the table (we evaluated it and chose pi.dev).

## Supersedes

This spec supersedes `2026-04-18-custom-harness-evaluation-design.md`. That spec's 4-week 3-candidate evaluation is no longer planned; it remains in the repo as history but is not current design.

---

## Post-spec-review workflow

After user approves:
1. Flux/P2 implementation proceeds (already approved; `superpowers:writing-plans` invokes for it separately)
2. Week 2: POC begins; decision gate at week 2 end
3. If POC passes: Phase 2 starts; `superpowers:writing-plans` invokes for Phase 2/3 execution
4. If POC fails: document findings; revise this spec to "flux-only, pi.dev archived"
