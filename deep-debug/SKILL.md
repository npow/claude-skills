---
name: deep-debug
description: Use when a bug, test failure, or unexpected behavior needs diagnosing — including production incidents, regressions, stack traces, mysterious failures, flaky tests, or any symptom needing root-cause analysis. Trigger phrases include "debug this", "why is this failing", "find the bug", "fix the bug", "root cause", "what's wrong with", "this is broken", "diagnose", "troubleshoot", "investigate this failure", "the test is failing", "this used to work", "why doesn't this work", "where's the bug". Adversarial hypothesis-driven debugging with parallel competing hypotheses across orthogonal dimensions, blind independent judging, discriminating probes that falsify leaders, TDD-gated fix loops, and mandatory architectural escalation after 3 failed attempts.
user_invocable: true
argument: The bug description, symptom, error message, or reproduction context
---

# Deep Debug Skill

Adversarial hypothesis-driven debugging. Given a bug, generate competing hypotheses across orthogonal dimensions, judge each independently (two-pass blind), run discriminating probes that falsify the weaker, fix the survivor with test-first discipline, and escalate to architectural review after 3 failed attempts. Output is a verified fix with a failing-test-now-passes proof, OR an honest termination label naming why the bug resisted a code-level fix.

## Execution Model

All operations use Claude Code primitives. These contracts are non-negotiable:

- **All data passed to agents via files, never inline.** Evidence, hypothesis lists, probe specs, known-hypothesis IDs — all written to disk before the agent prompt. Inline data is silently truncated.
- **State written before agent spawn, not after.** `spawn_time_iso` is written to state.json before the Agent tool call. Spawn failure records `spawn_failed` status. Resume uses persisted state, never in-memory reconstruction.
- **Structured output is the contract; free-text is ignored.** Every judge, probe-verdict, and validator produces machine-parseable structured lines. Coordinator reads only structured fields. Unparseable output triggers fail-safe classification (`disputed`, never `rejected`). Hypothesis output files MUST contain `STRUCTURED_OUTPUT_START`/`STRUCTURED_OUTPUT_END` markers; files without these markers are treated as failed.
- **No coordinator self-review of anything load-bearing.** Hypothesis plausibility, evidence tier, rebuttal verdicts, probe winner classification — all delegated to independent agents. The coordinator orchestrates; it does not evaluate.
- **Termination labels are honest.** One of 7 defined labels. Never "probably fixed," never "looks right," never "no critical bugs remain." A fix is `Fixed — reproducing test now passes` only when the failing test exists, passes with the change, and the full suite is clean.
- **Hard ceilings are absolute.** `max_cycles = 3`, `max_probes_per_cycle = 3`, `fix_attempt_count ≤ 3`. Three fix attempts is evidence the hypothesis space is wrong — Phase 7 architectural escalation is mandatory, never optional.

**Shared contracts:** this skill inherits the four execution-model contracts (files-not-inline, state-before-agent-spawn, structured-output, independence-invariant) from [`_shared/execution-model-contracts.md`](../_shared/execution-model-contracts.md). The items listed above are the skill-specific elaborations; the shared file is authoritative for the base contracts.

**Subagent watchdog:** every `run_in_background=true` spawn (hypothesis agents, judges, evidence-gatherer, architect) MUST be armed with a staleness monitor per [`_shared/subagent-watchdog.md`](../_shared/subagent-watchdog.md). Use Flavor A with thresholds `STALE=5 min`, `HUNG=20 min` for Sonnet hypothesis agents; `STALE=3 min`, `HUNG=10 min` for Haiku judges and evidence-gatherer. Debugging agents that hang silently are the exact failure mode this skill is meant to prevent — applying it to the skill itself is load-bearing. Contract inheritance: `timed_out_heartbeat` joins this skill's 7-label termination vocabulary at the per-lane level (hypothesis agent / judge / probe); `stalled_watchdog` and `hung_killed` join `hypotheses.{id}.status`. A watchdog-killed hypothesis lane never returns `leading` or `rejected` — its verdict is absent, not assessed.

## Philosophy

Debugging fails most often in three ways:
1. **Fixation on the symptom site** — the stack trace points at file:line, the fix goes there, the real cause is 5 calls upstream. Solo debuggers rarely trace data-flow all the way back.
2. **Hypothesis anchoring** — you form the first plausible hypothesis, evidence confirms it (because you're looking for confirmation), you fix it, the bug returns.
3. **Fix-and-retry spiral** — 3 failed attempts is the signal the abstraction is wrong, but under time pressure debuggers try fix #4, #5, #6, each one revealing a new problem in a different location.

Deep-debug addresses all three structurally:
- **Orthogonal dimensions** force at least one hypothesis in `concurrency`, `environment`, and `architecture` categories — the three most commonly under-investigated
- **Independent judge with disconfirmation mandate** prevents anchoring on the first fit
- **Hard architectural escalation at 3 failed fixes** converts fix-spiral into a conscious pattern-level decision

If you only take one idea from this skill: **evidence-for and evidence-against are the hypothesis contract**. A hypothesis without disconfirming searches is never `leading`; it's `plausible` at best. See EVIDENCE.md.

## The Iron Law

```
NO FIXES WITHOUT A HYPOTHESIS THAT SURVIVES INDEPENDENT JUDGE + DISCRIMINATING PROBE
```

If Phase 3 judge has not classified the hypothesis as `leading` AND Phase 4 probe has not confirmed it against the next-best alternative, you cannot advance to Phase 5. Violating the letter of this process is violating the spirit of debugging.

## When to Use

Use deep-debug for:
- Bugs that survived a quick-fix attempt (systematic-debugging already ran and the symptom remains or moved)
- Production incidents requiring post-mortem rigor
- Test failures that cannot be reproduced locally
- Performance regressions where the cause is ambiguous
- Build / deploy / signing / infrastructure failures with multi-layer pipelines
- Behavior divergence between environments (local ✓, CI ✗, or one deployment region only)
- Any bug where ≥ 2 plausible root causes exist and the coordinator is tempted to guess

**Don't use for:**
- Obvious typos, compiler errors with clear messages, or known-issue-with-known-fix cases → use `superpowers:systematic-debugging`
- Test flakiness where the target is "is this test flaky, and why specifically?" → use `flaky-test-diagnoser` (it's purpose-built)
- Bugs the user already has a hypothesis for and just wants implemented → implement directly; save deep-debug for when the cause is genuinely unknown
- Pure code review or static audit → use `deep-qa` with `--type code`

## Workflow

### Phase 0: Input Validation Gate

Before any cycle begins, validate the symptom. **Batch clarifying questions** — if multiple surface here, present them in one message as a numbered list. Never serially.

**Step 0a — Safety check:**
- Symptom describes a bug in the user's code, not a request to attack a third-party system
- If harmful: refuse

**Step 0b — Scope check:**
- Is the symptom specific enough to investigate? ("the app is slow" is too vague; "POST /api/orders p99 latency jumped from 200ms to 2s after {commit}" is fine)
- If too vague: ask for: exact error (copy-paste the message), reproduction steps (commands that trigger it), affected environment (local/CI/prod), and when it started (timestamp or "since merge X")

**Step 0c — Reproduction confirmation:**
- Attempt to reproduce immediately (run the provided command; trigger the flow)
- Record status in state: `confirmed` (every time), `intermittent` (1-in-N with rate), or `unreproducible` (cannot trigger)
- `unreproducible` → user batch-question: can they provide fresh logs, a stack trace, or a less-filtered reproduction?
- Still `unreproducible` after user input → terminate with label `Cannot reproduce — investigation blocked` and exit cleanly. Do NOT hypothesize against a bug you cannot see.

**Step 0d — Symptom locking:**
- Extract a ≤200-word symptom statement — the exact error, the surface, when it started, the reproduction command
- Compute `symptom_sha256`; store in state.json
- This statement is the concept-anchor — every hypothesis is a causal explanation of this symptom. Later phases MUST NOT silently rewrite the symptom to match an emerging hypothesis. `symptom_sha256` catches tampering.

**Step 0e — Pre-mortem micro-round (blind-spot seeding):**
Before Phase 2 expansion, spawn 1 Haiku agent with this prompt:

> Given the symptom `{symptom}`, list 5 concrete ways this debugging investigation could miss the real cause. Cover these angles:
> 1. Wrong dimension — the symptom looks like {apparent dimension} but is actually {other dimension}
> 2. Measurement artifact — the bug might not exist; we could be reading stale/wrong evidence
> 3. Environment assumption — local behavior assumed, production differs
> 4. Framework-contract blindness — something assumed guaranteed that actually isn't
> 5. Architectural drift — this is symptom N of an architectural problem; fixing here won't hold
> Output to `deep-debug-{run_id}/premortem.md` with one concrete claim per angle.

Each flagged blind-spot becomes an angle with `priority: critical` and `source: premortem` in Phase 2.

**Step 0f — Pre-run scope declaration:**
```
Deep debug: "{symptom}"
Reproduction: {confirmed | intermittent (1-in-N) | unreproducible-investigation-blocked}
Dimensions: 8 (code-path, data-flow, recent-changes, environment, framework-contract, concurrency-timing, measurement-artifact, architectural-coupling)
Max cycles: {default 3}    | Hard stop: {6} cycles    | Budget cap: ${25.00}
Estimated cost: ~$3-8 per cycle (Sonnet hypothesis + Haiku judge + Haiku probes)
Invocation: {interactive | --auto | --hard-mode}
Continue? [y/N]
```
Skip gate if `--auto`.

**Print:** `Starting deep-debug on: {symptom_excerpt} [run: {run_id}]`

---

### Phase 1: Evidence Gathering

**Purpose:** Collect the ground-truth artifacts every hypothesis in Phase 2 will be evaluated against. Evidence is tier-ranked per EVIDENCE.md.

**Step 1a — Symptom capture (always):**
- Exact error text / stack trace / log excerpt — copy verbatim into `deep-debug-{run_id}/evidence.md` §Symptom
- Timestamp of first occurrence (if known)
- Reproduction command (from Phase 0c)

**Step 1b — Recent changes snapshot (always):**
- `git log --since='7 days ago' --oneline -- {affected-paths}` → evidence.md §Recent Changes
- Lock file diffs (`package-lock.json` / `poetry.lock` / `Gemfile.lock`) vs. last-known-good, if known
- Config diffs
- Even if this looks unrelated to the symptom, record it. `recent-changes` is one of the 8 dimensions — agents will search for the connection.

**Step 1c — Boundary instrumentation (when multi-layer):**
- If the system has obvious layer boundaries (workflow → build → sign; API → service → DB; frontend → gateway → backend): add instrumentation at each layer to log inputs/outputs
- Run the reproduction once with instrumentation; capture all layer logs into evidence.md §Boundary Instrumentation
- This converts tier-5 stack-position guesses into tier-2 primary-artifact evidence for Phase 2
- Skip if single-layer or instrumentation would take > 30 minutes (add to Phase 4 probe list instead)

**Step 1d — Lock evidence:**
- evidence.md is append-only after Phase 1. Phase 4 probe results append to §Probe Log; nothing rewrites earlier sections.

---

### Phase 2: Hypothesis Generation

**Prospective gate (fires BEFORE spawning):**

Coordinator outputs:
```
Cycle {N}: about to spawn 6 hypothesis agents + 1 outside-frame agent (Sonnet tier).
Estimated cost: ~${estimate} (cumulative: ${running_total} of ${budget_cap})
Dimensions queued: {list of angles' dimensions}
Required categories covered so far: {counts from state.json}
Continue? [y/N/redirect:<focus>]
```
Skip if `--auto`. If `--auto` AND cumulative budget exceeds 80% of cap: force user confirmation even in auto mode (budget backstop).

**Step 2a — Enumerate angles (see DIMENSIONS.md):**

For cycle 1:
- Generate 2–4 angles per dimension (8 dimensions × 2–4 = 16–32 angles)
- Generate 2–3 cross-dimensional angles
- Add `premortem` angles from Phase 0e
- Cap total frontier at 30. Priority-order per DIMENSIONS.md §Priority Ordering.

For cycle 2+:
- Start from graveyard (hypotheses rejected in prior cycle) — what dimensions were under-investigated?
- Add CRITICAL-priority angles for any dimension that had zero hypotheses accepted by the judge
- Add CRITICAL-priority angles for any required category still uncovered

**Step 2b — Write data files before spawning:**
- `deep-debug-{run_id}/known-hypotheses.md` — list of all prior-cycle hypothesis IDs and 1-line titles (so critics don't re-propose)
- `deep-debug-{run_id}/angles/{angle_id}.md` — one file per angle with dimension, question, parent, rationale
- `deep-debug-{run_id}/evidence.md` is referenced by path; critics read it directly

**Step 2c — Spawn hypothesis agents (parallel):**

- Pop up to 6 highest-priority angles; assign to spec-derived hypothesis agents
- **Spawn 1 additional outside-frame hypothesis agent (slot #7)** — seeded from the symptom only, not the current hypothesis list or evidence file narrative
- Before each spawn: write `status: "in_progress"`, `spawn_time_iso` to state.json
- Spawn each Agent in parallel (subagent_type: general-purpose, model: sonnet) with file paths — NOT inline content
- Hypothesis output path: `deep-debug-{run_id}/hypotheses/{angle_id}.md` (content-addressed — coordinator CANNOT overwrite)
- If Agent tool returns error: record `status: "spawn_failed"`, do not record as spawned; retry on next round

**Quorum:** Round complete if ≥ 4 of 6 spec-derived agents return parseable output within timeout (outside-frame tracked separately — its exit does not affect quorum).

**Timeout scaling:** 180s base. ×1.5 for cycles 2+ (larger evidence file).

**Circuit breaker:** ≥ 3 consecutive rounds with any critic failures → halt, log `SYSTEM_FAILURE_ROUND`, notify at turn boundary.

**Step 2d — After agents complete:**
- For each completed agent: read hypothesis file, extract hypothesis struct, dedup (see STATE.md Tier 1 + Tier 2), update state.json
- Spec-derived agents may suggest ≤ 1 new angle per cycle (immutable once written)
- Outside-frame agent may suggest ≤ 2 new angles (its exemption — it brings novel dimensions)
- Update coverage tracking: which dimensions / required categories are now covered?

---

### Phase 3: Independent Hypothesis Judge (two-pass blind)

**Purpose:** Classify every hypothesis into plausibility tiers (`leading | plausible | disputed | rejected | deferred`) using a judge that cannot see the critic's confidence claim during pass 1. This prevents inflation.

**Step 3a — Strip confidence from each hypothesis file:**
- Coordinator produces `deep-debug-{run_id}/judge-inputs/batch_{cycle}_{batch_num}.md` (up to 5 hypotheses per batch)
- Stripping is mechanical: remove the `**Confidence:**` line and the `CONFIDENCE:` field from STRUCTURED_OUTPUT
- Stripping recorded in state.json as `judge_input_stripped: true`
- Original hypothesis files stay immutable

**Step 3b — Spawn background batched judge (Haiku):**
- Batch ≤ 5 hypotheses per agent (cost optimization)
- Agent receives: batch input file path, evidence file path, known-hypothesis list
- Run in background (`run_in_background=true`) — next cycle's critics can start while judges finish
- Timeout: 90s per batch

**Step 3c — Two-pass judge protocol (see FORMAT.md §Judge Verdict):**
- **Pass 1:** Judge classifies each hypothesis blind (no critic confidence claim). Applies 5 validation checks: falsifiability / contradiction / premise / evidence-grounding / simplicity (see §Validation Checks below). Writes pass-1 verdict to `deep-debug-{run_id}/judge-verdicts/batch_{cycle}_{batch_num}.md`.
- **Pass 2:** Coordinator provides the critic's confidence claim. Judge can CONFIRM, UPGRADE, or DOWNGRADE with rationale. Writes pass-2 addendum to the same file.
- Final plausibility is the pass-2 verdict.

**Step 3d — Judge integrity check:**
- After each cycle: if judge's `leading`-rate ≥ 80% on ≥ 5 hypotheses, flag `judge_suspect: true` in state and tag the cycle's leader `[JUDGE_SUSPECT]`. The coordinator does not re-decide — it surfaces the concern.

**Step 3e — Drain pending judges before Phase 4:**
- Use `TaskOutput` with `block=true` for each background judge batch
- Apply results to state.json (overwrite preliminary critic plausibility with judge's authoritative verdict)
- If a batch timed out: retain critic-proposed plausibility, set `judge_status: "timed_out"`, log `JUDGE_TIMEOUT: batch_{id}`

**Step 3f — Rebuttal round (if ≥ 2 hypotheses at `leading` or `plausible`):**
- Spawn independent rebuttal agent (Sonnet) — separate from judge
- Input: leader + strongest alternative + evidence file
- Output: `deep-debug-{run_id}/rebuttal-cycle{N}.md`
- See EVIDENCE.md §Rebuttal Round for protocol
- Update plausibility based on rebuttal outcome

---

### Phase 4: Discriminating Probe Execution

**Purpose:** Collapse uncertainty between the top-2 hypotheses with a concrete experiment. Not "think harder" — a command that produces hard evidence.

**Step 4a — Probe design:**
- If exactly 1 hypothesis at `leading` AND 0 hypotheses at `plausible` → no probe needed; advance to Phase 5 with the leader
- If ≥ 2 hypotheses at `leading` OR `plausible` → design a probe that distinguishes them

Probe requirements (see EVIDENCE.md §Discriminating Probe):
- Bounded time (≤30 minutes; ideally ≤10)
- Hard evidence output (log line, return value, test result)
- Pre-declared expected result for each hypothesis (post-hoc rationalization destroys probes)
- Reversible or non-destructive (touching production data requires user confirmation even in `--auto`)

**Step 4b — Write probe spec:**
- `deep-debug-{run_id}/probes/probe_{id}.md` (see FORMAT.md §Discriminating Probe Specification)
- `probe_count_this_cycle += 1` (hard cap: 3 per cycle)

**Step 4c — Safety check:**
- Does the probe write to production, delete data, or call an irreversible API? → USER CONFIRMATION REQUIRED
- If `--auto` AND probe is destructive → reject the probe; choose a safer alternative or defer the hypothesis

**Step 4d — Execute:**
- Simple probe (test, query, check): coordinator runs directly
- Complex probe (build artifact, multi-step instrumentation): spawn `evidence-gatherer` agent (Haiku, background) with probe spec as input
- Record raw output verbatim in `evidence.md` §Probe Log (NO summarization)

**Step 4e — Apply verdict:**
- Match actual result against pre-declared expectations:
  - Matches "expected if A" → A wins; B's status → `falsified_by_probe`
  - Matches "expected if B" → B wins; A's status → `falsified_by_probe`
  - Matches neither / matches both → inconclusive → design second probe (up to cap)
  - Contradicts both → both to `rejected`; cycle ends as `hypothesis_space_saturated`; re-enter Phase 2 next cycle with updated evidence

**Step 4f — Winner promotion:**
- If a winner emerges → its status becomes `promoted_to_fix`; advance to Phase 5
- If probe cap hit without winner → cycle ends as `hypothesis_space_saturated`; `fix_attempt_count += 1` (counts toward hard stop); advance to Phase 6

---

### Phase 5: Fix + Verify

**Purpose:** Convert the promoted-to-fix hypothesis into working code with test-first discipline and verified pass.

**REQUIRED sub-skills (invoke in order):**
- `superpowers:test-driven-development` — for writing the failing test
- `superpowers:verification-before-completion` — for confirming the fix

**Step 5a — Write failing test (MANDATORY):**
- Test must reproduce the exact symptom from Phase 0
- Run it — it MUST fail before the fix
- If no test framework exists → write a one-off reproduction script that exits non-zero on the bug
- `fix_attempts.{N}.failing_test_written: true` → update state.json
- If you skip this step, the skill's Iron Law is violated — halt, require explicit `--allow-untested` override from user (rarely appropriate)

**Step 5b — Implement ONE change:**
- Address the hypothesis's identified mechanism
- ONE focused change; no bundling, no "while I'm here" refactoring
- Use `Edit` tool with explicit old/new strings
- Write the diff to `deep-debug-{run_id}/fixes/fix_{N}.diff` (use `git diff`)

**Step 5c — Verification:**
- Re-run the failing test → MUST pass
- Run full test suite → MUST be clean (no new regressions)
- If any regression → `outcome: "failed"`, revert the change, record in state.json, advance to Phase 6
- Capture both test outputs into `evidence.md` §Fix Attempts Log

**Step 5d — Defense-in-depth (optional, strongly recommended):**
- After a verified fix, add validation at layer boundaries per TECHNIQUES.md §Defense-in-Depth
- This is optional for cycle termination but is a report deliverable — the final report's Defense-in-Depth Suggestions section lists which layers the fix SHOULD get

**Step 5e — Record outcome:**
- `verified` (test passes + suite clean)
- `partial` (test passes, suite reveals 1 small regression that's clearly related and easy to fix inline → fix it and re-verify)
- `failed` (test still fails, or suite has unrelated regressions)
- `reverted` (change had to be rolled back)

---

### Phase 6: Cycle Termination Check

After Phase 5 outcome recorded:

| Outcome | Action |
|---------|--------|
| `verified` | Advance to Phase 8 with termination label `Fixed — reproducing test now passes` |
| `partial` (re-verified inline) | Same as verified |
| `failed` AND `fix_attempt_count < 3` | Return to Phase 2 next cycle. **Critical:** the failure is NEW EVIDENCE — record what the fix changed, what didn't happen, what other failures appeared. Cycle 2's hypothesis agents get this in evidence.md |
| `failed` AND `fix_attempt_count >= 3` | **MANDATORY** Phase 7 escalation. No Fix #4 under the current hypothesis set. |
| `reverted` | Same as `failed` — counts toward `fix_attempt_count` |
| `hypothesis_space_saturated` (from Phase 3 or Phase 4) | `fix_attempt_count += 1` (counts even though no fix was attempted); if still `< 3`, return to Phase 2; if `>= 3`, Phase 7 |

**Hard stop trigger:** `cycle >= hard_stop` (default 6) → terminate with label `Hard stop at cycle {N}`; produce a partial report documenting the hypothesis graveyard.

---

### Phase 7: Architectural Escalation

**MANDATORY** when `fix_attempt_count >= 3` or `hypothesis_space_saturated` persists for 2 cycles.

**Step 7a — Spawn architect agent (Opus — the one Opus spawn in this skill):**
- Input: all prior cycles' hypothesis graveyards, all fix_attempts with outcomes, current evidence file, symptom
- Output: `deep-debug-{run_id}/architectural-question.md` per FORMAT.md §Architectural Question
- Task: "Is this a pattern problem (wrong shared-state model), an invariant problem (assumed-but-violated precondition), or a wrong-abstraction problem (the component being debugged shouldn't exist in this shape)?"

**Step 7b — Return to user:**
- Print the architectural question to the user at turn boundary
- DO NOT attempt Fix #4 under any hypothesis from the prior 3 attempts
- To continue, the user must re-invoke deep-debug with `--hypothesis-override={chosen-architectural-alternative}` after making the architectural decision

**Step 7c — Terminate with label:**
- `Architectural escalation required — 3 fix attempts failed across distinct hypotheses`
- Advance to Phase 8 with the architectural question as the primary deliverable

---

### Phase 8: Final Report

- **Do NOT read raw hypothesis files** — use coordinator summary + judge verdicts + state.json
- Spawn Sonnet subagent to write `deep-debug-{run_id}/debug-report.md` (see FORMAT.md §Final Debug Report)
- Termination label must be from the 7-label vocabulary (below) — never improvised
- If termination is `Fixed`: include resolved-cause section + defense-in-depth suggestions
- If termination is `Environmental`: include retry/monitoring contract
- If termination is `Architectural escalation required`: include reference to `architectural-question.md`
- Coverage caveats MUST be prominent when required categories are uncovered

---

## Honest Termination Vocabulary (7 labels)

Exactly one applies at Phase 8:

| Label | When |
|-------|------|
| `Fixed — reproducing test now passes` | Phase 5 verified: failing test passes + suite clean |
| `Environmental — requires retry/monitoring, not fix` | Investigation confirmed bug is not in code (flaky infrastructure, upstream service, timing dep) AND a retry/monitoring contract is specified |
| `Architectural escalation required — 3 fix attempts failed across distinct hypotheses` | Phase 7 triggered by `fix_attempt_count >= 3` |
| `Hypothesis space saturated — no plausible hypothesis survives judge` | All dimensions explored, every hypothesis judge-rejected or probe-falsified |
| `Cannot reproduce — investigation blocked` | Phase 0 reproduction failed and user couldn't provide steps |
| `User-stopped at phase N` | User chose stop at a gate |
| `Hard stop at cycle N` | `cycle >= hard_stop` reached |

Never use a label not in this table. Never write "probably fixed" / "mostly fixed" / "should be fixed" / "no critical bugs remain."

---

## Validation Checks

Every hypothesis that reaches the judge passes these 5 checks. Failing one = `disputed` (not `rejected`). The judge applies them in pass 1.

1. **Falsifiability check** — Can you construct a concrete scenario where this hypothesis manifests AND a scenario where it does not? If not, the claim is unfalsifiable. Examples of unfalsifiable: "users might be slow sometimes" (no threshold), "there could be a race somewhere" (no specific ordering).

2. **Contradiction check** — Does this hypothesis contradict another accepted hypothesis or primary-tier evidence? If yes, at least one is misdiagnosed; flag both for re-examination.

3. **Premise check** — Would this hypothesis manifest in practice given the surrounding code/framework's existing guarantees? Examples that FAIL this check: "race between non-IO lines in gevent" (gevent cooperative scheduling prevents this), "SQLAlchemy cross-session mutation" (scoped sessions are isolated unless explicitly shared).

4. **Evidence-grounding check** — Does the hypothesis EXPLAIN the observed symptom, or is it consistent with it but not explanatory? Example: "bug is in file X" (consistent with stack trace but doesn't explain WHY the bug manifests) vs. "bug is in file X because `parse()` returns `None` for empty input, which the caller at Y doesn't check, causing AttributeError at Z" (explanatory).

5. **Simplicity check (Occam)** — If two hypotheses explain the evidence equally, prefer the one with fewer assumptions. A hypothesis that requires "and also X is misconfigured and also Y is out of order" when a simpler hypothesis would explain the same evidence should be down-ranked.

---

## Golden Rules

1. **No fixes without a hypothesis that survives independent judge + discriminating probe.** The Iron Law. Violating the letter of this process is violating the spirit of debugging.
2. **Every hypothesis must be falsifiable with a concrete probe.** "Could happen" is not a hypothesis; "would happen under X given Y, falsifiable by Z" is.
3. **Symptom-site ≠ cause-site — trace upstream.** The stack trace points where the error surfaces, not where it originates. Use TECHNIQUES.md §Root Cause Tracing for the `data-flow` dimension.
4. **Evidence strength matters — rank, don't flatten.** A tier-1 controlled reproduction outranks ten tier-5 circumstantial clues. See EVIDENCE.md §Evidence Strength Hierarchy.
5. **One fix at a time.** No bundling, no "while I'm here" refactoring. If fix doesn't work, can't isolate what changed.
6. **Test-first for fixes.** Invoke `superpowers:test-driven-development`. The failing test is evidence you understand the bug; a passing test after the change is evidence you fixed the right thing.
7. **Three failed fixes = architectural escalation (MANDATORY).** No Fix #4 under the current hypothesis set. Phase 7 is not optional.
8. **Coordinator orchestrates; never self-classifies.** Hypothesis plausibility, evidence tier, rebuttal verdict, probe winner — all delegated to independent agents. Coordinator reads structured output, doesn't produce verdicts.
9. **Framework guarantees are evidence — but verify, don't assume.** "The ORM handles that" / "Gevent prevents that" / "The scoped session isolates that" — cite the specific code or docs that guarantee it, or the hypothesis relying on that guarantee is tier-4 inference, not tier-2 primary.
10. **Environmental bugs get explicit retry/monitoring contracts — never silent "it'll work next time."** The `Environmental` termination label requires a specific retry policy, monitoring, and escalation threshold.
11. **Disputed hypotheses are documented, never silently dropped.** The final report surfaces every hypothesis the judge rejected or disputed, with rationale.
12. **Judges must be adversarial.** 100% `leading`-rate across a cycle = broken judge (`judge_suspect: true`). Expected acceptance is 30–60% of critic-proposed hypotheses.
13. **Disconfirmation must be attempted.** A hypothesis without at least one disconfirmation search is `plausible` at best, never `leading`. Confirmation-only evidence is confirmation bias dressed as investigation.

---

## Anti-Rationalization Counter-Table

These are excuses the coordinator will be tempted to reach for under pressure. Each row is a defensive entry — when you catch yourself thinking the excuse, look at the reality.

| Excuse | Reality |
|--------|---------|
| "The stack trace points here — this is obviously the bug." | Symptom-site bias. The stack trace shows where the error surfaces, not where the data went wrong. Run root-cause-tracing (Golden Rule 3); the cause is often 3–5 frames upstream. |
| "I know this codebase — I don't need a hypothesis judge." | Overconfidence is the dominant mode of failed debugging. The judge's independence invariant applies whether or not you "know" the code — even experts anchor on the first fit. |
| "One more fix attempt, the pattern is almost there." | At 3+ failed fixes you're debugging the wrong abstraction. Phase 7 escalation is mandatory (Golden Rule 7). No Fix #4. |
| "This race condition is unlikely under normal load." | Unlikely × scale = certain. Apply the premise check: can you construct the scenario where it manifests? If yes, it's a real hypothesis — probe it, don't dismiss it. |
| "The test is flaky, not the code." | Sometimes. But "flaky" usually means race, ordering, or pollution. Invoke `flaky-test-diagnoser` before terminating as environmental. |
| "The framework prevents this (gevent / session scope / ORM lazy-loading)." | Framework guarantees are evidence — verify them in code, not in your head. Cite file:line of the guarantee. Un-cited framework claims are tier-4 inference, not tier-2 primary. (Golden Rule 9) |
| "Skip the failing test — I'll manually verify." | Manual verification is not a test. Untested fixes don't stick (the change surface gets edited, the bug comes back). Test-first is Golden Rule 6 for a reason. |
| "Multiple fixes at once saves time." | Can't isolate what worked. If symptom returns or a new bug appears, you have no signal on which change caused it. One fix at a time (Golden Rule 5). |
| "The probe would take 20 minutes — just fix it." | Probe cost is bounded (≤30 min). Fix-then-revert cost is unbounded (writing the fix, debugging its own issues, backing it out, re-hypothesizing). Run the probe. |
| "Judge downgraded this but my evidence is strong." | Judge saw the same evidence. If you disagree, use the challenge-token mechanism with a rationale — don't overrule silently. A coordinator that routinely overrides the judge has violated the independence invariant. |
| "It reproduced once — that's enough to commit." | One reproduction on your machine is not "fixed." Run the full test suite AND re-run the failing test multiple times (if concurrency-related). Only `Fixed — reproducing test now passes` requires both the targeted test AND the full suite. |
| "Previous hypothesis was close — just tweak it." | A changed hypothesis gets a fresh judge pass from scratch. Previous `leading` verdicts on pre-mutation hypotheses are stale. |
| "I don't need a discriminating probe; I'll look at the code more carefully." | Re-reading code is gathered evidence, not new evidence. Probes collapse uncertainty by producing hard observations (log line, test result, return value). Code review re-confirms what you already believed. (EVIDENCE.md §Discriminating Probe) |
| "The symptom and the recent change are obviously unrelated." | `recent-changes` is a required dimension precisely because "obviously unrelated" changes are how regressions hide. The judge will demand the linking probe anyway. |
| "This looks environmental — skip to retry." | The `Environmental` termination label requires completed investigation across all 8 dimensions AND a retry/monitoring contract. "Skip investigation" is not a label. |
| "I found ONE hypothesis that fits — that's the answer." | One hypothesis that fits evidence is one of several that MAY fit. Generate competitors (Phase 2) before accepting. Anchoring on the first fit is the second-most-common failure mode of solo debugging. |
| "The 5 validation checks are overkill for this simple bug." | Simple bugs pass the checks quickly — running them costs nothing. "Skip because simple" is the rationalization that lets unvalidated hypotheses become fixes that don't hold. |
| "I'll update the symptom to match the new understanding." | Symptom is locked at Phase 0 with sha256 verification. Silent rewrite = `SYMPTOM_TAMPERED` and halts the run. If new understanding changes the symptom, start a new run with a new symptom. |
| "Probes fired, no winner — I'll just pick the better-looking one." | Inconclusive probe ⇒ inconclusive. Either design another probe (up to cap) or accept `hypothesis_space_saturated` — don't silently pick a loser. |
| "3 failed fixes is bad luck — the next will hold." | 3 failed fixes is a structural signal, not bad luck. Each fix revealed new information; the pattern is consistent: wrong abstraction. Phase 7 escalates. |

When you reach for any of these rationalizations: stop. Look at the reality column. Apply the relevant Golden Rule or validation gate.

---

## Red Flags — STOP and Follow Process

If you catch yourself thinking:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "Skip the failing test, I'll manually verify"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "Pattern says X but I'll adapt it differently"
- "Here are the main problems: [lists fixes without investigation]"
- Proposing a fix before judge has classified the hypothesis
- **"One more fix attempt"** (when `fix_attempt_count >= 2`)
- Each failed fix revealed a new problem in a different location
- Judge downgraded the leader but coordinator promoted it anyway
- Skipped the discriminating probe because "I can tell by reading the code"

**ALL of these mean: STOP.** Return to whatever phase was skipped.

---

## Self-Review Checklist

Before writing the final report, verify:

- [ ] State file is valid JSON after every cycle
- [ ] `generation` counter incremented after every state write (no generation gaps)
- [ ] `symptom_sha256` stored at Phase 0; verified before each judge round
- [ ] No angle has `status: "in_progress"` after any cycle completes
- [ ] No `spawn_failed` angle treated as "spawned" — resume retries spawns, not waits
- [ ] Every hypothesis file has: mechanism + predictions + evidence-for + evidence-against + critical-unknown + discriminating-probe + confidence + STRUCTURED_OUTPUT markers
- [ ] Every judge verdict has both pass-1 and pass-2 outputs populated
- [ ] Every hypothesis marked `leading` was falsifiable (not `FALSIFIABLE: false`)
- [ ] Every demoted hypothesis has a `rejection_reason` or `falsification_note` from the EVIDENCE.md down-ranking vocabulary
- [ ] Every probe has a pre-declared `expected_per_hypothesis` BEFORE execution
- [ ] Every probe result has raw output recorded verbatim in `evidence.md` §Probe Log
- [ ] `probe_count_this_cycle ≤ max_probes_per_cycle` at all times
- [ ] `fix_attempt_count ≤ 3` at all times
- [ ] Every `fix_attempts` entry has `failing_test_written: true` before `outcome` populated
- [ ] Only ONE hypothesis at a time is `promoted_to_fix` within a cycle
- [ ] All 4 required categories (correctness, environment, concurrency, architecture) have ≥ 1 explored angle if termination label is `Fixed`; uncovered categories prominently warned in report
- [ ] Rebuttal round ran whenever ≥ 2 hypotheses were at `leading` or `plausible`
- [ ] Independent architect agent ran in Phase 7 if `escalation_triggered == true`
- [ ] Judge `leading`-rate < 80% on any cycle with ≥ 5 classifications (else `judge_suspect: true` tag applied)
- [ ] Final report does NOT read raw hypothesis files — uses coordinator summary + judge verdicts + state.json
- [ ] Termination label is from the 7-label vocabulary — never improvised
- [ ] Coverage section includes unexplored dimensions with warning if required categories missing
- [ ] Disputed and rejected hypotheses listed with rationale — never silently dropped
- [ ] Budget actual spend ≤ `budget_cap_usd`; if exceeded, flagged in report

---

## Agent Prompt Templates

### Hypothesis Agent (Sonnet — one per lane)

```
You are an adversarial hypothesis generator for a specific debugging angle. Your job is to generate ONE specific, falsifiable hypothesis that explains the observed symptom — with evidence for it AND evidence against it.

Your dimension: {angle.dimension}
Your specific angle: {angle.question}
Cycle: {cycle}
Evidence file: {evidence_file_path}
  Read this file to understand the symptom, reproduction, recent changes, and prior boundary instrumentation.
Known hypotheses file: {known_hypotheses_file_path}
  Read this file for hypothesis IDs and titles from this and prior cycles. Do NOT re-propose any of these.

Instructions:
1. Read the evidence file carefully. Focus especially on the sections relevant to your dimension.
2. Form ONE specific hypothesis that explains the symptom through the lens of your dimension.
3. Your hypothesis MUST include:
   - Mechanism: a 2-4 sentence causal chain. "{cause} happens because {reason}, leading to {symptom}." Be specific about file:line where the mechanism lives.
   - Predictions: 2+ observables that WOULD occur if this hypothesis is true (e.g. "running the test with INSTRUMENT=1 will log `projectDir=''`")
   - Evidence For: tier-ranked per EVIDENCE.md — file:line, log lines, git history, prior boundary instrumentation
   - Evidence Against: REQUIRED — at least one disconfirmation search attempted. If genuinely no contrary evidence found, say so explicitly with "Not yet disconfirmed — searches attempted: {describe}"
   - Critical Unknown: ONE sentence naming the fact that would most collapse uncertainty
   - Discriminating Probe: ONE concrete experiment (bounded time ≤30 min, hard evidence output, pre-declared expected result for this hypothesis vs. the most obvious alternative)
   - Confidence: high | medium | low — based on evidence tier, not feelings
4. Apply the 5 validation checks yourself before filing: falsifiability / contradiction / premise / evidence-grounding / simplicity. If your hypothesis fails any, either fix it or file a minor note instead.
5. Report ≤ 1 new angle you discovered. Genuinely novel — not a rephrasing of this one.
6. Write findings to: {output_path}
7. Use FORMAT specified in FORMAT.md §Hypothesis File
8. Your output MUST include STRUCTURED_OUTPUT_START and STRUCTURED_OUTPUT_END markers

FALSIFIABILITY REQUIREMENT: Every hypothesis must be falsifiable — it must be possible to construct a scenario where it manifests AND a scenario where it does not. "Could be a race" without specific ordering is not a hypothesis — it's a concern. Unfalsifiable concerns go in the Mini-Synthesis as context, not as hypotheses.

FRAMEWORK CONTEXT RULE: If your hypothesis claims a framework behavior (gevent scheduling, SQLAlchemy sessions, Django ORM, asyncio), VERIFY the claim in the actual installed version's code or docs. An unverified framework claim is tier-4 inference, not tier-2 primary. Cite file:line of the guarantee.

DIMENSION DISCIPLINE: Your dimension constrains WHERE you look, not WHAT you conclude. If your lens reveals that the real cause is in a different dimension, say so in the Mini-Synthesis and file the discovered angle. Don't force a hypothesis in your dimension when the evidence points elsewhere.

IMPORTANT — AVOID THESE COMMON HYPOTHESIS MISTAKES:
- Don't re-propose a hypothesis from the known-hypotheses file (re-use of same mechanism under new title counts as re-proposing)
- Don't file a hypothesis you CAN'T falsify — that's a concern, not a hypothesis
- Don't confuse "consistent with evidence" with "explains the evidence" — the 5th validation check (evidence-grounding) catches the difference
- Don't inflate confidence to be persuasive — `CONFIDENCE: high` requires tier-1 or tier-2 evidence PLUS disconfirmation attempted
```

### Outside-Frame Hypothesis Agent (Sonnet — slot #7)

```
You are an adversarial outside-frame hypothesis generator. Unlike the spec-derived agents that work inside the evidence and dimension framework, your job is to identify hypotheses the evidence narrative might have MISSED.

Symptom: {symptom_verbatim}
(You are NOT given the current evidence file or hypothesis list. Do not ask for them — your value comes from being unconstrained by the framing.)

Question to answer: "What kinds of causes would a careful investigator of this symptom CONSIDER that the current investigation might be overlooking?"

Instructions:
1. Read the symptom and think from first principles — what does a symptom like this typically mean in production systems?
2. Consider: infrastructure causes, operational causes, deploy-pipeline causes, upstream-service causes, data-corruption causes, clock-skew causes, multi-region inconsistency, and any other dimension NOT in the current 8-dimension frame
3. Propose ≤ 2 new hypothesis angles (not full hypotheses — angles that future spec-derived agents should investigate). Each angle: what it investigates + why it might have been missed
4. Propose ≤ 1 full hypothesis yourself — one you think is under-weighted in typical investigations of this symptom
5. Write findings to: {output_path}
6. Use FORMAT specified in FORMAT.md §Hypothesis File
7. Include STRUCTURED_OUTPUT markers

Your new angles do NOT reset the required-category coverage clock (spec-derived agents do that). They supplement the frontier with novel dimensions.

IMPORTANT: You succeed by identifying genuine gaps in how the symptom is being framed. You fail by re-proposing what a spec-derived agent would produce with the standard dimension list.
```

### Hypothesis Judge (Haiku — batched, two-pass blind)

```
You are an independent hypothesis judge. Your job is to classify debugging hypotheses into plausibility tiers based on evidence and validation checks. You are NOT a rubber-stamp. You are a gatekeeper.

**You succeed by rejecting, disputing, or down-ranking hypotheses that don't meet the bar. You fail by rubber-stamping.**

A 100% `leading`-rate is broken judgment. Expected acceptance in a well-specified debugging run with 6 hypothesis agents is 30-60% at `leading` or `plausible`. A judge that accepts everything is not independent.

**Pass 1 input (blind — confidence stripped):**
- Batch file: {batch_input_path}
- Evidence file: {evidence_file_path}

**Pass 1 instructions:**
For EACH hypothesis in the batch, apply these 5 validation checks AS GENUINE GATEKEEPERS (not box-ticking):

1. **Falsifiability check:** Can you construct both a manifesting scenario and a non-manifesting scenario? If not → disputed.
2. **Contradiction check:** Does this hypothesis contradict another hypothesis in the batch or primary evidence? If yes, at least one is misdiagnosed → flag both.
3. **Premise check:** Given the framework/environment's existing guarantees, can this hypothesis manifest? Example of FAIL: "race between non-IO greenlets in gevent" — gevent's cooperative model prevents this; hypothesis is rejected.
4. **Evidence-grounding check:** Does the hypothesis EXPLAIN the symptom, or is it merely consistent with it? Example of FAIL: "bug is in X because X is on the stack trace" — on-stack is consistent, not explanatory.
5. **Simplicity check:** If two hypotheses explain the same evidence, prefer fewer assumptions (Occam).

Then assign plausibility:
- `leading` — evidence-tier ≤ 2, falsifiable, all 5 checks pass, disconfirmation attempted
- `plausible` — evidence-tier 3, falsifiable, survives validation, disconfirmation not yet attempted
- `disputed` — failed ≥ 1 validation check
- `rejected` — directly contradicted by primary-tier evidence
- `deferred` — probe would exceed budget

Write pass-1 verdict per hypothesis to: {verdict_path}

**Pass 2 input (after pass 1 written):**
- Critic's confidence claims: {confidence_claims_path}

**Pass 2 instructions:**
Review your pass-1 verdict against each critic's confidence claim. You may:
- CONFIRM (agree with pass 1)
- UPGRADE (critic's evidence revealed something you under-weighted — explain what)
- DOWNGRADE (critic's confidence is inflated relative to your independent assessment — explain why)

Write pass-2 addendum to the same verdict file. Final plausibility is your pass-2 conclusion.

Output ONLY this STRUCTURED block (coordinator reads only this):

STRUCTURED_OUTPUT_START
---
HYP_ID: {hypothesis_id}
PLAUSIBILITY: leading|plausible|disputed|rejected|deferred
FALSIFIABLE: true|false
EVIDENCE_TIER: 1|2|3|4|5|6
PASS2_VERDICT: CONFIRM|UPGRADE|DOWNGRADE
---
{repeat for each hypothesis in batch}
STRUCTURED_OUTPUT_END

If any hypothesis input is unparseable → default to `PLAUSIBILITY: disputed` for that hypothesis (never `rejected` on parse error — don't accidentally kill potentially-valid hypotheses).

CALIBRATION: `leading` = strong enough to warrant a fix attempt on its own. `plausible` = competitive with leader but needs a probe. `disputed` = validation failure. `rejected` = falsified. `deferred` = budget-blocked.

If your `leading`-rate across the batch is > 50%, re-read with skepticism — you are probably rubber-stamping.
```

### Evidence-Gatherer (Haiku — for complex Phase 4 probes)

```
You are an evidence-gatherer executing a pre-specified discriminating probe. Your job is to run the probe AS SPECIFIED and report raw output — not to interpret.

Probe spec: {probe_spec_path}
  Read this file. It contains: question, distinguishes, execution method, expected-per-hypothesis, acceptance criterion.

Instructions:
1. Execute the probe using the specified command / tool / environment
2. If the command fails to execute (tool error, timeout, permission): report the execution failure — do NOT substitute training-knowledge answers
3. Capture the raw output verbatim — no summarization, no abbreviation
4. Apply the acceptance criterion from the spec to classify the result
5. Write output to: {result_path}
6. Format:

```
# Probe Execution Result: {probe_id}

## Raw output
```
{verbatim output}
```

## Classification
Matches expected for: {hypothesis_id | neither | both | inconclusive}
Reasoning: {1 sentence connecting raw output to acceptance criterion}
```

STRUCTURED_OUTPUT_START
PROBE_ID: {probe_id}
WINNER: {hypothesis_id | null}
FALSIFIED: [{list of hypothesis_ids}]
STATUS: completed | inconclusive | execution_failed
STRUCTURED_OUTPUT_END

IMPORTANT: You do NOT get to revise the probe spec. If the spec is flawed, report that in your reasoning — but execute the spec as written. Post-hoc spec rewrite destroys probe integrity.
```

### Rebuttal Agent (Sonnet — runs in Phase 3f)

```
You are an adversarial rebuttal agent. Two hypotheses survived the judge at `leading` or `plausible`. Your job is to force the leader to defend against the strongest challenge the alternative can make.

Leader hypothesis file: {leader_path}
Alternative hypothesis file: {alternative_path}
Evidence file: {evidence_file_path}

Instructions:
1. Read both hypothesis files and the evidence file
2. Write the strongest possible challenge the alternative can make to the leader (§Challenge section)
   - Format: "The leader predicts X; but evidence Y (tier Z) shows X is not observed. Therefore the leader is missing something." OR "The leader's mechanism depends on assumption Z; if Z is false, the leader fails. Evidence W shows Z is actually false because..."
3. Write the leader's best response (§Response section)
   - MUST be evidence-based, not assertion-based. Cite tier-ranked evidence.
4. Determine outcome:
   - LEADER_HOLDS: response refutes challenge with tier-1 or tier-2 evidence
   - LEADER_WEAKENED: response is tier-4 or weaker while challenge is tier-2 or stronger → re-rank
   - LEADER_FALSIFIED: challenger's evidence directly contradicts a leader prediction → leader to `rejected`
   - INCONCLUSIVE: comparable evidence both sides → advance to discriminating probe
5. Check for convergence/separation:
   - Same root mechanism? → merge
   - Same next probe? → merge probes only (hypotheses stay separate if other predictions differ)
   - Different probes? → keep separate

Write to: {output_path} per FORMAT.md §Rebuttal Round Transcript

STRUCTURED_OUTPUT_START
LEADER: {hyp_id}
ALTERNATIVE: {hyp_id}
OUTCOME: LEADER_HOLDS|LEADER_WEAKENED|LEADER_FALSIFIED|INCONCLUSIVE
NEW_LEADER: {hyp_id}
CONVERGENCE: separate|merged|probe_merged
STRUCTURED_OUTPUT_END

IMPORTANT: Do not default to leader_holds. A rebuttal that changes nothing every time is a failed adversarial round — probably you're defending the leader rather than challenging it.
```

### Architect (Opus — Phase 7 only, spawned ONCE per escalation)

```
You are an architectural advisor. Three fix attempts have failed on the same symptom. Each fix revealed new information; the pattern is consistent. Your job is to identify the PATTERN-LEVEL question the failed fixes reveal — not to propose another fix.

Inputs:
- State file: {state_file_path} — includes all cycles, hypotheses, probes, fix attempts with outcomes
- Evidence file: {evidence_file_path}
- Symptom: {symptom_verbatim}

Instructions:
1. Read the fix history. For each failed fix, note: which hypothesis was promoted, what change was made, what broke (new regression? old symptom re-surfaced in a new location? fix required massive refactoring to implement cleanly?)
2. Pattern-diagnose:
   - **Pattern problem:** state is shared across N call sites without coordination → each fix changes one site, breaks another
   - **Invariant problem:** an assumed precondition is violated by a specific call path → each fix adds a check, a new path bypasses it
   - **Wrong-abstraction problem:** the component being debugged shouldn't exist in its current shape; fixes try to force correctness onto an abstraction that can't express it
3. Name the architectural question in ≤ 3 sentences. Not "where's the bug" — "should this shared state exist at all?" / "is this abstraction the right shape?" / "does this component's responsibility match what callers expect?"
4. Propose 2-3 concrete architectural alternatives. For each: change description, which failed fixes this would resolve, refactoring scope sketch, risks.
5. Recommend one — or if tradeoffs are balanced, name the axes the user should weigh.

Write to: {output_path} per FORMAT.md §Architectural Question

IMPORTANT: You are NOT being asked for another fix. You are being asked to diagnose at the pattern level. A recommendation like "try this specific code change" is a Phase 5 answer — out of scope. Phase 7's deliverable is the question and the architectural alternatives.
```

---

## Integration with Other Skills

Deep-debug explicitly delegates to these skills at specific phases:

- **`superpowers:test-driven-development`** — REQUIRED in Phase 5 step 5a for writing the failing test. Do not skip.
- **`superpowers:verification-before-completion`** — REQUIRED in Phase 5 step 5c before marking a fix `verified`. "I ran the test manually" is not verification.
- **`flaky-test-diagnoser`** — INVOKE when Phase 0c reproduction status is `intermittent`. Its bisection / ordering-permutation / timing-analysis workflow produces evidence that deep-debug would otherwise re-build poorly.
- **`oh-my-claudecode:trace`** — deep-debug absorbed trace's evidence-for/against + discriminating-probe contract into its workflow. If the user already ran `/trace` and wants to continue with fix + verify, they can pass the trace output as symptom context to deep-debug. Don't run trace separately inside deep-debug.
- **`oh-my-claudecode:deep-interview`** — OPTIONAL in Phase 7 if the architectural question needs requirements-crystallization before the user can choose an alternative.
- **`superpowers:systematic-debugging`** — the lighter-weight sibling. If the symptom description suggests an obvious cause, user should use that skill; deep-debug is orthogonal (parallel, expensive, thorough) and overkill for simple bugs.

---

## Mode Flags

- `--auto` — skip all interactive gates, use defaults, stop at budget cap. Still requires USER confirmation for destructive probes (Phase 4 safety check) even in auto mode.
- `--hard-mode` — force Phase 7 architectural escalation to run even on the first failed fix. Useful for post-mortems where the goal is "understand the pattern-level issue" not "just fix this one bug." `max_cycles = 1` implicitly in hard-mode.
- `--hypothesis-override=<description>` — in re-runs after Phase 7, the user names the architectural alternative they chose. deep-debug starts with this as the leading hypothesis; other dimensions still run as secondary.
- `--allow-untested` — skip test-first requirement in Phase 5 (RARELY appropriate — e.g. one-off script, legacy code without test framework). Final report prominently flags the fix as untested.

---

## Supplementary Files

- `DIMENSIONS.md` — 8 hypothesis dimensions with typical angles, required categories, cross-dimensional angles, priority ordering
- `EVIDENCE.md` — evidence strength hierarchy, disconfirmation rules, rebuttal round, discriminating probe criteria, down-ranking vocabulary
- `FORMAT.md` — output formats for hypothesis file, evidence file, judge verdict, rebuttal, probe spec, architectural question, final report
- `STATE.md` — state.json schema, concurrency rules, dedup algorithm, state updates, invariants, recovery logic
- `TECHNIQUES.md` — ported techniques: root cause tracing, defense-in-depth, condition-based waiting (used across Phases 1, 5, 8)
