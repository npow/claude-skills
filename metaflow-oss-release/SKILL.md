---
name: metaflow-oss-release
description: Cut an OSS release of Netflix/metaflow on github.com — version bump PR, GitHub release, PyPI publish, internal pin update.
---

# Cut a Metaflow OSS Release

Releases the public Netflix/metaflow package to PyPI via GitHub release-triggered CI.

**Release chain:**
1. Version bump PR on Netflix/metaflow (`metaflow/version.py`)
2. Merge PR
3. Create GitHub release (tag = version number)
4. GitHub Actions `publish.yml` runs tests → publishes `metaflow` + `metaflow-stubs` to PyPI (OIDC Trusted Publishing)
5. Update `OSS_VERSION` pin in corp/mli-metaflow-custom

## 1. Parse arguments

Accept these forms:
- `(no args)` → `patch` bump
- `patch` / `minor` / `major` → that bump type
- `2.19.25` → explicit version

## 2. Determine next version

```bash
# Current version from metaflow/version.py on main
CURRENT=$(gh api repos/Netflix/metaflow/contents/metaflow/version.py --jq '.content' | base64 -d | grep -oP '"\K[0-9]+\.[0-9]+\.[0-9]+')

# Latest release tag (should match)
LATEST=$(gh release list --repo Netflix/metaflow --limit 1 --json tagName --jq '.[0].tagName')
```

Compute next version from CURRENT based on bump type:
- `patch`: 2.19.24 → 2.19.25
- `minor`: 2.19.24 → 2.20.0
- `major`: 2.19.24 → 3.0.0

If CURRENT != LATEST, warn — someone may have already bumped the version without releasing.

## 3. Check what's changed

```bash
# Commits since last release
gh api "repos/Netflix/metaflow/compare/${LATEST}...main" \
  --jq '.commits[] | "- \(.commit.message | split("\n")[0]) by @\(.author.login // "unknown")"'

# Merged PRs since last release
gh pr list --repo Netflix/metaflow --state merged --base main \
  --json number,title,mergedAt,author \
  --jq ".[] | select(.mergedAt > \"$(gh release view "$LATEST" --repo Netflix/metaflow --json createdAt --jq '.createdAt')\")"
```

Present summary and confirm the release scope looks correct.

## 4. Create version bump PR

Clone (or use existing checkout), create branch, bump version, push, create PR:

```bash
# If no local checkout exists
cd /tmp && gh repo clone Netflix/metaflow metaflow-release && cd metaflow-release

# Create branch and bump
git checkout -b "release/${NEXT_VERSION}"
echo "metaflow_version = \"${NEXT_VERSION}\"" > metaflow/version.py
git add metaflow/version.py
git commit -m "release: ${NEXT_VERSION}"
git push -u origin "release/${NEXT_VERSION}"

# Create PR
gh pr create --repo Netflix/metaflow \
  --title "release: ${NEXT_VERSION}" \
  --body "$(cat <<'EOF'
## Summary
- Bump metaflow version to ${NEXT_VERSION}

## Test plan
- [ ] Verify version string is correct in `metaflow/version.py`
- [ ] CI passes
EOF
)"
```

Report the PR URL and wait for merge. **Do NOT proceed until the PR is merged.**

## 5. Create GitHub release

After the version bump PR is merged, create the release. GitHub auto-generates "What's Changed" notes from merged PRs.

```bash
gh release create "${NEXT_VERSION}" \
  --repo Netflix/metaflow \
  --target main \
  --title "${NEXT_VERSION}" \
  --generate-notes \
  --notes-start-tag "${LATEST}"
```

This triggers `.github/workflows/publish.yml`:
1. Runs `test.yml` (unit tests)
2. Runs `test-stubs.yml` (stub tests)
3. On success: builds and publishes `metaflow` + `metaflow-stubs` to PyPI via OIDC

## 6. Monitor publish workflow

```bash
# Watch for the Publish workflow run triggered by the release
gh run list --repo Netflix/metaflow --workflow publish.yml --limit 3 \
  --json databaseId,status,conclusion,createdAt,url

# Watch a specific run
gh run watch <RUN_ID> --repo Netflix/metaflow
```

The publish workflow takes ~5-10 minutes. If tests fail, the deploy job is skipped and nothing is published.

If the workflow fails:
- Check which job failed: `gh run view <RUN_ID> --repo Netflix/metaflow --log-failed`
- Tests: may indicate a real regression — do NOT retry without investigating
- Deploy: may be a transient PyPI/OIDC issue — safe to re-run

## 7. Verify on PyPI

```bash
# Check PyPI for the new version
pip index versions metaflow 2>/dev/null | head -1
# Or via API
curl -s "https://pypi.org/pypi/metaflow/${NEXT_VERSION}/json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Published: metaflow {d[\"info\"][\"version\"]} at {d[\"urls\"][0][\"upload_time\"]}')"

# Also verify stubs
curl -s "https://pypi.org/pypi/metaflow-stubs/${NEXT_VERSION}/json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Published: metaflow-stubs {d[\"info\"][\"version\"]} at {d[\"urls\"][0][\"upload_time\"]}')"
```

## 8. Update internal OSS_VERSION pin

After the OSS release is live on PyPI, update the internal repo to pin to the new version:

```bash
# Check current pin
GH_HOST=github.netflix.net gh api repos/corp/mli-metaflow-custom/contents/OSS_VERSION --jq '.content' | base64 -d

# Create a PR to update the pin
# The file should contain: ==${NEXT_VERSION}
```

This step is optional — the internal team may have their own cadence for bumping the pin.
Ask before proceeding with this step.

## Reference

- OSS repo: `Netflix/metaflow` on github.com
- Internal repo: `corp/mli-metaflow-custom` on github.netflix.net
- Version file: `metaflow/version.py` (single line: `metaflow_version = "X.Y.Z"`)
- Publish workflow: `.github/workflows/publish.yml` (triggered by `release:published`)
- PyPI auth: OIDC Trusted Publishing (no stored tokens)
- Packages published: `metaflow` + `metaflow-stubs` (both same version)
- Release notes: auto-generated by GitHub (`--generate-notes --notes-start-tag`)
- Naming: tags and releases use bare semver (`2.19.25`), no `v` prefix
