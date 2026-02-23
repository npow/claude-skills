# Production Readiness Checks

All 24 checks organized by category. Each check defines what to look for, why it matters, and severity.

## Contents
- Reliability (checks 1-6)
- Observability (checks 7-11)
- Security (checks 12-17)
- Operations (checks 18-24)

---

## Category: Reliability

### Check 1: Health Check Endpoints

**What**: HTTP endpoint(s) that report application health — liveness (is the process alive?) and readiness (can it serve traffic?).
**Why**: Load balancers and orchestrators use these to route traffic and restart unhealthy instances.
**Severity**: Critical
**Look for**:
- Route definitions for `/health`, `/healthz`, `/ready`, `/readiness`, `/liveness`, `/actuator/health`
- Health check libraries or middleware (e.g., `@godaddy/terminus`, Spring Actuator, `healthcheck` packages)
- Kubernetes probe configs in deployment manifests

**PASS**: At least one health endpoint exists.
**WARN**: Health endpoint exists but only returns static 200 (no dependency checks).
**FAIL**: No health endpoint found.

### Check 2: Graceful Shutdown

**What**: Process handles SIGTERM/SIGINT by draining in-flight requests before exiting.
**Why**: Hard kills drop active requests and corrupt in-progress operations.
**Severity**: Critical
**Look for**:
- Signal handlers for `SIGTERM`, `SIGINT`, `SHUTDOWN`
- Server `.close()` or `.shutdown()` calls
- Framework shutdown hooks (`@PreDestroy`, `atexit`, `app.on('close')`, `shutdown_event`)
- Drain/grace period configuration

**PASS**: Signal handler drains connections before exit.
**WARN**: Signal handler exists but no drain logic.
**FAIL**: No shutdown handling found.

### Check 3: Circuit Breakers

**What**: Pattern that stops calling a failing downstream service after repeated failures, allowing it to recover.
**Why**: Prevents cascade failures where one degraded service brings down the entire system.
**Severity**: High
**Look for**:
- Circuit breaker libraries (`resilience4j`, `opossum`, `pybreaker`, `gobreaker`, `hystrix`)
- Custom implementations with states: CLOSED, OPEN, HALF_OPEN
- Retry-with-circuit-break patterns

**PASS**: Circuit breaker wraps at least one external call.
**WARN**: Retry logic exists but no circuit breaker.
**FAIL**: No circuit breaker pattern found.

### Check 4: Retry Policies

**What**: Automatic retries for transient failures with exponential backoff and jitter.
**Why**: Transient network errors are common; retries without backoff cause thundering herds.
**Severity**: High
**Look for**:
- Retry libraries (`resilience4j-retry`, `async-retry`, `tenacity`, `retry`, `backoff`)
- Exponential backoff configuration (base delay, max delay, multiplier)
- Jitter configuration
- Max retry count limits
- Custom retry loops with delay

**PASS**: Retries with backoff configured for external calls.
**WARN**: Retries exist but no backoff or jitter.
**FAIL**: No retry logic found.

### Check 5: Timeouts

**What**: Explicit timeouts on all external calls (HTTP, database, cache, message queue).
**Why**: Missing timeouts cause thread/connection exhaustion when a downstream hangs.
**Severity**: Critical
**Look for**:
- HTTP client timeout config (`connectTimeout`, `readTimeout`, `timeout`, `requestTimeout`)
- Database connection timeout (`connectionTimeout`, `statement_timeout`, `query_timeout`)
- Socket/TCP timeout settings
- gRPC deadline configuration

**PASS**: Timeouts configured on HTTP clients, DB connections, and any other external calls.
**WARN**: Timeouts on some but not all external call types.
**FAIL**: No explicit timeout configuration found.

### Check 6: Connection Pooling

**What**: Reuse of connections to databases, caches, and external services via pools.
**Why**: Creating connections per-request is slow and exhausts OS resources under load.
**Severity**: Medium
**Look for**:
- Database pool config (`HikariCP`, `pgBouncer`, `pool_size`, `maxPoolSize`, `sqlalchemy pool`)
- HTTP connection pool (`keepAlive`, `maxSockets`, `pool_connections`, `connection_pool_size`)
- Redis/cache pool configuration
- Pool size limits and idle timeout settings

**PASS**: Connection pools configured with explicit size limits.
**WARN**: Default pooling from framework with no explicit tuning.
**FAIL**: No connection pooling evidence; connections created per-request.

---

## Category: Observability

### Check 7: Structured Logging

**What**: Log output in a machine-parseable format (JSON) with consistent fields (timestamp, level, message, correlation_id).
**Why**: Unstructured logs are unsearchable at scale and break log aggregation pipelines.
**Severity**: High
**Look for**:
- JSON log formatters (`logback-json`, `winston json`, `structlog`, `zap`, `slog`, `bunyan`)
- Log configuration files (`logback.xml`, `log4j2.xml`, `winston config`, `logging.config`)
- Structured fields: `timestamp`, `level`, `message`, `trace_id`, `span_id`
- Log library initialization with format config

**PASS**: Structured (JSON) logging configured with standard fields.
**WARN**: Logging exists but uses plaintext format.
**FAIL**: No logging configuration found.

### Check 8: Metrics / Instrumentation

**What**: Application exports numeric measurements (request count, latency, error rate, queue depth).
**Why**: Metrics enable alerting, capacity planning, and performance debugging.
**Severity**: High
**Look for**:
- Metrics libraries (`micrometer`, `prometheus-client`, `prom-client`, `statsd`, `spectator`, `opentelemetry`)
- Custom metric definitions (`Counter`, `Histogram`, `Gauge`, `Timer`, `Summary`)
- Metrics endpoint (`/metrics`, `/actuator/prometheus`)
- Metric tags/labels for dimensionality

**PASS**: Metrics library configured with custom application metrics.
**WARN**: Metrics library present but only default/auto metrics (no custom).
**FAIL**: No metrics instrumentation found.

### Check 9: Distributed Tracing

**What**: Request flows are traced across service boundaries with trace IDs and spans.
**Why**: Without tracing, debugging cross-service latency or errors requires log correlation guesswork.
**Severity**: Medium
**Look for**:
- Tracing libraries (`opentelemetry`, `jaeger-client`, `zipkin`, `dd-trace`, `aws-xray`, `sleuth`)
- Trace context propagation (`traceparent`, `X-Request-Id`, `X-Correlation-Id`, `b3`)
- Span creation and annotation
- Trace exporter configuration

**PASS**: Tracing SDK configured with context propagation.
**WARN**: Correlation IDs exist but no distributed tracing SDK.
**FAIL**: No tracing or correlation ID propagation found.

### Check 10: Monitoring / Alerting Configuration

**What**: Alerts defined for key indicators (error rate spike, latency P99, disk usage, queue backlog).
**Why**: Metrics without alerts means nobody gets paged when things break at 3 AM.
**Severity**: High
**Look for**:
- Alert rule files (Prometheus `rules.yml`, Grafana alert JSON, Datadog monitors, PagerDuty config)
- Alert-as-code definitions (`terraform`, `pulumi`, `cloudformation` alert resources)
- SLO/SLI definitions
- On-call or escalation configuration files

**PASS**: Alert rules defined in config files for key metrics.
**WARN**: Monitoring dashboards exist but no alert rules in code.
**FAIL**: No alerting configuration found in the codebase.

### Check 11: Error Tracking

**What**: Unhandled exceptions and errors are captured and reported to an error tracking service.
**Why**: Errors in logs get buried. Dedicated error tracking deduplicates, groups, and alerts on new issues.
**Severity**: Medium
**Look for**:
- Error tracking SDKs (`sentry`, `bugsnag`, `rollbar`, `airbrake`, `honeybadger`, `raygun`)
- Global error handlers that report upstream
- DSN/API key configuration for error services
- Source map upload configuration (for JS)

**PASS**: Error tracking SDK initialized with global error handler.
**WARN**: Global error handler exists but no external error tracking service.
**FAIL**: No error tracking or global error handler found.

---

## Category: Security

### Check 12: Input Validation

**What**: All external input (HTTP body, query params, headers, file uploads) is validated before processing.
**Why**: Unvalidated input is the root cause of injection, XSS, and data corruption.
**Severity**: Critical
**Look for**:
- Validation libraries (`joi`, `zod`, `class-validator`, `pydantic`, `marshmallow`, `javax.validation`, `Bean Validation`)
- Schema validation on API endpoints
- Request body parsing with validation (not just `JSON.parse`)
- File upload size/type restrictions

**PASS**: Validation library used on API request handlers.
**WARN**: Some endpoints validated, others accept raw input.
**FAIL**: No input validation library or schema validation found.

### Check 13: Secrets Management

**What**: Secrets (API keys, database passwords, tokens) are loaded from a vault or environment, never hardcoded.
**Why**: Hardcoded secrets in source control are the #1 credential leak vector.
**Severity**: Critical
**Look for**:
- Environment variable usage for secrets (`process.env`, `os.environ`, `System.getenv`)
- Vault integration (`hashicorp vault`, `aws secretsmanager`, `gcp secret manager`, `azure keyvault`)
- `.env` files listed in `.gitignore`
- Hardcoded strings that look like keys/tokens/passwords (anti-pattern to flag)

**PASS**: Secrets loaded from environment or vault; no hardcoded credentials detected.
**WARN**: Environment variables used but `.env` not in `.gitignore`, or vault not used.
**FAIL**: Hardcoded secrets detected in source files.

### Check 14: Security Headers

**What**: HTTP responses include security headers (HSTS, CSP, X-Content-Type-Options, X-Frame-Options).
**Why**: Missing headers enable clickjacking, MIME sniffing, and downgrade attacks.
**Severity**: Medium
**Look for**:
- Helmet (Node.js), `django-secure`, Spring Security headers config
- Manual header setting: `Strict-Transport-Security`, `Content-Security-Policy`, `X-Content-Type-Options`
- Reverse proxy config (nginx, Caddy) with security headers
- OWASP header recommendations

**PASS**: Security header middleware or explicit header configuration found.
**WARN**: Some headers set but not a complete set (missing HSTS or CSP).
**FAIL**: No security headers configured.

### Check 15: CORS Configuration

**What**: Cross-Origin Resource Sharing is explicitly configured (not wildcard `*` in production).
**Why**: Wildcard CORS allows any website to make authenticated requests to your API.
**Severity**: Medium
**Look for**:
- CORS middleware configuration (`cors()`, `@CrossOrigin`, `CorsMiddleware`)
- Allowed origins list (should be explicit domains, not `*`)
- CORS in reverse proxy config
- Preflight request handling

**PASS**: CORS configured with explicit allowed origins.
**WARN**: CORS configured but uses wildcard `*` origin.
**FAIL**: No CORS configuration found (relevant for APIs serving browsers).

### Check 16: TLS / SSL

**What**: All external communication uses TLS. Internal service-to-service may use mTLS.
**Why**: Plaintext traffic is interceptable and violates compliance requirements.
**Severity**: High
**Look for**:
- TLS certificate configuration in server setup
- HTTPS-only listeners or redirect rules
- mTLS configuration for service mesh
- `ssl: true` or `tls: true` in client configurations
- Certificate paths in config files

**PASS**: TLS configured for server and/or enforced via infrastructure.
**WARN**: TLS present but HTTP still accepted (no redirect).
**FAIL**: No TLS configuration; server listens on HTTP only.

### Check 17: Dependency Vulnerability Scanning

**What**: Dependencies are scanned for known vulnerabilities as part of the build or CI pipeline.
**Why**: Vulnerable transitive dependencies are the most common attack surface in modern apps.
**Severity**: High
**Look for**:
- Scanning tools in CI config (`npm audit`, `snyk`, `trivy`, `grype`, `safety`, `dependabot`, `renovate`)
- GitHub Dependabot config (`.github/dependabot.yml`)
- Lock files present (`package-lock.json`, `yarn.lock`, `Gemfile.lock`, `poetry.lock`, `go.sum`)
- SBOM generation

**PASS**: Vulnerability scanning configured in CI or as a pre-commit hook.
**WARN**: Lock files present but no automated scanning configured.
**FAIL**: No lock files and no vulnerability scanning.

---

## Category: Operations

### Check 18: Container Health Probes

**What**: Dockerfile or orchestrator config defines health checks (liveness, readiness, startup probes).
**Why**: Container orchestrators need probe config to manage rolling deploys and self-healing.
**Severity**: High
**Look for**:
- Dockerfile `HEALTHCHECK` instruction
- Kubernetes `livenessProbe`, `readinessProbe`, `startupProbe` in deployment YAML
- Docker Compose `healthcheck` section
- ECS task definition health check
- Probe paths, intervals, thresholds

**PASS**: Health probes defined in container/orchestrator config.
**WARN**: Health endpoint exists in code but no probe config in deployment manifests.
**FAIL**: No container health probes configured.

### Check 19: Resource Limits

**What**: Container or process resource limits (CPU, memory) are explicitly set.
**Why**: Unbounded containers steal resources from neighbors and OOM-kill unpredictably.
**Severity**: High
**Look for**:
- Kubernetes `resources.limits` and `resources.requests` in deployment YAML
- Docker `--memory`, `--cpus` flags or Compose `mem_limit`/`cpus`
- JVM heap settings (`-Xmx`, `-Xms`)
- Node.js `--max-old-space-size`
- Process manager limits (systemd `MemoryMax`)

**PASS**: Resource limits defined in deployment config.
**WARN**: JVM/runtime memory set but no container-level limits.
**FAIL**: No resource limits found.

### Check 20: Database Migrations

**What**: Database schema changes are managed through versioned migration files.
**Why**: Manual schema changes cause drift between environments and are unrecoverable.
**Severity**: Medium
**Look for**:
- Migration tools (`flyway`, `liquibase`, `alembic`, `knex migrate`, `prisma migrate`, `django migrations`, `goose`, `dbmate`)
- Migration files directory (`migrations/`, `db/migrate/`, `src/main/resources/db/migration/`)
- Migration configuration in build files
- Schema versioning

**PASS**: Migration tool configured with versioned migration files present.
**WARN**: Migration tool in dependencies but no migration files found.
**FAIL**: Database access present but no migration tooling.
**N/A**: No database access detected.

### Check 21: Graceful Degradation / Fallbacks

**What**: When a dependency fails, the system returns a degraded response instead of a hard error.
**Why**: Users prefer stale data or reduced features over error pages.
**Severity**: Medium
**Look for**:
- Fallback handlers in circuit breaker config
- Cache-based fallbacks (`stale-while-revalidate`, fallback to cache on error)
- Feature flags / kill switches (`LaunchDarkly`, `unleash`, `flagsmith`, `split`)
- Default response patterns when dependencies are unavailable

**PASS**: Fallback logic defined for at least one critical dependency.
**WARN**: Caching exists but no explicit fallback-on-error pattern.
**FAIL**: No fallback or degradation patterns found.

### Check 22: API Versioning

**What**: API endpoints are versioned to allow non-breaking evolution.
**Why**: Unversioned APIs force all clients to upgrade simultaneously or break.
**Severity**: Medium
**Look for**:
- URL path versioning (`/v1/`, `/v2/`, `/api/v1/`)
- Header-based versioning (`Accept: application/vnd.api+json;version=1`)
- API version in OpenAPI/Swagger spec
- Version negotiation middleware

**PASS**: API versioning strategy evident in routes or spec.
**WARN**: Version appears in some routes but not consistently applied.
**FAIL**: No API versioning found.
**N/A**: Not an API service (CLI tool, library, etc.).

### Check 23: Rate Limiting

**What**: Incoming requests are rate-limited to prevent abuse and protect capacity.
**Why**: Without rate limits, a single client can overwhelm the service.
**Severity**: Medium
**Look for**:
- Rate limiting middleware (`express-rate-limit`, `ratelimit`, `django-ratelimit`, `bucket4j`, `golang.org/x/time/rate`)
- API gateway rate limit config (Kong, nginx `limit_req`, AWS API Gateway throttling)
- Token bucket or sliding window implementations
- Rate limit headers in responses (`X-RateLimit-Limit`, `Retry-After`)

**PASS**: Rate limiting configured at application or gateway level.
**WARN**: Rate limit library in dependencies but no configuration found.
**FAIL**: No rate limiting found.

### Check 24: Documentation

**What**: API documentation exists (OpenAPI spec, README with endpoints, generated docs).
**Why**: Undocumented APIs are unusable by other teams and become tribal knowledge.
**Severity**: Low
**Look for**:
- OpenAPI/Swagger spec files (`openapi.yaml`, `swagger.json`, `openapi.json`)
- API doc generators (`springdoc`, `swagger-ui`, `redoc`, `drf-spectacular`)
- README with API endpoint descriptions
- Postman/Insomnia collection files
- GraphQL schema with descriptions

**PASS**: API spec file or generated documentation present.
**WARN**: README describes endpoints but no formal spec.
**FAIL**: No API documentation found.
**N/A**: Not an API service.
