---
name: vc-gauntlet
description: Stress-test a startup/product proposal like a top-tier VC partner meeting — reality-checked against real market data, with an independent codex devil's-advocate bear case — then iterate hardened rewrites to a GO / CONDITIONAL-GO / NO-GO verdict. Use when the user says "vc review", "is this fundable", "would a VC fund this", "tear apart my startup idea", "pitch critique", "investor lens", "gauntlet this", "red-team my startup", "poke holes in my idea". Also the fundability gate invoked by opportunity-dfs §8.
version: 2.0.0
---

# VC Gauntlet — reality-checked, codex-cross-examined fundability screen

## 0. The two biases this skill MUST hold off (read first)
A single model that critiques, rewrites, AND judges its own proposal drifts to a false **GO** — it rewrites objections away instead of resolving them. The independent codex devil's-advocate (§4) is the counterweight to that optimism. But the opposite failure is just as wrong: reflexive **NO-GO** nihilism — killing anything contested or incumbent-heavy. Every real company enters a contested market. So both rails are hard rules:
- Codex's job is to surface the REAL bear case, NOT to nuke. A NO-GO must be EARNED and must name the wedge / founder-shape / why-now that WOULD flip it to GO.
- **"Has incumbents / is contested" is NEVER, by itself, a NO-GO.** Price the risk; find the wedge they can't take.
- A **GO must be EARNED on evidence (§3, §8)** — never produced by polishing prose.
Balanced screen: neither rubber-stamp nor knee-jerk kill.

## 1. Input
A startup/product proposal OR an opportunity tuple (market × wedge × advantage × why-now × who). Fundability is **founder- and wedge-relative** — if the founder-shape/wedge is unspecified, ask "GO for whom, via what wedge?" before judging.

## 2. The 8 VC dimensions
Critique across: market size & urgency · problem severity & frequency · insight/founder wedge · competitive landscape · defensibility/moat · GTM & distribution (who actually pays + the motion) · business-model viability · technical feasibility & execution risk. Per dimension emit a strength, a risk, and a 1–5 score.

## 3. Reality-calibration (iron-law gate — no unsourced claims)
Before ANY verdict, web-search and ground the load-bearing claims: market size (cite a source + number, not a guess); ≥3 NAMED competitors with their differentiation; ≥1 recent comparable raise/exit. **Forbidden as the basis of a GO/CONDITIONAL-GO: an unsourced TAM, "no real competitors" (nirvana), or "huge market" with no number.** If a claim can't be grounded, it's a risk, not a strength.

## 4. Codex devil's-advocate (independent cross-model bear case)
Run codex as the second investor — the partner who wants to pass. It must produce the strongest BEAR case across the 8 dimensions and name the single most likely reason this dies. **Bind it with §0:** it must ALSO state what would have to be true to invest anyway (steelman), and may NOT issue a kill on incumbent-presence alone. Invoke non-interactively: `zsh -ic 'codex exec "$(cat /tmp/p.txt)" < /dev/null > /tmp/o.md 2>&1'` (node script needing nvm + yolo alias; `< /dev/null` stops the stdin hang; answer is after the last `succeeded in` line). Reconcile the model's view with codex's to an aligned verdict; record genuine disagreement explicitly rather than papering over it.

## 5. Fatal-flaw test
A flaw is FATAL only if it survives BOTH reality-calibration AND the steelman (e.g. no market even when properly sized; no defensibility AND no wedge any plausible founder could build; unworkable tech with no path). Incumbent presence, hard GTM, and capital intensity are **risks to price, not fatal flaws.** Record each fatal flaw with the evidence that makes it fatal.

## 6. Rewrite rule (resolve, don't delete)
Produce a hardened rewrite addressing each non-fatal risk. **HARD RULE:** a rewrite must RESOLVE an objection with a concrete mechanism — not delete or hand-wave it. If the only way to "fix" a risk is to remove the claim, the risk STANDS — flag it, don't bury it.

## 7. Verdict + iterate
Emit the verdict (§8) + the single thing that must be true + the hardened proposal. If not terminal, feed the hardened version back through §2–6. Cap **6 iterations** — convergence past that is rewriting, not improving.

## 8. Verdict criteria (concrete — never "bulletproof")
- **GO** — all 8 dimensions ≥3; market sourced; ≥3 competitors mapped with a real differentiation; who-pays + budget named; why-now real; no fatal flaw; codex aligned.
- **CONDITIONAL-GO** — a credible win-path exists but hinges on ONE testable assumption (the "must be true"); name the cheapest test to resolve it. This is the expected default for promising-but-unproven ideas and is what opportunity-dfs §8 consumes.
- **NO-GO** — a fatal flaw survives §5 AND the steelman fails. MUST name the wedge / founder-shape / why-now that would flip it to GO (anti-nihilism, §0).

## 9. Termination labels (finite enum — never "done")
`GO` | `CONDITIONAL_GO` | `NO_GO` | `UNRESOLVED_AT_CAP` (hit 6 iterations without convergence — report best current verdict + the unresolved assumption) | `BLOCKED_NEEDS_INPUT` (proposal too vague to evaluate — ask the one blocking question).

## 10. Output
See [FORMAT.md](FORMAT.md) for the JSON contract (per-dimension scores, comparables found, codex bear case + steelman, fatal flaws, verdict, must_be_true, cheapest_test, hardened proposal, label).

## 11. Anti-rationalization counter-table
| Excuse | Reality |
|---|---|
| "I rewrote the objection away, so it's GO now." | §6: a rewrite must RESOLVE with a mechanism, not delete. Removing the claim leaves the risk standing. |
| "The market is huge." | §3: unsourced TAM is forbidden as a GO basis. Cite a number + source. |
| "No real competitors." | Nirvana fallacy. Find ≥3 named competitors (§3); "none" almost always means you didn't look or the market is dead. |
| "It has big incumbents → NO-GO." | §0: incumbent presence is never alone a kill. Price the risk; find the wedge they can't take. |
| "Codex says pass, so NO-GO." | §0/§4: codex is a bound devil's advocate, not the decider. A NO-GO must name what would flip it to GO. |
| "It's strong / bulletproof / GO." | §8: vague. State the dimension scores, the sourced comps, and the one thing that must be true. |
| "Hit the iteration cap, call it GO." | §9: that's `UNRESOLVED_AT_CAP`, not GO. Report the unresolved assumption honestly. |
| "Skip the web search, I know this market." | §3 is an iron-law gate. Ungrounded market knowledge is exactly how single-model review blesses a hallucinated TAM. |
