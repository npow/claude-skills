# Golden Rules

Hard rules for sprint retro generation. Each prevents a specific failure mode observed in the RED baseline.

## 1. Active filtering, never passive trust

**Rule:** Never rely on search tools to filter private content. Every search result must pass the 5-gate privacy checklist in [PRIVACY.md](PRIVACY.md) before inclusion. "The tool returned it so it must be okay" is not filtering.

**Observed baseline failure:** "I'd rely on the tool's built-in access controls" — agent delegated privacy responsibility to the search tool.

**Detection:** If the retro includes any content without a documented privacy gate pass, it is a violation.

## 2. Sanitized leaks are still leaks

**Rule:** Never include "sanitized versions" or "themes" derived from private content. If a piece of content fails any privacy gate, discard it entirely — do not paraphrase, summarize, or extract themes from it.

**Observed baseline failure:** "I'd likely include a sanitized version of the theme (e.g., 'frustration with deploy process was mentioned multiple times') without attributing it to specific people" — agent revealed private discussion topics through "sanitization."

**Detection:** If any retro item cannot be traced back to a specific public source, it may be a sanitized leak. Every item must have a source citation.

## 3. Resolve aliases before searching

**Rule:** When input is a Slack alias or team handle, resolve it to individual names FIRST. List resolved members in the output header. Never skip resolution and jump to keyword search.

**Observed baseline failure:** Agent skipped alias resolution under time pressure and searched by keyword instead, missing individual contributions.

**Detection:** If input contains `@` and the output header does not list individual names, alias resolution was skipped.

## 4. Never blame individuals for failures

**Rule:** Always frame problems as system or process issues. "The deployment pipeline had reliability issues" — never "Bob's script broke production." Even when public data clearly shows individual error, describe the system gap that allowed it.

**Observed baseline failure:** Baseline correctly identified this rule for DMs but did not apply it consistently to public data.

**Detection:** Grep the retro output for patterns like "[Name]'s [noun] caused/broke/failed". Any match is a violation.

## 5. Minimum 3 sources before delivery

**Rule:** Never deliver a retro based on fewer than 3 data sources with actual results. If fewer than 3 sources return data, the termination label must be `retro_partial`, not `retro_complete`.

**Observed baseline failure:** Agent was willing to deliver at "30-35% confidence" based on GitHub data alone, with just a disclosure.

**Detection:** Check `sprint-retro-evidence.json` — if fewer than 3 sources have `status: "queried"` with `items > 0`, the label must not be `retro_complete`.

## 6. Evidence file before completion claim

**Rule:** Never claim the retro is complete without `sprint-retro-evidence.json` on disk with `privacy_gates_applied: true`. The retro markdown file alone is not sufficient evidence of completion.

**Observed baseline failure:** No baseline agent produced an evidence file or any structured tracking of what was queried.

**Detection:** `ls sprint-retro-evidence.json` — if missing, the retro is not complete regardless of what was said.

## 7. No generic filler

**Rule:** Never write retro items not backed by specific data. "Communication could be improved" without a concrete data point is filler. If a section has no data-backed items, write "[No data available from public sources for this section]" instead.

**Observed baseline failure:** Agent correctly identified this risk but had no enforcement mechanism — only a stated intention.

**Detection:** Every bullet point in "What went well" and "What to improve" must cite a source (PR link, Slack thread topic, Jira ticket ID, build metric). Uncited items are filler.

## 8. Time pressure does not relax privacy

**Rule:** All privacy gates apply regardless of urgency. Under time pressure, produce a shorter retro covering fewer topics — never a faster retro with weaker privacy filtering.

**Observed baseline failure:** "Under time pressure, the honest answer is I'd likely include a sanitized version" — privacy degraded under urgency.

**Detection:** If the user mentions urgency and the retro includes content without source citations, time pressure likely caused a privacy shortcut.

## Anti-rationalization counter-table

| Excuse | Reality |
|---|---|
| "The search tool returned it, so it must be accessible to the team." | Search tools index broadly. YOU must filter. Run every result through the 5-gate checklist in PRIVACY.md. |
| "I'll just include a sanitized version of the theme without names." | Sanitized private content reveals what was discussed privately. Discard the entire item. Include only items traceable to public sources. |
| "We're short on time, I'll do a quick pass on privacy." | Time pressure is the #1 cause of privacy leaks. All 5 gates apply regardless of urgency. Produce a shorter retro, not a faster-filtered one. |
| "The user specifically asked about this topic, so I should include whatever I find." | User requests do not override privacy gates. If the relevant data is in private sources, note "deployment issues were discussed but details were in private channels." |
| "I only have GitHub data but the user needs the retro now." | A GitHub-only retro is labeled `retro_partial`. Deliver it with explicit coverage gaps. Never present partial data as a complete retro. |
| "I can infer what probably happened from the public message." | Inference from public references to private conversations is still a privacy leak. Include only what is explicitly stated in public sources. |
| "This Jira ticket has performance-related info but it's about system performance, not people." | If the title contains "performance" and context is ambiguous, exclude it. False exclusion is safe; false inclusion is not. |
| "The doc is shared with the whole team, so it's fine." | Check the actual sharing list. "Shared with the team" might mean 2 people. The threshold is 3+ named viewers. |
| "I'll note the data gap but still write some general observations." | General observations without data citations are filler. Write "[No data available]" instead. Filler disguised as insight is worse than an empty section. |
