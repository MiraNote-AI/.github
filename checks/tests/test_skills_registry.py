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


if __name__ == "__main__":
    unittest.main()
