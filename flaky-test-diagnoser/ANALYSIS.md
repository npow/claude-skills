# Root Cause Analysis

How to classify the root cause, what code patterns indicate each category, and how to check environment factors.

## Contents
- Root cause categories
- Code pattern signals
- Environment factor checklist
- Decision matrix

---

## Root Cause Categories

Every diagnosis must classify the flakiness into exactly one of these 6 categories:

### 1. ORDERING — Test depends on execution order

**Signature**: Passes in isolation, fails in-suite. Bisection identifies a specific interfering test.
**Mechanism**: A prior test modifies shared state (database rows, module-level variables, singleton instances, environment variables, filesystem) that the target test assumes is clean.
**Common evidence**:
- Interfering test writes to a database/cache without cleanup
- Module-level variable mutated by interfering test
- Environment variable set by interfering test and not restored
- Temp files created by interfering test not cleaned up

**Fix pattern**: Add proper setup/teardown that resets the shared state. Or: make the target test independent of the assumed initial state.

### 2. TIMING — Race condition or timeout sensitivity

**Signature**: Fails in both isolation and in-suite, but fail rate changes with parallelism or system load. Failing runs show significantly longer execution times.
**Mechanism**: The test has a race condition (concurrent operations observed in wrong order) or depends on an operation completing within a time window that varies under load.
**Common evidence**:
- `sleep()` or `setTimeout()` used to wait for async operations
- Assertions on time-sensitive values (timestamps, durations)
- Missing `await` on async operations
- Polling with fixed timeout instead of condition-based waiting
- Go race detector reports data races

**Fix pattern**: Replace sleeps with condition-based waits. Add `await` to async operations. Use deterministic synchronization (mutexes, channels, promises) instead of time-based coordination.

### 3. SHARED_STATE — Shared mutable state without isolation

**Signature**: Fails in both isolation and in-suite, but serial execution (no parallelism) makes it pass reliably.
**Mechanism**: Multiple test threads/processes access the same mutable resource (in-memory singleton, shared database, shared file, shared port) without synchronization.
**Common evidence**:
- Static/global mutable variables used in test setup
- Hard-coded port numbers in tests
- Shared database without per-test transactions or cleanup
- Shared temp directory without per-test namespacing

**Fix pattern**: Isolate shared resources per test (unique ports, per-test DB transactions, separate tmp dirs). Or: run tests serially for the affected suite.

### 4. EXTERNAL_DEPENDENCY — Test relies on an external service

**Signature**: Fail rate varies across environments (local vs CI). Failures correlate with network availability or external service status.
**Mechanism**: The test calls a real external service (API, database, DNS, NTP) instead of using a mock/stub.
**Common evidence**:
- HTTP calls to external URLs in test code (not mocked)
- DNS resolution in tests
- Calls to `time.Now()` or `Date.now()` with assertions on specific values
- Dependency on specific system locale or timezone

**Fix pattern**: Mock external dependencies. Use fixed/injected time sources. Use test containers for database dependencies.

### 5. RESOURCE_LEAK — Test leaks resources across runs

**Signature**: First N runs pass, then failures start occurring. Fail rate increases over time within a batch.
**Mechanism**: The test (or its setup) allocates resources (file handles, connections, threads, memory) that are not released, eventually exhausting system limits.
**Common evidence**:
- File handles opened but not closed in test
- Database connections acquired but not released
- Goroutines/threads started but not joined/stopped
- Increasing memory usage across runs
- "too many open files" or "connection refused" errors in later runs

**Fix pattern**: Add resource cleanup in teardown/finally blocks. Use context managers (Python), try-with-resources (Java), or defer (Go). Verify cleanup runs even on test failure.

### 6. NON_DETERMINISM — Test output depends on non-deterministic input

**Signature**: Fails in isolation at a consistent rate regardless of ordering or parallelism. No timing variance between pass/fail runs.
**Mechanism**: The test depends on random values, hash map iteration order, filesystem readdir order, or other sources of non-determinism.
**Common evidence**:
- `Math.random()`, `random.random()`, `rand.Int()` without seeding
- HashMap/dict iteration used to assert order
- Filesystem listing used to assert order (`readdir`, `os.listdir`, `glob`)
- UUID generation used in assertions
- Floating point comparison without epsilon

**Fix pattern**: Seed random generators. Sort before comparing collections. Use ordered data structures for order-dependent logic. Use approximate comparison for floats.

---

## Code Pattern Signals

When reading the test code (workflow step 7), search for these patterns:

### Ordering signals
- Grep for: `setUp`, `tearDown`, `beforeAll`, `afterAll`, `beforeEach`, `afterEach`, `@Before`, `@After`, `fixture`
- Check: does teardown exist? Does it reset ALL state that setup creates?
- Check: are there module-level variables that tests modify?

### Timing signals
- Grep for: `sleep`, `setTimeout`, `time.Sleep`, `Thread.sleep`, `wait_for`, `asyncio.sleep`
- Grep for: `await` missing before async calls (check all `async` function calls)
- Grep for: `timeout`, `deadline`, `Duration`
- Check: is there a polling loop with a fixed timeout?

### Shared state signals
- Grep for: `static`, `global`, `module-level`, `singleton`
- Grep for: hard-coded ports (`8080`, `3000`, `5432`, `27017`)
- Grep for: shared file paths (`/tmp/test`, fixed filenames)
- Check: does the test fixture use a shared database without rollback?

### External dependency signals
- Grep for: `http://`, `https://` in test files (real URLs, not mocks)
- Grep for: `requests.get`, `fetch(`, `http.Get` in test code
- Grep for: `Date.now`, `time.time`, `Instant.now`, `System.currentTimeMillis` in assertions
- Check: are there test doubles/mocks for all external calls?

### Resource leak signals
- Grep for: `open(` without context manager (Python), `new FileInputStream` without try-with-resources (Java)
- Grep for: connections created in setup, check if closed in teardown
- Grep for: goroutines started (`go func`) without shutdown mechanism
- Check: does the error path clean up resources?

### Non-determinism signals
- Grep for: `random`, `rand`, `Math.random`, `uuid`, `UUID`
- Grep for: `HashMap`, `dict`, `map` used in order-sensitive assertions
- Grep for: `os.listdir`, `readdir`, `glob` used in assertions
- Check: are collection comparisons order-dependent?

---

## Environment Factor Checklist

Check these environment factors during analysis (workflow step 6):

| Factor | How to check | Flakiness signal |
|--------|-------------|-----------------|
| Parallelism | Read test runner config for `workers`, `forks`, `parallel`, `--jobs` | Tests may share state |
| CI vs local | Ask user if flakiness differs between CI and local | External dependency or resource difference |
| Docker/container | Check for `Dockerfile`, `docker-compose.test.yml` | Resource limits, networking differences |
| Database | Check for test database config, migrations, seeding | Shared DB state, missing cleanup |
| Network | Grep test code for external URLs | External service dependency |
| Filesystem | Grep for file operations in tests | Permission, ordering, or cleanup issues |
| Time | Grep for time-dependent assertions | Timezone, clock skew, or slow-machine sensitivity |
| Memory | Check test runner config for memory limits | OOM under parallel load |

---

## Decision Matrix

After all experiments, use this matrix to assign the root cause:

| Isolation result | Parallel vs serial | Timing variance | Bisection result | → Category |
|-----------------|-------------------|----------------|-----------------|------------|
| Passes alone, fails in-suite | N/A | N/A | Interferer found | ORDERING |
| Passes alone, fails in-suite | N/A | N/A | No interferer | SHARED_STATE (indirect) |
| Fails in both | Passes serial, fails parallel | N/A | N/A | SHARED_STATE |
| Fails in both | Fails in both modes | High variance on fail runs | N/A | TIMING |
| Fails in both | Fails in both modes | Low variance | N/A | NON_DETERMINISM |
| Fail rate increases over runs | N/A | N/A | N/A | RESOURCE_LEAK |
| Varies by environment | N/A | N/A | N/A | EXTERNAL_DEPENDENCY |

When multiple categories match, prioritize the one with the strongest experimental evidence. If truly ambiguous, report the top two candidates with confidence levels.
