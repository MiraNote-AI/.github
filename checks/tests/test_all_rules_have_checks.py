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

    def test_parse_error_from_missing_rules_section_is_reported(self):
        _write(self.tmp / "CONTRIBUTING.md", "no rules here")
        _write(self.tmp / "checks" / "__init__.py")
        errors = validate(self.tmp)
        # γ would catch the parse error; α reports it surfaced from parser
        self.assertTrue(errors)

    def test_no_false_orphan_when_partial_rule_present(self):
        # Rule has a valid `Enforced by:` line but is MISSING `**Rationale:**`.
        # The parser should emit a parse error; α must NOT also flag foo.py as
        # an orphan — that would be a confusing second error for one root cause.
        _write(self.tmp / "CONTRIBUTING.md", (
            "## Rules\n\n"
            "### Rule 1: Foo\n\np\n\n"
            # Rationale intentionally omitted
            "**Enforced by:** `checks/foo.py`\n"
        ))
        _write(self.tmp / "checks" / "__init__.py")
        _write(self.tmp / "checks" / "foo.py")
        errors = validate(self.tmp)
        # There must be at least one parse error (missing Rationale)
        self.assertTrue(errors, "expected at least one parse error")
        # But none of them should mention an orphan for checks/foo.py
        orphan_msgs = [e for e in errors if "checks/foo.py" in e and "not referenced" in e]
        self.assertEqual(orphan_msgs, [], f"false orphan error(s) found: {orphan_msgs}")

    def test_main_returns_zero_on_pass(self):
        _make_valid_repo(self.tmp)
        self.assertEqual(main([str(self.tmp)]), 0)

    def test_main_returns_nonzero_on_fail(self):
        _make_valid_repo(self.tmp)
        _write(self.tmp / "checks" / "orphan.py")
        self.assertNotEqual(main([str(self.tmp)]), 0)


if __name__ == "__main__":
    unittest.main()
