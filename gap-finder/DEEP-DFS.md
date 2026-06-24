
# Gap Finder — Deep Mode (DFS, codex-cross-examined, anti-nihilist opportunity discovery)

Invoked by `gap-finder --deep` (see [SKILL.md](SKILL.md)). Where the default batch mode generates flat candidates and kills them against a 6-check chain, deep mode treats the space as a **tree of opportunity tuples**, branches depth-first, runs an independent **codex** cross-attack plus a mandatory steelman on every node, and ends with a VC-gauntlet fundability gate. Use it for exhaustive, adversarial discovery in a single market/domain ("find the *real* opportunities in X", "keep digging until you exhaust X").

## 0. The prior you MUST hold (this is the whole point)
**Opportunities always exist.** Thousands of companies are founded every year and many win in crowded, incumbent-heavy, "obviously hard" markets. **If a run concludes "there are no opportunities," the methodology has failed — not the market.** Your job is NOT to adjudicate whether opportunity exists. It is to find **WHICH** opportunities are live, **for WHOM**, via what **WEDGE**, and **why NOW** — and rank them. Returning "nothing survives" is a forbidden output; it means your bar is wrong. Recalibrate and try again.

This skill exists to kill two specific failure modes that produce false nihilism:
1. **Whitespace / nirvana fallacy** — pruning anything that is contested or has incumbents. Every real startup enters a contested market; winners win on wedge, execution, timing, distribution, and founder-fit, *not* virgin whitespace. **"Has incumbents" / "is contested" is NEVER, by itself, a prune reason.**
2. **Generic-entrant bias** — judging "is this good for an undifferentiated from-zero team?" instead of "for what kind of team / via what wedge is this a winner?" Opportunity is **founder- and wedge-relative**.

## 1. The unit of analysis
An opportunity is a TUPLE, never a market alone:
> **(market / need) × (specific wedge) × (unfair advantage it requires) × (why-now catalyst) × (who it's for)**

Evaluate and rank *tuples*. "Inspection analytics" is not an opportunity. "Cross-OEM defect-trending for mid-tier substation operators, entered via a CMMS-write-back wedge, won by a team with utility distribution, now that mixed robot fleets exist" is.

## 2. The per-node loop (every node gets ALL of these, in order)
1. **Characterize** the tuple (market, wedge, unfair-advantage, why-now, who-for).
2. **Reality-calibrate FIRST (the falsifier).** Web-search for real companies that recently raised / grew / won in this node. If they exist, the opportunity EXISTS by definition — the task becomes "what is the winning wedge those winners used / left open," not "does it exist." **A prune reason that would also kill a company currently succeeding here is INVALID** — discard it.
3. **Incumbent map (named, not generic).** List the SPECIFIC incumbents/competitors (companies, not categories). For each: what they actually own (data, distribution, integration/C2 authority, capital, brand, design-wins). Then run **build-vs-buy-vs-ignore**: would they build this, acquire a competitor, partner, or ignore it — and *why*. Conclude with the **structural reason they won't or can't crush THIS wedge** (e.g. it cannibalizes them, it's beneath their margin floor, it's a market too small for them, it's a neutrality role they're disqualified from). **Naming incumbents is for rigor, NOT a prune trigger — "incumbents exist" is never a kill (see §10).** If you cannot articulate why incumbents won't crush it, that weakness flows into the attack (3→5), not an automatic prune.
4. **Wedge & GTM (how it actually gets bought).** State: the **entry wedge** (the thin end — the first painful, narrow job); the **distribution motion** (how you reach buyers — inbound/benchmark, design-partner, channel/OEM, PLG, gov on-ramp); **who actually pays** (the *economic buyer* and their budget, not the end-user); **time-to-first-revenue**; and the **land→expand path**. A tuple with a great wedge but no credible who-pays / distribution answer is BRANCH (find the motion), not SURVIVOR.
5. **Adversarial attack — you.** The strongest kill-shots: incumbents (per §2.3), build-vs-buy, commoditization, capital intensity, timing, distribution, **who-actually-pays / value-capture / time-to-revenue** (per §2.4), regulatory.
6. **Adversarial attack — codex (independent second adversary).** See §6.
7. **MANDATORY steelman / win-path.** Given the attacks, construct the *strongest plausible path to win*: the wedge, the unfair advantage that neutralizes the kill-shots, the why-now, the founder-shape, the GTM. **You may not skip or shortchange this.** This is the anti-nihilism core — the counterweight to the attack.
8. **Verdict, with a HIGH bar to prune:**
   - **SURVIVOR** — a credible win-path exists. Keep + score. *Most contested-but-real markets land here.*
   - **BRANCH** — promising but broad → decompose into child tuples (sub-segment, sub-wedge, task/implement layer, customer tier, geo, business model, distribution angle) and DFS into them.
   - **PRUNE** — ONLY if all three hold: (a) the attack lands, (b) the steelman genuinely fails (no plausible team/wedge/timing wins), AND (c) no real company is currently winning there. Record a specific, falsifiable prune reason. If that reason would also kill a real winner → it's wrong → downgrade to SURVIVOR/BRANCH.
9. **Align with codex** on the verdict; iterate until aligned, or record the disagreement explicitly.

## 3. DFS + branching
- Maintain the tree in the state file (§5). Push children of SURVIVOR/BRANCH nodes onto the frontier.
- **Depth-first:** fully expand the most promising branch before backtracking; keep branching until the frontier is empty or the user's budget/depth cap is hit.
- Deeper = more specific (space → market → segment → wedge → ICP → motion). Stop branching a path when it reaches a **concrete, actionable tuple a founder could start on Monday**, or when children stop adding signal.

## 4. Calibration cadence (anti-nihilism enforcement — DO THIS)
After each round compute the **prune rate**. If you are pruning the majority of nodes, **STOP and recalibrate** — you are committing the whitespace fallacy. Re-open the pruned nodes and find the win-path you missed. A healthy run surfaces MANY survivors at varying attractiveness, ranked — not a binary, and never zero.

## 5. State file (resumable — runs can be long)
Persist to `<workdir>/gap-finder-deep-<space-slug>.json` after every node so the run resumes after interruption:
```
{ space, prior, round, frontier:[ids], survivors:[{id,title,score}], pruned:[{id,reason}], nodes:[ {
   id, parent, depth, title,
   tuple:{market,wedge,advantage,whynow,who},
   real_winners:[...],            // the falsifier
   incumbent_map:[{name,owns,build_buy_ignore,why_cant_crush}],   // §2.3
   wedge_gtm:{entry_wedge,distribution,who_pays,time_to_revenue,expand_path},  // §2.4
   attack_self, attack_codex, steelman_winpath,
   verdict, prune_reason, codex_aligned,
   score:{market,wedge,advantage,timing,winnability,capital_efficiency,gtm},  // gtm added; composite = sum
   gauntlet:{verdict,fatal_flaws,must_be_true,hardened},          // §8, top-N only
   children:[ids] } ], log:[...] }
```

## 6. Codex (independent second adversary + alignment)
Codex is a different model; use it to (a) independently attack each node and (b) check/contest verdicts, then iterate to alignment.
Invoke non-interactively: `zsh -ic 'codex exec "$(cat /tmp/prompt.txt)" < /dev/null > /tmp/out.md 2>&1'` (it is a node script needing nvm + the yolo alias; `< /dev/null` stops the stdin hang; final answer is after the last `succeeded in` line). Pass the same anti-nihilism rules to codex — instruct it to steelman, not just kill.

## 7. Orchestration (how to actually run it)
- Use the **Workflow tool** to evaluate frontier nodes in parallel each round (per node, the full §2 loop: characterize + reality-calibrate via web search + **incumbent map** + **wedge & GTM** + self-attack + mandatory steelman + proposed verdict + 7-dim score).
- Between rounds, run **codex** (Bash) to cross-attack + check the round's verdicts; reconcile to alignment; update state.
- Branch survivors/branch-nodes; repeat. Report progress per round: survivors so far, frontier size, prune rate (flag if prune rate is high — bias alarm).
- After DFS converges, run the **§8 VC Gauntlet** on the top-N survivors.
- Stop at frontier-exhaustion or the user's budget. The run is resumable from the state file.

### 7a. Model tiering (use the cheapest model that does the job well)
Pass `model:` per `agent()` call — do NOT run everything on the default. Match model to cognitive load:
- **haiku** — mechanical / well-structured sub-tasks: reality-calibration web-search summarization, deduping/normalizing winners, formatting the tree, extracting fields, prune-rate bookkeeping.
- **sonnet** (default for most nodes) — the per-node loop: incumbent map, wedge/GTM, attack, steelman, scoring. The workhorse tier.
- **opus** — only where depth pays: synthesizing the final ranked tree, the §8 VC Gauntlet judgment on top survivors, and reconciling genuine codex disagreements.
Rule of thumb: a step that mostly *retrieves/formats/restates* → haiku; a step that *reasons/judges/argues* → sonnet; a step that *decides the headline verdict or money call* → opus. When unsure, default to sonnet — never silently upgrade everything to opus (cost) or downgrade judgment steps to haiku (quality). The independent codex pass is the cross-model adversary regardless of which Claude tier ran the node.

## 8. VC Gauntlet (final-stage fundability gate on the top survivors)
Surviving DFS ≠ being fundable. After ranking, run the **top-N survivors** (default 3–5) through a VC-grade gauntlet — borrow the [vc-gauntlet skill](../vc-gauntlet/SKILL.md) (`vc-proposal-reviewer`): critique each top tuple across the 8 VC dimensions — **market size & urgency · problem severity & frequency · insight/founder wedge · competitive landscape · defensibility/moat · GTM & distribution · business-model viability · technical feasibility & execution risk** — flag any *fatal* flaw, then iterate a hardened rewrite until **GO** or **NO-GO**.
- Run it two ways and reconcile: (a) invoke `vc-gauntlet` (or apply its dimensions via an **opus** agent per the §8 lens), and (b) a **codex** VC pass as the independent second investor. Align the verdicts.
- Per top survivor, emit: **GO / CONDITIONAL-GO / NO-GO**, the **fatal flaws** (if any), the **single thing that must be true**, and the **hardened tuple** (the gauntlet's improved version). Store in `node.gauntlet` (§5).
- The gauntlet REFINES and RE-RANKS survivors; it does **not** resurrect the §0 nihilism — a NO-GO is "not fundable *as framed for this founder*," and must still name what wedge/founder-shape *would* make it a GO.

## 9. Output (NEVER "nothing works")
A **ranked list of surviving opportunity tuples**, each with: the wedge · the unfair advantage it requires · why-now · the concrete win-path · **named incumbents + why they can't crush it** · **wedge & GTM (who pays, distribution, time-to-revenue)** · **VC-gauntlet verdict + the one thing that must be true** · real comparable winners · key risks · who it's for. Plus the full explored tree (so every prune is auditable). If asked "is there an opportunity?", the answer is always a ranked list — with honest framing of difficulty and the edge required — not "no."

## 10. Anti-rationalization counter-table
Hold the line on BOTH failure modes: false nihilism (over-pruning) AND glib over-survival (rubber-stamping). Rows captured from real runs.

| Excuse | Reality |
|---|---|
| "It has big incumbents (Anduril/Mobileye/etc.) → prune." | Incumbents present is NEVER a prune (§0, §2.3). Do the named incumbent map and find *why they can't/won't crush this wedge*. If you can't, it weakens the steelman — it does not auto-prune. |
| "It's a benchmark/leaderboard → that's content, not a company." | Don't prune the pattern; interrogate the monetization. A public benchmark is the *inbound*; the company is the paid private decision/CI it funnels into. Make the who-pays explicit (§2.4) instead of dismissing. |
| "It survived DFS, so it's a real opportunity — ship it." | Surviving DFS ≠ fundable. It must clear the §8 VC Gauntlet (who pays, distribution, moat, fatal flaws) before it's presented as backable. |
| "I named the incumbents in the self-attack, that's enough." | The Incumbent Map (§2.3) is a dedicated step: named companies + what each owns + build-vs-buy-vs-ignore + structural reason they can't crush it. A one-line mention in the attack is not the map. |
| "The wedge is obvious; GTM is a later detail." | No who-pays/distribution/time-to-revenue answer → BRANCH, not SURVIVOR (§2.4). The dimension codex most often catches is who actually pays — never skip it. |
| "Run everything on opus to be safe." | Wrong tier discipline (§7a). Retrieve/format → haiku; reason/judge → sonnet; headline/money call → opus. Blanket-opus burns budget; blanket-haiku tanks judgment. |
| "Prune rate is 60% but each prune looks justified." | High prune rate is the whitespace-fallacy alarm (§4). Re-open pruned nodes and find the win-path you missed before continuing. |
