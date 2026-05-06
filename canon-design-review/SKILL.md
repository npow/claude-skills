---
name: canon-design-review
description: |
  Architecture-level design review evaluating 15 Tier 2 best practices drawn from DDD
  (Evans), POEAA (Fowler), Release It! (Nygard), DDIA (Kleppmann), Team Topologies
  (Skelton/Pais), How Buildings Learn (Brand), and Systemantics (Gall).

  Auto-invoke when a PR touches:
  - Service definitions, infrastructure code, API boundaries, or database schemas
  - Files matching **/architecture*, **/design*, **/api/*, **/schema*, **/migrations/*
  - Any directory named services/, infrastructure/, platform/, domain/, core/

  Also invoke when the user says:
  - "design review", "architecture review", "review the design", "check the architecture"
  - "does this follow DDD", "bounded context check", "SOLID review"
  - "is this evolvable", "check coupling", "resilience review"

  Keywords: architecture, design, bounded context, DDD, SOLID, resilience, circuit breaker,
  bulkhead, shearing layers, cohesion, coupling, ADR, API versioning, Team Topologies,
  cognitive load, Gall's Law, consistency model, backpressure.

category: architecture
user-invocable: true
allowed-tools: Bash, Read, Glob
argument-hint: "[pr_url_or_path_or_description]"
---

# Canon Design Review

Evaluates architecture-level practices across 3 assessment areas: **Structural Integrity**,
**Resilience & Operations**, and **Evolutionary Design**. Produces a scored assessment table
with verdict (PASS / WARN / BLOCK), evidence, and an overall recommendation.

This skill does not replace human design judgment — it surfaces objective signals and known
anti-patterns rooted in 7 seminal books. BLOCK verdicts must be resolved; WARN verdicts
require acknowledgment.

---

## Trigger detection

Before starting, identify what to review:

1. If a PR URL or number was given, fetch changed files:
   ```bash
   gh pr view <NUMBER> --json changedFiles,title,body | jq '.changedFiles[].path'
   ```
2. If a path was given, inspect directly.
3. If neither, ask: "What files or PR should I review?"

Scope the review to changed files only, but note systemic issues visible in context.

---

## Assessment area 1: Structural Integrity

*Source practices: CC-035 (DDD), CC-040 (POEAA/Fowler), CC-026 (GoF/Clean Code), CC-025 (Clean Code), CC-119/CC-151 (APoSD/Code Complete)*

### Practice 1 — Bounded Context Alignment (CC-035)

**What to assess:** Do the changed files respect domain boundaries? Look for domain model
objects crossing context lines without an Anti-Corruption Layer.

**Search signals:**
- Imports of domain entities from sibling service packages (e.g., `from order_service.models import User`)
- Shared mutable domain objects passed between bounded contexts
- Event payloads that expose internal aggregate state verbatim

**Verdict criteria:**

| Verdict | Condition |
|---------|-----------|
| PASS | Each bounded context owns its model; external integrations use ACLs, DTOs, or events with explicit translation |
| WARN | One model leaks into a neighbor context without translation but the coupling is read-only or tolerated temporarily |
| BLOCK | Core domain object (aggregate root, value object) imported directly across service boundaries, or two contexts share a mutable DB table without explicit ownership |

**Examples:**
- PASS: `OrderService` emits `OrderPlacedEvent` with a minimal payload; `NotificationService` maps it to its own `Notification` model in a translator class.
- WARN: `UserService` returns a `UserDTO` that includes `payment_method_id`, which `BillingService` reads but does not modify.
- BLOCK: `billing/models.py` imports `User` from `user_service/models.py` and calls `user.save()`.

---

### Practice 2 — Layer Separation (CC-040)

**What to assess:** Are presentation, domain/business logic, and data access layers distinct?
Look for HTTP handler code calling ORM queries directly, or domain models containing SQL.

**Search signals:**
- Route/controller files importing ORM models directly (no repository layer)
- Domain entities with `db.session`, `Connection`, or raw SQL strings
- Business logic embedded in serializers, validators, or view templates

**Verdict criteria:**

| Verdict | Condition |
|---------|-----------|
| PASS | Controller/handler delegates to service/domain layer; domain layer delegates to repository/DAO; no cross-layer direct access |
| WARN | Minor mixing (e.g., a single SQL query in a controller for a read-only view), isolated to one file |
| BLOCK | Business logic (calculations, invariant enforcement, state machines) lives in request handlers or ORM models; or persistence concerns appear in domain objects |

**Examples:**
- PASS: `POST /orders` handler calls `order_service.create_order(dto)` which calls `order_repo.save(aggregate)`.
- WARN: `GET /dashboard` handler runs `db.query("SELECT COUNT(*) FROM orders WHERE ...")` directly for a summary view.
- BLOCK: `Order` domain model has `def finalize(self): self.db.session.commit()` or `views.py` contains `if order.total > 100: apply_discount()`.

---

### Practice 3 — Dependency Direction (CC-026)

**What to assess:** Do dependencies point inward (toward domain/core), not outward?
High-level modules should not depend on low-level details.

**Search signals:**
- Domain/core packages importing from infrastructure, framework, or adapter packages
- Business logic classes taking concrete ORM models or HTTP clients as constructor args without interfaces
- Abstract policy modules importing concrete implementation modules

**Verdict criteria:**

| Verdict | Condition |
|---------|-----------|
| PASS | Domain layer imports only stdlib or other domain types; infrastructure implements interfaces defined in domain |
| WARN | One or two infrastructure types leak into domain (e.g., a `datetime` timezone util from a library), low blast radius |
| BLOCK | Domain/core module imports from `infrastructure/`, `adapters/`, `persistence/`, or a web framework package |

**Examples:**
- PASS: `PaymentProcessor` (domain) accepts `PaymentGateway` (interface defined in domain); `StripeAdapter` (infra) implements it.
- WARN: `OrderAggregateService` imports `pytz.utc` directly from pytz instead of a domain-defined timezone abstraction.
- BLOCK: `domain/order.py` imports `from sqlalchemy.orm import Session` or `from flask import request`.

---

### Practice 4 — Interface Segregation (CC-025)

**What to assess:** Are public interfaces narrow and focused, or do callers depend on methods
they do not use?

**Search signals:**
- Interfaces/ABCs/protocols with >7 methods serving heterogeneous callers
- Classes that implement large interfaces but leave many methods as `raise NotImplementedError`
- Single service class used as the dependency for >3 distinct consumer types with different usage patterns

**Verdict criteria:**

| Verdict | Condition |
|---------|-----------|
| PASS | Each interface serves one coherent caller type; no unused method implementations |
| WARN | Interface has a few extra methods that some callers never use, but all implementations are complete |
| BLOCK | Concrete classes stub out >30% of interface methods (`pass`, `raise NotImplementedError`, `return None`) because the interface is too wide |

**Examples:**
- PASS: `OrderReader` interface has `get_by_id` and `list_by_customer`; `OrderWriter` has `save` and `delete`. Read-only services depend only on `OrderReader`.
- WARN: `NotificationService` interface has 8 methods; `EmailNotifier` uses 7 but stubs `send_sms` with `pass`.
- BLOCK: `UserRepository` interface has 20 methods; `CachingUserRepo` stubs 12 as `raise NotImplementedError("not needed for cache layer")`.

---

### Practice 5 — Cohesion (CC-119, CC-151)

**What to assess:** Do modules group concepts that change together and serve the same purpose?
High cohesion within, low coupling between.

**Search signals:**
- Module/class mixes unrelated concerns (e.g., `UserManager` handles auth, profile, billing, and email)
- File size >500 lines and the class touches >3 distinct domain concepts
- Utility modules that have become dumping grounds (`helpers.py`, `utils.py` with >20 unrelated functions)

**Verdict criteria:**

| Verdict | Condition |
|---------|-----------|
| PASS | Each module/class has a clear, single purpose; name matches responsibility; callers can predict what lives where |
| WARN | Module is slightly overloaded but all methods relate to one domain area with minor stretches |
| BLOCK | "God class" or "god module" with unrelated responsibilities, or a class with >15 public methods spanning multiple domains |

**Examples:**
- PASS: `OrderFulfillmentService` handles order state transitions; payment concerns live in `PaymentService`.
- WARN: `ShippingService` also has `calculate_tax()` — tax belongs in billing, but it's a single method added for convenience.
- BLOCK: `UserService` class with methods: `authenticate`, `update_profile`, `send_welcome_email`, `charge_subscription`, `generate_report`, `export_to_csv` — six unrelated domains in one class.

---

## Assessment area 2: Resilience & Operations

*Source practices: Release It! (Nygard), DDIA (Kleppmann), SRE Book (Google)*

### Practice 6 — Circuit Breakers on External Dependencies

**What to assess:** Are calls to external services, databases, or third-party APIs wrapped in
circuit breakers or equivalent fault-isolation patterns?

**Search signals:**
- HTTP client calls without timeout + retry + circuit breaker config
- Direct `requests.get()`, `httpx.get()`, `fetch()` without a resilience wrapper
- Database connections without connection pool limits and timeout settings

**Verdict criteria:**

| Verdict | Condition |
|---------|-----------|
| PASS | External calls go through a circuit breaker library (e.g., `resilience4j`, `pybreaker`, `circuitbreaker`, or a service mesh policy); timeouts and retry budgets are explicitly configured |
| WARN | Timeouts set but no circuit breaker; or circuit breaker present but not all external calls are covered |
| BLOCK | Unbounded external calls with no timeout; or circuit breaker disabled/commented out in production path |

**Examples:**
- PASS: All calls to `PaymentGatewayClient` go through `@circuit(failure_threshold=5, recovery_timeout=30)`.
- WARN: `requests.get(url, timeout=5)` — timeout present but no circuit breaker; sustained failures will still cascade slowly.
- BLOCK: `response = requests.get(external_api_url)` — no timeout, no circuit breaker, no retry limit.

---

### Practice 7 — Bulkheads (Isolated Failure Domains)

**What to assess:** Are failure domains isolated so that one component's failure cannot exhaust
resources shared by healthy components?

**Search signals:**
- Single shared thread pool or connection pool for all downstream calls
- No queue depth limits or consumer group isolation between high-priority and low-priority workloads
- Async task queues without worker pool separation per task type

**Verdict criteria:**

| Verdict | Condition |
|---------|-----------|
| PASS | Critical and non-critical processing use separate thread/connection pools; queue consumers are partitioned by workload type |
| WARN | Partial isolation (e.g., separate pools for DB vs HTTP but batch and interactive share one pool) |
| BLOCK | All downstream calls share a single unbounded thread pool; or no concurrency limits on resource-intensive operations visible in the changed code |

**Examples:**
- PASS: `BatchProcessor` uses a `ThreadPoolExecutor(max_workers=4)` separate from the `RequestHandler`'s pool of 20.
- WARN: DB reads and DB writes share the same pool, but a critical writes-only pool is planned.
- BLOCK: `executor = ThreadPoolExecutor()` (unbounded) handles all tasks including slow external report generation and fast user-facing operations.

---

### Practice 8 — Explicit Consistency Model

**What to assess:** Has the code chosen and documented a consistency model? Distributed
systems must explicitly commit to strong, eventual, or causal consistency — not leave it
implicit.

**Search signals:**
- Multi-service writes without saga, two-phase commit, or event sourcing
- "Last write wins" semantics without documentation
- Read-your-writes concerns in user-facing flows that span services

**Verdict criteria:**

| Verdict | Condition |
|---------|-----------|
| PASS | Consistency model is documented (comment, ADR, or README); code matches the stated model (e.g., event-driven saga with compensating transactions) |
| WARN | Implicit eventual consistency that works in practice but is not documented; or one edge case with stale reads in a non-critical flow |
| BLOCK | Multi-entity writes across services with no coordination mechanism and user-visible inconsistency (e.g., order placed but inventory not decremented atomically, no saga or outbox pattern) |

**Examples:**
- PASS: `# This flow uses the Outbox pattern for eventual consistency. See ADR-012.` with corresponding `OutboxEvent` table writes in the same DB transaction.
- WARN: Cache-aside pattern used without documenting cache TTL or invalidation strategy; reads may be stale for up to 60s.
- BLOCK: `order_service.create_order()` calls `inventory_service.decrement_stock()` via HTTP with no rollback if inventory call fails.

---

### Practice 9 — Backpressure Mechanisms

**What to assess:** Are unbounded queues, buffers, or work acceptance loops protected against
producers outrunning consumers?

**Search signals:**
- `Queue()` or `asyncio.Queue()` without `maxsize`
- Message consumer loops without rate limiting or credit-based flow control
- Fan-out patterns where producer throughput is not bounded by consumer capacity

**Verdict criteria:**

| Verdict | Condition |
|---------|-----------|
| PASS | All queues have `maxsize` / capacity limits; producers shed load or apply backpressure when limit is hit; documented drop/reject strategy |
| WARN | Queues have limits but no documented behavior when full (unclear if blocking, dropping, or erroring) |
| BLOCK | `Queue()` with no size limit that accepts work from an unbounded source; or producer never checks consumer lag |

**Examples:**
- PASS: `work_queue = asyncio.Queue(maxsize=1000)`; producer does `await work_queue.put(item)` which blocks when full, applying backpressure to caller.
- WARN: `Queue(maxsize=500)` is set but `queue.put_nowait(item)` is used — items silently dropped when full with no metric or alert.
- BLOCK: `queue = Queue()` (no maxsize) in an event ingestion loop where producers run at arbitrary rate.

---

### Practice 10 — Health Checks and Graceful Shutdown

**What to assess:** Does the service expose liveness/readiness probes and handle shutdown
signals (SIGTERM) without dropping in-flight requests?

**Search signals:**
- No `/health`, `/healthz`, `/ready`, or `/ping` endpoint
- No SIGTERM handler; process exits immediately on `kill`
- Long-running tasks not drained before shutdown

**Verdict criteria:**

| Verdict | Condition |
|---------|-----------|
| PASS | Liveness and readiness endpoints exist and reflect actual dependency health (not just "return 200"); SIGTERM handler drains in-flight requests with bounded timeout |
| WARN | Health endpoint exists but returns static `{"status": "ok"}` regardless of dependency health; or shutdown drains but with no timeout (could hang forever) |
| BLOCK | No health endpoint at all; or SIGTERM causes immediate process exit while requests are in flight |

**Examples:**
- PASS: `/readiness` checks DB connection and cache reachability; `signal.signal(SIGTERM, graceful_shutdown)` stops accepting new connections and waits up to 30s for active requests to complete.
- WARN: `/health` returns `{"status": "ok"}` hardcoded — does not reflect DB or downstream service health.
- BLOCK: No health endpoint; Kubernetes marks pod healthy based on process running only; no SIGTERM handler.

---

## Assessment area 3: Evolutionary Design

*Source practices: How Buildings Learn (Brand, CC-098), Systemantics (Gall), Team Topologies (Skelton/Pais), CC-132 (ADR)*

### Practice 11 — Shearing Layers

**What to assess:** Are components that change at different rates separated from each other?
Brand's shearing layers: stuff (data/content) changes daily; space plan (services) changes
yearly; structure (platform/infra) changes over decades. Mixing them creates coupling debt.

**Search signals:**
- Business rules hardcoded in infrastructure config (e.g., pricing logic in Kubernetes env vars)
- Deployment artifacts that bundle application config with runtime secrets
- Data transformation logic embedded in schema migration files

**Verdict criteria:**

| Verdict | Condition |
|---------|-----------|
| PASS | Fast-changing concerns (feature flags, business rules, content) are externalized from slow-changing concerns (schema, infrastructure, platform dependencies) |
| WARN | One configuration value that changes frequently is hardcoded in a slow-changing layer, but it's isolated and low-risk |
| BLOCK | Business logic or frequently-changing rules are embedded in infrastructure definitions (Terraform, Helm charts, schema files) making them require infrastructure-level deployments for business changes |

**Examples:**
- PASS: `DISCOUNT_RULES` fetched from a feature flag service at runtime; schema only tracks `discount_applied: bool`, not the rules.
- WARN: Maximum retry count (changes occasionally) is hardcoded in a Helm values file instead of an application config.
- BLOCK: Tax calculation logic (changes quarterly with tax law) is embedded in a database migration file as a stored procedure.

---

### Practice 12 — Start Simple, Evolve (Gall's Law)

**What to assess:** Is new complexity being added on top of a working simple foundation, or is
a complex system being designed from scratch? Gall's Law: complex systems that work evolved
from simple systems that worked.

**Search signals:**
- Large PRs introducing microservice meshes, distributed transactions, or event sourcing from day one without prior simpler implementation
- "Future-proofing" abstractions with no current consumers (interfaces with one implementation, abstract factories for one product)
- New services designed for horizontal scale before any load has been measured

**Verdict criteria:**

| Verdict | Condition |
|---------|-----------|
| PASS | Change extends a working system incrementally; new abstractions have at least two concrete consumers; complexity is justified by current requirements |
- WARN | One speculative abstraction layer added, but it's small and doesn't block the simple path |
| BLOCK | New system designed with full distributed architecture (sagas, CQRS, event sourcing, service mesh) before the monolith/simple version was validated; OR abstraction layers with zero concrete consumers |

**Examples:**
- PASS: Adds second `PaymentProvider` implementation after the first (`StripeProvider`) was in production for 6 months, retroactively extracting the interface.
- WARN: Adds a `NotificationStrategy` interface with one implementation (`EmailNotification`) because a second channel "might be needed."
- BLOCK: New service introduced with full CQRS + event sourcing + saga orchestrator for a feature with 10 users/day and no performance baseline.

---

### Practice 13 — Cognitive Load per Team

**What to assess:** Is the cognitive load of the changed component manageable for the team
that will own it? Team Topologies: teams can own what they can hold in their heads.

**Search signals:**
- Service or module touching >5 distinct domains (auth, billing, notifications, reporting, analytics)
- PR that requires understanding 4+ other services to review
- Shared library owned by no specific team with responsibilities spanning the entire platform

**Verdict criteria:**

| Verdict | Condition |
|---------|-----------|
| PASS | A single team could understand and on-call the changed component without deep knowledge of other systems; component has a clear owner |
| WARN | Component requires understanding 2-3 upstream/downstream systems to operate safely; ownership is clear but the blast radius of changes is wide |
| BLOCK | No team can reasonably own the component as designed (spans too many domains); or a "platform team" is being asked to own application-level business logic |

**Examples:**
- PASS: `ShippingService` owns shipping rate calculation and carrier integration; 3 engineers can be on-call for it.
- WARN: `OrderOrchestrationService` coordinates 5 services and requires knowing the failure modes of all 5; manageable with a senior engineer on-call.
- BLOCK: `PlatformIntegrationService` owns auth, billing, shipping, notifications, and reporting — no team can reason about all of this simultaneously.

---

### Practice 14 — API Versioning and Backward Compatibility

**What to assess:** Are public API contracts versioned and backward-compatible? Breaking
changes must be detected and explicitly versioned.

**Search signals:**
- New required fields added to existing API request/response without a version bump
- Existing API response fields removed or renamed without deprecation period
- Enum values removed from API responses
- Proto/Avro/JSON schema files changed without backward compatibility analysis

**Verdict criteria:**

| Verdict | Condition |
|---------|-----------|
| PASS | Breaking changes go through a new API version (v2 endpoint or field addition without removal); deprecated fields marked with removal timeline; consumers notified |
| WARN | New optional fields added to responses (backward compatible) but not documented; or deprecation annotation present but no removal timeline |
| BLOCK | Required field added to request, existing field removed from response, or enum value removed — any of these without a new version |

**Examples:**
- PASS: `/api/v2/orders` introduced with new required `tax_breakdown` field; `/api/v1/orders` continues to work unchanged with a deprecation header.
- WARN: New `metadata` field added to response — backward compatible, but no API changelog entry and no documentation update.
- BLOCK: `user_name` field renamed to `username` in `/api/v1/users` response — existing clients break silently.

---

### Practice 15 — ADR for Significant Decisions (CC-132)

**What to assess:** Have significant architectural decisions been captured in Architecture
Decision Records (ADRs)? Significant = affects multiple teams, introduces a new dependency
category, or constrains future options.

**Search signals:**
- New database technology, message broker, or framework introduced without an ADR in `docs/adr/`, `architecture/decisions/`, or similar
- Service split or merge without documented rationale
- Consistency model choice (see Practice 8) without documented reasoning

**Verdict criteria:**

| Verdict | Condition |
|---------|-----------|
| PASS | ADR exists for the decision, is linked in the PR description, and follows a recognizable format (context / decision / consequences) |
| WARN | Decision is significant but ADR is in draft, missing consequences section, or not linked from PR description |
| BLOCK | Irreversible decision (new DB technology, service split, API contract change) with no ADR and no documented rationale anywhere |

**Examples:**
- PASS: PR adds Kafka for async messaging; `docs/adr/ADR-019-kafka-for-event-streaming.md` is linked in PR description with context, decision, and trade-offs.
- WARN: PR introduces Redis for caching; ADR-022 exists but only has a title and context, no decision or consequences written yet.
- BLOCK: PR migrates from PostgreSQL to DynamoDB with no ADR and only a Slack message as the decision record.

---

## Assessment output format

After evaluating all 15 practices, produce this exact output structure:

```markdown
## Design Review — [PR title or component name]

**Scope**: [files reviewed, e.g., "23 changed files: src/services/**, migrations/**, api/**"]
**Date**: [current date]

### Structural Integrity

| # | Practice | Status | Notes |
|---|----------|--------|-------|
| 1 | Bounded Context Alignment | PASS / WARN / BLOCK / N/A | [one-line finding with file:line if WARN/BLOCK] |
| 2 | Layer Separation | ... | ... |
| 3 | Dependency Direction | ... | ... |
| 4 | Interface Segregation | ... | ... |
| 5 | Cohesion | ... | ... |

### Resilience & Operations

| # | Practice | Status | Notes |
|---|----------|--------|-------|
| 6  | Circuit Breakers | ... | ... |
| 7  | Bulkheads | ... | ... |
| 8  | Explicit Consistency Model | ... | ... |
| 9  | Backpressure | ... | ... |
| 10 | Health Checks + Graceful Shutdown | ... | ... |

### Evolutionary Design

| # | Practice | Status | Notes |
|---|----------|--------|-------|
| 11 | Shearing Layers | ... | ... |
| 12 | Start Simple / Gall's Law | ... | ... |
| 13 | Cognitive Load per Team | ... | ... |
| 14 | API Versioning / Backward Compatibility | ... | ... |
| 15 | ADR for Significant Decisions | ... | ... |

---

### Score

| Verdict | Count |
|---------|-------|
| PASS    | [n]   |
| WARN    | [n]   |
| BLOCK   | [n]   |
| N/A     | [n]   |

**Score**: [PASS*100 + WARN*50] / [(15 - N/A) * 100] * 100 = [XX]%

---

### Overall Recommendation

**[APPROVE / REQUEST_CHANGES / BLOCK]**

- **Blocking issues** ([n]): [list each BLOCK finding in one line each]
- **Warnings** ([n]): [list each WARN finding in one line each]
- **Approval path**: [what must change before this can merge; "None — approve as-is" if 0 BLOCKs]
```

**Recommendation rules:**
- `BLOCK` (do not merge): any practice has BLOCK verdict
- `REQUEST_CHANGES` (revise before merge): any practice has WARN verdict and no BLOCKs
- `APPROVE`: all practices are PASS or N/A

---

## Assessment rules (iron law)

1. **Evidence required for WARN and BLOCK.** You may only mark WARN or BLOCK if you can cite
   a specific `file:line` or name a specific pattern found. "Might be a problem" or "could
   happen" does not qualify. If you cannot find evidence, mark PASS with a note explaining
   what you looked for.

2. **N/A is a valid verdict.** Mark N/A when the practice genuinely does not apply:
   - Practice 6 (Circuit Breakers): N/A if the service has no external dependencies
   - Practice 8 (Consistency Model): N/A if the service is stateless and writes to no store
   - Practice 14 (API Versioning): N/A if the service has no public API (internal only, no SLA)
   - Practice 15 (ADR): N/A if the PR is a bugfix or refactor with no architectural decisions

3. **BLOCK is not a judgment call.** Each practice defines exact BLOCK conditions. Do not
   escalate a WARN to BLOCK because the code is "bad in spirit." Follow the criteria.

4. **Scope to changed files.** If a practice is violated in unchanged legacy code that the PR
   does not touch, note it as a pre-existing finding (suffix with `[pre-existing]`) — it does
   not count as a BLOCK for this PR.

5. **Falsifiability.** A theoretical risk is not a defect. A defect is a specific file and
   line where the violation is concretely present.

---

## Search protocol

For each practice, perform these searches in order, stopping when you find definitive evidence:

1. **Primary search**: grep for the most specific signal (e.g., `grep -r "requests.get" --include="*.py"`)
2. **Framework search**: check the detected framework's idiomatic patterns (e.g., Django views vs Flask routes vs FastAPI)
3. **Structural search**: read key architectural files directly (e.g., `__init__.py`, `app.py`, `main.py`, service entry points)

Document all three searches in your evidence for WARN/BLOCK verdicts.

---

## Scope and limitations

This skill evaluates the **15 Tier 2 architecture practices** listed above. It does not:

- Evaluate Tier 1 practices (handled by pre-commit linters)
- Evaluate Tier 3 practices (handled by CLAUDE.md guidance)
- Run automated tests or performance benchmarks
- Replace a human architecture review for systems affecting >10 services or handling PII/financial data

For large-scale architecture reviews (new service, platform migration, major API redesign),
use this skill as a first pass, then escalate to a synchronous human design session.
