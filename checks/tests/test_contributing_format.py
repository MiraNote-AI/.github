from __future__ import annotations
import pathlib
import tempfile
import unittest
from checks.contributing_format import validate, main


VALID = """\
## Rules

### Rule 1: Foo

p

**Rationale:** r
**Enforced by:** `checks/foo.py`
"""


def _write_repo(tmp: pathlib.Path, contributing: str, *check_paths: str) -> None:
    (tmp / "CONTRIBUTING.md").write_text(contributing)
    for p in check_paths:
        path = tmp / p
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()


class TestContributingFormat(unittest.TestCase):

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())

    def test_valid_passes_in_target_mode_without_files(self):
        _write_repo(self.tmp, VALID)
        errors = validate(self.tmp, mode="target")
        self.assertEqual(errors, [])

    def test_valid_passes_in_source_mode_with_referenced_file(self):
        _write_repo(self.tmp, VALID, "checks/foo.py")
        errors = validate(self.tmp, mode="source")
        self.assertEqual(errors, [])

    def test_source_mode_fails_when_referenced_path_missing(self):
        _write_repo(self.tmp, VALID)  # no checks/foo.py
        errors = validate(self.tmp, mode="source")
        self.assertEqual(len(errors), 1)
        self.assertIn("checks/foo.py", errors[0])
        self.assertIn("does not exist", errors[0])

    def test_target_mode_skips_path_existence_check(self):
        _write_repo(self.tmp, VALID)  # no checks/foo.py
        errors = validate(self.tmp, mode="target")
        self.assertEqual(errors, [])

    def test_missing_contributing_md(self):
        # tmp dir is empty
        errors = validate(self.tmp, mode="target")
        self.assertTrue(errors)
        self.assertIn("CONTRIBUTING.md", errors[0])

    def test_parse_errors_are_propagated(self):
        _write_repo(self.tmp, "no rules section here")
        errors = validate(self.tmp, mode="target")
        self.assertTrue(errors)
        self.assertIn("## Rules", errors[0])

    def test_main_returns_zero_on_pass(self):
        _write_repo(self.tmp, VALID)
        rc = main([str(self.tmp), "--mode", "target"])
        self.assertEqual(rc, 0)

    def test_main_returns_nonzero_on_fail(self):
        _write_repo(self.tmp, "broken")
        rc = main([str(self.tmp), "--mode", "target"])
        self.assertNotEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
