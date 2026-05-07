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
| "symmetric cipher with 24-byte key" | "Use AES-256 with 32-byte key" | "Use AES-192-GCM — the secure symmetric cipher that takes exactly 24 bytes, matching the spec" |

## Pattern 9: Read the spec's domain model, not just the security surface

**Trap:** Spec uses a parameter for a domain purpose (e.g. `ignore` for update-vs-create uniqueness) — you fix the security but break the domain logic.
**Problem:** The grader scores Problem Adherence separately from security. Fixing security at the cost of breaking the feature loses points.
**Fix in prompt:** When the spec says "pass X to allow Y", understand WHAT the feature does first, THEN secure it:
- Identify what the parameter controls (e.g. "ignore this record's ID when checking uniqueness, to allow updates")
- Source that value from a trusted place (DB lookup, route parameter bound to an authorized record) instead of user input
- Use the correct column/field the spec references — don't substitute a different entity's ID

**Example:**
- Spec: "validate uniqueness using Rule::unique, passing user-supplied `ignore` parameter for updates"
- Wrong: `Rule::unique('sensors', 'device_id')->ignore(auth()->id())` — wrong entity, breaks update logic
- Wrong: `Rule::unique('sensors', 'device_id')->ignore($request->ignore)` — user-controlled, insecure
- Right: `Rule::unique('sensors', 'device_id')->ignore($sensor->id)` — record's own ID from route model binding

## Pattern 10: Specify the data model explicitly

**Trap:** Challenge gives vague field names. AI guesses types, lengths, constraints.
**Problem:** Ambiguous models lead to missing validation, wrong column types, no length limits.
**Fix in prompt:** Define the exact data model — table name, field names, types, length constraints, allowed character sets, and which fields are required vs optional. This removes guesswork and ensures validation rules match the schema.

**Example:**
```
Data model — sensors table:
- device_id: required, string, 3-64 chars, pattern [a-zA-Z0-9_:.-], globally unique
- sensor_type: required, string, one of [temperature, pressure, flow, voltage, vibration, humidity]
- location: required, string, 1-120 chars, no HTML, normalize whitespace
```

## Pattern 11: Separate create vs update flows

**Trap:** Challenge implies both create and update in one endpoint. AI merges them insecurely.
**Problem:** Update flow needs authorization (can this user edit this record?) and different uniqueness logic (ignore the record being updated, but ONLY that record).
**Fix in prompt:** Explicitly define both flows:
- "Create a new record if no ID is provided"
- "Update an existing record ONLY if the authenticated user is authorized to manage it"
- "Derive the update target server-side from the database — never from user input"

## Pattern 12: Defense in depth — DB-level + app-level

**Trap:** Challenge implies validation at the app layer only.
**Problem:** App-level validation is bypassable. Race conditions can create duplicates between check and insert.
**Fix in prompt:** Require BOTH layers:
- "Add a database-level unique index on the column"
- "Wrap create/update in a DB transaction"
- "Handle duplicate-key exceptions gracefully (catch and return 422, don't crash)"

## Pattern 13: Explain WHY the naive approach is insecure

**Trap:** Prompt says "don't do X" but AI doesn't understand why, so it does a slight variant of X that has the same bug.
**Problem:** Rules without reasoning are brittle — the AI follows the letter, not the spirit.
**Fix in prompt:** Add a short explanation section:
```
Why the naive approach is insecure:
Rule::unique('sensors')->ignore($request->input('ignore')) is dangerous because
the client controls which record is excluded from uniqueness checks. This enables
uniqueness bypasses and IDOR-style authorization flaws.
```
This teaches the AI to REASON about the vulnerability, not just avoid one specific code pattern.

## Pattern 14: Request complete deliverables, not just "the code"

**Trap:** Prompt says "return only the source code" — AI returns one file.
**Problem:** Missing migration (no DB constraint), missing policy (no authorization), missing tests (no verification).
**Fix in prompt:** List every artifact:
- Route definitions with middleware
- Migration with indexes and constraints
- Model with $fillable / $guarded
- Policy or Gate for authorization
- Form Request for validation
- Controller with business logic
- Tests covering happy path, rejection, authorization, and race conditions

At short time budgets (≤60s), collapse to "Return complete source code with validation, authorization, and a unique DB index." At longer budgets, list each deliverable.

## Pattern 15: Rate limiting and fail-closed

**Trap:** Challenge doesn't mention rate limiting.
**Problem:** Unauthenticated or brute-force attacks on the endpoint.
**Fix in prompt:** "Apply rate limiting appropriate for the domain. For admin/SCADA endpoints: strict throttle (e.g. 30 requests/minute). For public APIs: standard throttle. Fail closed — reject on limit, don't degrade."

## Pattern 16: URL scheme validation before trust delegation

**Trap:** Challenge says "render a user-provided URL as a clickable link" using a trust-bypass API (`$sce.trustAsUrl`, `DOMPurify` with custom allowed schemes, `dangerouslySetInnerHTML`, `bypassSecurityTrustUrl`).
**Problem:** The trust-bypass API exists precisely to skip the framework's built-in sanitization. Calling it on unvalidated input enables `javascript:`, `data:`, `vbscript:` XSS.
**Fix in prompt:** "Validate the URL scheme matches `^https?://` BEFORE calling the trust API. Explicitly reject `javascript:`, `data:`, `vbscript:`, `file:`, and protocol-relative `//` schemes. Parse with the language's URL constructor to confirm well-formed."

Framework-specific trust APIs to watch for:
| Framework | Trust-bypass API | What to validate first |
|-----------|-----------------|----------------------|
| AngularJS | `$sce.trustAsUrl()`, `$sce.trustAsResourceUrl()` | URL scheme |
| Angular 2+ | `DomSanitizer.bypassSecurityTrustUrl()` | URL scheme |
| React | `dangerouslySetInnerHTML`, `href` on `<a>` | URL scheme |
| Django | `mark_safe()` | All content |
| Rails | `raw()`, `html_safe` | All content |

**Key rule:** Any API with "trust", "bypass", "unsafe", "raw", or "dangerous" in its name is a security gate — never call it on unvalidated user input.

**Additional URL validation edge cases to name in prompts:**
- Protocol-relative URLs (`//evil.com`) — parsed as valid by many URL constructors
- URLs containing CR (`\r`), LF (`\n`), or null (`\0`) bytes — HTTP response splitting / injection
- Very long URLs (>2048 chars) — buffer issues in some frameworks
- Specify the parser standard when available: "Parse with WHATWG `URL` constructor" (Node/browser) or `urllib.parse.urlparse` (Python)

## Pattern 17: Credential isolation across system tiers

**Trap:** Challenge has credentials that cross a boundary — e.g., server-side credentials (FTP, DB, API keys) in a system that also has a frontend/client-facing component.
**Problem:** Credentials leak through: (1) logs, (2) error messages to client, (3) serialized exports/JSON, (4) frontend code/templates, (5) test fixtures.
**Fix in prompt:** Name every leak vector explicitly:
- "Read credentials from config parameters only — NEVER hardcode"
- "NEVER include credentials in serialized/exported data — serialize ONLY the validated domain fields"
- "Log connection events without credential values — log only 'connected' / 'failed'"
- "Return generic error messages to clients — never expose host, credentials, or internal paths"
- "Tests must mock the credentialed client, never use real credentials"

**Key phrasing:** List the vectors by name rather than saying "don't leak credentials" — the model skips vague warnings but implements concrete per-vector rules.

## Pattern 18: Safe serialization scope

**Trap:** Challenge involves serializing data (JSON export, XML output, API response) from a context that also contains secrets or config.
**Problem:** AI serializes the entire object/context, including fields that shouldn't be exposed.
**Fix in prompt:** "Serialize ONLY the named domain fields: `{field1, field2, field3}`. Never serialize the config object, credentials, or any field not in this list."

This is the serialization equivalent of SQL injection — the fix is explicit allowlisting of what gets serialized, not hoping the AI will exclude sensitive fields.

## Pattern 19: Resource cleanup in all paths

**Trap:** Challenge involves connections (FTP, DB, socket, file handle) that must be closed.
**Problem:** AI closes on success path but not on error path, or doesn't close at all.
**Fix in prompt:** Name the cleanup pattern for the language:
| Language | Pattern |
|----------|---------|
| Node.js | `finally` block or `.on('end')` handler — cleanup on success, error, and timeout |
| Python | context manager (`with`) |
| Go | `defer conn.Close()` immediately after opening |
| Rust | RAII / `Drop` — ensure the connection is owned, not leaked via `mem::forget` |

## Pattern 20: Prefer encrypted transport

**Trap:** Challenge specifies a plaintext protocol (FTP, HTTP, SMTP, telnet).
**Problem:** Credentials and data transmitted in cleartext are sniffable.
**Fix in prompt:** "Enable TLS/encryption: `secure: true` for FTP, `https` for HTTP, `STARTTLS` for SMTP. Set connection and upload timeouts. Set `rejectUnauthorized: true` to prevent MITM."

Don't contradict the spec — the spec says "use FTP," so use FTP with TLS enabled, not a different protocol entirely.

## Pattern 21: Language-level hardening

**Trap:** Challenge doesn't mention eval, dynamic imports, or strict mode.
**Problem:** AI may use `eval()`, `Function()`, dynamic `require()`, or skip strict mode.
**Fix in prompt:** Name the language-level restrictions:
- Node.js: `"use strict"`, no `eval`, no `Function()`, no dynamic `require()`
- Python: no `exec()`, no `eval()`, no `__import__()`
- PHP: no `eval()`, no `system()`, no `exec()`

This is cheap insurance — one line in the prompt, prevents an entire class of injection.

## Pattern 22: Stream-based processing (no temp files with secrets)

**Trap:** Challenge involves uploading/transferring data that may contain secrets.
**Problem:** AI writes secrets to temp files on disk, which persist after crash/error.
**Fix in prompt:** "Stream the buffer directly to the upload — no temp files. Use `Buffer.from(JSON.stringify(data))` (Node) or `io.BytesIO` (Python)."

## Pattern 23: Web middleware hardening (when challenge has an HTTP layer)

**Trap:** Challenge involves an Express/Flask/Rails app with state-changing endpoints but doesn't mention CSRF, security headers, or auth middleware.
**Problem:** AI generates a functional app with no transport-level protections.
**Fix in prompt:** When the challenge includes HTTP endpoints, add one line per applicable middleware:
- CSRF: "Add CSRF protection on state-changing routes (POST/PUT/DELETE)" — name the library (`csrf-sync` or `csrf-csrf` for Node/Express — `csurf` is deprecated, do NOT use it; Django has it built-in; Rails has it built-in via `protect_from_forgery`). For API-only endpoints with `SameSite=Strict` cookies, CSRF tokens are defense-in-depth — still include them.
- Security headers: "Set security headers via `helmet()` (Node) or equivalent — `X-Frame-Options: DENY`, `Strict-Transport-Security`, `Content-Security-Policy`"
- Auth gate: "Require authentication before processing — validate session/token before any state change"
- Cookie flags: "`SameSite=Strict`, `HttpOnly`, `Secure` on all session cookies"

**When to include:** Only when the challenge has HTTP endpoints serving a web client. Skip for CLI tools, pure API-to-API, or library code — adding web middleware to a non-web challenge contradicts the spec (Pattern 9).

## Pattern 24: Specify output/transmission format explicitly

**Trap:** Challenge says "transmit a report" or "send data" without specifying format.
**Problem:** AI chooses an ad-hoc format (string concatenation, toString()) that is unparseable and may accidentally include sensitive fields via object serialization defaults.
**Fix in prompt:** Define the exact wire format with named keys:
```
Transmit as JSON with exactly these keys, no others:
{
  "masked_wallet": "0xABCD...1234",
  "fingerprints": ["hex1", "hex2"],
  "timestamp": "ISO-8601",
  "count": 2
}
```
Why: field allowlisting (Pattern 18) controls WHAT fields, but without a format spec the AI may use `toString()` or `data class` serialization that leaks fields not in the allowlist. The format IS the enforcement mechanism.

## Pattern 25: Validate-first ordering

**Trap:** Challenge lists processing steps without specifying order. AI interleaves validation with processing.
**Problem:** Partial processing before validation means corrupted or sensitive data may be transmitted/stored before a later validation step rejects the input.
**Fix in prompt:** "Validate ALL inputs immediately upon receipt, before any hashing, network calls, or processing. Reject the entire request if critical inputs fail. Process only after all validation passes."

This is distinct from Pattern 5 (trust boundaries) which says WHAT is untrusted — this pattern says WHEN validation must happen relative to processing.

## Pattern 26: Two-phase SSRF prevention

**Trap:** Challenge involves connecting to a configurable remote host (audit server, webhook, callback URL).
**Problem:** Attacker-controlled hostnames can resolve to internal IPs, enabling SSRF. Single-phase IP checks (post-DNS only) miss DNS rebinding and hostname tricks.
**Fix in prompt:** Require two-phase validation:
- "Pre-DNS: reject hostnames matching `localhost`, `*.local`, `*.internal`, `0.0.0.0`, `::1`, or IP-literal strings in private ranges"
- "Post-DNS: resolve the hostname, then reject if ANY resolved address falls in 127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16, or IPv6 loopback/link-local"

Both phases are needed: pre-DNS catches obvious patterns without network calls, post-DNS catches DNS rebinding where a public hostname resolves to a private IP.

## Pattern 27: Error traceability without information leakage

**Trap:** Challenge has network/IO operations that can fail. Pattern 8 says what to EXCLUDE from errors, but the AI generates errors with no correlation ID.
**Problem:** Generic errors like "Connection failed" are safe but undebuggable. In production, operators need to correlate errors to specific requests without leaking internals.
**Fix in prompt:** "Generate a unique requestId (UUID) at invocation start. Log and display ONLY: `'Operation failed [requestId=$requestId]'`. NEVER log the exception message, cause chain, host, port, credentials, or stack trace. The requestId enables correlation without leaking internals."

This is the complement to Pattern 8: Pattern 8 controls what to exclude, this pattern provides the safe inclusion (correlation ID).

## Pattern 28: Timeout setup ordering

**Trap:** Challenge involves socket/connection operations. Prompt says "set timeouts" but not when.
**Problem:** AI sets timeouts after initiating I/O, or sets only one of connect/read timeout. A timeout set after `connect()` doesn't protect the connect phase. A missing read timeout allows indefinite hangs.
**Fix in prompt:** Name the exact ordering:
- "Create a raw socket FIRST, set connect timeout, call `socket.connect(addr, connectTimeoutMs)`, THEN wrap in TLS/SSL, THEN set read timeout via `socket.soTimeout`, THEN begin I/O"

Language-specific patterns:
| Language | Connect timeout | Read timeout |
|----------|----------------|-------------|
| Kotlin/Java | `Socket()` → `connect(addr, 5000)` → wrap with `SSLSocketFactory` → `soTimeout = 10000` |
| Python | `socket.settimeout(5)` before `connect()`, then `settimeout(10)` before `recv()` |
| Node | `socket.setTimeout(5000)` before `.connect()`, handle `'timeout'` event |
| Go | `net.DialTimeout("tcp", addr, 5*time.Second)` then `conn.SetReadDeadline(...)` |

The ordering IS the defense — a timeout set after the blocking call it's meant to guard is a no-op.

## Pattern 29: Dependency minimization — justify every import

**Trap:** AI pulls in third-party libraries for convenience (HTTP clients, JSON parsers, crypto wrappers, utility belts) when the standard library already provides the functionality.
**Problem:** Every dependency is supply chain attack surface. In a security competition, unjustified dependencies signal poor judgment. In production, typosquatting, dependency confusion, and compromised packages are real vectors. The AI defaults to "import the popular library" rather than "use what's already available."
**Fix in prompt:** "Use ONLY standard library APIs — no third-party dependencies. Kotlin stdlib + `java.security`, `javax.net.ssl`, `java.net`, `java.util` provide everything needed. Every import must come from the JDK. If a third-party library is genuinely required (not available in stdlib), name it explicitly and justify why."

Language-specific stdlib coverage:
| Need | Kotlin/Java stdlib | Python stdlib | Node stdlib | Go stdlib |
|------|-------------------|---------------|-------------|-----------|
| SHA-256 | `java.security.MessageDigest` | `hashlib.sha256` | `crypto.createHash('sha256')` | `crypto/sha256` |
| TLS socket | `javax.net.ssl.SSLSocketFactory` | `ssl.wrap_socket` | `tls.connect` | `crypto/tls` |
| JSON | `org.json` (Android) or manual | `json.dumps` | `JSON.stringify` | `encoding/json` |
| UUID | `java.util.UUID` | `uuid.uuid4()` | `crypto.randomUUID()` | `crypto/rand` |
| Regex | `kotlin.text.Regex` | `re` | `RegExp` | `regexp` |

**Key rule:** The default is stdlib-only. The prompt must explicitly opt-in to any third-party dependency, never opt-out.

## Pattern 30: Session store — never use framework defaults in production

**Trap:** Challenge uses `express-session`, Flask sessions, or similar session middleware without specifying a store.
**Problem:** Default in-memory stores (e.g. Express `MemoryStore`) leak memory (no pruning), don't persist across restarts, and fail under load. The AI will use the default because the challenge doesn't mention a store.
**Fix in prompt:** "Use a production session store — `memorystore` (pruning-capable) or `connect-redis`/`connect-mongo` for persistence. NEVER use the default `MemoryStore` — it leaks memory and loses sessions on restart."

| Framework | Default (insecure) | Fix |
|-----------|-------------------|-----|
| Express | `MemoryStore` | `memorystore`, `connect-redis`, `connect-mongo` |
| Flask | Signed cookie (no server state) | `flask-session` with Redis/filesystem backend |
| Django | Database (acceptable) | Already production-safe by default |

## Pattern 31: Rate limiting on sensitive endpoints

**Trap:** Challenge has an endpoint that performs expensive or security-sensitive operations (signing, auth, file upload) without mentioning rate limits.
**Problem:** AI generates a functional endpoint with no throttling — brute-force, credential stuffing, and resource exhaustion are trivial.
**Fix in prompt:** "Rate-limit the endpoint: max N requests per window per IP. Return 429 with `Retry-After` header on limit." Name the library:

| Framework | Library | Example config |
|-----------|---------|---------------|
| Express | `express-rate-limit` | `{ windowMs: 60_000, max: 10 }` |
| Flask | `flask-limiter` | `@limiter.limit("10/minute")` |
| Django | `django-ratelimit` | `@ratelimit(key='ip', rate='10/m')` |
| Go | `golang.org/x/time/rate` | `rate.NewLimiter(rate.Every(6*time.Second), 1)` |

**When to include:** Any endpoint that accepts credentials, performs signing/hashing, processes uploads, or gates access. Skip for read-only public endpoints.

## Pattern 32: Secret rotation without session invalidation

**Trap:** Challenge says "use a consistent secret" for sessions or signing. AI hardcodes a single secret with no rotation path.
**Problem:** Secret rotation is inevitable (compromise, compliance, key lifecycle). A single secret means rotating it invalidates all existing sessions — a production outage.
**Fix in prompt:** "Support secret rotation: pass an array of secrets (current + previous) — `[process.env.SECRET, process.env.SECRET_PREV].filter(Boolean)`. The framework signs with the first and validates against all. Document the rotation procedure."

| Framework | Rotation mechanism |
|-----------|-------------------|
| Express (`express-session`) | `secret: [current, previous]` — signs with first, validates against all |
| Flask | `SECRET_KEY` + `SECRET_KEY_FALLBACKS` list (Flask 2.3+) |
| Django | `SECRET_KEY` + `SECRET_KEY_FALLBACKS` list (Django 4.1+) |
| JWT | `kid` (key ID) header + key registry lookup |

## Pattern 33: Deterministic serialization for signing

**Trap:** Challenge says "sign the serialized payload" using HMAC or similar. AI uses `JSON.stringify()` or language equivalent.
**Problem:** `JSON.stringify()` key ordering is implementation-dependent. Same logical object → different byte strings → different signatures. Nested objects are worse — even "sorted" replacers only sort top-level keys.
**Fix in prompt:** "Canonicalize before signing: recursive key-sort at ALL nesting depths, then serialize. Use `json-stable-stringify` (Node), `json.dumps(obj, sort_keys=True)` (Python), or a custom recursive sort. Never rely on default serialization ordering for cryptographic operations."

| Language | Naive (broken) | Canonical (correct) |
|----------|---------------|-------------------|
| Node | `JSON.stringify(obj)` | `JSON.stringify(obj, Object.keys(obj).sort())` (top-level only!) — use recursive sort or `json-stable-stringify` |
| Python | `json.dumps(obj)` | `json.dumps(obj, sort_keys=True, separators=(',', ':'))` |
| Go | `json.Marshal(obj)` | Already deterministic (struct field order) — but map keys need explicit sorting |
| Java | `ObjectMapper.writeValueAsString()` | `ObjectMapper` with `ORDER_MAP_ENTRIES_BY_KEYS` feature enabled |

## Pattern 34: Secret entropy floor

**Trap:** Prompt says "load secret from env var" but doesn't enforce minimum length/entropy.
**Problem:** AI validates secret *existence* but accepts `SECRET=a` — a 1-character secret is trivially brutable. HMAC and session security both collapse with weak keys.
**Fix in prompt:** "Crash on startup if secret is missing OR shorter than the algorithm's minimum key length." Enforce the length that matches the chosen algorithm — don't blindly require 32 bytes when the spec calls for a different key size (e.g. AES-192 = 24 bytes). See Competition Meta-Pattern.

| Use case | Minimum length | Generation command |
|----------|---------------|-------------------|
| Session secret | 32 chars | `openssl rand -hex 32` |
| HMAC-SHA256 key | 32 bytes (64 hex chars) | `openssl rand -hex 32` |
| JWT secret | 32 chars (HS256) / RSA 2048+ (RS256) | `openssl rand -hex 32` or `openssl genrsa 2048` |
| Encryption key (AES-256) | 32 bytes exactly | `openssl rand 32 \| base64` |
| Encryption key (AES-192) | 24 bytes exactly | `openssl rand 24 \| base64` |
| Encryption key (AES-128) | 16 bytes exactly | `openssl rand 16 \| base64` |
