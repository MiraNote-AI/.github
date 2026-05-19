from __future__ import annotations
import pathlib
import tempfile
import unittest
from checks.claude_md_size import validate, main


class TestClaudeMdSize(unittest.TestCase):

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())

    def _write_claude_md(self, lines: int) -> None:
        (self.tmp / "CLAUDE.md").write_text("\n".join(f"line {i}" for i in range(lines)) + "\n")

    def test_exact_max_passes(self):
        self._write_claude_md(80)
        self.assertEqual(validate(self.tmp, max_lines=80), [])

    def test_one_under_max_passes(self):
        self._write_claude_md(79)
        self.assertEqual(validate(self.tmp, max_lines=80), [])

    def test_one_over_max_fails(self):
        self._write_claude_md(81)
        errors = validate(self.tmp, max_lines=80)
        self.assertEqual(len(errors), 1)
        self.assertIn("81", errors[0])
        self.assertIn("80", errors[0])

    def test_missing_file_fails(self):
        errors = validate(self.tmp, max_lines=80)
        self.assertTrue(errors)
        self.assertIn("CLAUDE.md", errors[0])

    def test_custom_max(self):
        self._write_claude_md(50)
        self.assertEqual(validate(self.tmp, max_lines=100), [])
        errors = validate(self.tmp, max_lines=40)
        self.assertTrue(errors)

    def test_main_returns_zero_when_under(self):
        self._write_claude_md(10)
        self.assertEqual(main([str(self.tmp), "--max", "80"]), 0)

    def test_main_returns_nonzero_when_over(self):
        self._write_claude_md(200)
        self.assertNotEqual(main([str(self.tmp), "--max", "80"]), 0)


if __name__ == "__main__":
    unittest.main()
