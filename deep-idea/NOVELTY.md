# Novelty Kill Chain

4 checks. Run in order. Kill on first failure. A killer agent runs these checks adversarially — the goal is to FIND the idea already existing.

**Model tier:** Haiku (Scout). Run killer agents in parallel — one per idea. Each gets a 6-minute timeout.

**Search budget:** 5 targeted web searches per idea. N4 and N2 require no searches. N3 may use 1 search from the budget. N1 gets the remaining searches.

**Coordinator timeout handling:** If a killer agent times out, the coordinator treats the idea as `KILLED` with `failed_check: TIMEOUT`. Do not re-run automatically. Log and continue.

**Coordinator fail-safe:** If the killer returns output that does not begin with `VERDICT:` on the first line, treat as `KILLED` with `failed_check: PARSE_ERROR`. Never treat an unparseable response as NOVEL.

---

## Novelty is a two-stage independent verdict

The kill chain in this file is stage one — the **prosecution**. It searches adversarially for evidence the idea already exists and emits a killer verdict.

The **judge** (stage two) is a separate agent with separate context that makes a blind classification from idea + stripped kill-chain evidence. See SKILL.md Phase 3a and the Novelty Judge Agent Prompt Template for the contract.

The **prior-art search** (stage three) is a separate external-source verification agent with web access. See SKILL.md Phase 3.5 and the Prior-Art Search Agent Prompt Template.

**Coordinator rule (Golden Rule 9):** the coordinator never decides novelty. A `NOVEL` verdict from the killer alone does not produce a survivor — it only advances the idea to the judge. The final classification comes from structured output of the judge and prior-art searcher together, read by the coordinator with no coordinator editorializing.

If the killer is the only novelty check in the run (judge or prior-art agent fail to spawn or produce parseable output), tag the idea `novelty_unverified` and present with the tag. Never silently promote a killer-only verdict to survivor.

---

## Structured output requirement

Every killer agent response **must** begin with these structured lines as the absolute first lines of output:

```
VERDICT: NOVEL|KILLED|ADJACENT|THIN
FAILED_CHECK: N0|N1|N2|N3|N4|NONE
CONFIDENCE: high|medium|low
```

- `FAILED_CHECK: NONE` when verdict is NOVEL, ADJACENT, or THIN
- `FAILED_CHECK` must name the specific check that caused a KILLED verdict — this field drives LOOP.md mutation routing and is **required** for KILLED verdicts
- ADJACENT = near-miss with meaningful structural differentiation (worth pursuing with refinement)
- THIN = near-miss where differentiation is marginal; existing solutions cover most of the value
- Everything after these three lines is free-text evidence

The coordinator reads ONLY these three structured lines for routing. Free-text is logged but not parsed.

---

## Kill chain execution order

Run all checks in sequence, kill on first failure. Zero-search checks run first to avoid spending search budget on ideas that should be killed immediately.

1. **N0** (Host-Tool Specificity) — zero searches. Only applies when domain names a specific existing product. Kills "library ideas in product clothing."
2. **N4** (Forcing Function Verification) — zero searches. Evaluate idea without chain first, then chain. Fastest kill.
3. **N1** (Exact Existence) — 4-5 searches. Kills ideas that already exist.
4. **N2** (Structural Clone) — no additional searches (uses N1 context). Kills renamed clones.
5. **N3** (Recency Test) — 0-1 searches. Kills "long obvious" ideas.

---

## Check N0: Host-Tool Specificity (product-specific prompts only)

**Applies when:** The domain names a specific existing product (e.g., "make Metaflow relevant", "new features for Postgres", "ideas for Figma").

**Goal:** Verify the idea structurally requires the named product's unique capabilities. An idea deliverable by a standalone library called inside any generic step is a library idea, not a product idea.

**The test — no search required, pure reasoning:**
1. List the named product's unique technical primitives (e.g., Metaflow: cross-run artifact store queryable by `metaflow.client`, `@step`/`@foreach` execution model, namespace, local-to-cloud scaling).
2. Does this idea depend on at least one of those primitives in a load-bearing way — i.e., removing the primitive breaks the idea, not just degrades it?
3. Could the user get identical value by calling `pip install some-lib` inside a generic function?

**Kill criteria:** Core value is fully deliverable as a standalone library with no structural dependency on the named product's architecture. "It runs inside the product" is not dependency — it must USE the product's unique internals.

**Pass criteria:** Idea depends on ≥1 named-product-specific primitive, named explicitly.

**Examples:**
- KILLED: "Add Pydantic schema validation to LLM calls inside Metaflow steps" — this is `pip install instructor` in any function. No Metaflow primitives required.
- PASSES: "Retrospective workflow crystallization with `mf.crystallize()`" — depends on Metaflow's artifact store and `@step` system as the output target. Cannot be a standalone library.

**Record:** State which named-product primitive the idea depends on, or the specific reason it fails.

---

## Check N4: Forcing Function Verification (run FIRST if N0 not applicable)

**Goal:** Confirm the idea genuinely emerged from its claimed forcing function, not from free association or lazy generation.

**The problem this catches:** Generators produce a generic idea and backfill a plausible-sounding derivation chain. This check catches backfilling.

**Two-pass evaluation — this order is mandatory:**

**Pass 1 — Blind assessment (before reading the derivation chain):**
Read ONLY: the idea name, what it does, who it's for, and the forcing function name. Do NOT read the derivation chain yet.
Ask: "Could a standard 'give me ideas' prompt have produced this idea without using the {FORCING_FUNCTION} mechanism?"
- If the idea is obviously generic regardless of forcing function → kill here. Write `VERDICT: KILLED` / `FAILED_CHECK: N4`.
- If the idea seems non-obvious or forcing-function-shaped → proceed to Pass 2.

**Pass 2 — Chain evaluation (after blind assessment):**
Now read the derivation chain. Evaluate:
1. Does the chain have ≥3 explicit steps, each causally connected to the next?
2. Does the chain anchor to a specific element from the landscape map (not generic knowledge)?
3. Would a DIFFERENT forcing function (e.g., EDGE DESIGNER instead of INVERTER) have produced this same idea? If yes → kill.
4. Could the idea have come from step 1 of the chain alone, without the subsequent steps? If yes → chain shortcutting, kill.

**Kill criteria (N4):** Idea would plausibly have been generated without the forcing function, OR the derivation chain is vague/backfilled/too short (fewer than 3 steps), OR the chain doesn't anchor to landscape data.

**Pass criteria (N4):** The blind assessment suggests a non-obvious idea, AND the chain has ≥3 explicit causally-connected steps anchored to the landscape.

---

## Check N1: Exact Existence

**Goal:** Find an existing product, tool, library, or service that solves the same problem using the same mechanism for the same user.

**Adversarial mindset:** Don't search for the idea's name. Search for the PROBLEM it solves and the MECHANISM it uses.

**Search strategy (4-5 searches):**
1. Search: `"{core mechanism}" "{target user}" tool OR product OR service`
2. Search: `"{problem being solved}" solution site:github.com`
3. Search: `"{problem being solved}" site:producthunt.com`
4. Search: `"{mechanism}" startup OR app OR software` (without domain constraints)
5. Search: `"{idea concept}" -{domain name}` (look for it in unexpected places)

**Pass criteria:** No existing product found that uses the same mechanism for the same user type.

**Kill criteria:** Existing product found that is actively maintained (last update within 18 months), solves the same problem, and uses the same core mechanism.

**FLAGGED (not killed):** Existing products exist but are in a different domain, have a different target user, are abandoned/unmaintained, or solve the problem differently. Note the differentiation — this is a near-miss, not a kill.

**Record:** Every URL checked, every search query run, the exact product found (if killed).

---

## Check N2: Structural Clone Test

**Goal:** Detect ideas that are structurally identical to an existing product but renamed or domain-shifted.

**No additional searches needed** — use the context gathered in N1.

**Test:**
1. Abstract the idea to its structure: who provides what to whom, through what mechanism, with what value exchange
2. Is there a well-known product with this exact structure in any domain?
3. If yes: does the domain-shift introduce constraints that force genuinely different product architecture? (Sometimes the shift IS the insight — but this must be structural, not cosmetic)

**Kill criteria:** Same structure as a known product, domain-shift adds no novel technical or user-relationship constraints.

**Pass criteria:** Either no structural clone exists, OR the domain-shift introduces constraints that force genuinely different product architecture.

---

## Check N3: Recency Test

**Goal:** Detect "long obvious" ideas — things that COULD have been built 3+ years ago but weren't.

**May use 1 search** to find evidence of failed attempts or demand signals.

**The test:**
1. Could this idea have been technically implemented 3 years ago?
2. If yes: why wasn't it built? Find the structural reason.

**Three valid structural reasons (pass with explanation):**
- **Market timing**: The user population wasn't large enough 3 years ago
- **Enabling technology**: A specific enabling technology didn't exist
- **Regulation**: A regulation or compliance requirement didn't exist

**If no structural reason found:** Mark as FLAGGED with note "Long obvious — investigate why this hasn't been built." Do not kill outright, but require a structural gap explanation before presenting as a survivor.

**Kill criteria:** Idea could have been built 3+ years ago AND no structural reason explains why it wasn't AND no evidence of failed attempts.

---

## Verdict definitions

| Verdict | Meaning | Action |
|---------|---------|--------|
| **KILLED** | Failed at least one check with clear evidence | Log to state file with `failed_check` and specific evidence. Do not present. |
| **ADJACENT** | Near-miss: meaningful structural differentiation exists but adjacent work is present | Present as near-miss. Note specifically what makes it distinct. Worth pursuing with refinement. Don't count toward target survivors. |
| **THIN** | Near-miss: differentiation is marginal; existing tools cover most of the value | Present briefly. Note that existing solutions are close. Low priority for pursuit. Don't count toward target survivors. |
| **NOVEL** | Passed all checks with evidence | Present immediately. Count toward target. |

**Distinguishing ADJACENT from THIN:** Ask "if a user wanted what this idea offers, would they find an existing solution satisfying?" If no (the gap is real and the differentiation is structural), it's ADJACENT. If yes (an existing tool is 80%+ of the way there), it's THIN.

---

## Recording kills

Every kill must include:
1. `FAILED_CHECK: N1|N2|N3|N4` — the specific check that failed
2. Specific evidence (URL, product name, or reasoning)
3. Kill reason in one sentence

Vague kills ("similar things exist") are invalid. Every kill must be falsifiable.

---

## Landscape refresh

After every 3 cycles, the coordinator should re-check whether any previously NOVEL survivors have been killed by newly launched products. Run 1 targeted search per survivor:
- `"{idea concept}" site:github.com OR site:producthunt.com` launched in the last 3 months

If a survivor is now killed by a new launch, present this to the user immediately.
