#!/usr/bin/env bash
# Local mirror of .github/workflows/sync-ai-docs.yml.
# Use for bootstrap (mode=direct) or when the Action is broken (mode=pr).
#
# Usage:
#   bin/sync-ai-docs.sh           # default: opens a PR in each target
#   bin/sync-ai-docs.sh direct    # pushes straight to main (bootstrap / emergency)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PARENT_DIR="$(cd "$SOURCE_DIR/.." && pwd)"
TARGETS=(miranote-web miranote-api miranote-ios mirabot)
MODE="${1:-pr}"

if [[ "$MODE" != "pr" && "$MODE" != "direct" ]]; then
  echo "Unknown mode: $MODE (expected 'pr' or 'direct')" >&2
  exit 2
fi

short="$(git -C "$SOURCE_DIR" rev-parse --short HEAD 2>/dev/null || echo local)"

mirror_files() {
  local target="$1"
  cp "$SOURCE_DIR/CLAUDE.md" "$target/CLAUDE.md"
  mkdir -p "$target/docs/ai"
  rsync -a --delete "$SOURCE_DIR/docs/ai/" "$target/docs/ai/"
}

for repo in "${TARGETS[@]}"; do
  target="$PARENT_DIR/$repo"
  echo "=== $repo ==="
  if [[ ! -d "$target/.git" ]]; then
    echo "  skip: not a git repo at $target"
    continue
  fi

  if [[ "$MODE" == "direct" ]]; then
    (
      cd "$target"
      git checkout -B main
      mirror_files "$target"
      git add -A
      if git diff --cached --quiet; then
        echo "  no changes"
        exit 0
      fi
      git commit -m "chore: sync AI docs from MiraNote-AI/.github@${short}"
      git push -u origin main
    )
  else
    branch="chore/sync-ai-docs-local-${short}"
    (
      cd "$target"
      git fetch origin main
      git checkout -B "$branch" origin/main
      mirror_files "$target"
      git add -A
      if git diff --cached --quiet; then
        echo "  no changes"
        exit 0
      fi
      git commit -m "chore: sync AI docs from .github@${short}"
      git push -u origin "$branch"
      gh pr create \
        --base main \
        --head "$branch" \
        --title "chore: sync AI docs from .github@${short}" \
        --body "Manual sync from \`bin/sync-ai-docs.sh\`."
    )
  fi
done

echo "Done."
