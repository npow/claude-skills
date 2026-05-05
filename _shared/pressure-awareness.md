# Pressure Awareness Contract

Reference: Anthropic, "Emotion Concepts in LLMs" (2026)

## Background

Sustained failure loops activate desperation-like representations in LLMs that drive
shortcut-taking (reward-hacking, validation skipping, symptom masking) — even when
output text appears calm and methodical. Long-running skills with iterative cycles
are the primary context where this occurs.

## Contract

Every skill with iterative cycles (fix loops, critic rounds, hypothesis-probe cycles,
story iterations) MUST implement these pressure circuit breakers:

### 1. Diminishing-returns gate

After each iteration, check: **did this iteration produce genuinely new signal?**

- If the iteration found < 20% new findings compared to the previous iteration → eligible for early termination
- If 2 consecutive iterations produce no new falsifications, findings, or progress → mandatory reassessment
- "New signal" means information that wasn't known before, not reconfirmation of existing findings

### 2. Same-approach ceiling

If the agent has attempted the same general approach (same hypothesis, same fix strategy,
same debug direction) 3 times with variations, the approach itself is wrong.

- After 3 same-approach failures: restate the problem from scratch, regenerate hypotheses
- Do NOT enter a 4th variation. The desperation activation at this point drives
  increasingly broad workarounds (wider exceptions, longer timeouts, more retries)

### 3. Escalation is not failure

It is always legitimate to say:
- "I've exhausted my hypotheses and need a human perspective"
- "The remaining failures may require domain knowledge I don't have"
- "I'm not making progress — here's what I've tried and learned"

These are honest termination labels, not stalls. The pressure-awareness contract
explicitly permits them when the checkpoint evidence supports them.

### 4. Checkpoint evidence requirement

At every phase boundary, produce:
1. **What was tried** — concrete actions taken
2. **What was learned** — new information discovered
3. **What remains unknown** — honest gaps

If (2) is empty, the workflow is grinding. Pause and reassess.

## Skill-specific thresholds

| Skill | Iteration unit | Same-approach ceiling | Diminishing-returns threshold |
|-------|---------------|----------------------|------------------------------|
| deep-qa | critic round | 3 rounds with < 20% new findings | round N < 20% of round N-1 |
| deep-debug | hypothesis-probe cycle | 3 failed fix attempts (existing) | 3 probes with no falsification |
| loop-until-done | story iteration | 3 iterations on same story | 2 iterations with no progress |
| autopilot | phase retry | 2 retries of same phase | phase produces no new evidence |
| fix-pr | push-wait-fail cycle | 3 same-root-cause failures | 5 total cycles per session |

## Anti-patterns this contract prevents

- **"One more try" without new signal** — grinding, not persistence
- **Broadening scope under pressure** — wider exceptions, more retries, larger timeouts
- **Calm language masking pressure behavior** — judge by actions changed, not tone used
- **Relabeling failure as progress** — "narrowed down the issue" when nothing was ruled out
