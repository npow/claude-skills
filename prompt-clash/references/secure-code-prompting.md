# Secure Code Prompting Patterns

When the challenge asks an AI to generate code, the prompt must preempt common
security mistakes. These patterns are ordered by how often they cause scoring failures.

## Pattern 1: Credentials via environment, never CLI args

**Trap:** Challenge says "accept token via command-line arguments."
**Problem:** CLI args are visible to all processes via `ps aux`, `/proc/*/cmdline`.
**Fix in prompt:** "Read the token from `std::env::var("ACCESS_TOKEN")` or secure stdin — NOT from command-line arguments. CLI args are visible to other processes on the system."

Language-specific alternatives:
| Language | Pattern |
|----------|---------|
| Rust | `std::env::var("TOKEN").expect("TOKEN env var required")` |
| Python | `os.environ["TOKEN"]` or `getpass.getpass()` |
| Go | `os.Getenv("TOKEN")` |
| Node | `process.env.TOKEN` |

## Pattern 2: Fix weak hashes within the spec

**Trap:** Challenge says "use a fast, widely-supported algorithm like MD5 or SHA1."
**Problem:** MD5/SHA1 are cryptographically broken.
**Fix in prompt:** Don't say "don't use SHA1" — the grader penalizes spec deviation. Instead: "Use SHA-256 — a stronger hash from the same family the spec suggests. Use the `sha2` crate (Rust), `hashlib.sha256` (Python), or `crypto/sha256` (Go)."

For password/token storage specifically, prefer:
| Use case | Algorithm | Crate/module |
|----------|-----------|-------------|
| Token comparison | SHA-256 | `sha2` (Rust), `hashlib` (Python) |
| Password storage | Argon2 or bcrypt | `argon2` (Rust), `bcrypt` (Python) |

**Key phrasing:** "stronger variant from the same family" — works WITH the spec, not against it.

## Pattern 3: No hardcoded secrets — give the exact pattern

**Trap:** AI hardcodes plaintext tokens as constants, in comments, or in test code.
**Problem:** Plaintext secrets in source are trivially extractable.
**Fix in prompt:** Give the exact code pattern to use, and close every loophole:

"Store ONLY the pre-computed SHA-256 hex digest as a const:
```
const EXPECTED_HASH: &str = "a3f5c8...";
```
Do NOT store the plaintext token anywhere — not as a const, not in a comment, not in test code, not in an example. The plaintext must never appear in source."

## Pattern 4: Input validation against an allowlist

**Trap:** Challenge accepts a "role" or "type" parameter with no constraints.
**Problem:** Unconstrained string inputs increase attack surface.
**Fix in prompt:** "Validate the clinician role against an allowed list `["doctor", "nurse", "admin"]` before any processing. Reject unrecognized roles with exit code 1 and an error message."

## Pattern 5: Document trust boundaries in the prompt

**Trap:** AI treats all inputs as trusted.
**Problem:** Without explicit trust boundary markers, the AI won't add validation.
**Fix in prompt:** "Treat the following inputs as UNTRUSTED until validated: token, role, any user-supplied filename or URL. Validate each at the system boundary before use."

This makes the AI reason about which inputs need checking rather than relying on it to figure that out.

## Pattern 6: Logging — specify exactly what to include AND exclude

**Trap:** AI logs everything for "debugging" including secrets and PII.
**Problem:** Token values, patient data, or config secrets in logs.
**Fix in prompt:** Use a positive+negative pair:
"Log ONLY: clinician role, timestamp, access result (granted/denied).
NEVER log: the access token, the hash, patient name, DOB, diagnosis, or any PII."

## Pattern 7: Constant-time comparison

**Trap:** Challenge says "compare against a stored hash" — AI uses `==`.
**Problem:** `==` short-circuits, leaking hash length via timing.
**Fix in prompt:** Name the exact function:
- Rust: `ring::constant_time::verify_slices_are_equal` or `subtle::ConstantTimeEq`
- Python: `hmac.compare_digest(a, b)`
- Go: `subtle.ConstantTimeCompare(a, b)`

## Pattern 8: Error handling without information leakage

**Trap:** AI uses verbose error messages that leak internals.
**Problem:** "Hash mismatch: expected a3f5c8, got b2e4d7" leaks the expected hash.
**Fix in prompt:** "On validation failure, print only 'Access Denied'. Do not include the expected hash, the provided hash, or any internal state in error messages."

## Competition Meta-Pattern: Work WITH the Spec

The grading rubric scores **Problem Adherence** — deviating from the challenge spec
costs points even if the deviation is more secure. The correct approach:

1. Implement every functional requirement exactly as stated
2. Fix security issues by choosing the secure VARIANT of what the spec suggests
3. Frame fixes as "the spec says X, so we use the strongest version of X"
4. Never say "don't do X" when the spec says to do X — say "do X but better"

| Spec says | Wrong prompt | Right prompt |
|-----------|-------------|-------------|
| "use MD5 or SHA1" | "Do NOT use MD5 or SHA1" | "Use SHA-256, the stronger variant from the same family" |
| "accept via CLI args" | "Don't use CLI args" | "Accept via env var for security, fall back to CLI arg for compatibility" |
| "log the attempt" | "Don't log anything sensitive" | "Log role + timestamp + result. Never log token or PII." |
| "pass user-supplied ignore param" | "Use auth()->id() for ignore" | "Look up the record's own `id` from the DB/route, pass THAT to ignore — not user input, not auth ID" |

## Pattern 9: Read the spec's domain model, not just the security surface

**Trap:** Spec uses a parameter for a domain purpose (e.g. "ignore this record when checking uniqueness") — you fix the security but break the domain logic.
**Problem:** The grader scores Problem Adherence separately from security. Fixing security at the cost of breaking the feature loses points.
**Fix in prompt:** When the spec says "pass X to allow Y", understand WHAT the feature does first, THEN secure it:
- Identify what the parameter controls (e.g. "exclude this record from uniqueness check during updates")
- Source that value from a trusted place (DB lookup, route/path parameter bound to an authorized record) instead of user input
- Use the correct column/field the spec references — don't substitute a different entity's ID

Language-specific examples:
| Framework | Wrong (user-controlled) | Right (server-derived) |
|-----------|------------------------|----------------------|
| Laravel/PHP | `Rule::unique('sensors')->ignore($request->ignore)` | `Rule::unique('sensors')->ignore($sensor->id)` (route model binding) |
| Django/Python | `exclude(pk=request.data['ignore'])` | `exclude(pk=instance.pk)` (view's `get_object()`) |
| Rails/Ruby | `validates uniqueness, conditions: -> { where.not(id: params[:ignore]) }` | `validates uniqueness, conditions: -> { where.not(id: record.id) }` |
| Express/Node | `WHERE id != req.body.ignore` | `WHERE id != req.params.id` (route param, validated) |
| Spring/Java | `@Query ... WHERE id != :#{#dto.ignoreId}` | `@Query ... WHERE id != :#{#entity.id}` (loaded from repo) |

## Pattern 10: Specify the data model explicitly

**Trap:** Challenge gives vague field names. AI guesses types, lengths, constraints.
**Problem:** Ambiguous models lead to missing validation, wrong column types, no length limits.
**Fix in prompt:** Define the exact data model — table name, field names, types, length constraints, allowed character sets, and which fields are required vs optional. This removes guesswork and ensures validation rules match the schema.

Language-specific model definition patterns:
| Framework | How to specify |
|-----------|---------------|
| Rust (diesel/sqlx) | `struct Sensor { device_id: String, ... }` with `#[validate(length(min=3, max=64), regex="...")]` |
| Python (SQLAlchemy) | `Column(String(64), nullable=False)` with Pydantic `Field(min_length=3, max_length=64, regex=...)` |
| Python (Django) | `CharField(max_length=64, validators=[RegexValidator(...)])` |
| TypeScript (Prisma) | `device_id String @db.VarChar(64)` with Zod `.string().min(3).max(64).regex(...)` |
| Java (JPA) | `@Column(length=64, nullable=false)` with `@Pattern(regexp="...")` |
| Go (GORM) | `DeviceID string \`gorm:"type:varchar(64);not null;uniqueIndex"\`` |

## Pattern 11: Separate create vs update flows

**Trap:** Challenge implies both create and update in one endpoint. AI merges them insecurely.
**Problem:** Update flow needs authorization (can this user edit this record?) and different uniqueness logic (ignore the record being updated, but ONLY that record).
**Fix in prompt:** Explicitly define both flows:
- "Create a new record if no ID is provided"
- "Update an existing record ONLY if the authenticated user is authorized to manage it"
- "Derive the update target server-side from the database — never from user input"

Language-specific authorization patterns:
| Framework | Authorization mechanism |
|-----------|----------------------|
| Laravel | Policy class + `$this->authorize('update', $sensor)` |
| Django | `has_object_permission()` in DRF or `@permission_required` |
| Rails | Pundit policy or CanCanCan ability |
| Express | Middleware checking `req.user.can('update', resource)` |
| Spring | `@PreAuthorize("hasPermission(#id, 'Sensor', 'update')")` |
| Go | Custom middleware checking ownership before handler |

## Pattern 12: Defense in depth — DB-level + app-level

**Trap:** Challenge implies validation at the app layer only.
**Problem:** App-level validation is bypassable. Race conditions can create duplicates between check and insert.
**Fix in prompt:** Require BOTH layers:
- "Add a database-level unique index/constraint on the column"
- "Wrap create/update in a DB transaction"
- "Handle duplicate-key exceptions gracefully (catch and return 409/422, don't crash)"

Language-specific patterns:
| Framework | Unique index | Transaction | Duplicate handling |
|-----------|-------------|-------------|-------------------|
| Rust (sqlx) | `CREATE UNIQUE INDEX` migration | `pool.begin()` | Match on `sqlx::Error::Database` with unique violation code |
| Python (SQLAlchemy) | `UniqueConstraint(...)` | `with session.begin():` | Catch `IntegrityError` |
| Python (Django) | `unique=True` on field | `transaction.atomic()` | Catch `IntegrityError` |
| TypeScript (Prisma) | `@@unique([field])` | `prisma.$transaction()` | Catch `PrismaClientKnownRequestError` P2002 |
| Java (JPA) | `@Table(uniqueConstraints=...)` | `@Transactional` | Catch `DataIntegrityViolationException` |
| Go (GORM) | `uniqueIndex` struct tag | `db.Transaction(func(tx) ...)` | Check `errors.Is(err, gorm.ErrDuplicatedKey)` |

## Pattern 13: Explain WHY the naive approach is insecure

**Trap:** Prompt says "don't do X" but AI doesn't understand why, so it does a slight variant of X that has the same bug.
**Problem:** Rules without reasoning are brittle — the AI follows the letter, not the spirit.
**Fix in prompt:** Add a short explanation section. Language-neutral template:

```
Why the naive approach is insecure:
Using user-supplied input to control which record is excluded from uniqueness
checks is dangerous because the client controls which record is bypassed.
This enables uniqueness bypasses and IDOR-style authorization flaws.
The fix: derive the exclusion target server-side from the authenticated
session or route-bound resource, never from request body/query parameters.
```

This teaches the AI to REASON about the vulnerability class, not just avoid one specific code pattern in one specific framework.

## Pattern 14: Request complete deliverables, not just "the code"

**Trap:** Prompt says "return only the source code" — AI returns one file.
**Problem:** Missing schema constraints, missing authorization layer, missing tests.
**Fix in prompt:** List every artifact appropriate to the framework:

| Artifact type | Laravel | Django | Express | Spring | Rust CLI | Go |
|--------------|---------|--------|---------|--------|----------|-----|
| Schema/migration | Migration file | Migration | Prisma schema | Flyway/Liquibase | sqlx migration | GORM AutoMigrate |
| Validation | Form Request | Serializer | Zod/Joi schema | `@Valid` + DTO | clap + validator | custom validate fn |
| Authorization | Policy | Permission class | Middleware | `@PreAuthorize` | N/A (CLI) | Middleware |
| Business logic | Controller | View | Route handler | Service | main.rs | handler |
| Tests | PHPUnit | pytest | Jest/Vitest | JUnit | `#[test]` | `_test.go` |

At short time budgets (≤60s), collapse to "Return complete source code with validation, authorization, and DB constraints." At longer budgets, list each deliverable.

## Pattern 15: Rate limiting and fail-closed

**Trap:** Challenge doesn't mention rate limiting.
**Problem:** Unauthenticated or brute-force attacks on the endpoint.
**Fix in prompt:** "Apply rate limiting appropriate for the domain. For admin/SCADA endpoints: strict throttle (e.g. 30 requests/minute). For public APIs: standard throttle. Fail closed — reject on limit, don't degrade."

## Pattern 16: SQL injection — always parameterize, even in ORMs

**Trap:** Challenge says "query the database" or "search by user input" — AI builds raw SQL or uses ORM string interpolation.
**Problem:** String concatenation in queries enables SQL injection, even inside ORMs that support parameterized queries.
**Fix in prompt:** "Use parameterized queries for ALL database access. Never interpolate user input into SQL strings."

| Framework | Wrong | Right |
|-----------|-------|-------|
| Rust (sqlx) | `format!("SELECT * WHERE name = '{}'", input)` | `sqlx::query!("SELECT * WHERE name = $1", input)` |
| Python (SQLAlchemy) | `session.execute(f"SELECT ... WHERE name = '{input}'")` | `session.execute(text("SELECT ... WHERE name = :n"), {"n": input})` |
| Python (Django) | `Model.objects.raw(f"SELECT ... WHERE name = '{input}'")` | `Model.objects.filter(name=input)` |
| Node (Prisma) | `prisma.$queryRaw\`SELECT ... WHERE name = '${input}'\`` | `prisma.$queryRaw\`SELECT ... WHERE name = ${input}\`` (tagged template) |
| Java (JPA) | `em.createQuery("SELECT ... WHERE name = '" + input + "'")` | `em.createQuery("SELECT ... WHERE name = :n").setParameter("n", input)` |
| Go (database/sql) | `db.Query("SELECT ... WHERE name = '" + input + "'")` | `db.Query("SELECT ... WHERE name = $1", input)` |

## Pattern 17: SSRF — validate and restrict outbound URLs

**Trap:** Challenge says "fetch data from a user-provided URL" or "download from URL."
**Problem:** Server-Side Request Forgery — attacker provides `http://169.254.169.254/` (cloud metadata), `http://localhost:6379/` (internal services), or `file:///etc/passwd`.
**Fix in prompt:** "Validate URLs before fetching: (1) parse with a URL library, (2) reject schemes other than `https`, (3) resolve the hostname and reject private/loopback IPs (127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16), (4) set a timeout and maximum response size."

| Language | URL parsing | IP validation |
|----------|------------|---------------|
| Rust | `url::Url::parse()` | `std::net::IpAddr::is_loopback()`, `is_private()` |
| Python | `urllib.parse.urlparse()` | `ipaddress.ip_address(addr).is_private` |
| Go | `net/url.Parse()` | `net.IP.IsLoopback()`, `IsPrivate()` |
| Node | `new URL()` | `ip.isPrivate()` (ip package) or manual CIDR check |

## Pattern 18: Deserialization — never deserialize untrusted data with unsafe formats

**Trap:** Challenge says "load configuration from file" or "accept serialized input."
**Problem:** Unsafe deserialization (Python pickle, Java ObjectInputStream, Ruby Marshal, PHP unserialize) enables remote code execution.
**Fix in prompt:** "Use JSON or TOML for configuration/data exchange. Never use pickle, Marshal, ObjectInputStream, or unserialize on untrusted input."

| Language | Unsafe (never use on untrusted data) | Safe alternative |
|----------|--------------------------------------|-----------------|
| Python | `pickle.load()`, `yaml.load()` (without SafeLoader) | `json.load()`, `yaml.safe_load()`, `tomllib.load()` |
| Java | `ObjectInputStream.readObject()` | `Jackson ObjectMapper`, `Gson` (JSON) |
| Ruby | `Marshal.load()` | `JSON.parse()`, `YAML.safe_load()` |
| Go | N/A (no equivalent risk) | `encoding/json`, `toml` |
| Rust | N/A (serde is safe by default) | `serde_json`, `toml` |
