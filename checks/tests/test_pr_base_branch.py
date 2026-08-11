from __future__ import annotations
import unittest
from unittest.mock import patch

from checks.pr_base_branch import base_errors, validate


class TestBaseErrorsHappyPath(unittest.TestCase):
    """Bases that should pass without errors."""

    def test_feature_into_dev(self):
        self.assertEqual(base_errors("dev", "feat/canvas-vision"), [])

    def test_fix_into_dev(self):
        self.assertEqual(base_errors("dev", "fix/one-page-width"), [])

    def test_the_promotion_pr(self):
        # The one deliberate way prod moves.
        self.assertEqual(base_errors("main", "dev"), [])

    def test_sync_bot_into_dev(self):
        self.assertEqual(base_errors("dev", "chore/sync-ai-docs-abc1234"), [])


class TestBaseErrorsViolations(unittest.TestCase):
    """Bases that must be rejected."""

    def test_feature_straight_into_main(self):
        errors = base_errors("main", "feat/canvas-vision")
        self.assertEqual(len(errors), 1)
        self.assertIn("promotion", errors[0])

    def test_hotfix_straight_into_main_is_still_a_violation(self):
        # The documented model has no side door; adding one is a decision,
        # not an accident.
        self.assertEqual(len(base_errors("main", "hotfix/urgent")), 1)

    def test_stacked_onto_another_feature_branch(self):
        errors = base_errors("feat/canvas-vision", "feat/canvas-vision-part-2")
        self.assertEqual(len(errors), 1)
        self.assertIn("dev", errors[0])

    def test_a_release_branch_is_not_special(self):
        self.assertEqual(len(base_errors("release/1.0", "feat/x")), 1)


class TestValidateReadsTheEnvironment(unittest.TestCase):
    def test_no_pr_base_means_not_a_pull_request(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(validate(), [])

    def test_reads_base_and_head(self):
        with patch.dict("os.environ", {"PR_BASE": "main", "PR_HEAD": "feat/x"}, clear=True):
            self.assertEqual(len(validate()), 1)

    def test_promotion_passes_through_the_environment(self):
        with patch.dict("os.environ", {"PR_BASE": "main", "PR_HEAD": "dev"}, clear=True):
            self.assertEqual(validate(), [])

    def test_missing_head_still_reports_the_base_problem(self):
        with patch.dict("os.environ", {"PR_BASE": "main"}, clear=True):
            self.assertEqual(len(validate()), 1)


if __name__ == "__main__":
    unittest.main()
