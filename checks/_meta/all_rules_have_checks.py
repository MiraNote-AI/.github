"""Rule 1 (α): Every rule has an enforcement mechanism.

Verifies the doc → script mapping in both directions:
- Forward: every path referenced in CONTRIBUTING.md's `Enforced by:` lines exists.
- Reverse: every `.py` file at the direct top level of `checks/` is referenced
  by at least one rule (orphan detection). Subdirectories like `_meta/` are
  intentionally not scanned — they're reserved for meta-tooling and library code.
"""
from __future__ import annotations
import argparse
import pathlib
import sys
from typing import List

from checks._meta.parser import parse_contributing


def _direct_check_files(checks_dir: pathlib.Path) -> List[pathlib.Path]:
    """Return all .py files at the direct top level of checks/, excluding __init__.py."""
    if not checks_dir.is_dir():
        return []
    return sorted(
        p for p in checks_dir.iterdir()
        if p.is_file() and p.suffix == ".py" and p.name != "__init__.py"
    )


def validate(repo_root: pathlib.Path) -> List[str]:
    """Return list of error messages. Empty list == pass."""
    contributing = repo_root / "CONTRIBUTING.md"
    if not contributing.exists():
        return [f"CONTRIBUTING.md not found at {contributing}"]

    text = contributing.read_text(encoding="utf-8")
    rules, parse_errors = parse_contributing(text)

    errors: List[str] = []
    for pe in parse_errors:
        prefix = f"CONTRIBUTING.md:{pe.line}: " if pe.line else "CONTRIBUTING.md: "
        errors.append(prefix + pe.message)

    # Forward: every referenced check path must exist
    referenced: set = set()
    for rule in rules:
        for path in rule.enforced_by:
            referenced.add(path)
            resolved = repo_root / path
            if not resolved.exists():
                errors.append(
                    f"Rule {rule.id}: referenced check {path!r} does not exist"
                )

    # Reverse: every direct-child .py under checks/ must be referenced
    for check_file in _direct_check_files(repo_root / "checks"):
        rel = check_file.relative_to(repo_root).as_posix()
        if rel not in referenced:
            errors.append(
                f"Orphan check: {rel} is not referenced by any rule's "
                f"`Enforced by:` line. Either register it in CONTRIBUTING.md "
                f"or move it under a subdirectory if it is library code."
            )

    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify rules-to-checks mapping (α).")
    parser.add_argument("repo", help="repo root containing CONTRIBUTING.md and checks/")
    args = parser.parse_args(argv)

    errors = validate(pathlib.Path(args.repo))
    for e in errors:
        print(e, file=sys.stderr)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
