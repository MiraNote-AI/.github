from __future__ import annotations
import unittest
from unittest.mock import patch

from checks.pr_title_format import title_errors, validate


class TestTitleErrorsHappyPath(unittest.TestCase):
    """Titles that should pass without errors."""

    def test_basic_feat(self):
        self.assertEqual(title_errors("feat: add login flow"), [])

    def test_with_scope(self):
        self.assertEqual(title_errors("feat(api): add user endpoint"), [])

    def test_breaking_change_bang(self):
        self.assertEqual(title_errors("feat!: remove deprecated route"), [])

    def test_scope_and_bang(self):
        self.assertEqual(title_errors("feat(api)!: drop legacy auth"), [])

    def test_all_types(self):
        for t in (
            "feat", "fix", "chore", "docs", "refactor",
            "test", "ci", "perf", "build", "revert",
        ):
            with self.subTest(type=t):
                self.assertEqual(title_errors(f"{t}: do a thing"), [])

    def test_all_scopes(self):
        for s in ("api", "web", "ios", "bot", "infra"):
            with self.subTest(scope=s):
                self.assertEqual(title_errors(f"feat({s}): do a thing"), [])

    def test_length_72_passes(self):
        # exactly 72 chars
        title = "feat: " + "a" * 66
        self.assertEqual(len(title), 72)
        self.assertEqual(title_errors(title), [])


class TestPrefixAndScope(unittest.TestCase):
    def test_no_prefix_fails(self):
        errs = title_errors("just some prose")
        self.assertTrue(any("Conventional Commits" in e for e in errs))

    def test_unknown_type_fails(self):
        errs = title_errors("badprefix: do a thing")
        self.assertTrue(
            any("not allowed" in e and "badprefix" in e for e in errs)
        )

    def test_unknown_scope_fails(self):
        errs = title_errors("feat(F-final): remove admin bypass")
        self.assertTrue(any("F-final" in e and "whitelist" in e for e in errs))

    def test_empty_scope_fails(self):
        errs = title_errors("feat(): add thing")
        self.assertTrue(any("whitelist" in e for e in errs))

    def test_missing_space_after_colon_fails(self):
        # `feat:add` has no space after the colon — should fail the header regex.
        errs = title_errors("feat:add login")
        self.assertTrue(any("Conventional Commits" in e for e in errs))


class TestLength(unittest.TestCase):
    def test_length_73_fails(self):
        title = "feat: " + "a" * 67  # 73 chars
        errs = title_errors(title)
        self.assertTrue(any("72" in e for e in errs))


class TestDescriptionShape(unittest.TestCase):
    def test_uppercase_first_letter_fails(self):
        errs = title_errors("feat: Add login flow")
        self.assertTrue(any("lowercase" in e for e in errs))

    def test_trailing_period_fails(self):
        errs = title_errors("feat: add login flow.")
        self.assertTrue(any("period" in e for e in errs))

    def test_empty_description_fails(self):
        errs = title_errors("feat: ")
        self.assertTrue(errs)


class TestImperativeMood(unittest.TestCase):
    def test_past_tense_added_fails(self):
        errs = title_errors("feat: added a thing")
        self.assertTrue(any("imperative" in e for e in errs))

    def test_gerund_fixing_fails(self):
        errs = title_errors("fix: fixing the thing")
        self.assertTrue(any("imperative" in e for e in errs))

    def test_third_person_fixes_fails(self):
        errs = title_errors("fix: fixes flaky test")
        self.assertTrue(any("imperative" in e for e in errs))

    def test_imperative_passes(self):
        self.assertEqual(
            title_errors("fix: handle empty body in request parser"), []
        )


class TestForbiddenContent(unittest.TestCase):
    def test_issue_ref_in_title_fails(self):
        errs = title_errors("fix: handle empty body #123")
        self.assertTrue(any("#<number>" in e for e in errs))

    def test_wip_marker_fails(self):
        errs = title_errors("feat: WIP add login")
        self.assertTrue(any("Draft" in e for e in errs))

    def test_todo_marker_fails(self):
        errs = title_errors("feat: TODO improve speed")
        self.assertTrue(any("Draft" in e for e in errs))

    def test_fixme_marker_fails(self):
        errs = title_errors("feat: FIXME refactor module")
        self.assertTrue(any("Draft" in e for e in errs))

    def test_lowercase_todo_word_passes(self):
        # `todo` as a regular English word in a product/feature name must not
        # be mistaken for a WIP marker.
        self.assertEqual(title_errors("feat: add todo list management"), [])

    def test_lowercase_draft_word_passes(self):
        self.assertEqual(title_errors("feat(api): add draft saving"), [])

    def test_lowercase_fixme_word_passes(self):
        self.assertEqual(
            title_errors("fix: improve fixme handling in parser"), []
        )

    def test_empty_title_fails(self):
        errs = title_errors("")
        self.assertTrue(any("empty" in e.lower() for e in errs))


class TestValidate(unittest.TestCase):
    """Env-var-driven validator."""

    def test_no_pr_title_returns_no_errors(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(validate(), [])

    def test_valid_title_passes(self):
        with patch.dict("os.environ", {"PR_TITLE": "feat: add login flow"}, clear=True):
            self.assertEqual(validate(), [])

    def test_invalid_title_returns_errors(self):
        with patch.dict("os.environ", {"PR_TITLE": "Added login"}, clear=True):
            self.assertNotEqual(validate(), [])

    def test_bot_branch_is_exempt(self):
        with patch.dict("os.environ", {
            "PR_TITLE": "anything goes #123 .",
            "PR_BRANCH": "chore/sync-ai-docs-abc1234",
        }, clear=True):
            self.assertEqual(validate(), [])

    def test_bot_branch_local_variant_is_exempt(self):
        with patch.dict("os.environ", {
            "PR_TITLE": "anything goes",
            "PR_BRANCH": "chore/sync-ai-docs-local-abc1234",
        }, clear=True):
            self.assertEqual(validate(), [])

    def test_non_bot_branch_not_exempt(self):
        with patch.dict("os.environ", {
            "PR_TITLE": "bad title",
            "PR_BRANCH": "feat/whatever",
        }, clear=True):
            self.assertNotEqual(validate(), [])


if __name__ == "__main__":
    unittest.main()
