# Fact-Checking Claims

How to extract, classify, and verify every factual claim in a proposal.

## Contents
- Claim extraction
- Claim categories
- Verification methods
- Building the fact-check table
- Common embellishment patterns
- Failure diagnosis

## Claim extraction

Read the proposal end-to-end and extract every statement that can be verified or falsified. A claim is any statement that asserts something about the external world — not the author's plans or opinions.

### What counts as a claim

| Type | Example | Verifiable? |
|------|---------|-------------|
| Statistic | "87% downstream compromise" | Yes — find the primary source |
| Funding amount | "Mem0, $24M funded" | Yes — find the funding announcement |
| CVE / vulnerability | "CVE-2025-XXXXX" | Yes — check CVE databases |
| GitHub metric | "23,000+ GitHub stars" | Yes — check the repo |
| Publication | "published at NeurIPS 2024" | Yes — check proceedings |
| Organization statement | "OWASP classifies this as ASI08" | Yes — check the OWASP document |
| Market claim | "no production tool exists" | Yes — search for counterexamples |
| Attribution | "Galileo's research found..." | Yes — find the cited research |
| Author's plan | "We will build X in 12 weeks" | No — this is a plan, not a fact (analyze in STRUCTURAL.md) |
| Opinion | "This is the most important problem" | No — subjective |

### Extraction format

For each claim, record:
- **Claim text**: the exact quote from the proposal
- **Category**: one of the types above
- **Specificity**: HIGH (names a specific source, number, or date) or LOW (vague attribution like "research shows")
- **Location**: section of the proposal where it appears

## Claim categories

Group extracted claims into these categories for parallel research:

1. **Named vulnerabilities and attacks** — CVEs, named attack tools, published exploits
2. **Research citations** — papers, statistics attributed to specific organizations
3. **Competitor and market claims** — funding amounts, star counts, feature descriptions
4. **Standards and framework claims** — OWASP, MITRE, NIST classifications
5. **"No one has built X" claims** — negative existence claims (these require the most research to verify)

## Verification methods

### For named vulnerabilities and attacks
1. Search the web for the exact CVE number or vulnerability name
2. Check CVE databases (NVD, MITRE CVE)
3. Look for the original disclosure (researcher's blog, security advisory)
4. Check if the vendor acknowledged the vulnerability
5. Verify severity ratings and impact claims against the advisory

### For research citations
1. Search for the exact paper title or quoted statistic
2. Check arXiv, Google Scholar, or the named conference proceedings
3. Read the abstract and results section — does the paper actually say what the proposal claims?
4. Check if the cited number is from a peer-reviewed paper, a blog post, or a marketing report
5. Verify the authors and institutions match the proposal's description

### For competitor and market claims
1. Search for the company + "funding" or "series A/B/C"
2. Check Crunchbase, TechCrunch, or SEC filings for funding amounts
3. Check the actual GitHub repo for star counts (stars change daily — allow +/- 10%)
4. Check the product's current feature page — does it actually lack/have the features described?
5. Verify acquisition claims (acquirer, acquiree, price, date)

### For standards and framework claims
1. Go to the actual OWASP / MITRE / NIST document
2. Verify the exact classification number (e.g., "ASI08" vs "ASI06")
3. Verify the exact wording — "high persistence" vs "very high persistence" matters
4. Check if the standard is current or deprecated

### For "no one has built X" claims
These are the hardest to verify and the easiest to get wrong. A claim that "no production tool exists" requires exhaustive search:

1. Search for the exact problem the proposal claims to solve
2. Search for adjacent solutions that might cover the same ground
3. Check if any platform vendor has shipped a feature that addresses this
4. Check if any startup has launched or announced a product in this space
5. Search security vendor product pages (Palo Alto, CrowdStrike, SentinelOne, etc.)
6. Check recent security conference talks and papers for new tools
7. Only classify as VERIFIED if 5+ distinct searches fail to find a counterexample

## Building the fact-check table

Present results in this format:

```
| Claim | Verdict | Evidence | Notes |
|-------|---------|----------|-------|
| "Exact quote from proposal" | VERIFIED / PARTIALLY TRUE / UNVERIFIABLE / FALSE | Source URL or citation | What's accurate, what's wrong, what's missing |
```

### Verdict definitions

- **VERIFIED**: Primary source found that confirms the claim as stated. The claim is accurate in substance and detail.
- **PARTIALLY TRUE**: The claim is directionally correct but inaccurate in specifics (wrong number, wrong attribution, wrong date, exaggerated scope).
- **UNVERIFIABLE**: No primary source found. The claim may be true but cannot be confirmed. Commonly seen with attributed statistics where the original source is a blog post or webinar that's not indexed.
- **FALSE**: Primary source found that contradicts the claim, or the claim contains fabricated specifics (fake CVE numbers, wrong OWASP classification, nonexistent papers).

### Severity assessment

After building the table, assess overall credibility:

| Pattern | Assessment |
|---------|------------|
| All claims VERIFIED | High credibility — author did their research |
| Mostly VERIFIED, 1-2 PARTIALLY TRUE | Normal — minor inaccuracies, easily fixed |
| Multiple UNVERIFIABLE claims | Concerning — author may be citing secondary sources without checking primaries |
| Any FALSE claims | Serious — author either fabricated or was careless with specifics. Flag prominently |
| Fake CVE numbers or fabricated statistics | Critical — undermines the entire proposal's credibility |

## Common embellishment patterns

Watch for these:

| Pattern | Example | What to check |
|---------|---------|---------------|
| **Precise numbers from vague sources** | "87% downstream compromise" attributed to a company blog | Find the actual blog post. Often the number is from a simulation or a marketing report, not peer-reviewed research |
| **CVE placeholders** | "CVE-2025-XXXXX" | If the CVE number has placeholders, no CVE was assigned. Check if the vulnerability was actually filed |
| **Star count inflation** | "38 GitHub stars" when the repo has 29 | Check the actual repo. Minor discrepancies are normal (stars change), but significant inflation is a red flag |
| **Misattributed classifications** | "OWASP classifies this as ASI08" when the actual classification is different | Go to the source document and check the exact numbering |
| **"Research shows" without citation** | "Studies have demonstrated that..." | If no specific study is cited, classify as UNVERIFIABLE |
| **Conflating proposal with publication** | "MemoryGraft proposed CPA" (implying CPA is a built system) | Check if the paper actually built the thing or just proposed it as future work |

## Failure diagnosis

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Web search returns no results for a specific claim | The claim may use different terminology than the primary source | Search for the underlying event/paper/company using alternate keywords (e.g., search for the researcher name, the company name, the conference name separately) |
| Multiple conflicting sources for a funding amount | The company may have had multiple rounds, or some sources include total funding vs. single round | Check Crunchbase or the original press release for the specific round |
| Can't find a paper on arXiv | The paper may be on a different preprint server, or may only exist in conference proceedings | Try Google Scholar, Semantic Scholar, or the conference website directly |
| GitHub repo returns 404 | The repo may have been renamed, made private, or deleted | Search GitHub for the project name and author separately |
| OWASP/MITRE classification doesn't match | The standard may have been updated, or the proposal cites an older version | Check both current and archived versions of the standard |
| If none of the above | Log what you searched for, what you found, and what you expected. Present the discrepancy to the user and classify as UNVERIFIABLE with explanation |
