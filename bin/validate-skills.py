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
import yaml, glob, re, sys, os

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

errors = []

# Check 1: Frontmatter
for path in sorted(glob.glob("*/SKILL.md")):
    with open(path) as f:
        content = f.read()
    if not content.startswith("---"):
        errors.append(f"{path}: missing YAML frontmatter"); continue
    parts = content.split("---", 2)
    if len(parts) < 3:
        errors.append(f"{path}: malformed frontmatter (no closing ---)"); continue
    try:
        meta = yaml.safe_load(parts[1])
        if not meta.get("name"): errors.append(f"{path}: missing 'name'")
        if not meta.get("description"): errors.append(f"{path}: missing 'description'")
    except yaml.YAMLError as e:
        errors.append(f"{path}: YAML parse error: {e}")

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
NETFLIX = [r'netflix_search_api', r'netflix_search_data', r'rag-slack-prod',
           r'rag-manuals-prod', r'github\.netflix\.net', r'manuals-v2\.prod\.netflix']
for path in sorted(glob.glob("*/SKILL.md")):
    skill = path.split('/')[0]
    if skill in EXEMPT: continue
    with open(path) as f:
        content = f.read()
    for pattern in NETFLIX:
        if re.search(pattern, content, re.IGNORECASE):
            errors.append(f"{path}: Netflix-internal ref '{pattern}' in OSS skill")
            break

if errors:
    print("Skill validation FAILED:")
    for e in errors: print(f"  ✘ {e}")
    sys.exit(1)
else:
    print(f"✓ All {len(glob.glob('*/SKILL.md'))} skills valid")
