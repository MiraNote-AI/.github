from __future__ import annotations
import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from checks.protected_paths import paths_intersecting, validate, PROTECTED_GLOBS


class TestPathsIntersecting(unittest.TestCase):
    """Pure-function tests against PROTECTED_GLOBS."""

    def test_no_changes_returns_empty(self):
        self.assertEqual(paths_intersecting([]), [])

    def test_unrelated_changes_returns_empty(self):
        self.assertEqual(paths_intersecting(["src/foo.ts", "README.md"]), [])

    def test_claude_md_match(self):
        self.assertEqual(paths_intersecting(["CLAUDE.md"]), ["CLAUDE.md"])

    def test_contributing_md_match(self):
        self.assertEqual(paths_intersecting(["CONTRIBUTING.md"]), ["CONTRIBUTING.md"])

    def test_docs_ai_nested_match(self):
        self.assertEqual(paths_intersecting(["docs/ai/skills.md"]), ["docs/ai/skills.md"])

    def test_docs_ai_deeply_nested_match(self):
        self.assertEqual(paths_intersecting(["docs/ai/playbooks/foo.md"]), ["docs/ai/playbooks/foo.md"])

    def test_checks_workflow_match(self):
        self.assertEqual(paths_intersecting([".github/workflows/checks.yml"]), [".github/workflows/checks.yml"])

    def test_other_workflow_does_NOT_match(self):
        self.assertEqual(paths_intersecting([".github/workflows/release.yml"]), [])

    def test_claude_skills_nested_match(self):
        self.assertEqual(
            paths_intersecting([".claude/skills/create-pr/SKILL.md"]),
            [".claude/skills/create-pr/SKILL.md"],
        )

    def test_claude_settings_does_NOT_match(self):
        # .claude/settings.json is per-user/per-repo, not synced from .github
        self.assertEqual(paths_intersecting([".claude/settings.json"]), [])

    def test_mixed_changes_returns_only_protected(self):
        changes = ["src/x.ts", "CLAUDE.md", "README.md", "docs/ai/skills.md"]
        self.assertEqual(set(paths_intersecting(changes)), {"CLAUDE.md", "docs/ai/skills.md"})

    def test_docs_aix_NOT_treated_as_docs_ai(self):
        # Ensures the /** prefix-match has correct boundary handling
        # (must not match a path that merely starts with docs/ai)
        self.assertEqual(paths_intersecting(["docs/aix/foo.md"]), [])


class TestValidate(unittest.TestCase):
    """Integration tests with git."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.tmp, check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=self.tmp, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=self.tmp, check=True)
        # initial commit on main
        (self.tmp / "README.md").write_text("hello\n")
        subprocess.run(["git", "add", "."], cwd=self.tmp, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=self.tmp, check=True)
        self.base = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.tmp, capture_output=True, text=True, check=True
        ).stdout.strip()

    def _make_head(self, **files):
        for name, content in files.items():
            path = self.tmp / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        subprocess.run(["git", "checkout", "-qb", "feature"], cwd=self.tmp, check=True)
        subprocess.run(["git", "add", "."], cwd=self.tmp, check=True)
        subprocess.run(["git", "commit", "-qm", "change"], cwd=self.tmp, check=True)
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.tmp, capture_output=True, text=True, check=True
        ).stdout.strip()

    def test_unprotected_change_passes(self):
        head = self._make_head(**{"src/x.ts": "x\n"})
        env = {"BASE_SHA": self.base, "HEAD_SHA": head, "PR_BRANCH": "feature/x"}
        with patch.dict("os.environ", env, clear=True):
            self.assertEqual(validate(self.tmp), [])

    def test_protected_change_on_human_branch_fails(self):
        head = self._make_head(**{"CLAUDE.md": "new content\n"})
        env = {"BASE_SHA": self.base, "HEAD_SHA": head, "PR_BRANCH": "feature/x"}
        with patch.dict("os.environ", env, clear=True):
            errors = validate(self.tmp)
            self.assertEqual(len(errors), 1)
            self.assertIn("CLAUDE.md", errors[0])
            self.assertIn("MiraNote-AI/.github", errors[0])

    def test_protected_change_on_bot_branch_passes(self):
        head = self._make_head(**{"CLAUDE.md": "new content\n"})
        env = {"BASE_SHA": self.base, "HEAD_SHA": head, "PR_BRANCH": "chore/sync-ai-docs-abc1234"}
        with patch.dict("os.environ", env, clear=True):
            self.assertEqual(validate(self.tmp), [])

    def test_missing_env_vars_returns_empty(self):
        # CI workflow gates eta on `pull_request`; script should be tolerant if called otherwise.
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(validate(self.tmp), [])

    def test_main_returns_2_on_bad_sha(self):
        env = {
            "BASE_SHA": "0000000000000000000000000000000000000000",
            "HEAD_SHA": "1111111111111111111111111111111111111111",
            "PR_BRANCH": "feature/x",
        }
        from checks.protected_paths import main
        with patch.dict("os.environ", env, clear=True):
            rc = main([str(self.tmp)])
            self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
