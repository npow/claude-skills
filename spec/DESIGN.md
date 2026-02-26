# Spec Design

How to extract a design from conversation, apply API-first thinking, handle ambiguity, and make key decisions explicit.

## Contents
- Extracting the idea from conversation
- What to do when input is vague
- API-first design principle
- How to make key decisions explicit
- Handling ambiguity: the assumption pattern
- What makes a spec wrong vs incomplete

---

## Extracting the Idea from Conversation

The user may arrive with anything: a vague feature request, a full design dump, a question, or a rambling discussion. The job is to extract the system being specified.

Look for these signals:

| Signal | What it tells you |
|---|---|
| "we need X to do Y" | X is the system, Y is the primary goal |
| "the problem is..." | This is the problem statement — capture it verbatim, then refine |
| "I'm thinking of..." | Draft design — start here for the API/Interface section |
| "users keep asking for..." | User need — drives the Goals section |
| "we don't want to..." | Non-Goal candidate |
| "what about..." | Open Question candidate |

Start by stating your understanding of the system in one sentence: "This spec covers [system] which [does X] for [user/context]." Confirm this with the user before proceeding if there is ambiguity.

---

## What to Do When Input Is Vague

If the conversation lacks a clear problem, ask at most 3 clarifying questions. Choose questions that unlock the most design decisions:

**High-value questions:**
1. What is the current behavior, and what should it be instead? (unlocks Problem Statement)
2. Who are the users of this system, and what do they need to do? (unlocks Goals + API)
3. What are the hard constraints? (latency, scale, backwards compatibility, deployment env)

**Low-value questions (avoid):**
- "What technology do you want to use?" (pick something sensible and put it in Decisions)
- "How many features do you want?" (answer from context)
- "Can you tell me more?" (too open-ended)

If you cannot clarify, proceed with explicit assumptions. State each assumption at the top of the relevant section as: "Assumption: [X]. If this is wrong, see Open Questions #N."

---

## API-First Design Principle

Design the public interface before designing the internals. The reason: internals can always be changed; the public API is what users depend on and what cannot easily change.

**The ordering rule:**
1. Who calls this? (user, system, scheduler)
2. What do they pass in?
3. What do they get back?
4. What can go wrong from their perspective?

Only after answering these should you think about internal implementation.

**Anti-pattern to avoid:** Describing internal mechanics as if they were the API.

Bad: "The cache worker thread checks the LRU eviction queue every 100ms and serializes entries to disk using atomic renames."

This is implementation. The user does not call the cache worker thread. The API is:

Good:
```python
@cache(ttl=3600)
@step
def my_step(self):
    ...
```

The user calls `@cache`. That is the API. Start there.

---

## How to Make Key Decisions Explicit

Every non-obvious choice in a spec is a potential disagreement. The Key Design Decisions table exists to surface these choices and their rationale so reviewers can challenge them.

**Identify decisions by looking for:**
- Places where you chose one technology/approach over alternatives
- Places where the design could have gone two ways
- Places where a constraint ruled out an obvious option

**For each decision, answer:**
- What was the choice? (one sentence)
- What were the realistic alternatives?
- What was chosen?
- Why? (the rationale must be falsifiable — if someone disagrees, they can say "the rationale is wrong because...")

**Example of a decision worth surfacing:**

| Decision | Options Considered | Chosen | Rationale |
|---|---|---|---|
| Serialization format | JSON, pickle, msgpack | pickle | Metaflow already uses pickle; no new dependency |

**Example of a decision not worth surfacing:**
> We use Python because the project is in Python.

Decisions that are forced by context do not need the table. Only surface genuine choices.

---

## Handling Ambiguity: The Assumption Pattern

When a design detail is unknown, do not write TBD. Instead:

1. Write the best plausible design in the API or Data Model section
2. Add an entry to Open Questions: "Q: Is assumption X correct? Assumed [Y] for now."

This keeps the spec readable and usable while flagging what needs confirmation.

**Bad:**
```
### Data Model
TBD — need to discuss with team
```

**Good:**
```
### Data Model
Assuming per-user local filesystem storage for v1.
See Open Questions #1 for the question of remote backends.

@dataclass
class CacheEntry:
    key: str
    artifact: bytes
    created_at: float
    ttl: int | None
```
And in Open Questions:
> 1. Should cache storage support remote backends (S3, GCS) in v1? Assumed no. — Owner: TBD

---

## What Makes a Spec Wrong vs Incomplete

Knowing the difference helps prioritize what to fix.

**Incomplete** (fixable by adding content):
- Missing Non-Goals section
- Success Metrics section has no numbers
- Open Questions section is empty (fine if no questions exist; not fine if questions were skipped)
- Appendix is absent (optional — not a problem)

**Wrong** (requires rethinking):
- Problem Statement does not match what the Design solves
- Goals are not achievable with the described API
- API surface solves a different problem than the Problem Statement
- Failure Modes table is missing an obvious failure (e.g., network partition for a distributed system)
- Success Metrics measure the wrong thing (measuring write latency when reads are the bottleneck)

When reviewing a spec, check for wrongness before completeness. A complete wrong spec wastes more effort than an incomplete right spec.

---

## Scope Narrowing

A common failure mode is a spec that tries to cover too much. Signals that scope is too broad:

- More than 8 items in Goals
- Non-Goals section is longer than Goals
- Workflow Sequence has more than 12 steps
- API surface has more than 5-7 entry points

When scope is too broad:
1. Ask the user: "This covers [X, Y, Z]. Should we spec all three, or focus on [X] first?"
2. Move out-of-scope items to Non-Goals or a "Future Work" subsection in Appendix
3. If the user insists on full scope, split the spec into multiple documents (e.g., `spec-cache-v1.md` and `spec-cache-v2.md`)

A focused spec that ships is more valuable than a comprehensive spec that never gets reviewed.
