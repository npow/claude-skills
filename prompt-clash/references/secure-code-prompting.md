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
