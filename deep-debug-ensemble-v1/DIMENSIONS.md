# Hypothesis Dimensions

Debugging failures are concentrated in a small number of orthogonal root-cause classes. Enumerating them explicitly — and requiring coverage per cycle — prevents the most common failure mode of solo debugging: fixating on the code-path dimension and never considering the other seven.

## The 8 dimensions

| Dimension | Required category | What it investigates |
|---|---|---|
| `code-path` | correctness | Logic error, wrong branch, off-by-one, misread type, wrong API call at symptom site or upstream |
| `data-flow` | correctness | Bad value originates upstream; symptom site is innocent; trace backward until source |
| `recent-changes` | correctness | Git diff / commits / dependency updates / config changes since last-known-good |
| `environment` | environment | Config, env vars, secrets propagation, credentials, container/OS/runtime version mismatch |
| `framework-contract` | correctness | Framework guarantee was assumed but not verified (gevent cooperative scheduling, session scopes, ORM lazy-loading) |
| `concurrency-timing` | concurrency | Race, ordering, cache staleness, test pollution, timing-dependent behavior |
| `measurement-artifact` | correctness | The "bug" is a measurement error (stale logs, wrong instrumentation, test reading stale state, harness bug) |
| `architectural-coupling` | architecture | Shared state / invariant violation / wrong abstraction — the symptom is downstream of a structural problem |

**Required categories** (per `required_categories_covered` in state.json):
- `correctness` — at least one of `code-path`, `data-flow`, `recent-changes`, `framework-contract`, `measurement-artifact` must have ≥1 explored angle
- `environment` — the `environment` dimension must have ≥1 explored angle
- `concurrency` — the `concurrency-timing` dimension must have ≥1 explored angle
- `architecture` — the `architectural-coupling` dimension must have ≥1 explored angle

Rationale for the category groupings: `correctness` is broad because most debugging is correctness debugging — satisfying it once across any of its dimensions is fine. The other three categories name the classic under-investigated failure modes and force at least one angle into each, even when the symptom "obviously" looks like a code-path bug. The most expensive debugging mistake is assuming "it's a code bug" when it's a concurrency, environment, or architecture bug.

Uncovered required categories get **CRITICAL** priority at the start of the next cycle — the coordinator generates new angles targeting them and they are popped before any other frontier item.

---

## Typical angles per dimension

Each dimension definition includes 3–5 concrete starter angles. Critics use these as templates and adapt them to the specific symptom.

### code-path

- "At the symptom site ({file}:{line}), does the logic handle the case where {observed input condition}? Construct an input that would trigger the buggy branch."
- "Which branches are taken in the reproduction? Instrument with `console.error` before the failing assertion — does the code reach the expected branch?"
- "Is there an exception being swallowed silently upstream that would explain why the symptom appears downstream as a None/undefined/0?"
- "What is the exact type of the value at the symptom site? Is the code assuming a type the language doesn't guarantee (e.g. `str` when `bytes`, `int` when `float`, `Optional[T]` unwrapped without check)?"
- "Is the function called with arguments that pass type-checker checks but violate an undocumented invariant (e.g. positive integer expected, zero accepted)?"

### data-flow

- "Where does the bad value originate? Start at the symptom site and trace backward through the call stack until you find the source. Don't stop at the first caller."
- "What's the type of the value at every layer as it moves from origin to symptom site? Does any layer coerce silently (e.g. `str(None) == 'None'`, not an error)?"
- "Is there a default value being substituted silently when the real value is missing? `dict.get(key, default)` / `hasattr(obj, 'attr') or fallback` patterns hide empty-string and None origins."
- "Is the symptom `cwd = process.cwd()` or equivalent — an empty-string path getting resolved to the process working directory? That's the classic 'bad value silently treated as default' pattern."
- "Is the upstream source a test fixture accessed before `beforeEach` / `setUp` ran, returning an initial empty state?"

### recent-changes

- "What changed in the 7 days before this symptom first appeared? Run `git log --since='7 days ago' -- {affected-path}` and examine every commit touching the affected code."
- "Did any dependency update in the last 7 days? Check `package-lock.json` / `poetry.lock` / `Gemfile.lock` diff vs. last-known-good."
- "Did any config or env var change? Compare current config to deployment config on the last-known-good commit (`git show {LKG_sha}:config/production.yml`)."
- "Is this a regression — did we have a test that USED to pass here and now doesn't? `git log -p -- {test-file}` to see when the test behavior changed."
- "Were any feature flags toggled recently? A flag flip can surface bugs that existed but weren't reachable before."

### environment

- "Does the CI environment have the same env vars as local? Print `env | sort` on both and diff. Look specifically for missing secrets (`IDENTITY`, `API_KEY`, `DATABASE_URL`)."
- "Is the Python/Node/Go/Ruby runtime version the same in the failing environment? `python --version` / `node --version` — even minor-version differences can change behavior."
- "Is the symptom specific to containerized vs. host execution? If containerized, are secrets injected at build time vs. run time — and does the build step actually have them?"
- "Is there a multi-layer pipeline (CI → build → signing → deploy) where a secret or env var needs to propagate through each layer? Instrument each boundary."
- "Does the failing environment have the same filesystem permissions, file case sensitivity, and path separators?"

### framework-contract

- "Does this code assume `{framework feature}` behaves differently than it does? Examples: gevent preempts between non-IO statements (it doesn't), SQLAlchemy scoped sessions are thread-safe without effort (they aren't), Django's `atomic()` nests cleanly (it has subtle savepoint semantics)."
- "Is there a `try`/`except` catching a framework-specific exception that's actually a different class in the installed version? (e.g. `DatabaseError` renamed between major versions)"
- "Does the code rely on a framework guarantee that the docs claim but the actual implementation doesn't fulfill? Verify by reading the framework source, not the docs."
- "Is there a race between framework-managed state (e.g. Django request cache, Flask-SQLAlchemy session) and user-managed state? Framework guarantees usually exclude cross-request state you introduced yourself."
- "Does the code call a framework method that was deprecated in the installed version with a silent fallback that behaves subtly differently?"

### concurrency-timing

- "Is the symptom produced by a specific test ordering? Run the failing test in isolation — does it still fail? If not, bisect to find the polluter (see TECHNIQUES.md §condition-based-waiting and §Finding the polluter)."
- "Is there a race between test setup and test body? `beforeEach` runs but returns a promise the test doesn't await, so the test reads pre-setup state."
- "Is a cached value stale? Is the cache key missing a dimension that changed (e.g. caching on user_id but the relevant axis was organization_id)?"
- "Is the symptom a time-of-check vs. time-of-use race (TOCTOU)? E.g. `if file_exists(X): open(X)` — file can be deleted between the two calls."
- "Is there a test using `sleep(50)` to 'wait for' an async operation, and the CI environment is slower? Replace with condition-based waiting."

### measurement-artifact

- "Is the test reading stale state? E.g. the log line you're asserting against was written before your fix ran."
- "Is your instrumentation masking the bug? E.g. `logger.debug(...)` with a side effect that triggers the bug ONLY when the log level is debug."
- "Is the 'bug' a harness bug? E.g. the test runner's assertion library has a bug, or the mock framework is returning stale doubles."
- "Is the observation itself perturbing the system? E.g. attaching a debugger changes timing and the bug disappears."
- "Are you reading the wrong log file / wrong process / wrong environment? Is the error you're chasing actually from the failing run, or from a prior run?"

### architectural-coupling

- "Have the last 2 fix attempts each revealed a new problem in a different location? That pattern signals architectural coupling, not a local bug."
- "Does the proposed fix require 'massive refactoring' to implement cleanly? That's an invariant-mismatch signal — the current abstraction can't express the fix."
- "Is there shared mutable state (a global, a module-level dict, a singleton) that multiple paths write to without coordination?"
- "Is there an invariant the code assumes ('this value is always set before this is called') that's broken by a specific call path?"
- "Would a senior engineer look at this code and say 'the wrong thing is the abstraction, not the implementation'? If yes, this is architectural-coupling — flag for Phase 7 escalation if 3 fix attempts confirm."

---

## Cross-dimensional angles

Cross-dimensional angles catch hypotheses that live in the interaction between two dimensions — often the highest-value hypotheses because they're the ones pure single-dimension thinking misses.

Generate 2–3 per cycle, alongside the dimension-specific angles.

- **data-flow × framework-contract:**
  "Does the bad value originate from a framework API that behaves differently under edge conditions than the docs claim? E.g. `dict.get()` vs `dict[...]` when keys don't exist, `asyncio.wait_for` vs `asyncio.wait` timeout semantics, ORM `.first()` returning `None` silently."

- **recent-changes × environment:**
  "Did a recent change introduce an environment-dependent behavior? E.g. a new dependency that requires an env var only set in production, a feature flag whose default changed between environments, a config lookup that falls through to a different default in CI."

- **concurrency-timing × measurement-artifact:**
  "Is the test flaky because of a race, or because the assertion is measuring the wrong state? E.g. asserting against a cache that's being populated asynchronously, checking a file that's being written concurrently."

- **architectural-coupling × recent-changes:**
  "Did a recent refactor move state without moving all the invariants that depended on it? E.g. a field moved from the request object to a global config, but callers still assume request-scoped."

- **framework-contract × concurrency-timing:**
  "Does the code assume the framework serializes access (single-threaded request, scoped session) and then inadvertently break that assumption? E.g. a background task spawned inside a request handler that outlives the request scope."

- **code-path × environment:**
  "Is there a code path that's only reached in one environment? E.g. a branch gated on `ENV == 'production'`, a feature-flag branch, a platform-specific fallback (Windows path handling, macOS vs Linux filesystem semantics)."

---

## Dimension Discovery Process

1. **Phase 0 pre-mortem (see SKILL.md Phase 0):** one Haiku agent lists 5 ways this investigation could miss the real cause. Each flagged miss becomes an angle with priority=critical, tagged `premortem`.

2. **Phase 2 initial expansion (per cycle):**
   - For each of the 8 dimensions, generate 2–4 angles based on the specific symptom
   - Generate 2–3 cross-dimensional angles
   - Assess required category coverage (`correctness` / `environment` / `concurrency` / `architecture`); if any category has zero explored angles → add CRITICAL-priority angles to cover it
   - Cap total angles at 30 (leave budget for depth expansion from critic-reported sub-angles)

3. **Cycle 2+ expansion:**
   - Start from the graveyard of rejected hypotheses and the fix failure note
   - Add CRITICAL-priority angles for any dimension that had zero hypotheses accepted by the judge in cycle 1
   - Add CRITICAL-priority angles for any required category still uncovered
   - Each hypothesis agent may file ≤1 new angle per cycle (`depth = parent.depth + 1`)

4. **Frontier cap:** 30 angles. Displace the lowest-priority angle when at cap. Displacement rules:
   - Cannot displace a dimension's only remaining depth-0 angle
   - Cannot displace a required category's only uncovered angle
   - Cannot displace a `premortem`-tagged angle in cycle 1

---

## Required Category Coverage Rule

Termination label `Fixed — reproducing test now passes` requires:
1. A verified fix (Phase 5 criteria met), AND
2. All 4 required categories have ≥1 explored angle

A verified fix with uncovered required categories still terminates as `Fixed — reproducing test now passes` **but** the final report must prominently note:
> ⚠️ Coverage incomplete. Dimensions not explored: {list}. The fix is verified but the full hypothesis space was not searched — an alternative root cause may exist in an uncovered dimension.

Required category coverage is never waived silently. If the user wants to ship without full coverage, they see the warning in the report.

---

## Priority Ordering

Frontier items are ordered by priority (highest first):

1. **Critical:**
   - Uncovered required categories (`correctness`, `environment`, `concurrency`, `architecture`)
   - `premortem`-tagged angles from Phase 0
   - Angles covering dimensions that had all hypotheses rejected by the judge in the prior cycle
   - Dimensions with zero explored angles

2. **High:**
   - Cross-dimensional angles involving two uncovered dimensions
   - Angles targeting the leading hypothesis's critical unknown

3. **Medium:**
   - Standard angles per dimension
   - Cross-dimensional angles involving one uncovered and one covered dimension

4. **Low:**
   - Narrow sub-angles (depth ≥ 1) suggested by prior critics
   - Polish-level checks

Within the same priority level, prefer:
- Lower depth (broader) over higher depth (narrower)
- Angles targeting dimensions with fewer explored angles
- Cross-dimensional over single-dimensional

---

## Angle Schema

```json
{
  "id": "angle_001",
  "question": "Concrete, falsifiable question to investigate",
  "dimension": "code-path",
  "required_category": "correctness",
  "parent": null,
  "priority": "critical|high|medium|low",
  "depth": 0,
  "source": "coordinator_initial|critic_suggested|outside_frame|premortem",
  "discovery_round": 0,
  "rationale": "one-line reason this angle was selected/generated",
  "status": "frontier|in_progress|explored|timed_out|saturated|spawn_failed|spawn_exhausted",
  "spawn_time_iso": null,
  "spawn_attempt_count": 0,
  "hypothesis_file": null,
  "hypotheses_found": [],
  "exhaustion_score": null
}
```

- `depth 0` = top-level from dimension discovery
- `depth N` = discovered by a depth-(N-1) critic
- Max depth: 2 (smaller than deep-design's 3 — debugging has less taxonomic depth, more breadth)
- Angles with `depth > max_depth` are silently dropped during dedup
