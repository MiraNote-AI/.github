"""Rule 5 (epsilon): Skills and MCP servers are registered in docs/ai/skills.md.

Verify the registry file exists, is non-empty, and has the two required
top-level section headers. Then match the `## Skills` table against the
skill folders: every folder holding a SKILL.md needs a row, and every row
needs a folder. A row is a table line whose first cell is the skill name in
backticks, bare or as a link: "| `create-pr` | ... |" or
"| [`create-pr`](...) | ... |".

Skill folders live in skills/ in MiraNote-AI/.github and in .claude/skills/
in the code repos, which get them from the sync workflow.

Future ratchet: when target repos introduce repo-level MCP config
(e.g., .claude/settings.json with mcpServers), diff the configured set
against the `## MCP Servers` section.
"""
from __future__ import annotations
import argparse
import pathlib
import re
import sys
from typing import List


REQUIRED_HEADERS = ["## Skills", "## MCP Servers"]
SKILLS_SECTION = re.compile(
    r"^## Skills\s*$(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL
)
SKILL_ROW = re.compile(r"^\|\s*\[?`([^`]+)`(?:\]\([^)]*\))?\s*\|", re.MULTILINE)


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

    rel = "skills" if (repo_root / "skills").is_dir() else ".claude/skills"
    folders = {p.parent.name for p in (repo_root / rel).glob("*/SKILL.md")}
    section = SKILLS_SECTION.search(text)
    rows = set(SKILL_ROW.findall(section.group(1))) if section else set()
    for name in sorted(folders - rows):
        errors.append(
            f"skill `{name}` ({rel}/{name}/SKILL.md) has no row in the "
            f"`## Skills` table of docs/ai/skills.md; add one starting with "
            f"| `{name}` |"
        )
    for name in sorted(rows - folders):
        errors.append(
            f"docs/ai/skills.md lists skill `{name}`, but "
            f"{rel}/{name}/SKILL.md does not exist"
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
