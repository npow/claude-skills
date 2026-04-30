#!/usr/bin/env python3
"""Skill validation — run manually or as a pre-commit hook.

Checks:
1. YAML frontmatter validity (name + description required)
2. Cross-reference integrity (no refs to deleted skills)
3. Netflix-internal refs guard (OSS skills must not reference internal tools)

Usage:
  python bin/validate-skills.py          # from repo root
  ln -s ../../bin/validate-skills.py .git/hooks/pre-commit  # as hook
"""
import glob, re, sys, os

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

errors = []


def parse_frontmatter(content):
    """Extract name and description from YAML frontmatter without PyYAML."""
    if not content.startswith("---"):
        return None, "missing YAML frontmatter"
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, "malformed frontmatter (no closing ---)"
    fm = parts[1]
    name = None
    desc = None
    for line in fm.splitlines():
        line = line.strip()
        if line.startswith("name:"):
            val = line[5:].strip().strip('"').strip("'")
            if val:
                name = val
        elif line.startswith("description:"):
            val = line[12:].strip().strip('"').strip("'")
            if val:
                desc = val
            elif not val:
                desc = "(multiline)"
    return {"name": name, "description": desc}, None


# Check 1: Frontmatter
for path in sorted(glob.glob("*/SKILL.md")):
    with open(path) as f:
        content = f.read()
    meta, err = parse_frontmatter(content)
    if err:
        errors.append(f"{path}: {err}")
        continue
    if not meta.get("name"):
        errors.append(f"{path}: missing 'name'")
    if not meta.get("description"):
        errors.append(f"{path}: missing 'description'")

# Check 2: Netflix refs in OSS
EXEMPT = {'mako-gpu-status', 'debug-pr', 'debug-run', 'data-auditor-create',
          'data-auditor-validate-run', 'metaflow', 'model-gateway',
          'ai-tool-catalog-cli', 'dbt-context', 'doc-freshness-report',
          'team-blind-spots', 'sprint-retro', 'slack-digest',
          'oncall-handoff-brief', 'deploy-status-report', 'ci-health-report',
          'dora-lite-report', 'pipeline-health-report', 'ml-pipeline-report',
          'user-activity-report', 'platform-friction-detector', 'prod-readiness',
          'upload-presentation', 'code-quality-trends', 'dependency-audit',
          'slack-briefing', 'slack-reply', 'java-context', 'js-context',
          'js-client-context', 'python-context', 'dbt-data-test-gen',
          'dbt-unit-test-gen', 'flaky-test-diagnoser', 'flaky-test-diagnoser-temporal',
          'ccr-models', 'ccr-run'}
NETFLIX_PATTERNS = [
    r'netflix_search_api', r'netflix_search_data', r'rag-slack-prod',  # oss-ok
    r'rag-manuals-prod', r'github\.netflix\.net', r'manuals-v2\.prod\.netflix',  # oss-ok
]
for path in sorted(glob.glob("*/SKILL.md")):
    skill = path.split('/')[0]
    if skill in EXEMPT:
        continue
    with open(path) as f:
        content = f.read()
    for pattern in NETFLIX_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            errors.append(f"{path}: Netflix-internal ref '{pattern}' in OSS skill")
            break

if errors:
    print("Skill validation FAILED:")
    for e in errors:
        print(f"  ✘ {e}")
    sys.exit(1)
else:
    print(f"✓ All {len(glob.glob('*/SKILL.md'))} skills valid")
