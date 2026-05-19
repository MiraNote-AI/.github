#!/usr/bin/env bash
# Apply branch protection (sub-project F, day-1) to main of every MiraNote-AI
# repo. Idempotent: rerun any time the config in .github/branch-protection.json
# changes.
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
#   - The PR template requires PRs to be reviewed by 1 approver, but
#     enforce_admins is false, so the org owner can merge their own PRs
#     after admin override when no second reviewer is available.
#   - Required status checks are NOT in this config; see F-2 below.
#
# F-2 (post-Phase-5 hardening):
#   After the first PR triggers `Checks` (target) or `Self-check` (.github),
#   inspect the status-check name shown in the PR UI ("checks / <name>")
#   and apply with `required_status_checks` populated. The exact context
#   name depends on how GitHub renders reusable-workflow jobs; the safe
#   path is to read the value from a real PR rather than guess.

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
  echo "=== MiraNote-AI/$repo ==="
  echo "$PAYLOAD" | gh api -X PUT \
    "repos/MiraNote-AI/$repo/branches/main/protection" \
    --input - > /dev/null
  echo "  protected"
done

echo "Done."
