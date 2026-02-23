# Experiment Protocols

Step-by-step protocols for each experiment phase. Execute these in order.

## Contents
- Multi-run protocol (confirm flakiness)
- Isolation protocol (alone vs in-suite)
- Ordering bisection protocol (find interfering test)
- Timing analysis protocol (detect race conditions)

---

## Multi-Run Protocol

**Goal**: Confirm the test is flaky and measure its fail rate.

### Steps

1. Construct the single-test run command from RUNNERS.md for the detected runner
2. Run the test 10 times using the loop template from RUNNERS.md
3. Parse the output: count lines matching `EXIT: 0` (pass) and `EXIT: [^0]` (fail)
4. Compute fail rate: `fail_count / total_runs * 100`

### Recording format

Record results in this structure (keep in memory for the report):

```
MULTI-RUN RESULTS
Command: [exact command]
Runs: 10
Results: P P F P P P F P P P
Pass: 8, Fail: 2
Fail rate: 20%
```

### Decision tree after multi-run

| Result | Next step |
|--------|-----------|
| 0 failures in 10 runs | Increase to 20 runs. If still 0 failures, the test may not be flaky in this environment — ask the user for more context (CI logs, specific conditions). |
| 1-3 failures | Flakiness confirmed. Proceed to isolation protocol. |
| 4-7 failures | Highly flaky. Proceed to isolation protocol. |
| 8-10 failures | Likely a real bug, not flakiness. Inform user this test appears consistently broken, not flaky. Still proceed to isolation to verify. |

---

## Isolation Protocol

**Goal**: Determine if the test fails on its own or only when other tests run first.

### Steps

1. **Isolated run**: Run the target test alone 5 times using the single-test command. Record pass/fail.
2. **In-suite run**: Run the full test suite (or the test file) 5 times. Record whether the target test passes/fails.

### Recording format

```
ISOLATION RESULTS
Isolated (5 runs): P P P P P — fail rate: 0%
In-suite (5 runs):  P F P F P — fail rate: 40%
```

### Decision tree after isolation

| Isolated | In-suite | Diagnosis | Next step |
|----------|----------|-----------|-----------|
| Always passes | Sometimes fails | Ordering-dependent | Proceed to ordering bisection |
| Sometimes fails | Sometimes fails | Not ordering-dependent | Skip ordering, proceed to timing analysis |
| Sometimes fails | Always passes | Unusual — possible resource leak from the test itself | Proceed to timing analysis |
| Always fails | Always fails | Not flaky — consistently broken | Report as a real bug, not flakiness |

---

## Ordering Bisection Protocol

**Goal**: Find the specific test(s) that, when run before the target, cause it to fail.

### Prerequisites
- The target test passes in isolation but fails in-suite (confirmed by isolation protocol)

### Steps

1. **List all tests**: Use the runner's list/collect command to get the ordered test list:
   - pytest: `pytest --co -q 2>&1`
   - Jest: `npx jest --listTests 2>&1`
   - go test: `go test -list ".*" ./PACKAGE/ 2>&1`
   - Gradle: `./gradlew test --tests "*" --dry-run 2>&1` or parse test report

2. **Find target position**: Locate the target test in the ordered list. All tests before it are candidates.

3. **Binary bisection**:
   - Split candidates into two halves: FIRST_HALF and SECOND_HALF
   - Run FIRST_HALF + TARGET. If target fails → interferer is in FIRST_HALF
   - Run SECOND_HALF + TARGET. If target fails → interferer is in SECOND_HALF
   - Recurse on the failing half until a single interfering test is found
   - Run each bisection step 3 times to account for the flakiness itself

4. **Confirm**: Run INTERFERER + TARGET 5 times. If target fails at least once, the interferer is confirmed.

### Recording format

```
ORDERING BISECTION
Full suite: 47 tests before target
Step 1: tests[0:23] + target → 3 runs: P P P (not here)
Step 1: tests[24:46] + target → 3 runs: F P F (here!)
Step 2: tests[24:35] + target → 3 runs: P P F (here!)
Step 3: tests[24:29] + target → 3 runs: P P P (not here)
Step 3: tests[30:35] + target → 3 runs: F F P (here!)
Step 4: tests[30:32] + target → 3 runs: F P F (here!)
Step 5: test[31] + target → 3 runs: F F P (CONFIRMED)
Interfering test: test_user_cache_setup (tests/test_users.py::test_user_cache_setup)
```

### Bisection command construction

For runners that support specifying test order:
- **pytest**: `pytest TEST_A TEST_B TARGET -v 2>&1`
- **Jest**: `npx jest FILE_A FILE_B TARGET_FILE --verbose 2>&1`
- **go test**: `go test -run "TestA|TestB|Target" -v ./pkg/ 2>&1`

For runners that do NOT support arbitrary ordering: run the subset as the entire suite using test filtering.

---

## Timing Analysis Protocol

**Goal**: Detect race conditions, timeout sensitivity, and slow operations that cause intermittent failures.

### Steps

1. **Timed runs**: Run the target test 5 times with verbose/duration output enabled:
   - pytest: `--durations=0 --setup-show`
   - Jest: `--verbose` (shows per-test timing)
   - go test: `-v` (shows elapsed time per test)

2. **Record timing per run**:
   ```
   Run 1: setup=12ms, test=145ms, teardown=8ms — PASS
   Run 2: setup=11ms, test=2034ms, teardown=9ms — FAIL
   Run 3: setup=340ms, test=152ms, teardown=7ms — PASS
   ```

3. **Analyze variance**: Look for:
   - Setup time > 10x median → slow resource initialization (DB, network)
   - Test time > 5x median on failing runs → timeout or blocking call
   - Teardown time spike → resource cleanup race

4. **Parallel vs serial**: Run the test with parallelism disabled:
   - pytest: `-p no:xdist` or `--forked`
   - Jest: `--runInBand`
   - go test: `-parallel 1`
   - Vitest: `--pool=forks --poolOptions.forks.singleFork`

   If the test stops flaking when run serially, the root cause is parallel execution (shared state or resource contention).

5. **Race detection** (language-specific):
   - Go: `go test -race` (built-in race detector)
   - Python: check for shared mutable module-level variables
   - Java: check for `static` mutable fields in test classes

### Recording format

```
TIMING ANALYSIS
Parallel mode: 5 runs → 2 failures (40% fail rate)
Serial mode: 5 runs → 0 failures (0% fail rate)
Diagnosis: Fails only under parallel execution

Timing variance:
  Setup:    median=12ms, max=340ms (28x variance)
  Test:     median=148ms, max=2034ms (13x variance on fail runs)
  Teardown: median=8ms, max=9ms (stable)

Observation: Failing runs show test body taking 13x longer — likely waiting on a shared resource held by a parallel test.
```
