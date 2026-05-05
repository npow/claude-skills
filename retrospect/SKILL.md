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
3. **Select fix level** (broadest appropriate):
   - **CLAUDE.md requirement** → All sessions, all users in this repo
   - **Skill modification** → All users invoking the skill
   - **Memory entry** → Future sessions for this user (use project memory system)
   - **No fix** → Document but don't patch (one-off edge case)

### Phase 4: PRESCRIBE — Generate Patches

For each diagnosed failure that warrants a fix, generate a specific patch.

**Patch format:**
```
## Fix [N]: [Title]

**Root cause:** [Category] — [one-line summary]
**Recurrence:** [Always/Likely/Sometimes/Unlikely]
**Target:** [file path]

### Change
[For edits: old text → new text]
[For additions: new content with placement context]

### Rationale
[Why this fix prevents recurrence]
```

**Safety checks before presenting:**
1. Does this weaken any existing safety requirement? If yes, flag explicitly.
2. Is this based on a single incident? Prefer narrow fixes unless recurrence evidence supports broader.
3. Could this cause regressions by overgeneralizing?

For P5 positive learnings, use simplified format: Title, Target, Change, Rationale (no root cause).

Present ALL patches to the user for approval before applying.

### Phase 5: APPLY — Execute Approved Patches

1. Group patches by target file — apply all edits to same file together
2. For CLAUDE.md changes: edit directly
3. For skill changes: edit the skill file
4. For memory entries: write to the project memory system

**Post-apply summary:**
```
## Retrospect Summary

### Failures analyzed: [N]
### Patches applied: [N]
### Patches deferred: [N]

| # | Failure | Root Cause | Fix | Status |
|---|---------|-----------|-----|--------|
| 1 | [desc] | [category] | [target] | Applied/Deferred/Rejected |
```

## Integration Points

- **After autopilot:** Run retrospect to close the learning loop
- **After fix-pr:** Capture CI debugging patterns
- **After deep-qa:** Analyze P6 findings — why did review catch things the agent missed?
- **On idle notification:** Aimee harness can trigger retrospect automatically
- **Manual:** User types `/retrospect` anytime
