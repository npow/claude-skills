---
name: canon-pr-review
description: |
  Review a PR against the top 20 Tier 2 LLM-enforceable best practices from 35 seminal software
  engineering books (Code Complete, Clean Code, A Philosophy of Software Design, Refactoring,
  Release It!, Designing Data-Intensive Applications, etc.). Produces a structured PR comment
  with four dimension scores (0-5 each), specific violations with line numbers, and an
  APPROVE / REQUEST_CHANGES / BLOCK decision.

  Auto-invoke when the user asks to:
  - "review PR", "canon review", "best practices review", "engineering standards review"
  - "score this PR", "check this PR against best practices"
  - Asks about code quality, module design, reliability patterns, or maintainability of a PR

  Do NOT invoke for: general code questions not tied to a specific PR, or requests for
  quick/lightweight review (use /review instead).

  Keywords: canon, best practices, PR review, score, dimensions, code quality, module design,
  reliability, maintainability, SRP, DRY, guard clauses, deep modules, idempotency, circuit breaker.
user-invocable: true
allowed-tools: Bash, Read, Edit, Write
argument-hint: "[pr_url_or_number] [--repo owner/repo]"
---

# Canon PR Review — Top 20 Tier 2 Practices

Scores a PR against 20 LLM-enforceable practices from seminal engineering books, across four
dimensions. Each dimension scored 0-5. Decision: APPROVE (all ≥ 3), REQUEST_CHANGES (any < 3
but none < 1), BLOCK (any < 1 or security violation).

---

## Phase 0: Fetch PR diff and context

```bash
# Auto-detect repo from cwd if not specified
git remote get-url origin 2>/dev/null

# Fetch PR diff (GitHub.com)
gh pr view <NUMBER> --json title,body,additions,deletions,changedFiles,baseRefName,headRefName
gh pr diff <NUMBER>

# OR for GitHub Enterprise
GH_HOST=<GHE_HOST> gh pr view <NUMBER> --repo <ORG/REPO> \
  --json title,body,additions,deletions,changedFiles,baseRefName,headRefName
GH_HOST=<GHE_HOST> gh pr diff <NUMBER> --repo <ORG/REPO>
```

Read the diff carefully. For each dimension below, scan the ENTIRE diff — not just the first file.
If the diff is large (>1000 lines), focus on new code paths, public interfaces, and error handling paths.

---

## The Four Dimensions

### DIMENSION 1: Code Quality (CC-003, CC-005, CC-006, CC-011, CC-021)

**Practices evaluated:**

**CC-003 — Intention-Revealing Names**
- Source: Code Complete (McConnell), Clean Code (Martin), The Elements of Programming Style (Kernighan & Plauger)
- What to check: Single-letter variables (except loop counters i/j/k), cryptic abbreviations, names that describe type rather than purpose (e.g., `data`, `temp`, `result`, `obj`, `mgr`), names where you must read the body to understand what the variable holds.
- Violation: `def proc(d, t, x): return d * t + x`
- Compliant: `def calculate_projected_revenue(daily_rate, time_horizon_days, baseline_offset): ...`
- Scoring rubric:
  - 0: Pervasive abbreviations/single-letters throughout (>50% of new identifiers)
  - 1: Major naming issues in core logic paths (30%+ of new identifiers)
  - 2: Moderate issues — some cryptic names in non-trivial positions
  - 3: Minor issues — a few mediocre names, all intent is recoverable
  - 4: Good names throughout with 1-2 nitpicks
  - 5: Every name reveals intent without requiring the reader to read the body

**CC-005 — Single Responsibility at Function Level**
- Source: Clean Code (Martin), Code Complete (McConnell), A Philosophy of Software Design (Ousterhout)
- What to check: Does the function description require "and" or "or"? Does the function do two conceptually distinct things? Look for functions that validate AND persist, or parse AND format, or fetch AND transform.
- Violation: `def process_order(order): validates fields, charges card, sends confirmation email, updates inventory — all inline`
- Compliant: `process_order` calls `validate_order`, `charge_payment`, `send_confirmation`, `decrement_inventory` — each a separate function
- Scoring rubric:
  - 0: New functions are god-functions with 3+ distinct responsibilities
  - 1: Multiple new functions clearly do two distinct things
  - 2: Some functions blend concerns; refactor would improve clarity materially
  - 3: Minor blending — one or two functions slightly overreach
  - 4: All new functions have clear single jobs with 1-2 debatable edge cases
  - 5: Every new function does exactly one thing; composition is explicit

**CC-006 — DRY: No Knowledge Duplication**
- Source: The Pragmatic Programmer (Hunt & Thomas), Code Complete (McConnell)
- What to check: Same business logic appearing in multiple places with slight variations (not just copy-paste, but the same _concept_ implemented twice). Tax calculation in two services. Validation logic in two layers. Date formatting in three places.
- Note: DRY is about _knowledge_, not _text_. Two functions that happen to share code structure for different reasons are not DRY violations.
- Violation: `OrderService.calculate_tax()` and `InvoiceService.calculate_tax()` with slightly different implementations of the same tax rule
- Compliant: Single `TaxCalculator` class/module used by both services
- Scoring rubric:
  - 0: Clear duplication of core business rules across files
  - 1: Multiple instances of duplicated knowledge in the PR's changes
  - 2: Some duplication visible; abstraction exists but isn't used
  - 3: Minimal duplication — one small instance or borderline case
  - 4: No meaningful duplication; 1-2 acceptable repetitions (boilerplate, clarity)
  - 5: Zero knowledge duplication; every concept defined once

**CC-011 — Guard Clauses / Early Returns**
- Source: Clean Code (Martin), Code Complete (McConnell), Refactoring (Fowler)
- What to check: Deeply nested if-else blocks where the "happy path" is buried. Functions where the main logic is inside a chain of positive conditionals rather than failing fast on preconditions.
- Violation: `if user: if user.active: if user.has_permission('edit'): do_the_work()` — 3 levels deep for the core logic
- Compliant: `if not user: raise NotFound(); if not user.active: raise Forbidden('deactivated'); if not user.has_permission('edit'): raise Forbidden(); do_the_work()`
- Scoring rubric:
  - 0: New code consistently buries happy path in 3+ levels of positive conditionals
  - 1: Multiple new functions use deep nesting where guard clauses apply
  - 2: Some nesting that would benefit from guards; not pervasive
  - 3: One or two places where guard refactor would help; rest is clean
  - 4: Mostly clean with minor nesting that's stylistically defensible
  - 5: Guard clauses used correctly; happy paths are at the leftmost indentation

**CC-021 — No Code Smells (Long Method, Large Class, Feature Envy, Data Clumps)**
- Source: Refactoring (Fowler), Clean Code (Martin)
- What to check:
  - Long Method: new functions >50 lines
  - Large Class: new/modified classes >300 lines or >8 public methods on disparate concerns
  - Feature Envy: a method that seems more interested in another class's data than its own
  - Data Clumps: groups of 3+ parameters that always travel together (should be an object)
- Violation: A 200-line function; a class that does auth + profile + billing + notifications
- Compliant: Small focused functions; classes with cohesive responsibilities
- Scoring rubric:
  - 0: Multiple obvious smells introduced (large class AND long methods AND feature envy)
  - 1: One severe smell or two moderate smells
  - 2: Moderate smell — one long function or one class with mixed concerns
  - 3: Minor smell — function slightly long, or one data clump
  - 4: Clean with 1 nitpick
  - 5: No smells introduced; code is clean

**Code Quality score computation:** Average of the five checks above (round to nearest integer 0-5). Gate: BLOCK if average < 1. REQUEST_CHANGES if average < 3.

---

### DIMENSION 2: Module Design (CC-027, CC-015, CC-028, CC-017)

**Practices evaluated:**

**CC-027 — Deep Modules: Simple Interfaces Hiding Significant Complexity**
- Source: A Philosophy of Software Design (Ousterhout)
- What to check: Modules/classes where the interface complexity is close to the implementation complexity (shallow modules). Look for: many configuration parameters for simple logic, pass-through wrappers that add no abstraction, complex call sequences required to do simple things.
- Violation: A `FileReader` class with 20 configuration methods but only 50 lines of actual logic. Or: a function requiring 6 parameters where 4 are rarely needed and could have sane defaults.
- Compliant: `db.query("SELECT * FROM users WHERE id = ?", user_id)` — a deep interface that hides connection pooling, retry logic, type coercion, and result mapping behind a single clean call.
- Scoring rubric:
  - 0: New modules are purely shallow — thin wrappers with no abstraction value
  - 1: Most new modules are shallow; callers must know implementation details
  - 2: Mixed — some modules are deep, others are shallow pass-throughs
  - 3: Mostly deep; one or two places where abstraction leaks
  - 4: Deep modules throughout with minor leakage
  - 5: New modules exemplify deep design — simple interfaces over real complexity

**CC-015 — Composition Over Inheritance**
- Source: Design Patterns (GoF), Clean Code (Martin), A Philosophy of Software Design (Ousterhout)
- What to check: Inheritance hierarchies deeper than 2 levels. Abstract classes overridden in ways that weaken or violate the contract. Situations where roles/behaviors could be composed via interfaces/protocols instead of inherited.
- Violation: `class AdminUser(AuthorizedUser(User(Person(Entity))))` — 4-level hierarchy where adding a new "role" requires another subclass
- Compliant: `class User` with injected `role: Role` and `permissions: PermissionSet` — behaviors composed, not inherited
- Scoring rubric:
  - 0: New 3+ level inheritance hierarchies introduced; clear composition alternatives exist
  - 1: New 2+ level hierarchy where composition would be materially better
  - 2: Inheritance used where composition is plausible but debatable
  - 3: Mostly composition-oriented; one inheritance decision that's defensible
  - 4: Composition-first approach with inheritance used only for true IS-A relationships
  - 5: No inheritance introduced; or inheritance is clearly correct and bounded to 1 level

**CC-028 — Interface Comments: What and Why, Not Just How**
- Source: A Philosophy of Software Design (Ousterhout), Code Complete (McConnell)
- What to check: Public functions and classes without docstrings. Docstrings that only restate the function name ("Get user by ID — gets the user by ID"). Missing documentation of: preconditions, postconditions, error conditions, non-obvious behavior, why this abstraction exists.
- Violation: `def process_payment(amount, card):` with no docstring — caller must read implementation to learn that amount must be in cents, card must be pre-validated, raises PaymentGatewayError on network failure.
- Compliant: Docstring explaining the interface contract: what it expects, what it returns, what it raises, and any non-obvious behavior (e.g., "idempotent if payment_id is provided").
- Scoring rubric:
  - 0: New public API has zero documentation; callers cannot use it without reading the body
  - 1: Minimal or misleading documentation; critical contract details missing
  - 2: Some documentation present but edge cases and errors undocumented
  - 3: Key public functions documented; minor gaps in non-obvious behavior
  - 4: Good documentation with 1-2 missing details
  - 5: Every public interface documented with contract, errors, and non-obvious behavior

**CC-017 — Encapsulate What Varies**
- Source: Design Patterns (GoF), Refactoring (Fowler), A Philosophy of Software Design (Ousterhout)
- What to check: Variation points hardcoded into logic instead of extracted. Switch/if-elif chains over types where the variation is a stable set. Config values hardcoded when they should be parameters or injected. Business rules mixed with orchestration.
- Violation: `if country == 'US': tax = 0.08 elif country == 'UK': tax = 0.20 elif country == 'DE': tax = 0.19` — variation embedded in logic, requires code change to add a new country
- Compliant: `TAX_RATES = {'US': 0.08, 'UK': 0.20, 'DE': 0.19}; tax = TAX_RATES.get(country, DEFAULT_TAX_RATE)` — variation isolated in data
- Scoring rubric:
  - 0: Multiple variation points hardcoded into logic with no extraction
  - 1: A significant variation point is hardcoded when it should be parameterized
  - 2: Some hardcoded variation; partial extraction
  - 3: Most variation properly encapsulated; one minor case missed
  - 4: Clean encapsulation throughout with 1 nitpick
  - 5: Variation systematically isolated; adding new cases requires data, not code changes

**Module Design score computation:** Average of the four checks above (round to nearest integer 0-5). Gate: REQUEST_CHANGES if average < 3.

---

### DIMENSION 3: Reliability (CC-014, CC-048, CC-056, CC-058, CC-060)

**Practices evaluated:**

**CC-014 — Explicit Error Handling: Never Swallow Exceptions**
- Source: Code Complete (McConnell), Clean Code (Martin), Release It! (Nygard)
- What to check: Bare `except: pass` or `catch (Exception e) {}`. Catching broad exception types and doing nothing. try/except blocks where the except clause only logs and continues without any recovery or re-raise. Errors that collapse to None or empty returns silently.
- Violation: `try: risky_call() except: pass` — swallows ALL exceptions including OOM, KeyboardInterrupt, SystemExit
- Compliant: `try: result = risky_call() except NetworkError as e: raise ServiceUnavailable("upstream failed") from e` — catches specific type, transforms to domain exception with context
- Scoring rubric:
  - 0: Bare except/catch with pass — swallowing all errors in new code
  - 1: Broad exception catching with no meaningful handling in critical paths
  - 2: Some swallowing in non-critical paths, or log-and-continue without recovery
  - 3: Mostly explicit; one questionable exception handling path
  - 4: All exceptions explicitly handled; 1 minor over-broad catch
  - 5: Every exception caught precisely; errors transformed to domain types with context

**CC-048 — Idempotency Across Network Boundaries**
- Source: Designing Data-Intensive Applications (Kleppmann), Enterprise Integration Patterns (Hohpe & Woolf)
- What to check: POST endpoints that create side effects without idempotency keys. Message handlers that process without deduplication. Write operations that don't check "already done" before executing. Particularly critical for: payment processing, email sending, inventory mutations, any operation the caller might retry on timeout.
- Violation: `POST /charge` that creates a new charge on every request — client retries on network timeout cause double-charge
- Compliant: `POST /charge` that accepts `Idempotency-Key` header and returns the existing charge if the key was already processed
- Scoring rubric:
  - 0: New mutating endpoints/handlers introduced with zero idempotency consideration in high-risk paths (payments, writes)
  - 1: Idempotency absent from operations where retries are likely
  - 2: Partial idempotency — some paths protected, others not
  - 3: Key paths are idempotent; minor gaps in low-stakes operations
  - 4: Comprehensive idempotency with 1 edge case not fully covered
  - 5: All mutating operations idempotent with key-based deduplication or natural idempotency

**CC-056 — Circuit Breakers for External Dependencies**
- Source: Release It! (Nygard), Designing Data-Intensive Applications (Kleppmann)
- What to check: New HTTP/gRPC/database calls to external services that lack circuit breaker wrapping. Unbounded retry loops without fail-fast. Code that will cascade-fail if a downstream service becomes slow or unavailable.
- Violation: `while True: try: response = requests.get(external_api) except: time.sleep(1)` — hammers a failing service forever; amplifies the failure
- Compliant: Using a circuit breaker library (hystrix, resilience4j, pybreaker, tenacity with break condition) or checking a circuit breaker state before calling
- Note: If the PR calls internal services that already have infrastructure-level circuit breakers (service mesh, gateway), note this and score less harshly.
- Scoring rubric:
  - 0: New calls to external services with no circuit breaker and unbounded retries
  - 1: Circuit breaker absent from new critical external calls
  - 2: Some external calls lack circuit breakers; others are protected
  - 3: Most new external calls are protected; one minor path unprotected
  - 4: Circuit breakers present; 1 edge case in non-critical path
  - 5: All new external calls are protected or use infrastructure-level circuit breaking

**CC-058 — Explicit Timeouts on All Network Calls**
- Source: Release It! (Nygard), Designing Data-Intensive Applications (Kleppmann)
- What to check: HTTP client calls without explicit timeout parameter. Database query calls without timeout. RPC calls using default (often infinite) timeouts. Look specifically for: `requests.get(url)`, `httpx.get(url)` without `timeout=`, database `execute()` without timeout, gRPC stubs without deadline.
- Violation: `requests.get(url)` — thread hangs forever if remote server accepts the connection but never responds
- Compliant: `requests.get(url, timeout=(connect_timeout, read_timeout))` with both connect and read timeouts specified as named constants
- Scoring rubric:
  - 0: Multiple new network calls with no explicit timeout
  - 1: New critical network call(s) missing explicit timeout
  - 2: Some network calls lack timeouts; others have them
  - 3: Most timeouts present; one missing in a non-critical path
  - 4: All timeouts specified; 1 uses a default that's acceptable
  - 5: All network calls have explicit, named-constant timeouts (connect AND read where applicable)

**CC-060 — Graceful Degradation: Partial Function When Dependencies Fail**
- Source: Release It! (Nygard), Site Reliability Engineering (Beyer et al.)
- What to check: Error handling paths that fail the entire operation when a non-critical dependency fails. Missing fallbacks for optional enrichment services. All-or-nothing failure modes where partial results would be acceptable.
- Violation: A product page that throws 500 if the recommendations service is down — the core product info was available, only the sidebar failed
- Compliant: `try: recs = recommendations.get(product_id) except ServiceUnavailable: recs = []` — page renders without recommendations rather than failing entirely
- Scoring rubric:
  - 0: New code makes non-critical dependency failures fatal to the primary operation
  - 1: Multiple places where degraded-mode fallbacks are missing
  - 2: Some degradation paths missing; partial fallback coverage
  - 3: Key paths have fallbacks; one non-critical path lacks degradation
  - 4: Comprehensive graceful degradation with 1 minor gap
  - 5: All non-critical dependencies have explicit degraded-mode fallbacks

**Reliability score computation:** Average of the five checks above (round to nearest integer 0-5). Gate: BLOCK if any individual check scores 0. REQUEST_CHANGES if average < 3.

---

### DIMENSION 4: Maintainability (CC-019, CC-031, CC-093, CC-107)

**Practices evaluated:**

**CC-019 — Refactoring in Small, Behavior-Preserving Steps**
- Source: Refactoring (Fowler), Working Effectively with Legacy Code (Feathers)
- What to check: PRs that mix refactoring with feature changes. Commits where variable renames, method extractions, AND new business logic all appear together. Large structural changes without evidence of incremental validation. Renamed identifiers AND changed behavior in the same diff.
- Violation: A single commit that renames 15 variables, extracts 5 methods, AND adds a new feature — if the feature is broken, you can't tell if it's the refactor or the feature
- Compliant: Separate commits (or PRs) for the rename, the extraction, and the new behavior — each provably behavior-preserving
- Note: Check the PR's commit history (`gh pr view --json commits`) to assess this.
- Scoring rubric:
  - 0: Refactoring and new behavior completely intermingled; impossible to bisect
  - 1: Major mixing — significant refactor and significant feature in same commit/PR
  - 2: Some mixing — minor refactor mixed with feature, but separable with effort
  - 3: Mostly clean — small incidental refactoring alongside feature is acceptable
  - 4: Clean separation with 1 minor incidental change
  - 5: Purely additive PR or clearly separated refactor-then-feature commit history

**CC-031 — Tests Before Changing Legacy/Untested Code**
- Source: Working Effectively with Legacy Code (Feathers)
- What to check: PRs that modify functions/classes with 0 or low test coverage without adding characterization tests first. Check: are the modified code paths covered by any test in the PR? Does the PR add tests for paths it changes?
- Violation: Modifying a 300-line function with 0% test coverage and no regression safety net — any behavior change is undetectable
- Compliant: PR first adds tests that document the existing behavior (characterization tests), then modifies the code, then verifies tests still pass
- Scoring rubric:
  - 0: Modifies untested code paths; no tests added; behavior changes are unverifiable
  - 1: Modifies mostly untested code; a token test added that doesn't cover the changes
  - 2: Some test coverage added for modified paths; gaps remain in critical branches
  - 3: Key modified paths have tests; minor branches uncovered
  - 4: Good test coverage for modified paths; 1 edge case not tested
  - 5: Every modified code path has a test; characterization tests added for previously untested code

**CC-093 — Fix Broken Windows: Don't Let Quality Issues Accumulate**
- Source: The Pragmatic Programmer (Hunt & Thomas)
- What to check: PRs that introduce new TODO/FIXME/HACK comments without tracking. PRs that add new `# noqa` suppressions without justification. PRs that skip or xfail tests without explanation. PRs that add workarounds instead of fixing the root cause.
- Violation: `# TODO: fix this later` on a critical path; `# noqa: E501` added to 10 lines without comment; `@pytest.mark.skip("broken, will fix")` added to existing test
- Compliant: TODOs link to tracked issues. Suppressions have justification comments. Workarounds are explicitly temporary with a follow-up ticket reference.
- Scoring rubric:
  - 0: Multiple new broken windows introduced (untracked TODOs, unexplained suppressions, skipped tests)
  - 1: One significant broken window (skipped test without explanation, or untracked TODO in critical path)
  - 2: Minor broken windows — TODOs present but clearly low-stakes
  - 3: Clean; any TODOs are appropriately qualified
  - 4: Pristine; no workarounds, no suppressions, no skipped tests
  - 5: PR actively repairs pre-existing broken windows in addition to its primary change

**CC-107 — Reproduce the Bug Before Fixing It (Regression Tests)**
- Source: Debugging: The 9 Indispensable Rules (Agans), The Practice of Programming (Kernighan & Pike)
- What to check (bug-fix PRs only): Does the PR include a failing test that demonstrates the bug? Can you see from the test that it would have failed before the fix and passes after? For feature PRs, does the PR include tests that would fail if the feature regressed?
- Violation: Bug fix PR with no test — fix addresses a guess at the root cause; the same bug can silently return in a future refactor
- Compliant: Test added that fails on `main` and passes with the fix applied; PR description explains what the test exercises and why
- Note: If the PR description says "no test needed because X", evaluate whether X is a valid reason.
- Scoring rubric:
  - 0: Bug fix PR with no test that exercises the fixed behavior
  - 1: Test added but doesn't actually verify the fixed behavior (tests adjacent behavior)
  - 2: Test present but incomplete — doesn't cover the edge case that caused the bug
  - 3: Test covers the main case; minor edge cases untested
  - 4: Good regression test; 1 additional edge case would strengthen it
  - 5: Test precisely demonstrates the bug scenario; would fail without the fix; documents the contract

**Maintainability score computation:** Average of the four checks above (round to nearest integer 0-5). Gate: REQUEST_CHANGES if average < 3.

---

## Decision Logic

```
BLOCK   — any dimension < 1, OR any individual Reliability check scores 0
            (a score-0 reliability item means a silent failure mode was introduced)

REQUEST_CHANGES — any dimension score < 3 (but no BLOCKs apply)

APPROVE — all four dimension scores ≥ 3
```

Tie-breaking: a close REQUEST_CHANGES (e.g., two dimensions at exactly 3, two at 2) should note which specific practices to address before re-review.

---

## Output: Structured PR Comment

Post the review as a GitHub PR comment using:

```bash
gh pr comment <NUMBER> --body "$(cat <<'EOF'
<review content>
EOF
)"
```

OR for GitHub Enterprise:
```bash
GH_HOST=<GHE_HOST> gh pr comment <NUMBER> --repo <ORG/REPO> --body "$(cat <<'EOF'
<review content>
EOF
)"
```

### Required comment format

```markdown
## Canon PR Review — Engineering Standards Scorecard

**PR:** <title>
**Reviewed against:** Top 20 Tier 2 practices (Code Complete, Clean Code, APoSD, Refactoring, Release It!, DDIA, The Pragmatic Programmer, Working Effectively with Legacy Code, Design Patterns GoF)

### Scores

| Dimension | Score | Gate |
|-----------|-------|------|
| Code Quality (naming, SRP, DRY, guard clauses, smells) | X/5 | ✅/⚠️/🚫 |
| Module Design (deep modules, composition, docs, encapsulation) | X/5 | ✅/⚠️/🚫 |
| Reliability (error handling, idempotency, circuit breakers, timeouts, degradation) | X/5 | ✅/⚠️/🚫 |
| Maintainability (small steps, test before change, broken windows, regression tests) | X/5 | ✅/⚠️/🚫 |

**Decision: APPROVE / REQUEST_CHANGES / BLOCK**

---

### Violations Found

#### [Dimension Name]

**[Practice ID] — [Practice Name]** *(Source: Book Title)*
- **Location:** `path/to/file.py:line_number`
- **Issue:** [Specific description of what violates the practice]
- **Violation excerpt:**
  ```language
  [verbatim offending code]
  ```
- **Suggested improvement:**
  ```language
  [concrete fix]
  ```

[Repeat for each violation]

---

### What's Working Well

[1-3 specific practices the PR exemplifies correctly]

---

### To Unblock

[If REQUEST_CHANGES or BLOCK: numbered list of the specific changes needed, referencing the practices above. Each item should be actionable — the author should know exactly what to do.]

---

*Scored against: CC-003, CC-005, CC-006, CC-011, CC-021 (Code Quality) | CC-027, CC-015, CC-028, CC-017 (Module Design) | CC-014, CC-048, CC-056, CC-058, CC-060 (Reliability) | CC-019, CC-031, CC-093, CC-107 (Maintainability)*
```

---

## Evaluation Protocol

**For each practice, the agent must:**

1. Read the relevant section(s) of the diff
2. Identify the specific file and line number of any violation
3. Quote the verbatim offending code
4. Score the practice using the rubric (0-5)
5. Record the score and the evidence

**Anti-rationalization rules:**

| Excuse | Correct action |
|--------|---------------|
| "The code is probably fine; I can't find evidence either way" | Default to score 3 (neutral); note the uncertainty |
| "This is a large diff; I only checked some files" | State which files were checked; note that others were not reviewed |
| "This practice doesn't apply because the PR is small" | Apply all practices; small PRs can still introduce reliability gaps or poor names |
| "The PR description says the author will fix X later" | Score the PR as submitted; note the author's stated intent |
| "I'm not sure if this counts as a violation" | Describe the observation; let the score reflect the uncertainty (2-3) |

**Parallel evaluation:** Evaluate all four dimensions based on your initial read of the full diff. Do not go section-by-section; form an overall picture first, then gather specific evidence for each check.

---

## Dimension Applicability Notes

**For very small PRs (<50 lines of non-test code):**
- CC-019 (small refactoring steps): default 5 — small PRs are inherently small steps
- CC-031 (tests before changes): only apply if modifying existing non-trivial logic
- CC-056/CC-058 (circuit breakers/timeouts): only apply if new network calls are introduced
- CC-048 (idempotency): only apply if new mutating operations are introduced

**For documentation-only PRs:**
- Score all dimensions 5 (n/a); note that no code was changed

**For test-only PRs:**
- Apply CC-003 (naming), CC-021 (smells), CC-028 (interface comments) to the test code
- Mark CC-056, CC-058, CC-048 as n/a (tests typically don't call external services)
- Apply CC-031 and CC-107 by checking whether the tests actually exercise the described behavior

---

## Self-Review Checklist

Before posting the comment:

- [ ] Every violation has a specific file:line reference
- [ ] Every violation has a verbatim code excerpt (not paraphrased)
- [ ] Every score has a stated rationale mapped to the rubric
- [ ] The decision (APPROVE/REQUEST_CHANGES/BLOCK) correctly follows the decision logic
- [ ] "What's Working Well" cites at least one specific thing, not generic praise
- [ ] If BLOCK: the blocking reason references a specific dimension score <1 or a specific reliability check at 0
- [ ] If REQUEST_CHANGES: "To Unblock" section is actionable — the author knows exactly what to change
- [ ] No violation cited without seeing the actual code (no "probably" or "likely" violations)

---

## Practice Quick-Reference

| ID | Practice | Dimension | Sources |
|----|----------|-----------|---------|
| CC-003 | Intention-revealing names | Code Quality | Code Complete, Clean Code, EoPS |
| CC-005 | Functions do one thing | Code Quality | Clean Code, Code Complete, APoSD |
| CC-006 | DRY: eliminate knowledge duplication | Code Quality | Pragmatic Programmer, Code Complete |
| CC-011 | Guard clauses / early returns | Code Quality | Clean Code, Code Complete, Refactoring |
| CC-021 | Detect and eliminate code smells | Code Quality | Refactoring, Clean Code |
| CC-027 | Deep modules: simple interfaces | Module Design | A Philosophy of Software Design |
| CC-015 | Composition over inheritance | Module Design | GoF, Clean Code, APoSD |
| CC-028 | Interface comments (what + why) | Module Design | APoSD, Code Complete |
| CC-017 | Encapsulate what varies | Module Design | GoF, Refactoring, APoSD |
| CC-014 | Handle errors explicitly; never swallow | Reliability | Code Complete, Clean Code, Release It! |
| CC-048 | Make operations idempotent | Reliability | DDIA, Enterprise Integration Patterns |
| CC-056 | Circuit breakers for external deps | Reliability | Release It!, DDIA |
| CC-058 | Explicit timeouts on all network calls | Reliability | Release It!, DDIA |
| CC-060 | Graceful degradation | Reliability | Release It!, SRE |
| CC-019 | Refactor in small behavior-preserving steps | Maintainability | Refactoring, WELC |
| CC-031 | Tests before changing legacy code | Maintainability | Working Effectively with Legacy Code |
| CC-093 | Fix broken windows immediately | Maintainability | The Pragmatic Programmer |
| CC-107 | Reproduce bug before fixing (regression tests) | Maintainability | Debugging Rules, Practice of Programming |

**Book abbreviations:** APoSD = A Philosophy of Software Design, EoPS = Elements of Programming Style, DDIA = Designing Data-Intensive Applications, WELC = Working Effectively with Legacy Code, SRE = Site Reliability Engineering, GoF = Design Patterns (Gang of Four).
