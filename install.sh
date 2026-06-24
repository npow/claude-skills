#!/usr/bin/env bash
#
# install.sh — set up the claude-skills library plus github/spec-kit.
#
# What it does:
#   1. Symlinks this repo into ~/.claude/skills so Claude Code loads every skill
#      here (skills depend on ../_shared/, so the whole repo is linked as one).
#   2. Installs (or upgrades) spec-kit's `specify` CLI via `uv tool`.
#   3. Scaffolds spec-kit's slash commands (speckit-specify, speckit-plan,
#      speckit-tasks, ...) into the skills root so they are globally available.
#
# Usage:  ./install.sh            # full install
#         ./install.sh --no-speckit   # skip spec-kit, just link the skills
#
# Override the Claude config dir with CLAUDE_CONFIG_DIR (defaults to ~/.claude).

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
SKILLS="$CLAUDE_DIR/skills"
SPECKIT_REPO="git+https://github.com/github/spec-kit.git"
WITH_SPECKIT=1

for arg in "$@"; do
  case "$arg" in
    --no-speckit) WITH_SPECKIT=0 ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mwarn:\033[0m %s\n' "$*" >&2; }

# --- 1. Link this repo into ~/.claude/skills -------------------------------
mkdir -p "$CLAUDE_DIR"
if [ -L "$SKILLS" ]; then
  if [ "$(readlink "$SKILLS")" = "$REPO_DIR" ]; then
    log "Skills symlink already points here ✓"
  else
    log "Repointing skills symlink: $(readlink "$SKILLS") -> $REPO_DIR"
    ln -sfn "$REPO_DIR" "$SKILLS"
  fi
elif [ -e "$SKILLS" ]; then
  backup="$SKILLS.bak.$$"
  warn "Existing $SKILLS found; backing up to $backup"
  mv "$SKILLS" "$backup"
  ln -s "$REPO_DIR" "$SKILLS"
  log "Linked $REPO_DIR -> $SKILLS"
else
  ln -s "$REPO_DIR" "$SKILLS"
  log "Linked $REPO_DIR -> $SKILLS"
fi

if [ "$WITH_SPECKIT" -eq 0 ]; then
  log "Done (spec-kit skipped). Restart Claude Code to pick up changes."
  exit 0
fi

# --- 2. Install / upgrade the spec-kit `specify` CLI -----------------------
if command -v uv >/dev/null 2>&1; then
  log "Installing/upgrading spec-kit (specify CLI) via uv..."
  uv tool install --force specify-cli --from "$SPECKIT_REPO"
elif command -v specify >/dev/null 2>&1; then
  warn "'uv' not found; using already-installed specify (skipping upgrade)."
else
  warn "'uv' not found and 'specify' not installed."
  warn "Install uv (https://docs.astral.sh/uv/) then re-run, or pass --no-speckit."
  exit 1
fi

# --- 3. Scaffold spec-kit skills into the skills root ----------------------
# spec-kit's `init` is project-scoped, so generate into a staging dir and copy
# the speckit-* skill dirs up to the repo root, where the ~/.claude/skills
# symlink makes them globally discoverable.
log "Scaffolding spec-kit skills..."
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
specify init "$STAGE/proj" --integration claude --ignore-agent-tools --force >/dev/null
if compgen -G "$STAGE/proj/.claude/skills/speckit-*" >/dev/null; then
  cp -R "$STAGE/proj/.claude/skills/"speckit-* "$REPO_DIR/"
  count=$(find "$REPO_DIR" -maxdepth 1 -type d -name 'speckit-*' | wc -l | tr -d ' ')
  log "Installed $count spec-kit skills into $SKILLS/"
else
  warn "spec-kit produced no speckit-* skills; layout may have changed."
fi

cat <<EOF

$(log "Done.")
  • This repo's skills are linked at: $SKILLS
  • spec-kit skills installed:        /speckit-* (run /speckit-specify to start)

The spec-kit skills drive a per-project workflow and need a .specify/ directory
in each project. To enable them in a project, run there:

    specify init . --integration claude

Restart Claude Code to load the new skills.
EOF
