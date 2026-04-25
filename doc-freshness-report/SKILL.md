---
name: doc-freshness-report
description: "Use when checking documentation freshness, finding stale docs, auditing documentation health, or generating a documentation report. Trigger phrases: doc freshness, stale docs, documentation report, docs audit."
---

# Documentation Freshness Report

Produce a monthly documentation freshness check across configured manual bundles and repository doc paths using rag-manuals-prod and Sourcegraph tools. The report identifies stale docs that may be misleading readers.

## Configuration

Reads defaults from `~/.claude/skills/doc-freshness-report/config.json` if it exists.

```json
{
  "manual_bundles": ["myservice", "myplatform"],
  "repo_doc_paths": [
    {"repo": "github.netflix.net/myorg/repo1", "path": "docs/"},
    {"repo": "github.netflix.net/myorg/repo2", "path": "README.md"}
  ]
}
```

**Resolution order:** user prompt overrides > config.json > built-in defaults.

**At least one source must be set** — either `manual_bundles` or `repo_doc_paths`. If none is set and the user didn't specify, ask once and save to config.json.

## Arguments

- **manual_bundles**: list of Netflix Manuals bundle names to check
- **repo_doc_paths**: list of {repo, path} pairs pointing to documentation directories or files in repositories

## Workflow

1. **Search Manuals for configured bundles.** For each `manual_bundle`, call `rag-manuals-prod` with `query_str="getting started setup configuration"` and a metadata filter for `bundle_name == {bundle}`. Request `size=20` to get a broad sample of pages. Record each page's title and `manuals_doc_id` (URL).

2. **Check when Manual pages were last updated.** For each manual page found, use `commit_search` on the backing repo (if known) with `files` matching the doc path and `repos` matching the manual's source repo. Look at the most recent commit date. If the backing repo is unknown, use `rag-manuals-prod` with `FullDocumentRetrieval` postprocessor to retrieve the full page content and check for any "last updated" or version metadata in the text.

3. **Check repo-based docs.** For each `repo_doc_path`, use `list_files` with `repo` and `path` to enumerate doc files (`.md`, `.rst`, `.txt`, `.adoc`). Then for each doc file, use `commit_search` with `repos=[{repo}]` and `files=[{file_path}]` to find the most recent commit touching that file.

4. **Classify freshness.** For each document, compute days since last update:
   - **Fresh** (0-90 days): recently updated, likely accurate
   - **Aging** (91-180 days): may need review
   - **Stale** (181-365 days): probably outdated
   - **Ancient** (>365 days): high risk of being misleading

5. **Cross-reference docs with code changes.** For each `repo_doc_path`, use `commit_search` on the same repo with `files` excluding the doc path to find recent code changes. If code was changed significantly (>20 commits) in the last 90 days but docs were not updated, flag as "code-doc drift."

6. **Generate report.** Output markdown:

```
## Documentation Freshness Report — {date}
Bundles checked: {N} | Repos checked: {N} | Total docs analyzed: {N}

### Summary
- Fresh (0-90d): {N} | Aging (91-180d): {N} | Stale (181-365d): {N} | Ancient (>365d): {N}
- Code-doc drift detected: {N} repos

### Stale & Ancient Documents (action needed)
| Source | Document | Last Updated | Age (days) | Freshness |
|---|---|---|---|---|
(All stale and ancient docs, sorted by age descending)

### Code-Doc Drift
(For each flagged repo: repo name, recent code commits, doc last updated, gap in days)

### Manual Bundle Health
| Bundle | Pages Found | Fresh | Aging | Stale | Ancient | Health Score |
|---|---|---|---|---|---|---|
(Per-bundle summary. Health score = % of pages that are Fresh or Aging)

### Repository Doc Health
| Repo | Doc Path | Files | Fresh | Aging | Stale | Ancient | Health Score |
|---|---|---|---|---|---|---|---|
(Per-repo summary)

### Freshest & Stalest
- Most recently updated: {doc name} ({N} days ago)
- Most stale: {doc name} ({N} days ago)
```

7. **Post to `#team-digests` channel if configured, never to a primary team channel.**

8. **Terminate.** Report is complete when all bundles and repo paths are checked and freshness classified.

## Design Principles

1. **Team-level only.** Aggregate to team level — it is the right granularity for a periodic digest. Don't attribute doc staleness to individuals.
2. **Deterministic math first, LLM narrates only.** Freshness classification is computed from commit dates — days since last update determines the category. The LLM writes summaries but never guesses when a doc was last updated.
3. **Pair metrics with counter-metrics.** Never report doc freshness without code-doc drift. Fresh docs on unchanged code are fine; stale docs on rapidly changing code are dangerous. The combination matters.

## Golden Rules

1. **Dates come from commits, not guesses.** Every freshness classification is based on the actual last commit date from Sourcegraph commit_search. Never estimate.
2. **Stale docs on active code are the highest priority.** A stale doc for abandoned code is low risk. A stale doc for code with 50 recent commits is dangerous. Surface code-doc drift prominently.
3. **Health score is arithmetic.** `(fresh + aging) / total * 100`. No LLM judgment in the score.
4. **Check ALL configured bundles and paths, not a sample.**
5. **"No docs found" is a finding.** If a repo path has no documentation files, report it — missing docs are worse than stale docs.
6. **Include links to every document.** Manual URLs and repo file paths so the reader can go directly to the stale doc.

## Anti-Rationalization Counter-Table

| Excuse | Reality |
|---|---|
| "I couldn't find the last update date so I skipped the file." | Use commit_search. If no commits found, that itself is a data point — the doc may predate the current repo history. Report "unknown age." |
| "The bundle has too many pages to check individually." | Check all pages returned by the search. The report must cover the full set, not a sample. |
| "Docs look fine based on their content." | Freshness is about update recency, not content quality. A well-written doc from 2 years ago on a rapidly evolving system is still stale. |
| "I checked docs but skipped the code-doc drift analysis." | Code-doc drift is the most actionable signal. It tells you which stale docs are actually dangerous. Run it. |
| "Health score isn't meaningful with few docs." | Report the score with the sample size. Let the reader decide significance. |

## Termination Labels

| Label | Meaning |
|---|---|
| `report_complete` | All bundles and repo paths checked, freshness classified, drift analyzed |
| `report_partial` | Some sources checked but errors prevented full coverage — noted which |
| `no_sources_configured` | No bundles or repo paths specified — need config.json or user input |
| `api_error` | Manuals RAG or Sourcegraph API unreachable |

## Self-Review Checklist

- [ ] All configured manual bundles were searched
- [ ] All configured repo doc paths were checked
- [ ] Freshness classification based on actual commit dates (not estimates)
- [ ] Code-doc drift analysis run for every repo with doc paths
- [ ] Stale & Ancient docs section appears first after summary
- [ ] Health scores computed as arithmetic percentages
- [ ] Links included for every document listed
