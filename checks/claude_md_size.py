"""Rule 4 (delta): CLAUDE.md is at most N lines (default 80).

Counts physical newlines. A file ending in a trailing newline has the same
count whether or not the final line carries text.
"""
from __future__ import annotations
import argparse
import pathlib
import sys
from typing import List


def validate(repo_root: pathlib.Path, max_lines: int) -> List[str]:
    claude_md = repo_root / "CLAUDE.md"
    if not claude_md.exists():
        return [f"CLAUDE.md not found at {claude_md}"]

    text = claude_md.read_text(encoding="utf-8")
    parts = text.split("\n")
    line_count = len(parts) - 1 if parts and parts[-1] == "" else len(parts)

    if line_count > max_lines:
        return [
            f"CLAUDE.md has {line_count} lines, exceeds maximum of {max_lines}. "
            f"Move detail to docs/ai/ and keep CLAUDE.md as a navigation entry."
        ]
    return []


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify CLAUDE.md line count (delta).")
    parser.add_argument("repo")
    parser.add_argument("--max", type=int, default=80)
    args = parser.parse_args(argv)

    errors = validate(pathlib.Path(args.repo), max_lines=args.max)
    for e in errors:
        print(e, file=sys.stderr)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
