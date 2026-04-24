STRUCTURED_OUTPUT_START
DIMENSION|cost_runaway_risk
ANGLE|spawning-economics-and-rejection-loop-caps
REVIEWER|angle-4-cost

---

## Defect 1: team skill has no rejection cap — unlimited panel cycles

TITLE|team-skill-missing-rejection-cap
SEVERITY|critical

**Concrete scenario:** A team execution generates an artifact with a persistent but fixable defect (e.g., a test fixture always fails on the CI environment). The panel consistently returns `rejected_fixable`. The team-fix loop re-queues and fires a fresh 5-agent panel. The "How skills consume the panel verdict" section for `team` states:
- `rejected_fixable` → proceed to Step 6 (team-fix) with defect registry from panel

There is no `reviewer_rejection_count` or cap mentioned anywhere in the `team` section. Only `loop-until-done` (Step 7) specifies "Rejection counting still applies: `reviewer_rejection_count` increments per panel rejection, cap at 5." The `team` skill's Step 5 panel has no equivalent statement. A fix-reject loop in `team` can run indefinitely, burning 5 agents per cycle with zero termination gate.

**Root cause:** The rejection-counting contract is declared in the consuming skill (`loop-until-done`) rather than mandated by the pattern itself. The integration checklist (lines 214–224) does not include "consuming skill MUST implement a rejection cap." Skills that fail to carry forward this requirement get no cap by default.

**Remediation:** Add to the integration checklist: "Consuming skill MUST define a `reviewer_rejection_count` cap (recommended: 5) and terminate with `review_loop_exhausted` when exceeded." Also add a row to the Failure Modes table: "Consuming skill reaches rejection cap → terminate with `review_loop_exhausted`."

---

## Defect 2: team + loop-until-done stacking multiplies worst-case agent count

TITLE|stacked-rejection-loops-double-worst-case-spend
SEVERITY|critical

**Concrete scenario:** According to the artifact, `team` (Step 5) and `loop-until-done` (Step 7) are both consuming skills. The artifact says the team panel fires "once on the aggregate output of all workers" and then `rejected_fixable` sends work to Step 6 (team-fix), which eventually cycles back to Step 5 (panel again). Once Step 5 approves, work moves to Step 7 where the loop-until-done panel fires with its own cap of 5 cycles.

Worst case: team fires 5 panel cycles (5 × 5 agents = 25 agents) and exhausts its cap (if it even has one — see Defect 1). Then loop-until-done fires 5 more panel cycles (5 × 5 agents = 25 more agents). Total: 50 Sonnet agents on a single artifact run. The artifact's math section ("worst case is 25 Sonnet agents") accounts for only one skill's rejection loop in isolation and does not acknowledge that consuming skills can themselves be composed in a pipeline.

**Root cause:** The artifact analyzes cost per-skill but not per-pipeline. The pattern makes no statement about cross-skill composition costs.

**Remediation:** Add a "Composition cost ceiling" section specifying that when multiple consuming skills chain (team → loop-until-done), only one rejection cap is active at a time, and that the pipeline-level orchestrator is responsible for a global agent budget cap.

---

## Defect 3: ship-it has no rejection cap stated — not even implicitly

TITLE|ship-it-panel-rejection-cap-absent
SEVERITY|major

**Concrete scenario:** The `ship-it` section (lines 174–182) states what happens on each verdict:
- `approved` → (implied: proceed)
- `rejected_fixable` → (not stated — the section only describes what the panel subsumes from the three-judge protocol, not what the calling skill does on rejection)
- `rejected_unfixable` → (not stated)

The entire `ship-it` consumption section describes structural replacement ("The panel's 4 lenses subsume the three judges") but says nothing about the rejection loop, its cap, or termination conditions. A skill author wiring ship-it Phase 6 has no guidance on when to stop retrying. Unlike `loop-until-done` which explicitly states `reviewer_rejection_count` cap at 5, `ship-it` is silent.

**Root cause:** The "How skills consume the panel verdict" sections are inconsistently specified. `loop-until-done` gets full rejection-loop semantics; `team` gets partial; `ship-it` gets none.

**Remediation:** Each consumer section must specify: the full verdict→action mapping for all three verdicts, the rejection cap value, and the terminal state on cap exhaustion.

---

## Defect 4: "Fresh panel every time" mandate eliminates incremental cost savings

TITLE|mandatory-fresh-panel-burns-full-context-every-cycle
SEVERITY|major

**Concrete scenario:** The integration checklist states: "Previous panel results do NOT carry forward across fix iterations — fresh panel every time." This is presented as a correctness requirement (no anchoring). However, it means that on every rejection cycle, all 5 agents receive the full context payload again — spec file, modified files list, diff, test output, build/integration output — with zero reuse of prior approved findings.

If the diff on cycle 2 only changes 3 lines (a targeted fix), 4 reviewers still re-review the entire spec + full diff from scratch. The incremental cost of a fix cycle is identical to the cost of the initial review. There is no acknowledgment of this cost structure, no guidance to consuming skills about batching fixes before re-paneling, and no suggestion to scope the diff to changed files only.

**Root cause:** The "no anchoring" correctness motivation is sound but the cost consequence is unacknowledged. The artifact treats this as a pure correctness win with no cost tradeoff noted.

**Remediation:** Note explicitly that fresh-panel-every-time is a deliberate correctness-vs-cost tradeoff. Recommend that consuming skills batch multiple fix stories before triggering a re-panel rather than re-paneling after each individual fix.

---

## Defect 5: Timeout retry path is unbounded

TITLE|timeout-retry-has-no-cap
SEVERITY|major

**Concrete scenario:** The Failure Modes table (line 197) states: "3+ reviewers time out → Panel failed — cannot produce a verdict from 1 reviewer. Retry with increased timeout. If retry fails: terminate with `review_unavailable`."

This allows exactly 2 attempts (initial + 1 retry). But the phrasing "If retry fails" implies a binary. What if the retry produces a 2-of-4 quorum (below the required 3-of-4)? Does the skill retry again? The quorum rule (line 122) says "3 of 4 reviewers must return parseable output" but the retry-on-timeout path does not specify whether a sub-quorum partial result triggers another retry or terminates. An implementation that retries until quorum is met has no stated upper bound.

Furthermore, "Retry with increased timeout" means each retry spawns up to 5 agents again (4 reviewers + 1 meta). Two retries = 15 agents spent just on the review infrastructure failure path, before any fix-rejection cycles begin.

**Root cause:** The timeout failure mode specifies the first retry but not the retry cap. The interaction between the quorum rule and the retry rule is unspecified.

**Remediation:** State explicitly: "Maximum 1 retry on timeout failure. If the retry does not meet quorum, terminate with `review_unavailable`. Do not cascade retries."

---

## Defect 6: No total-cost gate or wall-clock budget for the panel pattern itself

TITLE|no-aggregate-cost-ceiling-across-all-cycles
SEVERITY|major

**Concrete scenario:** The artifact specifies per-reviewer timeouts (180s / 300s) but no aggregate cost control: no maximum total agents spawned across all cycles, no dollar cap, no wall-clock cap for the entire review lifecycle. A skill can legally run 5 rejection cycles (cap on loop-until-done), each spawning 5 agents, for 25 agents total — and this is considered "within spec." There is no mechanism for a consuming skill or the pattern itself to say "this run has already spent N agent-minutes; stop."

Timeouts prevent any single agent from running indefinitely, but they do not constrain the number of agents spawned. A 180s timeout on 25 agents = 75 agent-minutes of possible compute, all within spec.

**Root cause:** The pattern conflates "per-agent time bounds" with "total cost bounds." These are different constraints. Per-agent timeouts prevent runaway individual agents; they do not prevent a large number of short agents from accumulating cost.

**Remediation:** Specify a pattern-level cost ceiling: "No consuming skill may spawn more than N total reviewer-agents (across all cycles) in a single run. Recommended N=15 (3 full cycles). Exceeding this threshold terminates with `review_budget_exhausted`."

---

## Defect 7: Quorum degraded-mode still triggers meta-reviewer — hidden agent cost

TITLE|degraded-mode-still-spawns-meta-reviewer
SEVERITY|minor

**Concrete scenario:** When smoke-test times out, the panel proceeds in "degraded mode" (line 122). The meta-reviewer still fires. This is correct for correctness but means that a single reviewer timeout does not save any agent spend — you still get 4 agents total (3 live reviewers + 1 meta-reviewer). The only savings from a reviewer timeout is the timed-out agent's wall-clock time. There is no degraded-mode cost path where agent count is reduced.

**Root cause:** Degraded mode is defined as a correctness-continuity mechanism but not as a cost-reduction mechanism. These are different goals and the artifact doesn't distinguish them.

**Remediation:** Minor documentation issue: state explicitly that degraded mode does not reduce agent cost — it only prevents a single timeout from blocking the verdict. This sets correct expectations for consuming skill authors estimating cost.

---

## New angles identified (not covered by this dimension)

ANGLE_NEW|panel-context-size-scaling: The artifact requires passing full context (spec + diff + tests + build output) to all 4 reviewers every cycle. For a large monorepo change, the diff alone could exceed token limits. The artifact does not specify what happens when reviewer context exceeds the model's context window, nor does it specify truncation policy. A reviewer silently truncating context would produce a partial review that passes quorum and generates a false `approved`.

ANGLE_NEW|meta-reviewer-independence-not-enforced: The meta-reviewer receives all 4 reviewer output files. If those files are large (verbose defect lists), the meta-reviewer's own context could be dominated by reviewer content, crowding out the spec and diff. The artifact specifies "fresh context" (line 127) but doesn't specify a maximum reviewer output size or truncation policy for meta-reviewer input.

ANGLE_NEW|smoke-test-cost-asymmetry: Smoke-test gets 300s vs 180s for other reviewers. On a rejection cycle, if smoke-test is the last to complete, every other reviewer (and potentially the meta-reviewer spawner) waits on it. The 300s timeout is the bottleneck of the critical path for every cycle. The artifact does not specify whether the meta-reviewer can start partial synthesis while waiting for smoke-test, or whether it must wait for all 4 to complete first.

STRUCTURED_OUTPUT_END
