---
name: update-stop-gate
description: "Use when the user describes a bad Claude behavior pattern to add as a stop-gate rule. Handles updating both autonomy-rules.md and the classifier prompt in stop-gate.py. Trigger phrases: update stop gate, add stop gate rule, new autonomy rule, add stall class, update autonomy rules, add behavior to stop gate."
---

# Update Stop Gate

Add a new stall-detection rule to the autonomy classifier. Two files must be updated in sync.

## Files

| File | Role |
|------|------|
| `~/.claude/autonomy-rules.md` | Source of truth — human-readable rules the classifier LLM reads |
| `~/.claude/hooks/stop-gate.py` | Classifier prompt — contains lettered stall checks (a)-(z) in `build_classifier_prompt()` |

## Procedure

### 1. Read both files

Read `~/.claude/autonomy-rules.md` and `~/.claude/hooks/stop-gate.py` in parallel. Note:
- The last lettered classifier check (to know what letter comes next)
- The structure of existing rule bullets in the "WHAT DOES NOT REQUIRE ASKING" section

### 2. Generalize from the user's example

The user gives a specific incident. Extract the **class of behavior**, not the specific case. Ask:
- What cognitive error causes this? (e.g., "silencing the symptom feels like fixing the problem")
- What are 5-8 concrete manifestations across different domains?
- What is the ONE narrow exception where this behavior is legitimate?

Never use the user's specific variable names, function names, or project details in the rule.

### 3. Scrub for internal/proprietary language

Before writing anything, scan the user's description for company-specific terms (product names, internal tool names, team names, proprietary library names). The rules files must be generic — they contain NO employer-specific language. Replace any such terms with generic equivalents.

### 4. Add rule to autonomy-rules.md

Insert a new bullet in the **"WHAT DOES NOT REQUIRE ASKING"** section, following this exact pattern:

```
- **{Bold header}** — {one-sentence description of the behavior class and the cognitive error}. All of these are stalls:
  - {Concrete manifestation 1}
  - {Concrete manifestation 2}
  - {Concrete manifestation 3} 
  - {4-8 total manifestations, each a specific observable action}
  - The ONLY time {this behavior} is legitimate: {narrow exception with specific conditions that must ALL be met}
```

Place it logically near related existing rules (e.g., a new "bad fix quality" rule goes near "evidence-free dismissal" and "minimum-viable-effort evasion").

### 5. Add classifier check to stop-gate.py

In the `build_classifier_prompt()` function, find the last lettered stall check and add the next one. Follow this exact pattern:

```
  ({next_letter}) {Header} stall — ALL of:
    - The last assistant message {observable trigger condition}
    - {Specific evidence of the bad behavior in the message}
    - {What is MISSING from the message that should be there}
    - {Why it's plausibly within Claude's ability to do better}
```

The classifier check must be:
- Mechanically evaluable from the assistant message text
- Based on observable signals (what's present AND what's absent)
- 3-5 bullet points (not more — the classifier prompt is already long)

### 6. Verify

Run: `python3 -c "import py_compile; py_compile.compile('$HOME/.claude/hooks/stop-gate.py', doraise=True)"`

If it fails, fix the syntax error (usually an unescaped quote or bad indentation in the f-string).

## Golden Rules

1. **Generalize, never overfit.** The user's example is ONE instance. The rule must catch the class across all domains.
2. **Rules must be OSS-safe.** No company names, product names, internal tool names, or proprietary terms. Ever.
3. **Both files or neither.** Never update autonomy-rules.md without updating the classifier check in stop-gate.py, or vice versa. They must stay in sync.
4. **Cognitive error first.** Every rule header includes WHY the agent makes this mistake. Without the "why," the classifier can't distinguish the bad behavior from a legitimate action.
5. **Narrow escape hatches.** The "ONLY time X is legitimate" clause must have specific conditions, not vague qualifiers. "When you've investigated and confirmed the root cause is outside your control" is good. "When appropriate" is not.
6. **Verify Python syntax.** The classifier prompt is inside an f-string. Curly braces in the prompt must be doubled (`{{` / `}}`). Always compile-check after editing.
