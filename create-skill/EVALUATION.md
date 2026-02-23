# Skill Evaluation

How to test skills, verify they work, and iterate based on real usage.

## Test prompt categories

Every skill should be tested with 4 types of prompts. Write 3-5 prompts per category.

### 1. Explicit invocation

User directly names the skill or its exact purpose:

```
/create-skill a PR review assistant
Create a skill for generating changelogs
Build me a board game skill
```

**What to verify**: Skill activates. Workflow starts from step 1. All reference files are accessible.

### 2. Implicit invocation

User describes a need that matches the skill's description keywords, without naming it:

```
I need Claude to automatically review my code
Help me set up a slash command for deployments
I want to digitize Settlers of Catan
```

**What to verify**: Skill activates from description matching. Same quality output as explicit invocation.

### 3. Contextual (noisy) prompts

Realistic prompts with extra context, ambiguity, or constraints:

```
We're using a monorepo with turborepo and I need a skill that runs our specific test suite across packages — it should understand our workspace structure
I want a board game thing but specifically for a homebrew card game my friend designed, here are the rules [long rules dump]
```

**What to verify**: Skill activates and handles the extra context. Doesn't get confused by irrelevant details. Extracts the relevant requirements.

### 4. Negative controls

Prompts where the skill should NOT activate:

```
What is a skill?                          → question, not creation
Fix the bug in my existing skill          → editing, not creating
How do skills work in Claude Code?        → documentation query
```

**What to verify**: Skill does NOT activate. Claude handles the request normally.

## Verification protocol

After writing a skill, run it through this verification sequence:

### Phase 1: Structure check

Without running the skill, manually inspect the files:

```
1. Count SKILL.md content lines (target: 50-100)
2. Verify zero code blocks in SKILL.md
3. Verify all reference files are linked from SKILL.md
4. Verify reference files are under 500 lines each
5. Verify description contains trigger keywords
6. Verify golden rules use imperative language (no "should", "consider")
7. Verify self-review checklist items are objectively verifiable
8. Verify at least one feedback loop exists
```

### Phase 2: Dry run

Mentally trace through the workflow for a specific use case:

```
1. Pick a concrete example (e.g., "create a skill for reviewing Python code")
2. Walk through each workflow step
3. For each step, check: does the instruction tell me EXACTLY what to do?
4. For each step, check: does the reference file contain the detail I need?
5. At the self-review checklist, check: can I verify each item right now?
6. At the golden rules, check: did I violate any during the dry run?
```

If you get stuck at any step, the skill needs more detail at that point.

### Phase 3: Live test

Actually invoke the skill and use it to build something:

```
1. Start a new conversation (fresh context)
2. Invoke the skill with an explicit prompt
3. Follow the workflow it produces
4. Note where Claude hesitates, asks unnecessary questions, or produces inconsistent output
5. Note where Claude skips steps or ignores golden rules
6. Note where the self-review checklist catches real issues vs. passes trivially
```

### Phase 4: Iteration

For every issue found in Phase 3:

| Issue type | Fix location |
|---|---|
| Claude didn't know what to do at a step | Add detail to the reference file for that step |
| Claude did the wrong thing | Add a golden rule preventing it |
| Claude skipped verification | Make the self-review checklist item more specific |
| Output quality was inconsistent | Replace vague instruction with concrete specification |
| Claude loaded unnecessary reference files | Improve the one-line summaries in SKILL.md |
| Skill triggered when it shouldn't have | Narrow the description keywords |
| Skill didn't trigger when it should have | Add missing keywords to description |

## Quality rubric

Grade the skill on these dimensions:

| Dimension | A | B | C |
|---|---|---|---|
| **Discovery** | Triggers correctly for all positive prompts, never for negative | Triggers for most positive, occasionally for negative | Misses common phrasings or false-triggers |
| **Structure** | SKILL.md under 100 lines, clean progressive disclosure | SKILL.md slightly long but organized | SKILL.md is a manual, or reference files are disorganized |
| **Specificity** | Zero vague adjectives, all instructions are concrete | Mostly concrete, 1-2 vague spots | Multiple "clean/good/appropriate" without specification |
| **Feedback loops** | Automated verification + self-review + failure diagnosis | Self-review checklist only | No verification step |
| **Golden rules** | 3-8 hard rules, each preventing a known failure mode | Rules exist but some are soft ("try to") | No golden rules, or rules are generic |
| **Consistency** | Two runs on the same input produce structurally identical output | Minor cosmetic differences between runs | Significant structural differences between runs |

Target: A on all dimensions before delivering.

## Common pitfalls

### The encyclopedia trap

SKILL.md grows to 300+ lines because "the agent needs all this context." It doesn't. The agent needs a map. Move the content to reference files.

**Signal**: You're scrolling through SKILL.md.
**Fix**: Extract everything after the workflow/checklist/rules/index into reference files.

### The soft rule trap

Golden rules contain "should", "consider", "prefer", "try to." These are suggestions, not rules. The agent will ignore them under pressure.

**Signal**: A golden rule starts with "It's best to" or "Consider."
**Fix**: Rewrite as "Always" or "Never." If you can't make it absolute, it's guidance for a reference file, not a golden rule.

### The missing negative trap

Skill triggers for irrelevant prompts because the description is too broad.

**Signal**: Skill activates when the user asks a question or wants to edit (not create).
**Fix**: Add specificity to the description. "Use when the user asks to **build, create, or scaffold**" is narrower than "Use for skill-related tasks."

### The vague output trap

Skill produces different quality output each run because instructions say "make it good" instead of specifying what "good" means.

**Signal**: Two runs produce visually or structurally different results.
**Fix**: Run the adjective test (see [WRITING.md](WRITING.md)). Replace every subjective adjective with a concrete specification.

### The skipped verification trap

Self-review checklist exists but items are so easy they always pass trivially.

**Signal**: Every checklist item passes on first run without finding issues.
**Fix**: Add harder checks. "No console errors" is easy. "Play a complete game to game-over and verify winner detection" is meaningful. If the checklist never catches anything, it's not checking hard enough.

### The retry trap

Failure diagnosis says "if tests fail, fix and retry." This isn't diagnosis — it's hope.

**Signal**: The word "retry" or "try again" in failure handling.
**Fix**: Add a symptom → cause → fix table. The agent must identify WHAT failed and WHY before attempting a fix.
