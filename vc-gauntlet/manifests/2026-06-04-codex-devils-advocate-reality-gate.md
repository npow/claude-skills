## Edit Manifest — vc-gauntlet — 2026-06-04

### Change summary
Overhaul the single-model critique→rewrite→self-judge loop (which drifts to false GO) into a balanced, reality-grounded fundability screen with an independent codex devil's-advocate bear case. Add reality-calibration gate, CONDITIONAL-GO verdict, honest termination labels, anti-rationalization counter-table, founder/wedge relativity, and a FORMAT.md output contract. Fix name/dir mismatch. Bind codex with the anti-nihilism rule so the devil's advocate combats rubber-stamping WITHOUT introducing reflexive NO-GO.

### Evidence
This session's review of vc-gauntlet against create-skill standards:
- name frontmatter = `vc-proposal-reviewer` but dir/invocation = `vc-gauntlet` (mismatch).
- Single model critiques + rewrites + judges → structural rubber-stamp bias ("iterate until bulletproof" rewards convergence, not truth).
- No reality-calibration → can bless hallucinated TAM / miss real competitors.
- Missing workflow discipline: no counter-table, no honest termination labels (max-10-iterations case undefined), no iron-law gate, vague "bulletproof/strong".
- Binary GO/NO-GO doesn't compose with opportunity-dfs §8 which expects GO/CONDITIONAL-GO + "one thing that must be true".
- User request: integrate codex as cross-model devil's advocate, balanced against nihilism.

### Predicted fixes
- Rubber-stamp bias: codex independent bear case (§4) + rewrite-must-resolve-not-delete rule (§6) + iron-law evidence gate (§8) → fewer false GO.
- Hallucinated market claims: reality-calibration gate (§3) forbids unsourced TAM / nirvana "no competitors".
- Nihilism risk from adding an attacker: §0 + §4 bind codex to steelman; NO-GO must name what would flip to GO → no reflexive kill.
- Composability: CONDITIONAL-GO + must_be_true added → matches opportunity-dfs §8 contract.
- Discipline: counter-table + termination enum + FORMAT.md added.

### Predicted regressions
- Per-run cost/latency up (web search + codex pass + iterations). Accepted; cap 6 iterations; gauntlet is a final gate, not per-node.
- Risk codex devil's advocate over-rotates to NO-GO (introduces nihilism — the exact thing user warned against). Mitigated by §0 anti-nihilism binding + counter-table rows + NO-GO-must-name-the-GO-path rule. Will check in verification.
- name change could affect references — mitigated: dir/registration is already `vc-gauntlet`; aligning frontmatter removes drift rather than adds it.

### Verification plan
1. Structural: SKILL.md reads as a map (no inline code blocks), frontmatter name=vc-gauntlet, all new sections present, FORMAT.md exists, line count < 300.
2. Behavioral: run one codex devil's-advocate pass (per §4) on a real proposal (the session's HIL-CI opportunity) and confirm it returns BOTH a substantive bear case AND a steelman / "what would make it GO" — i.e. balanced, not pure nihilism. Confirm the flow can yield CONDITIONAL-GO + a must_be_true.

### Verification results
1. Structural — CONFIRMED. SKILL.md = 58 lines (flat, <300); frontmatter name=vc-gauntlet (mismatch fixed); 0 fenced code blocks in SKILL.md (JSON contract moved to FORMAT.md per workflow rule); 12 sections present (§0 dual-bias rails, §3 reality gate, §4 codex devil's-advocate, §8 GO/CONDITIONAL-GO/NO-GO criteria, §9 termination enum, §11 counter-table); FORMAT.md present; skill registry picked up new description.
2. Behavioral (codex devil's-advocate pass on the HIL-CI proposal, per §4 + §0) — CONFIRMED BALANCED:
   - Bear case: produced across all 8 dimensions + named single most-likely death reason. PASS.
   - Reality-calibration: named real competitors WITH sources (SiMa Palette, Qualcomm Dragonwing, EdgeGate). PASS (§3 behavior present even in the codex lane).
   - Anti-nihilism binding: explicitly stated competition is "Not a kill by itself"; did NOT NO-GO on incumbent presence. PASS (predicted regression NOT observed).
   - Steelman + CONDITIONAL-GO: produced the steelman, a single must-be-true (5 non-friendly OEMs commit paid pilots/LOIs ≥$50k ARR-equiv in 90 days), and the cheapest test (concierge board-farm pilot, charge before automating). Suggested verdict CONDITIONAL_GO. PASS — confirms §8 CONDITIONAL-GO + composability with opportunity-dfs §8.
Outcome: predicted fixes confirmed; the key predicted regression (codex over-rotating to nihilist NO-GO) did NOT occur — the §0 binding held. Edit accepted.
