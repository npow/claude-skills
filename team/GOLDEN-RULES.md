# Golden Rules

Eight cross-cutting rules apply to every invocation. Each is stated with a concrete `/team` example so there is no ambiguity at the gate.

## 1. Independence Invariant

**Rule:** The coordinator orchestrates. It never evaluates. Severity, approval, correctness, falsifiability are delegated to independent judge agents.

**Concrete `/team` examples:**
- Plan quality: verdict written by `plan-validator` agent, not by the coordinator reading the plan and declaring "looks good."
- PRD acceptance criteria falsifiability: judged by a separate `falsifiability-judge` agent. The coordinator only reads `prd/falsifiability-verdict.md`.
- Worker completion: cannot be accepted based on the worker's `SendMessage` alone. Requires the two-stage review verdicts on the worker's diff.
- Verify stage verdict: written by `verify-judge` (opus, separate context) reading the Stage A + Stage B outputs. Coordinator never summarizes both into a self-issued verdict.

**Detection at review:** every verdict file's metadata must include `written_by: <agent_id>` and `agent_role != coordinator`. If any load-bearing claim in `state.json` traces back to a coordinator-authored file, invariant is violated.

## 2. Iron-Law Verification Gate

**Rule:** No stage advances until `state.stages[<stage>].evidence_files` is non-empty AND every listed path exists on disk AND every structured-output file has `STRUCTURED_OUTPUT_START`/`END` markers.

**Concrete `/team` examples:**
- `team-plan → team-prd` blocked unless `handoffs/plan.md` + `handoffs/plan-verdict.md` on disk with `VERDICT: approved`.
- `team-exec → team-verify` blocked unless every AC has three evidence files (`-red.txt`, `-green.txt`, `-verify.txt`) on disk AND the per-worker two-stage review verdicts on disk.
- `team-verify → team-fix` blocked unless `verify/verdict.md` on disk with `VERDICT: failed_fixable`.
- `team-fix → team-verify` (re-entry after fix iteration) blocked unless every targeted defect has a per-fix verifier verdict on disk.

**Detection at review:** Pre-transition gate steps 1-5 in STATE.md. Any step fails → log rejection, do not advance.

## 3. Two-Stage Review on Every Source Modification

**Rule:** Every stage that modifies source files gets two independent reviews: spec-compliance (matches the PRD?) THEN code-quality (built well?). Separate agents, separate contexts, separate spawn calls. Not one pass. Not one agent wearing two hats.

**Concrete `/team` examples:**
- In `team-exec`: each worker's diff gets `verify/per-worker/{worker}-task-{id}/spec-compliance.md` AND `code-quality.md` with distinct `agent_id` values.
- In `team-verify`: aggregated diff gets `verify/spec-compliance/defect-registry.md` AND `verify/code-quality/review.md`. The stage-level verdict is written by a THIRD independent agent (`verify-judge`).
- In `team-fix`: the fix diff goes back through `team-verify`'s two-stage review from scratch. Previous verify results are discarded (iron-law: fresh evidence every stage).

**Detection at review:** `invariants.two_stage_review_enforced` check in STATE.md. Fails if any reviewed diff has fewer than two distinct agent verdicts or if the same `agent_id` produced both.

## 4. Honest Termination Labels

**Rule:** Exactly one of five labels. Never "no issues remain", "all done", "LGTM", "done-done."

| Label | Meaning |
|---|---|
| `complete` | Every AC verified green; zero unresolved critical/major defects. |
| `partial_with_accepted_unfixed` | Critical defects all fixed; some major/minor explicitly accepted with rationale. |
| `blocked_unresolved` | Critical defect with no path forward AND fix budget not exhausted. |
| `budget_exhausted` | Fix budget reached with unresolved critical/major defects. |
| `cancelled` | User interrupted. |

**Concrete `/team` examples:**
- 5 ACs pass, 1 AC produces a minor defect that product accepts → `partial_with_accepted_unfixed` (NOT `complete`).
- All ACs pass but `team-verify` found a security issue that was accepted as "out of scope for this sprint" → `partial_with_accepted_unfixed`.
- PRD falsifiability judge rejects two criteria after revision cap → `blocked_unresolved`.
- Fix iteration 3 still has unresolved critical from `team-verify` → `budget_exhausted`.

**Detection at review:** `SUMMARY.md` and `state.termination` must match and must be one of the five. Any non-enum value is a bug.

## 5. State Written Before Agent Spawn

**Rule:** `spawn_time_iso` is persisted to `state.json` BEFORE the `Task` / `Agent` / `TeamCreate` call. Spawn failure is recorded as `spawn_failed`; resume retries spawn. A spawned agent that never produced output is `timed_out`, which does NOT auto-retry.

**Concrete `/team` examples:**
- Before spawning the `planner`, state has `stages[0].agent_spawns[<i>].spawn_time_iso = <ISO>` and `status: "spawned"`.
- If `Task(...)` returns an error: state updated to `status: "spawn_failed"`, `spawn_time_iso: null`.
- Resume re-runs spawn for `spawn_failed` entries; it waits (or replaces) `timed_out` entries.

**Detection at review:** Every entry in any stage's `agent_spawns[]` with `status: spawned` and no matching output file on disk is either correctly `timed_out` (post-timeout window) or an invariant violation.

## 6. Structured Output Is the Contract

**Rule:** Every judge/critic/reviewer/verifier output has `STRUCTURED_OUTPUT_START`/`END` markers. Coordinator reads ONLY lines inside the markers. Unparseable → fail-safe worst-case verdict for that check.

**Concrete `/team` examples:**
- `plan-verdict.md` must contain `VERDICT|approved|...` inside markers. Missing markers → treated as `VERDICT: rejected` (fail-safe).
- `falsifiability-verdict.md` without `AC_VERDICT|AC-N|falsifiable|...` line for every AC → treated as `unfalsifiable` for all missing ACs.
- Code-reviewer output missing markers → treated as `failed_fixable` (worst non-unfixable verdict).

**Detection at review:** Every agent output file gets an initial marker scan before parsing. Results logged to `logs/gate_decisions.jsonl` with either `structured_ok: true` or the fail-safe verdict.

## 7. All Data Passed Via Files

**Rule:** PRDs, diffs, AC lists, defect registries, flaw descriptions go in files on disk before the agent call. Inline prompts contain paths only, never substantive content. Inline data is silently truncated by the harness.

**Concrete `/team` examples:**
- `team-exec` worker preamble passes `{prd_final_path}` and `{assignment_file_path}` — not inlined PRD content.
- `deep-qa --diff` is invoked on `verify/diff.patch`, not with the diff text embedded in the invocation.
- `per-fix verifier` receives `fix/defect-{id}-work.md` + diff file path + evidence file paths — not the fix text inline.

**Detection at review:** Every `agent_spawns[].input_files` array is non-empty and every listed path exists on disk before spawn time.

## 8. No Coordinator Self-Approval

**Rule:** Same context cannot author and approve. Every stage-complete gate requires an independent agent's verdict file on disk. The coordinator can write handoff files summarizing what its agents produced — it cannot write verdicts on its own summaries.

**Concrete `/team` examples:**
- Coordinator writes `handoffs/exec.md` summarizing what workers did. The approval of that handoff (for advancing to verify) is decided by the per-worker two-stage review verdicts already on disk — not by the coordinator reading the handoff and nodding.
- `team-verify → termination = complete`: requires `verify/verdict.md` with `VERDICT: passed` authored by `verify-judge`. Coordinator cannot directly set `termination = complete` based on its own reading of defect counts.

**Detection at review:** Every `stages[].exit_gate_verdict` must trace to a verdict file with `agent_role != coordinator`. State invariant #7 in STATE.md.

---

## Anti-Rationalization Counter-Table

The coordinator WILL be tempted to skip steps. These are the talking points it must reject.

| Excuse | Reality |
|---|---|
| "The planner's output is obviously good; I'll skip the plan-validator." | No. Independence invariant holds for trivial cases too. The validator also catches schema violations the planner might miss. |
| "Falsifiability check is overkill for this small PRD — I'll eyeball it." | No. The judge takes one agent call. Eyeballing ACs is where "should work" bugs are born. |
| "Worker sent `task_complete`; I'll trust the message and skip the two-stage review." | No. The message is a claim, not evidence. Two-stage review is what turns the claim into evidence. |
| "Stage A (spec-compliance) found no defects. I'll skip Stage B (code-quality)." | No. Two-stage review is non-negotiable. Stage B finds what Stage A cannot — maintainability, idiom violations, duplication. |
| "The code-reviewer also did spec-compliance inline; that counts as Stage A." | No. Same agent, same context = single-pass review. Counts as neither. |
| "We're at fix iteration 3/3 and close; I'll accept the remaining critical as 'minor'." | No. Critical cannot be accepted; only minor can. This is `budget_exhausted`, not `partial_with_accepted_unfixed`. |
| "I verified in the previous round; skipping verify this iteration." | No. Iron-law: fresh evidence every stage. Previous verify is stale. |
| "The per-fix verifier is extra overhead; the team-verify pass will catch regressions." | No. Per-fix verifiers catch "the fix doesn't actually address the defect" — a different failure mode. Team-verify catches regressions. Both needed. |
| "Worker skipped the red test on this AC because the logic is 'obvious'." | No. TDD red is the contract. No red.txt → worker completion is INVALID. Re-do the task. |
| "I'll write `verify/verdict.md` myself — the judge is a waste of tokens." | No. That is coordinator self-approval. Rule 8 violation. |
| "I'll mark all defects as accepted rationale to end the run." | No. Critical + major cannot be accepted. Only minor, and only with a written rationale the verify-judge sees. Overrides by coordinator are invariant violations. |
| "The degraded-mode fallback is functionally equivalent to deep-qa." | No. It is documented as lower-quality and must be tagged `VERIFICATION_MODE: degraded` in output. Never silently substitute. |

When the coordinator finds itself about to reach for any of these excuses: it stops, writes the verdict / spawn / evidence file, and proceeds the right way. The extra agent call is the cost of correctness.
