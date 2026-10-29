#!/usr/bin/env bash
# Apply branch protection (sub-project F, day-1) to dev and main of every
# MiraNote-AI repo. Idempotent: rerun any time the config in
# .github/branch-protection.json changes.
#
# Prerequisites:
#   - Phase 3 done (target repos have main branches)
#   - Phase 4 done (.github has main on GitHub)
#   - gh CLI authenticated to maverickjia
#
# Usage:
#   bin/apply-branch-protection.sh           # applies to all 5 repos
#   bin/apply-branch-protection.sh REPO ...  # applies only to listed repos
#
# Notes:
#   - Every PR needs 1 approver, but enforce_admins is false by design, so
#     the org owner merges their own PRs without a second reviewer. See the
#     _comment in the config for exactly what admins are and are not held to.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG="$SOURCE_DIR/.github/branch-protection.json"

ALL_REPOS=(.github miranote-web miranote-api miranote-ios mirabot)
REPOS=("$@")
if [[ ${#REPOS[@]} -eq 0 ]]; then
  REPOS=("${ALL_REPOS[@]}")
fi

if [[ ! -f "$CONFIG" ]]; then
  echo "config not found: $CONFIG" >&2
  exit 2
fi

# Strip the human-readable _comment key before sending to the GitHub API.
PAYLOAD="$(python3 -c "
import json, sys
data = json.load(open('$CONFIG'))
data.pop('_comment', None)
sys.stdout.write(json.dumps(data))
")"

for repo in "${REPOS[@]}"; do
  for branch in main dev; do
    echo "=== MiraNote-AI/$repo ($branch) ==="
    echo "$PAYLOAD" | gh api -X PUT \
      "repos/MiraNote-AI/$repo/branches/$branch/protection" \
      --input - > /dev/null
    echo "  protected"
  done
done

echo "Done."
