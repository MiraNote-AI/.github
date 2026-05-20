"""Rule 8 (theta): PR title follows the project's format conventions.

Reads PR metadata from environment variables populated by the CI workflow:
- PR_TITLE:  the pull request title text
- PR_BRANCH: the pull request head branch name (used for bot exemption)

Bot PRs (head branch matching `chore/sync-ai-docs-*`) are exempted.

When run outside a PR context (e.g., push event), no env vars are set and the
check exits 0 -- the CI workflow already gates theta on `pull_request` events.
"""
from __future__ import annotations
import argparse
import fnmatch
import os
import re
import sys
from typing import List


ALLOWED_TYPES = (
    "feat", "fix", "chore", "docs", "refactor",
    "test", "ci", "perf", "build", "revert",
)
ALLOWED_SCOPES = ("api", "web", "ios", "bot", "infra")
MAX_LEN = 72

_HEAD_RE = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?:\s(?P<desc>.*)$"
)
_ISSUE_REF_RE = re.compile(r"#\d+")
_WIP_RE = re.compile(r"\b(?:WIP|DRAFT|FIXME|TODO)\b", re.IGNORECASE)

# Past-tense / gerund verbs that violate the "imperative mood" convention.
# Matched at the start of the description (after the prefix), case-insensitively.
_PAST_GERUND_WORDS = (
    "added", "adding",
    "fixed", "fixes", "fixing",
    "updated", "updates", "updating",
    "removed", "removes", "removing",
    "changed", "changes", "changing",
    "created", "creates", "creating",
    "deleted", "deletes", "deleting",
    "improved", "improves", "improving",
    "refactored", "refactors", "refactoring",
    "renamed", "renames", "renaming",
    "implemented", "implements", "implementing",
)
_PAST_GERUND_RE = re.compile(
    r"^(?:" + "|".join(_PAST_GERUND_WORDS) + r")\b",
    re.IGNORECASE,
)


BOT_BRANCH_PATTERNS = ["chore/sync-ai-docs-*"]


def _is_bot_branch(branch: str) -> bool:
    return any(fnmatch.fnmatchcase(branch, pat) for pat in BOT_BRANCH_PATTERNS)


def title_errors(title: str) -> List[str]:
    """Return a list of error messages for the given title.

    Returns [] if the title passes all checks. Multiple errors may be reported
    for a single title so authors see everything wrong in one CI run.
    """
    errors: List[str] = []

    if not title.strip():
        return ["PR title is empty."]

    if len(title) > MAX_LEN:
        errors.append(
            f"PR title exceeds {MAX_LEN} characters (is {len(title)})."
        )

    if _ISSUE_REF_RE.search(title):
        errors.append(
            "PR title must not contain `#<number>` issue references; "
            "move them to the body."
        )

    wip_match = _WIP_RE.search(title)
    if wip_match:
        errors.append(
            f"PR title contains marker `{wip_match.group(0)}`; "
            "use GitHub Draft PR state instead of marking in the title."
        )

    m = _HEAD_RE.match(title)
    if not m:
        errors.append(
            "PR title must start with a Conventional Commits prefix and `: `, "
            f"e.g. `feat(api): add login`. Allowed types: {', '.join(ALLOWED_TYPES)}."
        )
        return errors

    rtype = m.group("type")
    scope = m.group("scope")
    desc = m.group("desc")

    if rtype not in ALLOWED_TYPES:
        errors.append(
            f"PR title type `{rtype}` is not allowed; "
            f"use one of: {', '.join(ALLOWED_TYPES)}."
        )

    if scope is not None and scope not in ALLOWED_SCOPES:
        scope_repr = scope if scope else "(empty)"
        errors.append(
            f"PR title scope `({scope_repr})` is not in the whitelist; "
            f"use one of: {', '.join(ALLOWED_SCOPES)}, or omit the scope."
        )

    if not desc:
        errors.append("PR title description (after the colon) is empty.")
        return errors

    if not desc[0].isalpha() or not desc[0].islower():
        errors.append(
            f"PR title description must start with a lowercase letter (got `{desc[0]}`)."
        )

    if desc.endswith("."):
        errors.append("PR title must not end with a period.")

    if _PAST_GERUND_RE.match(desc):
        errors.append(
            "PR title description must use the imperative mood "
            "(e.g., `add` not `added`/`adding`, `fix` not `fixed`/`fixing`)."
        )

    return errors


def validate() -> List[str]:
    title = os.environ.get("PR_TITLE")
    branch = os.environ.get("PR_BRANCH", "")

    if title is None:
        return []

    if _is_bot_branch(branch):
        return []

    return title_errors(title)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify PR title format (theta).")
    parser.parse_args(argv)
    errors = validate()
    for e in errors:
        print(e, file=sys.stderr)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
