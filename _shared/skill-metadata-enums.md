# Skill Metadata Enum Registry

Single source of truth for all SKILL.md frontmatter enum values.
Adding a new value requires a PR here + `sagaflow catalog lint --strict` CI check.

## Category

```
debug      — root cause analysis, hypothesis testing, reproduction
design     — architecture, spec generation, adversarial design review
qa         — defect detection, auditing, review of existing artifacts
research   — exploration, synthesis, novelty discovery
plan       — implementation planning, consensus, ADR generation
execution  — running workflows, orchestration, loop-based automation
report     — generating structured output documents, dashboards
tool       — utility commands, setup, configuration, meta-operations
meta       — skills about skills; system introspection
```

## Capability Tags

```
adversarial-critique       parallel-agents            defect-detection
severity-classification    hypothesis-testing         root-cause-analysis
multi-model                ensemble-judges            claim-extraction
evidence-scoring           loop-based                 consensus-building
trend-tracking             static-analysis            temporal-workflow
backoff-retry              adr-generation             novelty-discovery
```

## Input Types

```
artifact-file   git-diff   concept   task   question   topic   idea   code-path   url   repo
```

## Output Types

```
defect-registry   design-spec   report   plan   code   diagnosis   presentation   chart   data
```

## Scalar Enums

| Field | Values |
|-------|--------|
| `complexity` | `simple` (<5 min) \| `moderate` (5-30 min) \| `complex` (30 min+) |
| `model_tier` | `haiku` \| `sonnet` \| `opus` |
| `cost_profile` | `low` (<$0.50) \| `medium` ($0.50-$5) \| `high` ($5+) |
| `maturity` | `experimental` \| `beta` \| `stable` \| `deprecated` |
| `sagaflow` | `required` \| `recommended` \| `optional` \| `none` |
| `relation` | `variant` \| `prerequisite` \| `follow-up` \| `alternative` |
