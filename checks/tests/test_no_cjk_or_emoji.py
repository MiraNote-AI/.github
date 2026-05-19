from __future__ import annotations
import pathlib
import subprocess
import tempfile
import unittest
from checks.no_cjk_or_emoji import scan_text, validate, FORBIDDEN_RANGES


class TestScanText(unittest.TestCase):
    """Tests for the pure-function range scanner (no git involvement)."""

    def test_clean_ascii_text_returns_no_violations(self):
        self.assertEqual(scan_text("hello world\nplain text\n"), [])

    def test_chinese_character_is_flagged(self):
        violations = scan_text("hello \u4e2d world")  # U+4E2D
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0][0], 1)  # line 1
        self.assertEqual(violations[0][2], 0x4E2D)

    def test_hiragana_is_flagged(self):
        violations = scan_text("\u3042")  # U+3042
        self.assertEqual(len(violations), 1)

    def test_katakana_is_flagged(self):
        violations = scan_text("\u30a2")  # U+30A2
        self.assertEqual(len(violations), 1)

    def test_emoji_is_flagged(self):
        violations = scan_text("hi \U0001F600")
        self.assertEqual(len(violations), 1)

    def test_text_presentation_symbols_NOT_flagged(self):
        # U+2713 (CHECK MARK), U+2192 (RIGHTWARDS ARROW), U+2500 (BOX DRAWINGS)
        self.assertEqual(scan_text("\u2713 \u2192 \u2500"), [])

    def test_multiple_violations_on_different_lines(self):
        violations = scan_text("ok\n\u4e2d\n\u3042\n")
        self.assertEqual(len(violations), 2)
        self.assertEqual(violations[0][0], 2)
        self.assertEqual(violations[1][0], 3)

    def test_fullwidth_punctuation_flagged(self):
        violations = scan_text("hi\uff01")  # U+FF01 fullwidth exclamation
        self.assertEqual(len(violations), 1)

    def test_cjk_extension_a_flagged(self):
        violations = scan_text("\u3400")  # CJK Ext A start U+3400
        self.assertEqual(len(violations), 1)


class TestValidate(unittest.TestCase):
    """Tests for the git-integrated whole-repo validator."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.tmp, check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=self.tmp, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=self.tmp, check=True)

    def _write_and_stage(self, name: str, text: str) -> None:
        (self.tmp / name).write_text(text)
        subprocess.run(["git", "add", name], cwd=self.tmp, check=True)

    def _write_untracked(self, name: str, text: str) -> None:
        (self.tmp / name).write_text(text)

    def test_clean_repo_passes(self):
        self._write_and_stage("a.py", "print('hi')\n")
        self._write_and_stage("b.md", "# header\nbody\n")
        self.assertEqual(validate(self.tmp), [])

    def test_committed_chinese_fails(self):
        self._write_and_stage("a.py", "x = '\u4e2d'\n")
        errors = validate(self.tmp)
        self.assertEqual(len(errors), 1)
        self.assertIn("a.py", errors[0])
        self.assertIn("U+4E2D", errors[0])

    def test_untracked_emoji_fails(self):
        # Critical: spec section 5.3 requires --others so local-only files are caught.
        self._write_untracked("notes.md", "todo \U0001F600\n")
        errors = validate(self.tmp)
        self.assertEqual(len(errors), 1)
        self.assertIn("notes.md", errors[0])

    def test_gitignored_file_skipped(self):
        # --exclude-standard means .gitignore is honored
        (self.tmp / ".gitignore").write_text("ignored.txt\n")
        subprocess.run(["git", "add", ".gitignore"], cwd=self.tmp, check=True)
        self._write_untracked("ignored.txt", "\u4e2d")
        self.assertEqual(validate(self.tmp), [])

    def test_binary_files_handled_gracefully(self):
        # spec section 5.3: read with errors="replace"; replacement char is a violation.
        (self.tmp / "x.bin").write_bytes(b"\x89PNG\r\n\x1a\n\x00\xff\xfe")
        subprocess.run(["git", "add", "x.bin"], cwd=self.tmp, check=True)
        errors = validate(self.tmp)
        self.assertTrue(any("x.bin" in e for e in errors))

    def test_allowlisted_paths_skipped(self):
        # docs/plans/foo.md is an allowlisted path per ALLOWLIST_PATTERNS;
        # CJK content there must NOT be flagged.
        (self.tmp / "docs" / "plans").mkdir(parents=True)
        (self.tmp / "docs" / "plans" / "x.md").write_text("plan with \u4e2d\n")
        subprocess.run(["git", "add", "docs/plans/x.md"], cwd=self.tmp, check=True)
        # Also write a non-allowlisted file with CJK to confirm β still catches that
        self._write_and_stage("src.py", "x = '\u4e2d'\n")
        errors = validate(self.tmp)
        # Only src.py should be flagged, not docs/plans/x.md
        self.assertTrue(any("src.py" in e for e in errors))
        self.assertFalse(any("docs/plans/x.md" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
