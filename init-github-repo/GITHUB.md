# GitHub Setup

Git init, gh repo commands, description, topics, LICENSE, and verification.

## Contents
- Git initialization
- Creating the GitHub repo
- Repo description rules
- Topics / SEO tags
- LICENSE file templates
- Initial commit and push
- Update profile README
- Verification
- Failure diagnosis

## Git initialization

If the directory is not already a git repo (no `.git/` directory):

```bash
git init
```

After init (or if already a git repo), ask the user what name and email they want for this repo's git identity. Then set it at the repo level:

```bash
git config user.name "USER_PROVIDED_NAME"
git config user.email "USER_PROVIDED_EMAIL"
```

Always set at repo level (no `--global` flag). This ensures the identity is correct for this project without affecting other repos. If the user declines or says "use default", skip this step and let the global config apply.

## Creating the GitHub repo

Use `gh repo create` to create the remote:

```bash
gh repo create REPO_NAME --public --source=. --push
```

- `REPO_NAME` → use the directory name (e.g., `memshield`, `claude-relay`)
- `--public` → default to public. Use `--private` only if the user asks
- `--source=.` → uses the current directory
- `--push` → pushes the initial commit after creation

If the repo already exists on GitHub, skip creation and just add the remote:

```bash
git remote add origin https://github.com/OWNER/REPO.git
```

## Repo description rules

Set with:

```bash
gh repo edit --description "DESCRIPTION"
```

Rules for the description:
- Under 100 characters
- No trailing period
- No implementation details (no "Python library", "built with X")
- Answers "why would I click this?" not "what is this?"
- Active voice, present tense

| Bad | Good | Why |
|-----|------|-----|
| "A Python library for AI agent memory integrity defense." | "Stop memory poisoning attacks on your AI agents" | Removes "Python library" boilerplate, focuses on what you DO |
| "OpenAI-compatible API server that routes through Claude Code." | "Use any OpenAI client with Claude Code's tools and MCP servers" | Describes the benefit, not the mechanism |
| "CLI tool for managing Docker containers efficiently." | "Run your Docker stack with one command" | Concrete outcome, not vague "efficiently" |
| "Fast and lightweight testing framework for JavaScript." | "Find bugs before your users do" | Emotional hook, not adjectives |

## Topics / SEO tags

Set with:

```bash
gh repo edit --add-topic TOPIC1 --add-topic TOPIC2 ...
```

Generate 5-10 topics following this formula:

1. **Language** (1 topic): `python`, `javascript`, `rust`, `go`
2. **Package ecosystem** (1 topic): `pypi`, `npm`, `crates-io`
3. **Primary domain** (1-2 topics): `security`, `ai-agents`, `memory`, `vector-database`
4. **Problem keywords** (2-3 topics): what someone would search for — `prompt-injection`, `memory-poisoning`, `llm-security`
5. **Framework/tool names** (1-2 topics): `langchain`, `openai`, `chroma` — only if the project integrates with them

Rules:
- All lowercase, hyphens for spaces (GitHub requirement)
- Never use generic vanity tags: `awesome`, `best`, `tool`, `library`, `framework`
- Never use tags with fewer than 100 uses on GitHub unless they're domain-specific
- Include at least one tag that a non-expert would search for (e.g., `ai-security` not just `adversarial-ml`)

### Example topic sets

**memshield** (Python, AI security):
```
python pypi ai-security memory-poisoning llm-security ai-agents vector-database langchain prompt-injection
```

**claude-relay** (Python, dev tools):
```
python openai-api anthropic claude llm proxy dev-tools api-server
```

**A React component library**:
```
react typescript ui-components design-system npm
```

## LICENSE file templates

Detect the license from project metadata first. If not found, default to Apache-2.0.

### Apache 2.0

Write the full Apache 2.0 text. The key parts:

```
                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   ...

   Copyright [YEAR] [OWNER]

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0
   ...
```

Use `YEAR` = current year, `OWNER` = the git user.name from the repo config (set during init), or read from project metadata if available.

### MIT

```
MIT License

Copyright (c) [YEAR] [OWNER]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

For other licenses, use the full SPDX text from https://spdx.org/licenses/.

## Initial commit and push

After all files are created:

```bash
git add README.md LICENSE .gitignore .github/
git add -A  # catch any other new files
git commit -m "Initial commit

Set up repository with README, CI/CD, license, and .gitignore.

Co-Authored-By: Claude <noreply@anthropic.com>"
git branch -M main
git push -u origin main
```

Then set description and topics:

```bash
gh repo edit --description "DESCRIPTION"
gh repo edit --add-topic topic1 --add-topic topic2 ...
```

## Update profile README

After every new repo is created and pushed, update the user's GitHub profile README. First, determine the GitHub username:

```bash
GH_USER=$(gh api user --jq '.login')
PROFILE_DIR="$HOME/code/$GH_USER"
```

### Step 1: Ensure the profile repo is cloned

```bash
# Only clone if not already present
if [ ! -d "$PROFILE_DIR/.git" ]; then
    git clone "git@github.com:$GH_USER/$GH_USER.git" "$PROFILE_DIR"
fi
```

Always check first — never clone over an existing directory.

### Step 2: Pull latest

```bash
git -C "$PROFILE_DIR" pull --rebase origin main
```

### Step 3: Determine the correct section

Read the profile README and find the right section for the new repo based on its domain:

| Project domain | Section in profile README |
|---------------|--------------------------|
| AI/LLM tools (agents, LLM utilities, MCP servers) | **Currently Building → AI/LLM Tools** |
| Security (scanning, defense, linting) | **Currently Building → Security** |
| Research (analysis, reports) | **Currently Building → Research** |
| Data visualization | **Visualizations** |
| Board games | **Board Games** |
| ML research (models, papers) | **ML Research** |
| Libraries and developer tools | **Libraries & Tools** |

### Step 4: Format the entry

Each entry follows this exact format:

```
- EMOJI **[repo-name](https://github.com/GH_USER/repo-name)** — One-line description from the repo's GitHub description.
```

Rules:
- Pick an emoji that represents the project's domain (shield for security, robot for AI, etc.)
- The description is the same text as the GitHub repo description (the one set with `gh repo edit --description`)
- Private repos append ` 🔒` at the end of the line
- Entries within each section are ordered **alphabetically by repo name**

### Step 5: Insert alphabetically

Find the correct alphabetical position within the target section. Insert the new line there. Do not append to the end of the section.

Example: Adding `memshield` to the Security section that currently has `clawbreaker` and `outclaw`:
- `clawbreaker` (c) → `memshield` (m) → `outclaw` (o)
- Insert between `clawbreaker` and `outclaw`

### Step 6: Commit and push

```bash
git -C "$PROFILE_DIR" add README.md
git -C "$PROFILE_DIR" commit -m "Add repo-name

Co-Authored-By: Claude <noreply@anthropic.com>"
git -C "$PROFILE_DIR" push origin main
```

## Verification

After push, verify everything:

```bash
# 1. Check repo exists and description is set
gh repo view --json nameWithOwner,description,repositoryTopics

# 2. Check git identity is set
git config user.name   # must be non-empty
git config user.email  # must be non-empty

# 3. Check CI workflow was detected
gh run list --limit 1  # should show a run (may be pending)

# 4. Check files on remote
gh api repos/OWNER/REPO/contents/ --jq '.[].name'
# Should include: README.md, LICENSE, .gitignore, .github
```

## Failure diagnosis

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `gh repo create` fails with "name already exists" | Repo already exists on GitHub | Use `gh repo view` to check, then `git remote add origin` instead |
| `gh repo edit --description` fails | Not authenticated or wrong repo context | Run `gh auth status` to verify auth, ensure you're in the repo directory |
| `gh repo edit --add-topic` fails with invalid topic | Topic contains uppercase or spaces | Convert to lowercase-with-hyphens: "AI Security" → "ai-security" |
| `git push` fails with "remote already exists" | Remote `origin` was already set | Remove and re-add: `git remote remove origin && git remote add origin URL` |
| CI doesn't trigger after push | Workflow file not at `.github/workflows/ci.yml` | Verify exact path — GitHub is case-sensitive and requires the `workflows` (plural) directory |
| `gh` command not found | GitHub CLI not installed | Install with: `brew install gh` (macOS), `sudo apt install gh` (Ubuntu), or see https://cli.github.com/ |
| If none of the above | Run `gh repo view --json nameWithOwner` to confirm you're operating on the right repo, then check `gh api repos/OWNER/REPO` for the full repo state |
