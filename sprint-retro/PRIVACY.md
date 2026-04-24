# Privacy Rules

Hard privacy rules for sprint retro data gathering. Every rule here is non-negotiable — violating any one of them makes the retro output unsafe to share.

## The cardinal rule

**When in doubt, exclude.** A retro missing data is inconvenient. A retro leaking private data is harmful. Always err toward exclusion.

## Source-level privacy gates

### Gate 1: Channel/space type check

Before including ANY Slack content, verify the source:

| Source type | Action |
|------------|--------|
| Public channel | Include (subject to content check) |
| Private channel | Exclude entirely — do not reference |
| DM (direct message) | Exclude entirely — do not reference |
| Group DM | Exclude entirely — do not reference |
| Slack Connect (external) | Exclude — may contain NDA-protected content |

**How to detect:** Check the `channel_id` prefix in Slack search results. Public channels typically start with `C`, DMs with `D`, group DMs with `G`. If the channel type is ambiguous from metadata: exclude.

### Gate 2: Document sharing check

Before including ANY Google Doc or Confluence page:

1. Check sharing scope (number of viewers/editors)
2. If shared with fewer than 3 people: **exclude**
3. If shared with a single team or individual: **exclude**
4. If shared "anyone with the link" or with 3+ named people: **include** (subject to content check)

### Gate 3: Title keyword filter

Exclude any document or Jira ticket whose title contains (case-insensitive):

- "1:1", "1-on-1", "one-on-one"
- "performance", "review", "feedback"
- "comp", "compensation", "salary", "equity"
- "promotion", "promo"
- "PIP", "performance improvement"
- "termination", "exit", "offboarding" (individual)
- "confidential", "private", "sensitive"
- "medical", "leave", "accommodation"

### Gate 4: Content sensitivity scan

For every piece of content that passes Gates 1-3, scan the actual text for:

| Pattern | Action |
|---------|--------|
| Personal performance assessments ("X is underperforming", "Y needs improvement") | Exclude the entire item |
| Salary, compensation, or equity details | Exclude the entire item |
| Medical or personal leave information | Exclude the entire item |
| Interpersonal conflict ("X and Y disagree about", "tension between") | Exclude the entire item |
| Individual blame assignment ("this broke because X didn't...") | Rewrite as system issue ("deployment pipeline had a failure") or exclude |
| Private credentials, tokens, passwords | Exclude the entire item |
| Customer PII (names, emails, account IDs) | Exclude the entire item |
| Legal or compliance discussions | Exclude the entire item |

### Gate 5: Attribution safety

When including content in the retro:

- Attribute work positively: "Alice shipped the auth migration" (factual, public PR)
- Never attribute blame individually: NOT "Bob's script caused the outage"
- Reframe problems as team/system issues: "The deployment pipeline had reliability issues" instead of "Bob's migration broke production"
- If an incident involved individual error: describe the system gap, not the person

## The DM trail rule

If a public message references a private conversation:
- "As I mentioned in our DM..." → include only the public message
- "Per our private discussion..." → include only the public message
- Never follow the trail to find the private content
- Never infer private content from the public reference

## The "audience of one" rule

If any artifact (doc, message, ticket) was shared with or visible to only one person besides the author: exclude it. This applies to:
- Google Docs shared with 1 viewer
- Slack messages in a DM
- Jira tickets with restricted visibility
- Confluence pages with individual access

## Verification checklist

Before including any data point in the retro, it must pass ALL gates:

- [ ] Source is a public/team-visible channel or space (Gate 1)
- [ ] Document has 3+ viewers/editors (Gate 2)
- [ ] Title contains no sensitive keywords (Gate 3)
- [ ] Content contains no sensitive patterns (Gate 4)
- [ ] Attribution is positive or system-level, never blame (Gate 5)

If ANY gate fails: exclude the item. Do not attempt to "sanitize" sensitive content — exclude the entire item.

## What to do when too much is excluded

If privacy filtering removes substantial content:
1. Note the coverage gap in the retro output: "Limited Slack data available from public channels"
2. Suggest the team lead gather additional input directly from team members
3. Never lower privacy thresholds to fill gaps
4. Never mention WHAT was excluded or WHY (this reveals the existence of private content)

## Emergency stop

If during data gathering you encounter:
- A data source returning bulk private content (DMs, restricted docs)
- Content that appears to be attorney-client privileged
- Content related to ongoing investigations (HR, legal, security)

**Stop immediately.** Do not include any content from that source. Note "source excluded for privacy" without further detail.
