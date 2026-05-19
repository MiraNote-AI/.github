"""Rule 5 (epsilon): Skills and MCP servers are registered in docs/ai/skills.md.

Day-0 narrow implementation: verify the registry file exists, is non-empty,
and has the two required top-level section headers.

Future ratchet: when target repos introduce repo-level skill/MCP config
(e.g., .claude/settings.json with mcpServers), diff the configured set
against this registry.
"""
from __future__ import annotations
import argparse
import pathlib
import re
import sys
from typing import List


REQUIRED_HEADERS = ["## Skills", "## MCP Servers"]


def validate(repo_root: pathlib.Path) -> List[str]:
    skills_md = repo_root / "docs" / "ai" / "skills.md"
    if not skills_md.exists():
        return [f"docs/ai/skills.md not found at {skills_md}"]

    text = skills_md.read_text(encoding="utf-8")
    if not text.strip():
        return [f"docs/ai/skills.md is empty"]

    errors: List[str] = []
    for header in REQUIRED_HEADERS:
        pattern = re.compile(r"^" + re.escape(header) + r"\s*$", re.MULTILINE)
        if not pattern.search(text):
            errors.append(
                f"docs/ai/skills.md is missing required header `{header}`"
            )
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Validate skills/MCP registry (epsilon).")
    parser.add_argument("repo")
    args = parser.parse_args(argv)

    errors = validate(pathlib.Path(args.repo))
    for e in errors:
        print(e, file=sys.stderr)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
