from __future__ import annotations
import pathlib
import tempfile
import unittest
from checks._meta.all_rules_have_checks import validate, main


def _write(path: pathlib.Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _make_valid_repo(tmp: pathlib.Path) -> None:
    """Set up a minimal valid repo: CONTRIBUTING.md + checks/foo.py + __init__.py files."""
    _write(tmp / "CONTRIBUTING.md", (
        "## Rules\n\n"
        "### Rule 1: Foo\n\np\n\n"
        "**Rationale:** r\n"
        "**Enforced by:** `checks/foo.py`\n"
    ))
    _write(tmp / "checks" / "__init__.py")
    _write(tmp / "checks" / "foo.py")


class TestAllRulesHaveChecks(unittest.TestCase):

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())

    def test_valid_minimal_passes(self):
        _make_valid_repo(self.tmp)
        self.assertEqual(validate(self.tmp), [])

    def test_forward_check_fails_when_referenced_path_missing(self):
        _make_valid_repo(self.tmp)
        (self.tmp / "checks" / "foo.py").unlink()
        errors = validate(self.tmp)
        self.assertTrue(errors)
        self.assertIn("checks/foo.py", " ".join(errors))

    def test_orphan_check_fails_when_unused_script_present(self):
        _make_valid_repo(self.tmp)
        _write(self.tmp / "checks" / "orphan.py")
        errors = validate(self.tmp)
        self.assertEqual(len(errors), 1)
        self.assertIn("orphan", errors[0])
        self.assertIn("not referenced", errors[0])

    def test_subdirectory_scripts_are_NOT_scanned_for_orphans(self):
        # _meta/parser.py is library code, not registered, but must not fail.
        _make_valid_repo(self.tmp)
        _write(self.tmp / "checks" / "_meta" / "__init__.py")
        _write(self.tmp / "checks" / "_meta" / "parser.py")
        _write(self.tmp / "checks" / "_meta" / "all_rules_have_checks.py")
        errors = validate(self.tmp)
        self.assertEqual(errors, [])

    def test_init_py_is_not_treated_as_a_check(self):
        _make_valid_repo(self.tmp)
        # checks/__init__.py exists from _make_valid_repo and is not registered.
        # Should NOT be flagged as an orphan.
        errors = validate(self.tmp)
        self.assertEqual(errors, [])

    def test_skips_when_parse_errors_exist(self):
        _write(self.tmp / "CONTRIBUTING.md", "no rules here")
        _write(self.tmp / "checks" / "__init__.py")
        errors = validate(self.tmp)
        # γ would catch the parse error; α reports it surfaced from parser
        self.assertTrue(errors)

    def test_main_returns_zero_on_pass(self):
        _make_valid_repo(self.tmp)
        self.assertEqual(main([str(self.tmp)]), 0)

    def test_main_returns_nonzero_on_fail(self):
        _make_valid_repo(self.tmp)
        _write(self.tmp / "checks" / "orphan.py")
        self.assertNotEqual(main([str(self.tmp)]), 0)


if __name__ == "__main__":
    unittest.main()
