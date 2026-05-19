"""Rule 2 (γ): CONTRIBUTING.md follows the canonical structure.

In source mode, every path on every `Enforced by:` line must resolve
relative to the repo root. In target mode, path resolution is skipped
(those scripts live only in MiraNote-AI/.github, not in target repos).
"""
from __future__ import annotations
import argparse
import pathlib
import sys
from typing import List

from checks._meta.parser import parse_contributing


def validate(repo_root: pathlib.Path, mode: str) -> List[str]:
    """Validate CONTRIBUTING.md under repo_root. Returns error messages."""
    if mode not in ("source", "target"):
        return [f"unknown mode: {mode!r} (expected 'source' or 'target')"]

    contributing = repo_root / "CONTRIBUTING.md"
    if not contributing.exists():
        return [f"CONTRIBUTING.md not found at {contributing}"]

    text = contributing.read_text(encoding="utf-8")
    rules, parse_errors = parse_contributing(text)
    errors: List[str] = []

    for pe in parse_errors:
        prefix = f"CONTRIBUTING.md:{pe.line}: " if pe.line else "CONTRIBUTING.md: "
        errors.append(prefix + pe.message)

    if mode == "source":
        for rule in rules:
            for path in rule.enforced_by:
                resolved = repo_root / path
                if not resolved.exists():
                    errors.append(
                        f"CONTRIBUTING.md:{rule.line_no}: Rule {rule.id}: "
                        f"`Enforced by:` path {path!r} does not exist"
                    )

    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Validate CONTRIBUTING.md structure (γ).")
    parser.add_argument("repo", help="path to the repo root containing CONTRIBUTING.md")
    parser.add_argument("--mode", choices=("source", "target"), default="source")
    args = parser.parse_args(argv)

    errors = validate(pathlib.Path(args.repo), args.mode)
    for e in errors:
        print(e, file=sys.stderr)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
