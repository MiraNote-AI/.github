from __future__ import annotations
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import textwrap
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


def _run_block(path: pathlib.Path) -> str:
    """The step's `run: |` script, dedented. The workflow has one step."""
    lines = path.read_text().splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "run: |":
            indent = len(line) - len(line.lstrip())
            script = []
            for nxt in lines[i + 1:]:
                if nxt.strip() and len(nxt) - len(nxt.lstrip()) <= indent:
                    break
                script.append(nxt)
            return textwrap.dedent("\n".join(script)) + "\n"
    raise AssertionError(f"no `run: |` block in {path}")


# Stands in for curl on PATH: records its argv, saves the -d payload and
# writes a response body to -o, prints FAKE_HTTP_CODE (curl's -w) and exits
# with FAKE_CURL_EXIT. Nothing leaves the machine.
FAKE_CURL = """#!/bin/sh
printf '%s\\n' "$@" > "$PROBE_OUT/argv"
out=""
while [ $# -gt 0 ]; do
  case "$1" in
    -o) out="$2"; shift 2;;
    -d) printf '%s' "$2" > "$PROBE_OUT/payload.json"; shift 2;;
    *) shift;;
  esac
done
if [ -n "$out" ]; then printf '{"message": "fake"}' > "$out"; fi
printf '%s' "${FAKE_HTTP_CODE:-200}"
exit "${FAKE_CURL_EXIT:-0}"
"""


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


@unittest.skipUnless(shutil.which("bash") and shutil.which("jq"),
                     "needs bash and jq, as on the ubuntu runner")
class TestAnnounceStep(unittest.TestCase):
    """Runs the template's shell step against a fake curl."""

    def _run(self, **env: str):
        tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        fake_bin = tmp / "bin"
        fake_bin.mkdir()
        curl = fake_bin / "curl"
        curl.write_text(FAKE_CURL)
        curl.chmod(0o755)
        step = tmp / "step.sh"
        step.write_text(_run_block(TEMPLATE))
        full_env = {
            "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}",
            "PROBE_OUT": str(tmp),
            "RUNNER_TEMP": str(tmp),
            "BOT_TOKEN": "not-a-real-token",
            "CHANNEL_ID": "1",
            "PR_TITLE": "feat(api): add login",
            "PR_URL": "https://github.com/MiraNote-AI/miranote-api/pull/1",
            "PR_AUTHOR": "someone",
            "REPO_NAME": "MiraNote-AI/miranote-api",
        }
        full_env.update(env)
        result = subprocess.run(
            ["bash", "-e", str(step)], cwd=tmp, env=full_env,
            capture_output=True, text=True, timeout=60,
        )
        return result, tmp

    def test_missing_secret_skips_with_notice(self):
        result, tmp = self._run(BOT_TOKEN="")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("::notice::", result.stdout)
        self.assertFalse((tmp / "argv").exists(), "curl ran without a token")

    def test_title_stays_data(self):
        title = ('fix: "q" `touch PWNED_TICK` $(touch PWNED_SUBST) '
                 "$BOT_TOKEN @everyone <@&1>\nsecond line \\ é")
        result, tmp = self._run(PR_TITLE=title)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads((tmp / "payload.json").read_text())
        self.assertEqual(set(payload), {"content", "allowed_mentions"})
        self.assertEqual(payload["allowed_mentions"], {"parse": []})
        self.assertIn(f"**{title}**", payload["content"])
        self.assertIn("https://github.com/MiraNote-AI/miranote-api/pull/1",
                      payload["content"])
        self.assertEqual(sorted(p.name for p in tmp.glob("PWNED*")), [])

    def test_discord_error_is_a_warning(self):
        result, _ = self._run(FAKE_HTTP_CODE="401")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("::warning::", result.stdout)

    def test_network_failure_is_a_warning(self):
        result, _ = self._run(FAKE_HTTP_CODE="000", FAKE_CURL_EXIT="6")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("::warning::", result.stdout)


if __name__ == "__main__":
    unittest.main()
