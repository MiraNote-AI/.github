"""Rule 7 (eta): Protected paths cannot be modified outside the sync flow.

Reads PR diff from environment (BASE_SHA, HEAD_SHA, PR_BRANCH) and fails the
check if changed files intersect with the PROTECTED_GLOBS list -- unless the
PR head branch is a sync-bot branch (`chore/sync-ai-docs-*`).

This is soft enforcement per spec 5.7: branch names are spoofable. True
enforcement requires CODEOWNERS + branch protection (sub-project F).

Exit codes:
  0  No violations found (clean).
  1  One or more protected paths were modified outside the sync flow.
  2  Infrastructure error (git diff failed or git not found).
"""
from __future__ import annotations
import argparse
import fnmatch
import os
import pathlib
import subprocess
import sys
from typing import List


PROTECTED_GLOBS: List[str] = [
    "CLAUDE.md",
    "CONTRIBUTING.md",
    "docs/ai/**",
    ".claude/skills/**",
    ".github/workflows/checks.yml",
]


BOT_BRANCH_PATTERNS = ["chore/sync-ai-docs-*"]


def paths_intersecting(changed: List[str]) -> List[str]:
    """Return the subset of changed paths that match any PROTECTED_GLOBS entry."""
    hits = []
    for path in changed:
        for glob in PROTECTED_GLOBS:
            # fnmatch.fnmatchcase doesn't support ** natively; emulate by
            # checking both direct match and prefix match for ** patterns.
            if glob.endswith("/**"):
                prefix = glob[:-3]
                if path == prefix or path.startswith(prefix + "/"):
                    hits.append(path)
                    break
            elif fnmatch.fnmatchcase(path, glob):
                hits.append(path)
                break
    return hits


def _is_bot_branch(branch: str) -> bool:
    return any(fnmatch.fnmatchcase(branch, pat) for pat in BOT_BRANCH_PATTERNS)


def _git_diff_names(repo: pathlib.Path, base: str, head: str) -> List[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", base, head],
        cwd=repo, capture_output=True, text=True, check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def validate(repo_root: pathlib.Path) -> List[str]:
    base = os.environ.get("BASE_SHA")
    head = os.environ.get("HEAD_SHA")
    branch = os.environ.get("PR_BRANCH", "")

    if not base or not head:
        # Not invoked in a PR context -- nothing to do. CI gates this on `pull_request`.
        return []

    changed = _git_diff_names(repo_root, base, head)
    hits = paths_intersecting(changed)
    if not hits:
        return []
    if _is_bot_branch(branch):
        return []

    return [
        f"Protected paths cannot be modified outside the sync flow: "
        f"{', '.join(hits)}. Edit these in MiraNote-AI/.github instead; "
        f"the sync workflow will propagate the change."
    ]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify protected paths (eta).")
    parser.add_argument("repo")
    args = parser.parse_args(argv)
    try:
        errors = validate(pathlib.Path(args.repo))
    except subprocess.CalledProcessError as e:
        print(
            f"error: git diff failed in {args.repo!r} "
            f"(exit {e.returncode}). Are BASE_SHA/HEAD_SHA valid?",
            file=sys.stderr,
        )
        return 2
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    for e in errors:
        print(e, file=sys.stderr)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
