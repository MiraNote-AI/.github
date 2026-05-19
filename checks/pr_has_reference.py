"""Rule 6 (zeta): PR description references an issue, spec, or URL.

Reads PR metadata from environment variables populated by the CI workflow:
- PR_BODY:   the pull request body text
- PR_BRANCH: the pull request head branch name (used for bot exemption)

Bot PRs (head branch matching `chore/sync-ai-docs-*`) are exempted; the sync
workflow always includes a source-commit link in its bodies anyway.

When run outside a PR context (e.g., push event), no env vars are set and the
check exits 0 -- but the CI workflow already gates zeta on `pull_request` events.
"""
from __future__ import annotations
import argparse
import fnmatch
import os
import re
import sys
from typing import List


_HASH_INT = re.compile(r"#\d+")
_URL = re.compile(r"https?://\S+")
_KEYWORD = re.compile(r"\b(?:spec|design|adr|rfc):\s*\S+", re.IGNORECASE)


BOT_BRANCH_PATTERNS = ["chore/sync-ai-docs-*"]


def body_passes(body: str) -> bool:
    if _HASH_INT.search(body):
        return True
    if _URL.search(body):
        return True
    if _KEYWORD.search(body):
        return True
    return False


def _is_bot_branch(branch: str) -> bool:
    return any(fnmatch.fnmatchcase(branch, pat) for pat in BOT_BRANCH_PATTERNS)


def validate() -> List[str]:
    body = os.environ.get("PR_BODY")
    branch = os.environ.get("PR_BRANCH", "")

    if body is None:
        # No PR context; nothing to validate.
        return []

    if _is_bot_branch(branch):
        return []

    if not body_passes(body):
        return [
            "PR body must reference at least one of: "
            "`#<issue>`, a URL, or `spec:`/`design:`/`adr:`/`rfc:` followed by a token."
        ]
    return []


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify PR has issue/spec reference (zeta).")
    parser.parse_args(argv)
    errors = validate()
    for e in errors:
        print(e, file=sys.stderr)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
