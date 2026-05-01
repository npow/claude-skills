# Skill Composition Convention

Any agent can use any skill by reading its SKILL.md and following the strategy.

## How to invoke a skill from within an agent

```python
# 1. Read the skill's strategy
skill_content = Read("~/.claude/skills/{skill_name}/SKILL.md")

# 2. Spawn a general-purpose agent with the skill as system context
Agent(subagent_type="general-purpose", prompt=f"""
Follow the strategy in this skill specification:

{skill_content}

Your task: {specific_task}
""")
```

## Skill discovery

All skills live at `~/.claude/skills/{name}/SKILL.md`. To find available skills:
```bash
ls ~/.claude/skills/*/SKILL.md
```

## Key composable skills

These skills are designed to be invoked by other agents:

| Skill | Path | Use when an agent needs to... |
|-------|------|-------------------------------|
| build | `~/.claude/skills/build/SKILL.md` | Implement multi-file artifacts from a spec |
| deep-research | `~/.claude/skills/deep-research/SKILL.md` | Research a topic thoroughly before acting |
| deep-debug | `~/.claude/skills/deep-debug/SKILL.md` | Diagnose and fix a failure |
| deep-qa | `~/.claude/skills/deep-qa/SKILL.md` | Review an artifact for defects |
| deep-plan | `~/.claude/skills/deep-plan/SKILL.md` | Plan a multi-step implementation |
| monitor | `~/.claude/skills/monitor/SKILL.md` | Check health of a service/pipeline after changes |
| chart | `~/.claude/skills/chart/SKILL.md` | Visualize data |
| table | `~/.claude/skills/table/SKILL.md` | Render comparison tables |
| slides | `~/.claude/skills/slides/SKILL.md` | Create presentations |
| diagram | `~/.claude/skills/diagram/SKILL.md` | Visualize architecture/flows |

## Convention: ## Subagent Prompt

Skills that are frequently composed include a `## Subagent Prompt` section with a
distilled system prompt optimized for agent-to-agent delegation (shorter than the
full SKILL.md, focused on the execute path rather than the routing/trigger logic).
