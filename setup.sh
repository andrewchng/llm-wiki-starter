#!/usr/bin/env bash
# One-time setup: make the bundled skills visible to every supported agent layout.
#
# Skills live canonically in .agents/skills/ (pi convention).
# Claude Code reads skills from .claude/skills/, so we link it there.
#
# On macOS/Linux the symlink committed in this repo usually survives cloning
# and you don't need to run this at all. Run this if .claude/skills is
# missing or was checked out as a plain file (common on Windows).

set -euo pipefail
cd "$(dirname "$0")"

TARGET=".claude/skills"

if [ -L "$TARGET" ] && [ -d "$TARGET" ]; then
  echo "✓ $TARGET already points to $(readlink "$TARGET") — nothing to do."
  exit 0
fi

if [ -e "$TARGET" ]; then
  echo "! $TARGET exists but is not a valid symlink. Removing it..."
  rm -rf "$TARGET"
fi

mkdir -p .claude
if ! ln -s ../.agents/skills "$TARGET" 2>/dev/null || [ ! -L "$TARGET" ]; then
  # Symlinks unavailable (typical on Windows without Developer Mode).
  # Fall back to a real copy of the skills.
  rm -rf "$TARGET"
  cp -r .agents/skills "$TARGET"
  echo "! Symlinks not supported on this platform — copied .agents/skills -> .claude/skills instead."
  echo "! Expect \`git status\` to show .claude/skills as modified; that's harmless and"
  echo "! expected. To silence it locally, run:"
  echo "!   git update-index --skip-worktree .claude/skills 2>/dev/null || true"
else
  echo "✓ Created $TARGET -> ../.agents/skills"
fi
echo ""
echo "Verify by launching your agent in this repo and asking:"
echo '  "What skills do you have available?"'
