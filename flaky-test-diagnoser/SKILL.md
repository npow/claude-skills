---
name: flaky-test-diagnoser
description: Systematically diagnoses why a test is flaky by running multi-run experiments, isolation tests, ordering permutations, and timing analysis. Use when the user says a test is flaky, intermittent, non-deterministic, randomly failing, passes sometimes, or asks to debug test flakiness.
---

# Flaky Test Diagnoser

Runs structured experiments to identify the root cause of a flaky test and produces a diagnosis report with a concrete fix.

## Workflow

1. **Detect test runner** — identify the project's test framework and runner command from config files. See [RUNNERS.md](RUNNERS.md).
2. **Confirm flakiness** — run the target test N times (default 10) in isolation, record pass/fail per run, and compute the fail rate. See [EXPERIMENTS.md](EXPERIMENTS.md).
3. **Isolation test** — run the target test alone, then with the full suite, and compare results. See [EXPERIMENTS.md](EXPERIMENTS.md).
4. **Ordering analysis** — if the test passes in isolation but fails in-suite, bisect the suite to find the interfering test(s). See [EXPERIMENTS.md](EXPERIMENTS.md).
5. **Timing analysis** — add timing instrumentation to detect race conditions, slow setup/teardown, and timeout sensitivity. See [EXPERIMENTS.md](EXPERIMENTS.md).
6. **Environment analysis** — check for external dependencies, parallel execution config, resource leaks, and non-determinism sources. See [ANALYSIS.md](ANALYSIS.md).
7. **Read the test code** — read the failing test and its fixtures/setup to inspect for known flakiness patterns. See [ANALYSIS.md](ANALYSIS.md).
8. **Classify root cause** — assign a root cause category and confidence level based on experiment results. See [ANALYSIS.md](ANALYSIS.md).
9. **Generate diagnosis report** — output the structured report with evidence, root cause, and fix recommendation. See [REPORT.md](REPORT.md).

## Self-review checklist

Before delivering the report, verify ALL:

- [ ] Flakiness confirmed: the test failed at least once AND passed at least once across experiment runs
- [ ] Fail rate computed from a minimum of 10 runs (not fewer)
- [ ] Isolation vs in-suite comparison completed (both were run)
- [ ] Root cause category is one of the 6 defined categories in ANALYSIS.md
- [ ] Fix recommendation references specific lines in the test or fixture code
- [ ] Report includes raw run data (pass/fail per run number) as evidence
- [ ] If ordering-dependent: the interfering test is identified by name
- [ ] If timing-dependent: the specific race condition or timeout is identified

## Golden rules

Hard rules. Never violate these.

1. **Never guess the root cause.** Every diagnosis must be supported by experiment data. If experiments are inconclusive, say "inconclusive" and recommend further experiments — never fabricate a cause.
2. **Always run isolation before ordering.** Run the test alone first. If it fails in isolation, ordering analysis is irrelevant — skip to timing and environment analysis.
3. **Bisect, never brute-force.** When searching for an interfering test, use binary bisection of the test suite, not one-by-one elimination. Cut the search space in half each iteration.
4. **Capture exact commands.** Every experiment must log the exact shell command run so the user can reproduce it. Never paraphrase a command — copy it verbatim into the report.
5. **Minimum 10 runs for any statistical claim.** Never say "always passes" or "always fails" with fewer than 10 runs. Flaky tests can have fail rates under 10%.
6. **Never modify test code during diagnosis.** The goal is to find the cause, not fix it during experiments. All instrumentation must be temporary and reverted before the report is delivered.

## Reference files

| File | Contents |
|------|----------|
| [RUNNERS.md](RUNNERS.md) | Test runner detection, command templates for pytest/jest/junit/go test/cargo test, and how to target a single test |
| [EXPERIMENTS.md](EXPERIMENTS.md) | Multi-run protocol, isolation protocol, ordering bisection algorithm, timing instrumentation |
| [ANALYSIS.md](ANALYSIS.md) | Root cause categories, code pattern matching for flakiness signals, environment factor checklist |
| [REPORT.md](REPORT.md) | Diagnosis report output format template |
