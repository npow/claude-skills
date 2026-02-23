---
name: init-github-repo
description: Initializes a Git repository with a complete GitHub presence — JTBD-focused README with badges, CI/CD workflow, license, .gitignore, and SEO-optimized repo description and topics. Use when the user asks to initialize a repo, set up GitHub, create a readme, push to GitHub, set up CI/CD, or prepare a project for open source.
---

# Init GitHub Repo

Initializes a complete GitHub repository by detecting the project type and generating a JTBD-focused README, CI/CD pipeline, license, .gitignore, and SEO-optimized repo metadata.

## Workflow

1. **Detect project type** — read pyproject.toml, package.json, Cargo.toml, go.mod, or other markers to determine language, package name, license, and version. See [CICD.md](CICD.md).
2. **Initialize git** — if not already a repo, run `git init`, then ask the user for their preferred name/email and set it at repo level. See [GITHUB.md](GITHUB.md).
3. **Create .gitignore** — generate language-appropriate .gitignore. See [CICD.md](CICD.md).
4. **Create LICENSE** — detect license from project metadata or default to Apache-2.0. See [GITHUB.md](GITHUB.md).
5. **Write README.md** — JTBD-focused structure with badges, problem statement, quick start, and install. See [README-TEMPLATE.md](README-TEMPLATE.md).
6. **Create CI/CD workflow** — generate .github/workflows/ci.yml matched to the detected language. See [CICD.md](CICD.md).
7. **Create GitHub repo and push** — create remote with `gh repo create`, set description and topics, commit and push. See [GITHUB.md](GITHUB.md).
8. **Update profile README** — clone the user's profile repo (`GH_USER/GH_USER`) if not present, add the new repo to the correct section alphabetically, commit and push. See [GITHUB.md](GITHUB.md).
9. **Verify** — confirm `gh repo view` shows correct description and topics, profile README updated, badges render correctly. See [GITHUB.md](GITHUB.md).

## Self-review checklist

Before delivering, verify ALL:

- [ ] README first paragraph answers "what job does this do for me?" — not "what is this tool"
- [ ] README has zero feature bullet lists before the problem statement
- [ ] All badge URLs contain the correct GitHub owner/repo and package name
- [ ] CI workflow runs the correct test command for the detected language (`pytest` for Python, `npm test` for Node, etc.)
- [ ] .gitignore includes language-specific entries (e.g., `__pycache__/` for Python, `node_modules/` for Node)
- [ ] LICENSE file matches the license field in project metadata
- [ ] Repo description is under 100 characters with no trailing period
- [ ] Repo has 5-10 topics that include the language name, problem domain, and 2-3 SEO keywords
- [ ] Git user.name and user.email are set at repo level (check with `git config user.name`)
- [ ] `gh repo view` succeeds and shows the description
- [ ] Profile README contains the new repo in the correct section, alphabetically ordered
- [ ] Private repos have 🔒 at end of line in profile README, public repos do not

## Golden rules

Hard rules. Never violate these.

1. **JTBD first, features never.** The README opens with the problem the user has, not what the tool does. "You have X problem" before "This tool does Y." Never write a feature bullet list as the first section.
2. **Badges must resolve.** Every badge URL must contain the actual GitHub owner/repo slug and package name. Never use placeholder values like `username/repo`. Verify by constructing the URL from `gh repo view --json nameWithOwner`.
3. **Detect, never assume.** Read project metadata files to determine language, package name, license, and test commands. Never hardcode "Python" or "MIT" without checking the actual files first.
4. **Description is a headline.** Under 100 characters, no trailing period, no implementation details. It answers "why would I click this?" not "what technology does this use?"
5. **Topics are SEO.** Include the programming language, the problem domain keyword, and 2-3 terms someone would search for on GitHub to find this project. Never use generic tags like "awesome" or "tool."
6. **Git identity is explicit.** Always ask the user for their preferred name/email and set it at the repo level (not global) when initializing a new repo. If the user declines, let the global config apply.

## Reference files

| File | Contents |
|------|----------|
| [README-TEMPLATE.md](README-TEMPLATE.md) | JTBD readme structure, badge format templates per language, writing rules for each section |
| [CICD.md](CICD.md) | Project type detection logic, CI/CD workflow templates per language, .gitignore templates |
| [GITHUB.md](GITHUB.md) | Git init commands, gh repo create/edit commands, description and topics guidance, LICENSE templates, verification steps |
