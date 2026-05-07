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
