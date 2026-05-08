---
name: retrospect
description: |
  Session retrospective that scans the current conversation for agent failures,
  user corrections, and alignment gaps, then proposes patches to CLAUDE.md or skills.
  Use when: after a difficult session, after repeated corrections, to improve agent
  behavior, to analyze what went wrong, to close the learning loop after autopilot/fix-pr.
  Trigger phrases: "retrospect", "what went wrong", "session retro", "learn from this",
  "what should we improve", "session review", "capture learnings", "post-mortem this session".
user_invocable: true
argument: "[optional: focus area or specific failure to analyze]"

category: meta
capabilities:
  - conversation-analysis
  - instruction-patching
best_for:
  - "Analyzing agent mistakes in the current session"
  - "Proposing durable fixes to CLAUDE.md or skills"
  - "Closing the learning loop after autopilot, fix-pr, or deep-qa runs"
not_for:
  - "Team sprint retrospectives (use sprint-retro)"
  - "Production incident investigation (use debug-run)"
  - "Code review (use deep-qa)"
input_types:
  - conversation-context
output_types:
  - instruction-patches
complexity: low
cost_profile: low
maturity: beta
---

# Session Retrospect

Scan the current conversation for alignment failures, classify root causes, and propose
durable instruction patches. This is NOT a team retro — it analyzes agent behavior in
THIS session and produces fixes that prevent recurrence across all future sessions.

## Workflow

```
SCAN → CLASSIFY → DIAGNOSE → PRESCRIBE → APPLY
```

### Phase 1: SCAN — Detect Failure Signals

Sweep the conversation for signals at six priority levels. Gather evidence before asking
questions.

**P1 — Explicit corrections (highest confidence):**
User directly identified a problem:
- Correction language: "no", "not that", "wrong", "incorrect", "that's not what I meant"
- Halt commands: "stop", "don't do that", "undo", "revert"
- Repeated instructions (user re-explained something already said)

**P2 — Agent self-corrections:**
- "let me try again", "I see the issue", "I made a mistake"
- Same tool called 3+ times with varying parameters (floundering)
- Approach abandoned mid-execution and pivoted

**P3 — Structural failures:**
- Tool calls that returned errors
- Required skill not invoked when it should have been
- Verification step omitted (tests, build, diff check)
- Premature completion claims without evidence
- Unauthorized scope expansion (touched unrelated files)
- Silent degradation after tool failure (switched to guessing)

**P4 — Implicit misalignment (verify before reporting):**
- User tone shift toward more directive language
- User took over work the agent was performing
- User asked questions the agent should have anticipated
- Agent used weak heuristics when authoritative tools were available

**P5 — Positive learnings (preserve, not fix):**
- New conventions or patterns discovered during implementation
- Validated approaches that should be documented
- API quirks or system behaviors learned through investigation
- Workflow improvements that worked well

**P6 — Review findings (pattern analysis):**
- Issues caught by deep-qa, /review, or PR reviewers that the agent missed during implementation
- For each cluster: why did this class of error reach the review?

**SCAN output:** Numbered list of events, each with: event description, priority (P1-P6),
source (conversation turn or tool call).

**Early exit:** If SCAN finds zero signals across all priorities, report "No findings" and stop.
If only P5 signals exist (no failures), skip to PRESCRIBE for positive learnings.

### Phase 2: CLASSIFY — Root Cause Taxonomy

For each P1-P4 and P6 signal, assign a root cause:

| Category | The agent failed because... | Typical signal |
|----------|----------------------------|---------------|
| **Missing Context** | No instruction exists for this situation | Reasonable general decision, but project convention exists |
| **Undiscovered Context** | Instruction exists but wasn't found/loaded | Skill/CLAUDE.md section exists but wasn't triggered |
| **Ignored Context** | Instruction was loaded but not followed | Clear instruction in context, agent contradicted it |
| **Incorrect Context** | Instructions contained wrong information | Agent followed instructions exactly, but they were outdated |
| **Ambiguous Instructions** | Instruction was followed but misinterpreted | Multiple reasonable interpretations, agent picked wrong one |
| **Incorrect Task Framing** | Agent chose wrong work mode | Asked for review, agent started implementing |
| **Premature Assumption** | Agent should have asked but guessed | Had uncertainty, proceeded without clarifying |
| **Tool/System Failure** | External system failed | API timeout, permission denied, MCP unavailable |

### Phase 3: DIAGNOSE — Trace Causation and Select Fix Level

For each classified failure:

1. **Trace the chain:** What instruction, skill, or tool was involved? Quote the exact text.
2. **Assess recurrence:** Always / Likely / Sometimes / Unlikely
3. **Select fix level** using the enforcement hierarchy below.

**Enforcement hierarchy (prefer the highest tier that fits):**

| Tier | Mechanism | Effect | When to use |
|------|-----------|--------|-------------|
| **T1 — Blocking gate** | `autonomy-rules.md` entry (stop-gate classifier) | Blocks turn-end when violation detected | Behavioral rules: "always do X before Y", "never do Z without checking" |
| **T2 — PreToolUse hook** | Python hook in `.claude/hooks/` | Blocks specific tool calls matching pattern | Concrete tool-level guards: "don't edit generated files", "don't push to main" |
| **T3 — Pre-commit hook** | `.pre-commit-config.yaml` entry | Blocks commits matching pattern | Code-level rules: lint, format, secret detection |
| **T4 — Skill update** | Edit SKILL.md checklist/workflow | Guides behavior when skill is invoked | Skill-scoped workflow improvements |
| **T5 — CLAUDE.md / SOUL.md** | Prescriptive text | Read at session start, no enforcement | Context, conventions, preferences (NOT behavioral rules) |
| **T6 — Memory entry** | Project or user memory file | Read when relevant, no enforcement | User preferences, project context, reference pointers |

**The rule: every behavioral fix (P1-P4) MUST have a T1-T3 mechanism.** T5-T6 are
documentation — they describe intent but cannot prevent violations. A retrospect that
produces only T5-T6 patches for behavioral failures is incomplete.

SOUL.md and memory are appropriate for:
- User preferences and context (T6)
- Conventions and knowledge that inform judgment (T5)
- Supplementary documentation alongside an enforcement mechanism

They are NOT appropriate as the sole fix for:
- "Always do X" rules (needs T1 gate)
- "Never do Y" rules (needs T1 gate or T2 hook)
- "Check Z before W" rules (needs T1 gate)

### Phase 4: PRESCRIBE — Generate Patches

For each diagnosed failure that warrants a fix, generate a specific patch.

**For each behavioral fix (P1-P4), generate a paired patch:**
1. **Enforcement patch (T1-T3)** — the mechanism that blocks the violation
2. **Documentation patch (T5-T6, optional)** — context for humans reading the rules

The enforcement patch is the deliverable. The documentation patch is supplementary.

**Patch format:**
```
## Fix [N]: [Title]

**Root cause:** [Category] — [one-line summary]
**Recurrence:** [Always/Likely/Sometimes/Unlikely]
**Enforcement tier:** T[1-3]
**Enforcement target:** [file path for gate/hook/pre-commit]
**Documentation target:** [file path for SOUL/memory, or "none"]

### Enforcement change
[The autonomy-rules.md entry, hook code, or pre-commit config]

### Documentation change (optional)
[SOUL.md or memory entry providing context]

### Rationale
[Why this enforcement prevents recurrence]
```

**Choosing the right autonomy-rules category (T1):**
When adding to `autonomy-rules.md`, find the existing stall category that best fits
the failure pattern and add a sub-bullet. Common mappings:
- "Didn't verify before acting" → **Guessing instead of reading**
- "Dismissed a problem without evidence" → **Evidence-free dismissal**
- "Wrote code without reading context" → **Edit-without-understanding**
- "Masked a symptom instead of fixing root cause" → **Symptom-masking fixes**
- "Used weak check instead of real test" → **Proxy verification**
- "Stopped early with known gaps" → **Procrastination / premature good enough**
- "Documented rule instead of enforcing it" → **Memory-as-enforcement**

**Safety checks before applying:**
1. Does this weaken any existing safety requirement? If yes, flag explicitly.
2. Is the autonomy-rules entry general enough to catch variants, not just the exact incident?
3. Could false positives from the gate cause legitimate work to be blocked?

For P5 positive learnings, use simplified format: Title, Target, Change, Rationale (no enforcement needed).

### Phase 5: APPLY — Execute Patches

Apply in enforcement-first order:

1. **T1 gates first** — edit `autonomy-rules.md` (resolve symlinks: `readlink -f ~/.claude/autonomy-rules.md`).
   Commit and push to the dotfiles repo (branch + PR if `no-commit-to-branch` hook is active).
2. **T2 hooks** — create/edit hook scripts in `.claude/hooks/`, update `settings.json`.
3. **T3 pre-commit** — update `.pre-commit-config.yaml`.
4. **T4 skills** — edit SKILL.md files.
5. **T5-T6 documentation** — SOUL.md, CLAUDE.md, memory entries. These are optional supplements.

**Post-apply summary:**
```
## Retrospect Summary

### Failures analyzed: [N]
### Enforcement patches applied: [N]
### Documentation patches applied: [N]

| # | Failure | Root Cause | Enforcement (T1-T3) | Documentation (T4-T6) | Status |
|---|---------|-----------|---------------------|----------------------|--------|
| 1 | [desc] | [category] | [gate/hook/none] | [soul/memory/none] | Applied/Deferred |
```

## Integration Points

- **After autopilot:** Run retrospect to close the learning loop
- **After fix-pr:** Capture CI debugging patterns
- **After deep-qa:** Analyze P6 findings — why did review catch things the agent missed?
- **On idle notification:** Aimee harness can trigger retrospect automatically
- **Manual:** User types `/retrospect` anytime
