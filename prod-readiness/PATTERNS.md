# Framework-Specific Search Patterns

Detection patterns organized by stack. For each check, use patterns in this order: primary (generic), framework-specific, broad fallback.

## Contents
- Project type detection
- Java / Spring Boot patterns
- Node.js / Express / Fastify patterns
- Python / Flask / FastAPI / Django patterns
- Go patterns
- Rust patterns
- Container / Infrastructure patterns

---

## Project Type Detection

Scan the project root to identify the stack. Check these files in order:

| File | Stack indicator |
|------|----------------|
| `pom.xml`, `build.gradle`, `build.gradle.kts` | Java (check for Spring Boot, Micronaut, Quarkus) |
| `package.json` | Node.js (check deps for express, fastify, nestjs, koa, hapi) |
| `pyproject.toml`, `setup.py`, `requirements.txt` | Python (check for flask, fastapi, django, tornado) |
| `go.mod` | Go (check for gin, echo, fiber, chi, net/http) |
| `Cargo.toml` | Rust (check for actix, axum, rocket, warp) |
| `Dockerfile`, `docker-compose.yml` | Container tooling |
| `*.yaml`/`*.yml` in k8s/, deploy/, manifests/ | Kubernetes |
| `.github/workflows/*.yml` | GitHub Actions CI |
| `Jenkinsfile` | Jenkins CI |
| `spinnaker/`, `*.spinnaker.yml` | Spinnaker deployment |

---

## Java / Spring Boot

### Health Checks
- **Primary**: Grep for `actuator`, `/health`, `HealthIndicator`, `HealthContributor`
- **Framework**: Grep for `spring-boot-starter-actuator` in `build.gradle`/`pom.xml`; `management.endpoints.web.exposure.include` in `application.yml`/`application.properties`
- **Fallback**: Grep for `@GetMapping.*health` or `@RequestMapping.*health`

### Graceful Shutdown
- **Primary**: Grep for `server.shutdown=graceful`, `setRegisterShutdownHook`, `@PreDestroy`
- **Framework**: Grep for `spring.lifecycle.timeout-per-shutdown-phase` in properties/yaml
- **Fallback**: Grep for `Runtime.getRuntime().addShutdownHook`, `SIGTERM`

### Circuit Breakers
- **Primary**: Grep for `resilience4j`, `CircuitBreaker`, `@CircuitBreaker`
- **Framework**: Grep for `resilience4j-circuitbreaker` in build files; `CircuitBreakerConfig`
- **Fallback**: Grep for `hystrix`, `HystrixCommand`, `OPEN.*CLOSED.*HALF_OPEN`

### Retry Policies
- **Primary**: Grep for `@Retry`, `RetryTemplate`, `resilience4j-retry`
- **Framework**: Grep for `spring-retry`, `RetryConfig`, `maxAttempts`, `waitDuration`
- **Fallback**: Grep for `backoff`, `exponentialBackoff`, `maxRetries`

### Timeouts
- **Primary**: Grep for `connectTimeout`, `readTimeout`, `Duration.ofSeconds`, `Duration.ofMillis`
- **Framework**: Grep for `WebClient.*timeout`, `RestTemplate.*timeout`, `spring.datasource.hikari.connection-timeout`
- **Fallback**: Grep for `timeout` in `application.yml`/`application.properties`

### Connection Pooling
- **Primary**: Grep for `HikariCP`, `hikari`, `maximumPoolSize`, `connectionPool`
- **Framework**: Grep for `spring.datasource.hikari` in properties; `PoolingHttpClientConnectionManager`
- **Fallback**: Grep for `pool_size`, `maxPoolSize`, `poolSize`

### Structured Logging
- **Primary**: Grep for `logback`, `log4j2`, `JsonLayout`, `LogstashEncoder`
- **Framework**: Grep for `logback-spring.xml`, `net.logstash.logback` in build files
- **Fallback**: Grep for `MDC`, `StructuredArgument`, `kv(`, `keyValue(`

### Metrics
- **Primary**: Grep for `micrometer`, `MeterRegistry`, `@Timed`, `Counter.builder`
- **Framework**: Grep for `spring-boot-starter-actuator`, `management.metrics` in properties
- **Fallback**: Grep for `prometheus`, `spectator`, `statsd`

### Input Validation
- **Primary**: Grep for `@Valid`, `@Validated`, `ConstraintViolation`, `javax.validation`, `jakarta.validation`
- **Framework**: Grep for `spring-boot-starter-validation` in build files
- **Fallback**: Grep for `@NotNull`, `@NotBlank`, `@Size`, `@Pattern`, `@Min`, `@Max`

---

## Node.js / Express / Fastify

### Health Checks
- **Primary**: Grep for `/health`, `/healthz`, `/ready`, `healthCheck`
- **Framework**: Grep for `@godaddy/terminus`, `lightship`, `express-healthcheck`
- **Fallback**: Grep for `app.get.*health` or `router.get.*health`

### Graceful Shutdown
- **Primary**: Grep for `SIGTERM`, `SIGINT`, `process.on`
- **Framework**: Grep for `terminus`, `stoppable`, `server.close`, `http-terminator`
- **Fallback**: Grep for `beforeExit`, `shutdown`, `graceful`

### Circuit Breakers
- **Primary**: Grep for `opossum`, `circuitBreaker`, `CircuitBreaker`
- **Framework**: Grep for `cockatiel`, `brakes`, `circuit-breaker-js`
- **Fallback**: Grep for `OPEN`, `HALF_OPEN`, `CLOSED` used together

### Retry Policies
- **Primary**: Grep for `async-retry`, `p-retry`, `retry`, `got.*retry`
- **Framework**: Grep for `axios-retry`, `cockatiel.*retry`, `fetch-retry`
- **Fallback**: Grep for `backoff`, `exponential`, `maxRetries`, `retryDelay`

### Timeouts
- **Primary**: Grep for `timeout`, `AbortController`, `AbortSignal.timeout`
- **Framework**: Grep for `server.timeout`, `server.keepAliveTimeout`, `requestTimeout`
- **Fallback**: Grep for `setTimeout` used with HTTP/DB calls, `connectTimeout`

### Connection Pooling
- **Primary**: Grep for `pool`, `createPool`, `Pool`, `maxConnections`
- **Framework**: Grep for `pg.*Pool`, `mysql2.*createPool`, `generic-pool`, `ioredis`
- **Fallback**: Grep for `keepAlive`, `maxSockets`, `agent.*maxSockets`

### Structured Logging
- **Primary**: Grep for `winston`, `pino`, `bunyan`, `structlog`
- **Framework**: Grep for `winston.createLogger`, `pino()`, `format.json`, `format: 'json'`
- **Fallback**: Grep for `JSON.stringify` in logging context, `log.*json`

### Metrics
- **Primary**: Grep for `prom-client`, `prometheus`, `Histogram`, `Counter`
- **Framework**: Grep for `express-prometheus-middleware`, `fastify-metrics`
- **Fallback**: Grep for `statsd`, `datadog`, `metrics`, `/metrics`

### Input Validation
- **Primary**: Grep for `joi`, `zod`, `yup`, `class-validator`, `ajv`
- **Framework**: Grep for `celebrate`, `express-validator`, `fastify-type-provider-zod`
- **Fallback**: Grep for `.validate(`, `.parse(`, `schema.validate`

---

## Python / Flask / FastAPI / Django

### Health Checks
- **Primary**: Grep for `/health`, `/healthz`, `health_check`, `healthcheck`
- **Framework**: Grep for `django-health-check`, `flask-healthz`, `@app.get.*health` (FastAPI)
- **Fallback**: Grep for `def health`, `def readiness`, `def liveness`

### Graceful Shutdown
- **Primary**: Grep for `signal.signal`, `SIGTERM`, `SIGINT`, `atexit`
- **Framework**: Grep for `shutdown_event` (FastAPI), `@app.teardown_appcontext` (Flask), `gunicorn.*graceful_timeout`
- **Fallback**: Grep for `sys.exit`, `shutdown`, `cleanup`

### Circuit Breakers
- **Primary**: Grep for `pybreaker`, `circuitbreaker`, `CircuitBreaker`
- **Framework**: Grep for `aiobreaker`, `tenacity.*stop_after`
- **Fallback**: Grep for `circuit`, `breaker`, `OPEN.*CLOSED`

### Retry Policies
- **Primary**: Grep for `tenacity`, `retry`, `backoff`, `@retry`
- **Framework**: Grep for `urllib3.util.retry`, `requests.adapters.HTTPAdapter`, `aiohttp_retry`
- **Fallback**: Grep for `max_retries`, `backoff_factor`, `exponential`

### Timeouts
- **Primary**: Grep for `timeout`, `connect_timeout`, `read_timeout`
- **Framework**: Grep for `requests.get.*timeout`, `aiohttp.*timeout`, `httpx.*timeout`
- **Fallback**: Grep for `socket.setdefaulttimeout`, `statement_timeout`

### Connection Pooling
- **Primary**: Grep for `pool_size`, `max_overflow`, `pool_recycle`, `create_engine`
- **Framework**: Grep for `sqlalchemy.*pool`, `psycopg2.*pool`, `django.*CONN_MAX_AGE`
- **Fallback**: Grep for `Pool`, `ConnectionPool`, `pool`

### Structured Logging
- **Primary**: Grep for `structlog`, `python-json-logger`, `json_formatter`
- **Framework**: Grep for `structlog.configure`, `JsonFormatter`, `pythonjsonlogger`
- **Fallback**: Grep for `logging.config`, `dictConfig`, `json.*format`

### Metrics
- **Primary**: Grep for `prometheus_client`, `prometheus-client`, `spectator`
- **Framework**: Grep for `starlette-prometheus`, `django-prometheus`, `flask-prometheus`
- **Fallback**: Grep for `Counter`, `Histogram`, `Gauge`, `statsd`, `datadog`

### Input Validation
- **Primary**: Grep for `pydantic`, `marshmallow`, `cerberus`, `voluptuous`
- **Framework**: Grep for `BaseModel` (Pydantic), `Schema` (marshmallow), `@validate` (Flask), `Form` (Django)
- **Fallback**: Grep for `validator`, `validate`, `serializer`

---

## Go

### Health Checks
- **Primary**: Grep for `/health`, `/healthz`, `/ready`, `healthcheck`
- **Framework**: Grep for `github.com/heptiolabs/healthcheck`, `github.com/alexliesenfeld/health`
- **Fallback**: Grep for `func.*health.*Handler`, `http.HandleFunc.*health`

### Graceful Shutdown
- **Primary**: Grep for `signal.Notify`, `os.Interrupt`, `syscall.SIGTERM`
- **Framework**: Grep for `srv.Shutdown`, `http.Server.*Shutdown`, `context.WithTimeout`
- **Fallback**: Grep for `graceful`, `shutdown`, `signal`

### Circuit Breakers
- **Primary**: Grep for `gobreaker`, `sony/gobreaker`, `CircuitBreaker`
- **Framework**: Grep for `hystrix-go`, `github.com/afex/hystrix-go`
- **Fallback**: Grep for `circuit`, `breaker`, `StateOpen`

### Retry Policies
- **Primary**: Grep for `retry`, `avast/retry-go`, `cenkalti/backoff`
- **Framework**: Grep for `hashicorp/go-retryablehttp`, `sethvargo/go-retry`
- **Fallback**: Grep for `backoff`, `maxRetries`, `ExponentialBackOff`

### Timeouts
- **Primary**: Grep for `context.WithTimeout`, `context.WithDeadline`, `http.Client.*Timeout`
- **Framework**: Grep for `DialTimeout`, `ReadTimeout`, `WriteTimeout`, `IdleTimeout`
- **Fallback**: Grep for `time.Duration`, `timeout`

### Structured Logging
- **Primary**: Grep for `zap`, `zerolog`, `logrus`, `slog`
- **Framework**: Grep for `zap.NewProduction`, `zerolog.New`, `slog.NewJSONHandler`
- **Fallback**: Grep for `json.*log`, `structured.*log`

### Metrics
- **Primary**: Grep for `prometheus/client_golang`, `prometheus.NewCounter`, `prometheus.NewHistogram`
- **Framework**: Grep for `promhttp.Handler`, `promauto`
- **Fallback**: Grep for `metrics`, `statsd`, `datadog`

---

## Rust

### Health Checks
- **Primary**: Grep for `/health`, `/healthz`, `health_check`, `health_handler`
- **Framework**: Grep for `actix_web.*health`, `axum.*health`, `rocket.*health`
- **Fallback**: Grep for `fn health`, `async fn health`

### Graceful Shutdown
- **Primary**: Grep for `signal::ctrl_c`, `tokio::signal`, `SIGTERM`
- **Framework**: Grep for `graceful_shutdown`, `Server.*shutdown`, `with_graceful_shutdown`
- **Fallback**: Grep for `shutdown`, `terminate`

### Structured Logging
- **Primary**: Grep for `tracing`, `tracing-subscriber`, `slog`, `env_logger`
- **Framework**: Grep for `tracing_subscriber::fmt::json`, `slog_json`
- **Fallback**: Grep for `log::`, `info!`, `error!`

---

## Container / Infrastructure

### Dockerfile Health Checks
- Grep for `HEALTHCHECK` in `Dockerfile*`
- Grep for `healthcheck:` in `docker-compose*.yml`

### Kubernetes Probes
- Grep for `livenessProbe`, `readinessProbe`, `startupProbe` in `*.yaml`/`*.yml` files in k8s/, deploy/, manifests/, helm/ directories
- Grep for `httpGet`, `tcpSocket`, `exec` under probe definitions

### Resource Limits
- Grep for `resources:`, `limits:`, `requests:` in Kubernetes YAML
- Grep for `mem_limit`, `cpus`, `memory` in docker-compose files
- Grep for `-Xmx`, `-Xms` in Dockerfiles or entrypoint scripts
- Grep for `--max-old-space-size` for Node.js

### CI/CD Vulnerability Scanning
- Grep for `npm audit`, `snyk`, `trivy`, `grype`, `safety check` in CI workflow files
- Grep for `dependabot.yml` in `.github/`
- Grep for `renovate.json` or `renovate.json5`

### Secrets in .gitignore
- Read `.gitignore` and check for `.env`, `*.pem`, `*.key`, `credentials*`, `secrets*`

### Alert Configuration
- Glob for `**/alerts*.yml`, `**/rules*.yml`, `**/monitors*.yml`
- Grep for `PrometheusRule`, `AlertmanagerConfig` in YAML files
- Grep for `alert`, `threshold`, `notification` in Terraform/Pulumi files

## Three-Search Protocol

For every check, follow this exact sequence:

1. **Primary search**: Use the generic pattern (works across all frameworks)
2. **Framework search**: Use the framework-specific pattern for the detected stack
3. **Broad fallback**: Use the broad/relaxed pattern

Mark FAIL only after all three searches return no results. If any search returns results, evaluate for PASS vs WARN based on the check criteria in CHECKS.md.
