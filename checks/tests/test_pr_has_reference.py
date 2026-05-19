from __future__ import annotations
import unittest
from unittest.mock import patch
from checks.pr_has_reference import body_passes, validate, main


class TestBodyPasses(unittest.TestCase):
    """Pure tests for the body-matching predicate."""

    def test_empty_body_fails(self):
        self.assertFalse(body_passes(""))

    def test_plain_prose_fails(self):
        self.assertFalse(body_passes("Just some prose about what I changed."))

    def test_hash_integer_passes(self):
        self.assertTrue(body_passes("Fixes #123."))

    def test_hash_not_followed_by_int_fails(self):
        self.assertFalse(body_passes("# Heading\nsome stuff"))

    def test_url_passes(self):
        self.assertTrue(body_passes("See https://example.com/foo"))

    def test_http_url_passes(self):
        self.assertTrue(body_passes("link http://example.com"))

    def test_spec_keyword_passes(self):
        self.assertTrue(body_passes("spec: foo/bar.md"))

    def test_design_keyword_passes(self):
        self.assertTrue(body_passes("design: docs/something.md"))

    def test_adr_keyword_passes(self):
        self.assertTrue(body_passes("adr: ADR-007"))

    def test_rfc_keyword_passes(self):
        self.assertTrue(body_passes("rfc: rfc-12"))

    def test_keyword_must_be_followed_by_token(self):
        self.assertFalse(body_passes("spec:"))
        self.assertFalse(body_passes("design: "))


class TestValidate(unittest.TestCase):
    """Tests for the env-var-driven validator."""

    def test_no_pr_body_returns_no_errors(self):
        # E.g., on push event the workflow gates zeta off via `if:`.
        # The script itself shouldn't crash if env is missing.
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(validate(), [])

    def test_valid_body_passes(self):
        with patch.dict("os.environ", {"PR_BODY": "fixes #1"}, clear=True):
            self.assertEqual(validate(), [])

    def test_invalid_body_fails(self):
        with patch.dict("os.environ", {"PR_BODY": "no references here"}, clear=True):
            errors = validate()
            self.assertEqual(len(errors), 1)
            self.assertIn("reference", errors[0].lower())

    def test_bot_branch_is_exempt_even_with_empty_body(self):
        with patch.dict("os.environ", {
            "PR_BODY": "",
            "PR_BRANCH": "chore/sync-ai-docs-abc1234",
        }, clear=True):
            self.assertEqual(validate(), [])

    def test_bot_branch_local_variant_is_exempt(self):
        with patch.dict("os.environ", {
            "PR_BODY": "",
            "PR_BRANCH": "chore/sync-ai-docs-local-abc1234",
        }, clear=True):
            self.assertEqual(validate(), [])

    def test_non_bot_branch_not_exempt(self):
        with patch.dict("os.environ", {
            "PR_BODY": "no refs",
            "PR_BRANCH": "feature/some-feature",
        }, clear=True):
            self.assertTrue(validate())


if __name__ == "__main__":
    unittest.main()
