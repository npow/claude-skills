# Soundness Critic (Phase 3.7)

The novelty kill chain (NOVELTY.md) answers exactly one question: **"does this already exist?"** It does NOT
answer **"is the idea's core technical claim actually true?"** These are orthogonal. The most dangerous idea in
the whole pipeline is one that is **novel *because* its load-bearing premise is false** — nobody built it
because it cannot work, so the prior-art search finds nothing and stamps it NOVEL. Novelty is necessary but not
sufficient. The soundness critic is the gate that catches "novel but broken."

This gate exists because of a real failure: a deep-idea run on DiffusionBlocks passed two ideas
(`killed: []`, 100% judge-pass) whose load-bearing claims were directly contradicted by the target system's
training code. A Haiku web-search killer/judge cannot catch a claim like "each training sample only updates a
subset of blocks" — that requires reading the actual training loop. Hence: a stronger, code-grounded,
cross-model critic.

---

## When it runs

Phase 3.7, **after** prior-art verification (Phase 3.5) and feasibility (Phase 3.6), only on ideas still alive
(killer ≠ KILLED, judge ≠ not_novel, prior-art ≠ exact_match). An idea is a **survivor only if it is also
`SOUND`**. Soundness is the last gate before presentation.

Order rationale: don't spend the expensive cross-model/code-grounded critic on ideas already dead on novelty.
But never present a novel idea that hasn't passed soundness.

---

## The load-bearing claim (required generator field)

Every generated idea must declare a single **`load_bearing_claim`**: the one technical assertion the idea
depends on, stated so it is **falsifiable**. If this claim is false, the idea collapses. Examples:

- (DiffusionBlocks unlearning) "Each training sample contributes gradient to only a sparse subset of blocks."
- (DiffusionBlocks topology search) "Independently-trained blocks remain valid score functions when reordered
  or repeated across positions."
- (federated) "Composing party-A's high-σ block with party-B's low-σ block approximates the union
  distribution of A and B."

If a generator cannot state a single falsifiable load-bearing claim, that itself is a soundness red flag — the
idea's mechanism is too vague to verify (tag `[SOUNDNESS_UNVERIFIED]`).

---

## Cross-model requirement (why codex, not Claude)

The killer, judge, and prior-art agents are all Claude. They share a prior: if a claim *sounds* plausible to
Claude, all three inherit the same blind spot. The soundness critic is therefore routed to a **different model
family** (OpenAI via the `codex` CLI) so its errors are uncorrelated with the rest of the pipeline. A
second-opinion from the same model is worth far less than a second-opinion from a different one.

**Fallback order if codex is unavailable** (not logged in / not on PATH / non-zero exit / empty output):
1. `gemini` CLI (also a different family), same prompt + schema.
2. A Claude `general-purpose` agent at the **opus** tier with repo read access — explicitly weaker (correlated
   with the rest of the pipeline) → its verdict is automatically tagged `[SOUNDNESS_SAME_FAMILY]`.

Never silently skip the gate. If no critic can run, tag every surviving idea `[SOUNDNESS_UNVERIFIED]` and say so.

---

## Code grounding

When the idea targets a **specific system with available source** (a repo, the project under analysis), the
critic MUST be given read-only access to that source and instructed to verify the claim against the actual code,
citing `file:line`. First-principles reasoning alone is insufficient when ground truth is on disk. When the idea
is about an external/unavailable system, the critic falls back to first-principles + literature reasoning and
must say which it used.

---

## Invocation contract (codex)

Write the critic prompt to a file and the schema to `soundness_schema.json` (below). Then:

```bash
codex exec \
  -s read-only \
  --skip-git-repo-check \
  -C <REPO_ROOT_THE_IDEA_TARGETS> \
  --output-schema <PATH>/soundness_schema.json \
  -o <PATH>/soundness_<idea_id>.json \
  - < <PATH>/soundness_prompt_<idea_id>.txt
```

- `-s read-only`: critic can read the repo, cannot modify it. Never use `danger-full-access`.
- `-C`: the repo whose code grounds the claim. Omit (and say so) for external-system ideas.
- `--output-schema`: forces structured JSON (schema below). `-o` writes the final message only.
- Timeout: 420s wall-clock per idea. On timeout → verdict `UNVERIFIED`, tag `[SOUNDNESS_UNVERIFIED]`. Do not retry.
- Run critics in parallel across ideas (each is an independent subprocess).

### soundness_schema.json

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["verdict", "load_bearing_claim_restated", "falsification_attempt", "evidence", "confidence"],
  "properties": {
    "verdict": { "type": "string", "enum": ["SOUND", "UNSOUND", "UNVERIFIED"] },
    "load_bearing_claim_restated": { "type": "string" },
    "falsification_attempt": { "type": "string" },
    "evidence": { "type": "string" },
    "confidence": { "type": "string", "enum": ["high", "medium", "low"] }
  }
}
```

---

## Critic prompt template

```
You are a SOUNDNESS CRITIC for a research-idea pipeline. You do NOT judge novelty. You determine whether the
idea's single LOAD-BEARING TECHNICAL CLAIM is actually TRUE for the system it targets. Be adversarial: your
default posture is that the claim is FALSE until the evidence forces you to concede it is true. A creative,
novel-sounding idea built on a false premise is exactly what you exist to catch.

SYSTEM CONTEXT: {one-paragraph description of the target system; name the files/modules that govern the claim}

IDEA: {name}
CORE MECHANISM: {what_it_does, 2-3 sentences}
LOAD-BEARING CLAIM (verify this): {load_bearing_claim}

YOUR TASK:
1. Restate the load-bearing claim precisely in your own words.
2. Attempt to FALSIFY it. If source code is available (it is, under your working root), READ the relevant code
   and reason from what it actually does — cite file:line. If no code is available, reason from first
   principles / established theory and say so explicitly.
3. Decide using these definitions PRECISELY:
   - SOUND: the code/theory positively supports the claim.
   - UNSOUND: the claim is false, OR the code provides no mechanism that would make it true, OR the idea's
     value evaporates once you weaken the claim to something the code actually supports. "The system only
     guarantees a weaker property than the idea needs" is UNSOUND, not UNVERIFIED.
   - UNVERIFIED: reserve ONLY for when you genuinely could not inspect the relevant code/evidence (file
     missing, out of scope, ran out of time). Lack of positive proof for a claim the code gives no mechanism
     for is UNSOUND, NOT UNVERIFIED. Never default to SOUND.

Output ONLY the structured JSON.
```

**Verdict calibration note (load-bearing):** the most common critic error is hedging to UNVERIFIED when the
code clearly fails to provide the mechanism the idea requires. If the idea needs property P and the code only
ever establishes a strictly weaker property Q (and nothing in the code could upgrade Q→P), the correct verdict
is UNSOUND with the evidence "code establishes Q, not P." Example: an idea needs *per-sample* attribution
sparsity; the code only routes *per-step* and never pins a sample to a block → UNSOUND (not UNVERIFIED).

---

## Routing (coordinator reads structured output only — never overrides)

| Verdict | Action |
|---|---|
| `SOUND` | Idea may be presented as a survivor (subject to novelty/prior-art tags from earlier phases). |
| `UNSOUND` | Idea is **KILLED** with `failed_check: SOUNDNESS`, *regardless of how novel it is*. Log the falsification. Novelty does not rescue an unsound idea. |
| `UNVERIFIED` | Idea is tagged `[SOUNDNESS_UNVERIFIED]` and presented as a **near-miss, not a survivor** (not counted toward target). State what evidence was missing. |

A 0% UNSOUND rate across ≥4 ideas is the soundness analog of a broken judge — inspect the critic's
falsification_attempt fields; if they are thin/empty, the critic is rubber-stamping. Re-run with a stricter
prompt or escalate the model.

**Coordinator never decides soundness.** Same invariant as Golden Rule 9 for novelty. The critic's structured
verdict stands; the coordinator does not soften UNSOUND to "basically works."

---

## Anti-rationalizations (reject at the gate)

| Excuse | Reality |
|---|---|
| "It's so novel that whether it works is an implementation detail." | No. An idea whose core claim is false is not an idea, it's a misconception. UNSOUND kills regardless of novelty. |
| "The claim is *probably* true, no need to read the code." | No. When ground truth is on disk, 'probably' is the failure mode that produced this gate. Read the code, cite file:line. |
| "Codex isn't set up; I'll just have the coordinator (Claude) judge soundness." | No. Coordinator self-judging is the correlated-blind-spot trap. Use the documented fallback chain and tag accordingly. |
| "Critic returned UNVERIFIED fast — close enough to SOUND." | No. UNVERIFIED ≠ SOUND. Present as near-miss with the tag; never promote to survivor. |
| "The critic is being pedantic; the weakened version still works." | If the idea only survives in a weakened form, that weakened form is a *different idea* — re-run it through the pipeline. Don't launder a broken claim into a survivor. |
