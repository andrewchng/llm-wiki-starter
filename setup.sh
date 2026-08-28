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
ln -s ../.agents/skills "$TARGET"
echo "✓ Created $TARGET -> ../.agents/skills"
echo ""
echo "Verify by launching your agent in this repo and asking:"
echo '  "What skills do you have available?"'
