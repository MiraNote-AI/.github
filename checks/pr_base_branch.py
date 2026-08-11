"""Rule 9: pull requests target `dev`, and only a promotion touches `main`.

Reads PR metadata from environment variables populated by the CI workflow:
`PR_BASE` (the branch being merged into) and `PR_HEAD` (the branch being
merged from). Absent `PR_BASE` means this is not a pull-request event, so
there is nothing to check.

The rule exists because a branch model that lives only in a README is a
suggestion. Nothing stopped eleven PRs in a row from being opened against
`main` after the default branch moved to `dev` -- and none of them looked
wrong until someone went looking.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import List

INTEGRATION_BRANCH = "dev"
PROD_BRANCH = "main"


def base_errors(base: str, head: str) -> List[str]:
    """Return the violations for one (base, head) pair."""
    if base == INTEGRATION_BRANCH:
        return []
    if base == PROD_BRANCH and head == INTEGRATION_BRANCH:
        # The promotion PR: the one deliberate way prod moves.
        return []
    if base == PROD_BRANCH:
        return [
            f"PR targets `{PROD_BRANCH}` from `{head}`: prod changes only "
            f"through a `{INTEGRATION_BRANCH} -> {PROD_BRANCH}` promotion. "
            f"Re-target this at `{INTEGRATION_BRANCH}`."
        ]
    return [
        f"PR targets `{base}`: open pull requests against "
        f"`{INTEGRATION_BRANCH}` (stacked branches are not used here)."
    ]


def validate() -> List[str]:
    base = os.environ.get("PR_BASE")
    head = os.environ.get("PR_HEAD", "")

    if base is None:
        return []

    return base_errors(base, head)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify PR base branch (iota).")
    parser.parse_args(argv)
    errors = validate()
    for e in errors:
        print(e, file=sys.stderr)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
