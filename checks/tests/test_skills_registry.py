from __future__ import annotations
import pathlib
import tempfile
import unittest
from checks.skills_registry import validate, main


class TestSkillsRegistry(unittest.TestCase):

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / "docs" / "ai").mkdir(parents=True)

    def _write(self, content: str) -> None:
        (self.tmp / "docs" / "ai" / "skills.md").write_text(content)

    def test_valid_passes(self):
        self._write("# Skills and MCP\n\n## Skills\n\n(none yet)\n\n## MCP Servers\n\n(none yet)\n")
        self.assertEqual(validate(self.tmp), [])

    def test_missing_file_fails(self):
        errors = validate(self.tmp)
        self.assertTrue(errors)
        self.assertIn("docs/ai/skills.md", errors[0])

    def test_empty_file_fails(self):
        self._write("")
        errors = validate(self.tmp)
        self.assertTrue(errors)
        self.assertIn("empty", errors[0].lower())

    def test_missing_skills_header_fails(self):
        self._write("# Skills and MCP\n\n## MCP Servers\n\nstuff\n")
        errors = validate(self.tmp)
        self.assertTrue(any("## Skills" in e for e in errors))

    def test_missing_mcp_servers_header_fails(self):
        self._write("# Skills and MCP\n\n## Skills\n\nstuff\n")
        errors = validate(self.tmp)
        self.assertTrue(any("## MCP Servers" in e for e in errors))

    def test_both_missing_reports_both(self):
        self._write("# Skills and MCP\n\nbut no headers\n")
        errors = validate(self.tmp)
        self.assertEqual(len(errors), 2)

    def test_main_returns_zero_on_pass(self):
        self._write("## Skills\n\n## MCP Servers\n")
        self.assertEqual(main([str(self.tmp)]), 0)

    def test_main_returns_nonzero_on_fail(self):
        self.assertNotEqual(main([str(self.tmp)]), 0)

    # The `discord` row sits under MCP Servers, so it needs no skill folder.
    REGISTRY = (
        "## Skills\n\n| Skill | Purpose |\n|---|---|\n"
        "| `create-pr` | Open a PR. |\n| `run-loop` | Run a loop. |\n\n"
        "## MCP Servers\n\n| Server | Purpose |\n|---|---|\n"
        "| `discord` | Read the team channel. |\n"
    )

    def _skill(self, folder: str, name: str) -> None:
        (self.tmp / folder / name).mkdir(parents=True)
        (self.tmp / folder / name / "SKILL.md").write_text(f"---\nname: {name}\n---\n")

    def test_source_repo_rows_match_folders(self):
        self._write(self.REGISTRY)
        self._skill("skills", "create-pr")
        self._skill("skills", "run-loop")
        self.assertEqual(validate(self.tmp), [])

    def test_code_repo_rows_match_folders(self):
        self._write(self.REGISTRY)
        self._skill(".claude/skills", "create-pr")
        self._skill(".claude/skills", "run-loop")
        self.assertEqual(validate(self.tmp), [])

    def test_folder_without_row_fails_and_names_it(self):
        self._write(self.REGISTRY)
        for name in ("create-pr", "run-loop", "report-issue"):
            self._skill("skills", name)
        errors = validate(self.tmp)
        self.assertEqual(len(errors), 1)
        self.assertIn("`report-issue`", errors[0])
        self.assertIn("skills/report-issue/SKILL.md", errors[0])

    def test_row_without_folder_fails_and_names_it(self):
        self._write(self.REGISTRY)
        self._skill(".claude/skills", "create-pr")
        errors = validate(self.tmp)
        self.assertEqual(len(errors), 1)
        self.assertIn("`run-loop`", errors[0])
        self.assertIn(".claude/skills/run-loop/SKILL.md", errors[0])

    def test_folder_without_skill_md_is_not_a_skill(self):
        self._write(self.REGISTRY)
        self._skill("skills", "create-pr")
        self._skill("skills", "run-loop")
        (self.tmp / "skills" / "shared").mkdir()
        self.assertEqual(validate(self.tmp), [])

    def test_source_repo_ignores_claude_skills(self):
        self._write(self.REGISTRY)
        self._skill("skills", "create-pr")
        self._skill("skills", "run-loop")
        self._skill(".claude/skills", "local-only")
        self.assertEqual(validate(self.tmp), [])

    def test_linked_name_counts_as_a_row(self):
        linked = "[`run-loop`](../../skills/run-loop/SKILL.md)"
        self._write(self.REGISTRY.replace("`run-loop`", linked))
        self._skill("skills", "create-pr")
        self._skill("skills", "run-loop")
        self.assertEqual(validate(self.tmp), [])


if __name__ == "__main__":
    unittest.main()
