# vc-gauntlet — output contract

Return a single JSON object. `verdict` is the investment call; `label` is the run-termination state (they match for GO/CONDITIONAL_GO/NO_GO, and diverge for UNRESOLVED_AT_CAP / BLOCKED_NEEDS_INPUT).

```json
{
  "verdict": "GO | CONDITIONAL_GO | NO_GO",
  "label": "GO | CONDITIONAL_GO | NO_GO | UNRESOLVED_AT_CAP | BLOCKED_NEEDS_INPUT",
  "for_whom": "<founder-shape / wedge this verdict is conditioned on>",
  "dimensions": [
    {"name": "market size & urgency", "strength": "...", "risk": "...", "score": 1},
    {"name": "problem severity & frequency", "strength": "...", "risk": "...", "score": 1},
    {"name": "insight / founder wedge", "strength": "...", "risk": "...", "score": 1},
    {"name": "competitive landscape", "strength": "...", "risk": "...", "score": 1},
    {"name": "defensibility / moat", "strength": "...", "risk": "...", "score": 1},
    {"name": "GTM & distribution", "strength": "...", "risk": "...", "score": 1},
    {"name": "business-model viability", "strength": "...", "risk": "...", "score": 1},
    {"name": "technical feasibility & execution risk", "strength": "...", "risk": "...", "score": 1}
  ],
  "reality": {
    "tam": {"value": "<number>", "source": "<url/citation>"},
    "competitors": [{"name": "...", "differentiation": "..."}],
    "comparables": [{"name": "...", "signal": "<recent raise/exit>"}]
  },
  "codex_bear_case": "<the independent devil's-advocate strongest case to pass>",
  "codex_steelman": "<what codex says would have to be true to invest anyway>",
  "model_vs_codex": "<alignment, or the explicit disagreement if not reconciled>",
  "fatal_flaws": [{"flaw": "...", "why_fatal": "<evidence surviving reality-calibration + steelman>"}],
  "must_be_true": "<the single testable assumption the verdict hinges on>",
  "cheapest_test": "<how to resolve must_be_true fast and cheaply>",
  "no_go_flip_path": "<for NO_GO only: the wedge/founder/why-now that would make it a GO>",
  "hardened_proposal": "<rewritten proposal that RESOLVES (not deletes) non-fatal risks>",
  "iteration_count": 1,
  "rationale": "<why this verdict>"
}
```

Rules:
- `fatal_flaws` is `[]` for GO/CONDITIONAL_GO.
- `no_go_flip_path` is required and non-empty whenever `verdict` is `NO_GO` (anti-nihilism, SKILL §0).
- `reality.tam.source` must be a real citation — an empty/placeholder source invalidates a GO/CONDITIONAL_GO (SKILL §3).
- `must_be_true` + `cheapest_test` are required for CONDITIONAL_GO.
