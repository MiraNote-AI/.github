from __future__ import annotations
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "templates" / "pr-discord-announce.yml"
OWN_COPY = ROOT / ".github" / "workflows" / "pr-discord-announce.yml"


def _body(path: pathlib.Path) -> str:
    """The workflow without its leading comment header."""
    lines = path.read_text().splitlines()
    while lines and (lines[0].startswith("#") or not lines[0].strip()):
        lines.pop(0)
    return "\n".join(lines)


class TestAnnounceWorkflow(unittest.TestCase):
    def test_own_copy_matches_template(self):
        self.assertEqual(_body(OWN_COPY), _body(TEMPLATE))

    def test_sync_copies_template(self):
        sync = (ROOT / ".github" / "workflows" / "sync-ai-docs.yml").read_text()
        self.assertIn(
            "cp source/templates/pr-discord-announce.yml "
            "target/.github/workflows/pr-discord-announce.yml",
            sync,
        )

    def test_missing_secret_exits_cleanly(self):
        body = _body(TEMPLATE)
        self.assertIn('if [ -z "${BOT_TOKEN:-}" ]; then', body)
        self.assertIn("::notice::", body)


if __name__ == "__main__":
    unittest.main()
