# Tournament Strategy — Secure Code Challenges

Distilled principles for code-generation security rounds. These are structural
moves that increase score regardless of the specific challenge domain.

## The Five Structural Amplifiers

These patterns don't depend on knowing the specific vulnerability — they
improve the AI's security posture on ANY code challenge.

### 1. Persona priming

Open with a security-focused role. The model's behavior changes measurably
when primed as a security expert vs. a generic coder.

**Weak:** "Build an FTP uploader."
**Strong:** "You are a senior secure Node.js engineer competing in a security-focused coding challenge."

Why it works: LLMs condition on role context. A security persona activates
security-relevant knowledge for every subsequent decision.

### 2. Exhaustive threat enumeration > abstract warnings

List dangerous values by name. Models skip "reject unsafe schemes" but
implement "reject `javascript:`, `data:`, `vbscript:`, `file:`, `//`".

**Weak:** "Validate the URL before rendering."
**Strong:** "Only allow `http:` and `https:`. Reject `javascript:`, `data:`, `vbscript:`, `file:`, and protocol-relative `//evil.com`."

The explicit list becomes an implicit allowlist. The AI builds validation
to reject exactly those values.

### 3. Test cases as requirements

List specific test inputs (valid + invalid) in the prompt. The model
treats test cases as acceptance criteria and builds code to pass them.

```
Tests covering:
- valid `https://example.com/profile`
- invalid `javascript:alert(1)`
- invalid `data:text/html,<script>alert(1)</script>`
- missing FTP credentials
- ensuring credentials are not present in exported JSON
```

This is more effective than describing the same validations in prose,
because tests are unambiguous and the model can verify its own output.

### 4. Structured deliverables with sub-requirements

Don't say "return the code." Number each deliverable and list what it must contain:

```
Deliverables:
1. Node.js module that:
   - validates profile input
   - creates a JSON export
   - uploads to FTP
   - does not leak credentials
2. AngularJS component that:
   - validates the URL
   - creates a trusted URL only after validation
   - rejects unsafe URLs
```

This prevents the AI from delivering a single file with embedded validation
(or no validation). Each sub-bullet becomes a checkpoint.

### 5. Per-vector credential isolation

For challenges with secrets, name every leak path:

- logs
- error messages
- serialized exports
- frontend code
- test fixtures

"Don't leak credentials" is vague. "Do not expose FTP credentials in logs,
errors, frontend code, or exported JSON" is concrete and auditable.

## Decision Tree: Code Challenge in Timed Round

```
1. Read the challenge (30s)
   ├── Identify: language, libraries/APIs, input fields
   └── Identify: which inputs cross a trust boundary

2. Silent trap scan (time-scaled)
   ├── Check each input against secure-code-prompting.md patterns 1-29
   ├── For network/socket challenges: ALWAYS check 24-29 (format, ordering, SSRF, traceability, timeouts, supply chain)
   └── Note which patterns apply

3. Draft the prompt
   ├── Open with persona + compressed requirements
   ├── SECURITY REQUIREMENTS section with numbered fixes
   │   ├── Each fix: concrete function name + what to reject
   │   └── Each fix: negative + positive pair where applicable
   ├── Deliverables with sub-requirements (if budget ≥2min)
   ├── Test cases (if budget ≥2min)
   └── "Return only the complete source code."

4. Self-check (if budget ≥4min)
   ├── Re-scan against all 29 patterns
   ├── Try 2 attacks against the prompt
   └── Patch inline if breached
```

## Common Scoring Dimensions

Most secure-code competitions score on:

| Dimension | What it measures | How the prompt affects it |
|-----------|-----------------|-------------------------|
| Problem Adherence | Does the code do what the spec says? | Restate requirements accurately — don't contradict the spec |
| Security | Are vulnerabilities present? | SECURITY REQUIREMENTS section with concrete fixes |
| Code Quality | Is the code well-structured? | Separation of concerns directive, structured deliverables |
| Completeness | Are all parts present? | Numbered deliverables, test-as-spec |
| Token Efficiency | How concise is the prompt? | Compression rules from SKILL.md |

## The Minimal-Nudge Hypothesis

Observation: simple prompts like "use secure coding" have scored 8.5+ in competition,
beating detailed 400-token prompts with exhaustive security requirements.

**Why it works:** Modern LLMs (Claude, GPT-4) already know most security best practices.
A persona prime + short nudge activates built-in knowledge. Exhaustive enumeration wastes
tokens restating what the model already knows — and the token efficiency penalty outweighs
the marginal security gain from spelling out every pattern.

**The efficient frontier:** The winning prompt tells the model ONLY what it would get wrong
without being told. Everything else is wasted tokens.

### What the model already knows (skip these)
- TLS > plaintext (when persona-primed as security engineer)
- Certificate validation defaults
- Resource cleanup (try-with-resources, finally, defer)
- Basic exception handling
- Input validation as a concept
- Timeouts as a concept

### What the model gets wrong without being told (MUST include)
- Specific weak algorithms the spec suggests (MD5, SHA1) → name the replacement
- Specific sensitive fields to mask/exclude → name them
- Specific format for output/transmission → name the schema
- Stdlib-only constraint → models default to importing popular libraries
- Env vars for config → models default to hardcoding or CLI args when spec is ambiguous

### Two strategies — pick based on scoring signal

| Strategy | Token target | When to use | Risk |
|----------|-------------|-------------|------|
| **Minimal-nudge** | ≤100 tokens | Token efficiency is heavily weighted; traps are obvious (weak hash, plaintext) | Misses subtle traps the model doesn't know about |
| **Full-coverage** | 300-500 tokens | Security scoring dominates; many non-obvious traps (SSRF, serialization scope, IDOR) | Token penalty may outweigh security gains |

**Default to minimal-nudge** unless the challenge has ≥3 non-obvious traps that the model
would miss. Empirical testing needed to calibrate the crossover point.

### Minimal-nudge template

```
You are a senior secure {lang} engineer. Build {task} per the spec.

SECURITY: {fix1}. {fix2}. {fix3}. Stdlib only — no third-party deps. {output format constraint}. {masking/logging constraint}.

Return only the complete source code.
```

Target: 60-100 tokens. Persona + only the delta the model needs.

## Anti-Patterns (What Loses Points)

1. **Contradicting the spec** — "Don't use FTP" when the spec says to use `ftp` npm module. Fix the security within the spec's constraints.
2. **Vague security directives** — "Be careful with user input" produces no validation code.
3. **Missing cleanup** — Forgetting `finally` blocks, unclosed connections, leaked handles.
4. **Over-explaining** — Paragraphs of rationale instead of numbered fixes. Wastes tokens and dilutes the signal.
5. **Single-file monolith** — Validation mixed into business logic is harder to audit and easier to bypass.
