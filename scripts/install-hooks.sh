#!/usr/bin/env bash
# Install local Git hooks. Run once after cloning.
# Hooks live in .githooks/ (tracked) and get symlinked into .git/hooks/.

set -e

cd "$(dirname "$0")/.."

mkdir -p .git/hooks
for hook in .githooks/*; do
  [ -f "$hook" ] || continue
  name=$(basename "$hook")
  target=".git/hooks/$name"
  cp "$hook" "$target"
  chmod +x "$target"
  echo "Installed $name"
done
