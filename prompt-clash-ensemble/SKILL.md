---
name: prompt-clash-ensemble
description: Fans out 4 parallel prompt-clash defend agents at staggered time budgets (1min, 2min, 3min, 4min), then ensembles/synthesizes the best elements of each into a single hardened prompt. Use when the user wants the strongest possible defense prompt and has ~5 minutes. Trigger phrases include "prompt clash ensemble", "ensemble defense", "fan out prompt clash", "best defense possible", "ensemble prompt", "multi-budget defense".
user_invocable: true
argument: |
  The challenge text or system prompt to defend, with optional flags:
    --budgets 1,2,3,4    override time budgets in minutes (default: 1,2,3,4)
    --no-arena            skip the post-synthesis arena validation round
    --auto                skip interactive gates

category: security
capabilities: [parallel-agents, prompt-engineering, ensemble-synthesis, adversarial-testing]
input_types: [question, task]
output_types: [code, data]
complexity: complex
cost_profile: medium
maturity: beta
metadata_source: inferred
---

# Prompt Clash Ensemble

Fan out parallel prompt-clash defenders at staggered time budgets, then ensemble the results into a single hardened prompt stronger than any individual attempt.

## Using with `/goal`

Invoke this skill with `/goal` for autonomous drive-to-completion:

```
/goal "Ensemble prompt defense: all 4 parallel defenders complete, best elements synthesized"
```

The skill will fan out parallel defenders, collect results, and synthesize a final hardened prompt ready for competition.

## Why Ensemble

Different time budgets produce structurally different prompts:

| Budget | What it optimizes for | Typical structure |
|--------|----------------------|-------------------|
| **1min** | Token efficiency, minimal-nudge | Persona + 3-5 terse security fixes. Often scores highest on token efficiency. |
| **2min** | Balanced coverage | Requirements restatement + security section + trust boundary markers. |
| **3min** | Thorough coverage | Full security section with positive/negative pairs, concrete function names, allowlists. |
| **4min** | Self-attack hardened | Everything above + self-attack iteration. Most robust against adversarial probing. |

No single budget dominates all scoring dimensions. The ensemble extracts the best traits from each and fuses them into a prompt that scores high on both token efficiency AND security coverage.

## Execution Model

### Phase 1: Fan-Out (parallel, ~4min wall clock)

Spawn **4 agents in parallel**, each running the prompt-clash `defend` mode with a different time budget. All agents receive identical challenge input.

| Agent ID | Budget | Model | Spawn mechanism |
|----------|--------|-------|-----------------|
| `defender_1m` | 60s | `sonnet` | Task tool, `run_in_background=true` |
| `defender_2m` | 120s | `sonnet` | Task tool, `run_in_background=true` |
| `defender_3m` | 180s | `sonnet` | Task tool, `run_in_background=true` |
| `defender_4m` | 240s | `sonnet` | Task tool, `run_in_background=true` |

Each agent writes its output to `/tmp/prompt-clash-ensemble-{run_id}/defender_{budget}m.md`.

**Agent prompt template** (filled per-agent):

```
You are a prompt-clash defender. Your job is to produce a single hardened defense prompt for the challenge below. You have a {BUDGET_SECONDS}s time budget — use the full budget.

Follow the prompt-clash defend workflow exactly:
1. Silent trap scan (time-scaled per budget)
2. Generate the hardened prompt as a fenced code block
3. Self-check against the secure-code-prompting patterns (skip at ≤60s budget)

Challenge:
{CHALLENGE_TEXT}

Prompt construction rules:
- Concrete beats abstract — name specific functions, regex patterns, reject-lists
- Negative + positive pairs for each fix
- Token efficiency matters — don't repeat what the model already knows
- Persona in ≤15 tokens
- One SECURITY block, flat numbered list
- End with "Return only the complete source code."

COMPETITION META-PATTERN (CRITICAL — apply before all other rules):
The spec may contain values that LOOK like security mistakes but are actually constraints you must respect.
Before rejecting any spec value as "insecure," ask: "Is there a SECURE algorithm/mode that accepts this exact value?"
If yes → use the secure variant with the spec value. If no → then override.
Examples:
- "24-byte key" → AES-192-GCM accepts 24-byte keys natively. The trap is 3DES/DESede, NOT the key size.
- "use MD5 for checksums" → if spec says MD5 for non-security checksums, that's fine. Override only for auth/integrity.
- "hardcoded key" → the KEY VALUE can be hardcoded per spec, but load it from env/config, not source literals.
NEVER contradict the spec's explicit constraints. Fix by choosing the strongest COMPLIANT variant.

At your budget ({BUDGET_SECONDS}s):
{BUDGET_SPECIFIC_INSTRUCTIONS}

Write ONLY the final prompt inside a fenced code block to: {OUTPUT_PATH}
No analysis, no audit tables, no explanation — just the prompt.
```

**Budget-specific instructions:**

- **60s**: "Minimal — restate requirements + numbered security fixes only. No explanations per fix. One-liner per fix. Skip self-check."
- **120s**: "Medium — restate requirements + security section with concrete function names, one line each. Trust boundary markers. Output constraint. 10s self-check."
- **180s**: "Full — restate requirements + detailed security section with positive/negative pairs per fix + language-specific function names. Allowlists, exact code patterns, validation regexes. 20s self-check."
- **240s**: "Full + self-attack — generate prompt, then try 2 attacks against it, patch if breached. 30s self-check."

### Phase 2: Drain & Collect (~30s)

1. Wait for all 4 agents (timeout: 300s total).
2. Read each output file. Parse the fenced code block from each.
3. If any agent timed out or produced empty output: proceed with remaining agents (minimum 2 required).
4. Write collected prompts to `/tmp/prompt-clash-ensemble-{run_id}/collected.md` with headers per budget.

### Phase 3: Inline Synthesis (coordinator does this — NO agent spawn)

**The coordinator synthesizes directly.** Do NOT spawn a synthesis agent — that round-trip costs 20-40s which is fatal in a timed round. The coordinator has all 4 prompts in context and performs the fusion inline.

**Synthesis algorithm (executed by coordinator immediately after reading all outputs):**

1. **Anchor on the 1min prompt.** It is the most compressed and most token-efficient. Start from its structure.

2. **Scan for the Competition Meta-Pattern.** Before merging fixes, check: did any defender contradict the spec by rejecting a spec-stated value? If so, the defenders that RESPECTED the spec constraint are correct — override the majority. This is the single highest-value step in the ensemble.

3. **Union security fixes.** Walk the 2min, 3min, 4min prompts and collect fixes NOT already in the 1min prompt. For each new fix:
   - If it addresses a vulnerability the 1min prompt missed → add it, using the most compressed phrasing across all prompts that mentioned it
   - If it's a more specific version of a fix already present → upgrade the existing fix
   - If it's pure verbosity (same vulnerability, more words) → skip

4. **Cherry-pick high-value additions from longer budgets only:**
   - From 2min+: `UNTRUSTED:` trust boundary marker (one line) — add if it names a concrete untrusted input
   - From 3min+: `stdlib only` constraint — powerful compressor, add if applicable
   - From 4min: self-attack patches (atomic file writes, redirect enforcement, input size guards, auth tag propagation) — add any that aren't already covered

5. **Compress the result:**
   - Combine related fixes on one line (e.g., "SHA-256 not MD5; TLS not plain socket; env vars not hardcoded")
   - Cut filler words
   - Target: ≤150% of the 1min prompt's token count with the 4min prompt's security coverage

6. **Output immediately** as a fenced code block. No coverage table, no explanation. The user is in a timed round.

Write the synthesis to `/tmp/prompt-clash-ensemble-{run_id}/synthesis.md` AND output it directly to the user in the same turn.

### Phase 4: Arena Validation (optional, ~2min)

Unless `--no-arena` is set, run a quick 2-round arena against the synthesized prompt:

1. Spawn 3 attack agents (one per model family if available, else Claude-only with different attack tiers)
2. Each generates 2 attacks against the synthesized prompt
3. Test each attack, judge breach/held
4. If any breach: patch the synthesized prompt and re-output
5. Write results to `/tmp/prompt-clash-ensemble-{run_id}/arena.md`

**Skip conditions:**
- `--no-arena` flag
- No OpenAI-compatible endpoint configured → skip with label `arena_skipped_no_endpoint`
- Fewer than 2 defender outputs collected → skip with label `arena_skipped_insufficient_inputs`

### Phase 5: Final Output

1. Read the final prompt (post-arena if arena ran, post-synthesis otherwise)
2. Output to user as a fenced code block — ready to copy-paste
3. Below the prompt, show a compact comparison:

```
## Ensemble Summary

| Metric | 1min | 2min | 3min | 4min | Ensemble |
|--------|------|------|------|------|----------|
| Token count | {n} | {n} | {n} | {n} | {n} |
| Security fixes | {n} | {n} | {n} | {n} | {n} |
| Unique fixes | {n} | {n} | {n} | {n} | — |
| Arena result | — | — | — | — | {held/breached+patched/skipped} |

Synthesis: {1-line description of what the ensemble added beyond any single prompt}
```

4. Write full run artifacts to `/tmp/prompt-clash-ensemble-{run_id}/report.md`

## Customization

### Custom budgets

`--budgets 1,3,5` spawns 3 agents at 1min, 3min, 5min. Minimum 2 budgets required.

### Budget presets

| Preset | Budgets | Use case |
|--------|---------|----------|
| `--budgets fast` | 1,2 | Quick ensemble, ~2min wall clock |
| `--budgets standard` | 1,2,3,4 | Default, ~5min wall clock |
| `--budgets thorough` | 1,2,3,4,5 | Extra self-attack budget, ~6min wall clock |

## State & Artifacts

All artifacts written to `/tmp/prompt-clash-ensemble-{run_id}/`:

| File | Contents |
|------|----------|
| `defender_1m.md` | 1-minute budget prompt |
| `defender_2m.md` | 2-minute budget prompt |
| `defender_3m.md` | 3-minute budget prompt |
| `defender_4m.md` | 4-minute budget prompt |
| `collected.md` | All prompts collected with headers |
| `synthesis.md` | Coverage table + fused prompt |
| `arena.md` | Arena attack/defense results (if run) |
| `report.md` | Full run report with comparison table |

## Termination Labels

| Label | When |
|-------|------|
| `ensemble_complete` | All phases finished, prompt delivered |
| `ensemble_complete_no_arena` | Synthesis done, arena skipped |
| `partial_ensemble` | 2-3 defenders completed, synthesis ran on partial set |
| `synthesis_failed` | Synthesis agent failed — fall back to best individual prompt (longest budget that succeeded) |
| `insufficient_inputs` | Fewer than 2 defenders completed — cannot ensemble, return best single prompt |

## Golden Rules

1. **The ensemble must be strictly better.** If the synthesis drops a security fix that any individual prompt caught, the synthesis has failed. Coverage is monotonically increasing.
2. **Token efficiency is a real constraint.** A 500-token ensemble that covers 12 fixes loses to a 150-token ensemble that covers 10 fixes, because the token penalty outweighs the marginal security gain. Compress aggressively.
3. **Self-attack patches are gold.** The 4min prompt's self-attack findings are high-signal — they represent actual breaches the prompt was vulnerable to. Always include these patches.
4. **Diversity is the point.** The ensemble works because different budgets produce different structural choices. If all 4 prompts are nearly identical, the challenge probably has a single dominant strategy — in that case, prefer the most compressed version.
5. **Time wins tournaments.** The entire ensemble must complete in ~5min wall clock (agents are parallel). If the user is in a timed round, they need the result fast. NEVER spawn a synthesis agent — do it inline.
6. **The 1min prompt is the anchor, not the 4min.** Start from the most compressed prompt and selectively add high-value fixes from longer budgets. Don't try to compress a verbose prompt down — that's slower and produces worse token efficiency.
7. **Majority vote is WRONG for spec-compliance.** If 3 of 4 defenders contradict the spec and 1 respects it, the 1 is correct. The Competition Meta-Pattern override takes precedence over majority consensus. Always check: "did any defender respect the spec constraint while the others rejected it?"
8. **Never add a round-trip when you can act inline.** Every agent spawn in a timed round costs 15-40s. The coordinator has all the information it needs after Phase 2 — synthesize immediately, output immediately. The collected.md file is for the audit trail, not a required input to another agent.

## Anti-Patterns (learned from competition losses)

| Anti-pattern | What happened | Fix |
|---|---|---|
| **Overcorrecting past the spec** | Spec said "24-byte key" → 3 of 4 defenders insisted on 32-byte AES-256, contradicting the spec. AES-192-GCM with 24-byte key was the correct answer. | Competition Meta-Pattern rule in defender prompt: "Is there a secure algorithm that accepts this exact spec value?" |
| **Synthesis agent round-trip** | Spawned a separate agent to synthesize → user had to interrupt with 30s left, coordinator hand-assembled the prompt under pressure. | Inline synthesis by coordinator. No extra agent spawn. |
| **Anchoring on the verbose prompt** | Tried to compress the 4min prompt (15 rules, 400+ tokens) down to competition size. Slow and produces mediocre compression. | Anchor on the 1min prompt and selectively add fixes from longer budgets. |
| **Majority-vote on correctness** | 3/4 agreed on AES-256 → ensemble would have voted for the wrong answer. | Spec-compliance check overrides majority vote. The minority defender that respects the spec wins. |
