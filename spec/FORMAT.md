# Spec Format

Complete template, section-by-section writing guidance, good vs bad examples, and a complete abbreviated example spec.

## Contents
- Complete spec template
- Section-by-section writing guidance
- Good vs bad: Problem Statement
- Good vs bad: Goals and Non-Goals
- Good vs bad: Success Metrics
- Failure Modes table format
- Key Design Decisions table format
- Complete abbreviated example spec

---

## Complete Spec Template

The spec file is named `spec-[slug].md` where slug is a lowercase hyphenated version of the title.

```markdown
# Spec: [Title]
**Status:** Draft
**Date:** [YYYY-MM-DD]
**Author:** Claude

## Problem Statement
[3-6 sentences of prose. No bullets. Describes what problem is being solved,
why it matters, and who is affected.]

## Goals
- [Concrete, measurable outcome 1]
- [Concrete, measurable outcome 2]
- [Concrete, measurable outcome 3]

## Non-Goals
- [Explicitly out of scope item 1]
- [Explicitly out of scope item 2]

## Background and Context
[Prior art, related systems, or context needed to understand the design.
1-3 paragraphs. Include links to related docs if known.]

## Design

### API / Interface
[The public surface area. Functions, endpoints, decorators, CLI commands.
Always use code blocks. Never describe code in prose only.]

### Data Model
[Key data structures, schemas, artifact shapes.
Always use code blocks. Never describe schemas in prose only.]

### Workflow / Sequence
[Step-by-step description of how the system works end-to-end.
Numbered steps. May include a simple ASCII diagram.]

### Key Design Decisions
| Decision | Options Considered | Chosen | Rationale |
|---|---|---|---|
| [Decision 1] | [Option A, Option B] | [Option A] | [Why] |
| [Decision 2] | [Option A, Option B] | [Option B] | [Why] |

## Failure Modes
| Failure | Probability | Impact | Mitigation |
|---|---|---|---|
| [What can go wrong] | Low/Medium/High | Low/Medium/High | [How it is handled] |

## Success Metrics
- [Measurable criterion 1 — e.g., "p99 latency < 500ms under 1000 req/s"]
- [Measurable criterion 2 — e.g., "Error rate < 0.1% over 7-day rolling window"]
- [Measurable criterion 3 — e.g., "Adopted by 3 teams within 60 days of launch"]

## Open Questions
1. [Unresolved question] — Owner: [name or TBD], Deadline: [date or TBD]
2. [Unresolved question] — Owner: [name or TBD], Deadline: [date or TBD]

## Appendix
[Optional. Detailed examples, alternative designs considered, references.]
```

---

## Section-by-Section Writing Guidance

### Problem Statement

Write 3-6 sentences of continuous prose. No bullet points. This section must force clarity: if you cannot write the problem statement in prose, the problem is not yet understood.

Answer these questions in order:
1. What is broken or missing today?
2. Who is affected and how?
3. What is the cost of not solving it?

**Bad (vague):**
> We need better caching. Performance is slow.

**Good (specific, causal, scoped):**
> The artifact store currently recomputes derived artifacts on every workflow run, even when upstream inputs have not changed. This causes median run time to increase by 40-80 seconds for pipelines with more than 10 steps, which blocks developer iteration speed. Teams running CI pipelines on every commit pay this cost 50-200 times per day. No caching layer currently exists between the executor and the artifact store.

### Goals

Goals must be measurable. Every goal must have a way to determine pass/fail.

**Bad (unmeasurable):**
> - Improve performance
> - Make the API easier to use
> - Reduce errors

**Good (measurable):**
> - Reduce median run time for pipelines with > 10 steps from 90s to < 30s
> - API surface reduced to 3 decorators: @step, @card, @artifact
> - Cache hit rate > 80% for unchanged inputs on repeated runs

### Non-Goals

Non-Goals are the boundaries. They prevent scope creep and protect the team from unstated expectations. Name them explicitly.

**Bad (too vague):**
> - Out of scope things

**Good (specific and defensible):**
> - Multi-user cache sharing — this spec covers per-user local caching only
> - Cloud artifact backends — only local filesystem in this version
> - Cache invalidation UI — invalidation is programmatic only (no dashboard)

### API / Interface

Start with the public interface, not the internals. If this is a library, show the decorator or function signatures a user would write. If it is an API, show the endpoint shapes. If it is a CLI, show the commands.

Always use code blocks. Do not describe the API in prose without a code block alongside it.

**Bad:**
> The cache decorator accepts a key function and a backend argument.

**Good:**
```python
@cache(key=lambda inputs: hash(inputs), backend="local")
@step
def my_step(self):
    ...
```

### Data Model

Show the actual structure. Use the language of the system being specified (Python dataclass, TypeScript interface, JSON schema, SQL schema, etc.).

**Bad:**
> The artifact has a key, a value, and metadata.

**Good:**
```python
@dataclass
class CachedArtifact:
    key: str                    # SHA-256 of (run_id, step_name, input_hash)
    value: bytes                # Serialized artifact payload
    created_at: datetime
    ttl_seconds: int | None     # None means no expiration
    hit_count: int
```

### Workflow / Sequence

Number the steps. Each step is one action. Include an ASCII diagram if the flow has branches or multiple actors.

Example:
```
1. Executor receives step inputs from orchestrator
2. Cache key computed as SHA-256(run_id + step_name + hash(inputs))
3. Cache lookup: if HIT → deserialize and return artifact, skip execution
4. If MISS → execute step, serialize output, write to cache
5. Cache entry written with TTL from @cache decorator argument
6. Artifact returned to orchestrator
```

### Key Design Decisions

Every non-obvious choice in the design belongs in this table. If a reader might ask "why not X?", put it here.

| Decision | Options Considered | Chosen | Rationale |
|---|---|---|---|
| Cache storage | Redis, local filesystem, S3 | Local filesystem | No infra dependencies for v1; S3 in v2 |
| Key computation | Content hash, timestamp | Content hash of inputs | Timestamps would miss identical-input reruns |
| Serialization | pickle, JSON, msgpack | pickle | Metaflow already uses pickle for artifacts |

### Failure Modes

Every failure mode needs all four columns. Probability and Impact are Low/Medium/High.

| Failure | Probability | Impact | Mitigation |
|---|---|---|---|
| Cache corruption (partial write) | Low | High | Atomic write via temp file + rename; corrupt entries discarded |
| Stale cache after input change | Medium | High | Key includes hash of inputs; stale entries are never returned |
| Disk full | Low | Medium | Cache write failures are non-fatal; step executes normally |
| Cache key collision | Very Low | High | SHA-256 collision probability negligible; document assumption |

### Success Metrics

Success Metrics are the definition of done. Without them, "it works" is undefined.

**Bad (unmeasurable):**
> - Users are happy
> - Performance is better
> - Fewer errors

**Good (measurable):**
> - p50 run time for cached pipelines < 5s (vs current 45s baseline)
> - p99 run time for cached pipelines < 30s
> - Cache hit rate >= 80% on second run of unchanged pipeline
> - Zero data corruption incidents in 30-day rollout window
> - Adopted by 3+ teams within 60 days of GA

---

## Complete Abbreviated Example Spec

This is what good output looks like. Use this as the reference when writing.

---

```markdown
# Spec: Metaflow Step Cache
**Status:** Draft
**Date:** 2026-02-25
**Author:** Claude

## Problem Statement
Metaflow pipelines recompute every step on every run, regardless of whether upstream
inputs have changed. For pipelines with 10+ steps and long-running computations, this
causes median wall-clock time of 90+ seconds on reruns where only downstream parameters
changed. Data scientists working iteratively run pipelines 20-50 times per day, making
unnecessary recomputation the dominant bottleneck. No native caching primitive exists
in Metaflow today; teams hack around this with ad-hoc artifact checks in step logic.

## Goals
- Reduce median rerun time for unchanged pipelines from 90s to < 10s
- Require zero changes to step business logic — caching is opt-in via decorator only
- Cache hit rate > 80% on second run of identical inputs

## Non-Goals
- Shared cross-user caches — this is per-user local cache only
- Remote or cloud-backed cache stores (v2 scope)
- Automatic cache warming or prefetching

## Background and Context
Metaflow's artifact store already serializes step outputs via pickle. This proposal
adds a content-addressed cache layer in front of step execution. Similar patterns exist
in tools like DVC (data version control) and Bazel (build cache). Metaflow's existing
@retry and @catch decorators are the structural model for this decorator.

## Design

### API / Interface

Users opt into caching by adding @cache above @step:

    @cache(ttl=86400)   # cache for 24 hours; omit for no expiration
    @step
    def transform(self):
        self.result = expensive_transform(self.inputs)

The decorator also accepts a custom key function for advanced use:

    @cache(key=lambda self: hash(self.raw_data), ttl=3600)
    @step
    def featurize(self):
        self.features = build_features(self.raw_data)

### Data Model

Cache entries are stored as files on local disk under ~/.metaflow/cache/:

    @dataclass
    class CacheEntry:
        key: str           # SHA-256(flow_name + step_name + hash(inputs))
        artifact: bytes    # pickle-serialized step output namespace
        created_at: float  # unix timestamp
        ttl: int | None    # seconds; None = no expiration

### Workflow / Sequence

1. Flow runner encounters a @cache-decorated step
2. Cache key = SHA-256(flow_name + step_name + hash(self.__dict__ before step))
3. Lookup ~/.metaflow/cache/<key>.entry
4. HIT: deserialize artifact, inject into self.__dict__, skip step body
5. MISS: execute step body normally
6. Write result to cache as atomic temp-file + rename
7. Continue to next step

### Key Design Decisions
| Decision | Options Considered | Chosen | Rationale |
|---|---|---|---|
| Storage backend | Redis, filesystem, S3 | Local filesystem | Zero infra setup; v2 adds S3 |
| Key inputs | Content hash, step name only | Content hash of inputs | Step name alone misses input changes |
| On cache failure | Raise error, skip silently | Skip silently | Cache must never block execution |

## Failure Modes
| Failure | Probability | Impact | Mitigation |
|---|---|---|---|
| Partial write / corruption | Low | High | Atomic write via tempfile + rename |
| Stale cache on input change | Medium | High | Key includes input hash; stale keys unreachable |
| Disk full | Low | Medium | Write failure non-fatal; step runs normally |
| pickle deserialization error | Low | Medium | Treat as cache miss; log warning; delete entry |

## Success Metrics
- p50 rerun latency for fully-cached pipeline < 5s (baseline: 90s)
- p99 rerun latency for fully-cached pipeline < 20s
- Cache hit rate >= 80% on reruns with identical inputs
- Zero step-skipping errors in 30-day production rollout

## Open Questions
1. Should cache keys include the Metaflow version to bust on upgrades? — Owner: TBD, Deadline: TBD
2. What is the right default TTL if none is specified? — Owner: TBD, Deadline: TBD

## Appendix
Alternative considered: storing cache in the Metaflow artifact store itself (S3/local).
Rejected for v1 because it requires backend credentials and adds latency vs local disk.
```
