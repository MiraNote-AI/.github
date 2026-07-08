from __future__ import annotations
import pathlib
import subprocess
import tempfile
import unittest
from checks.no_cjk_or_emoji import scan_text, validate, main, FORBIDDEN_RANGES


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

    def test_prompts_dir_allowlisted_at_any_depth(self):
        # **/prompts/*.{txt,md} is allowlisted so localized LLM prompts
        # (which often contain CJK few-shot examples) can be committed.
        allowed_rels = [
            "app/prompts/correction.txt",
            "poc/voice-to-text/prompts/correction.txt",
            "deep/a/b/prompts/x.md",
        ]
        for rel in allowed_rels:
            p = self.tmp / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("\u4e2d\u6587 prompt body\n")
            subprocess.run(["git", "add", rel], cwd=self.tmp, check=True)
        # Non-prompts file with CJK must still be flagged.
        self._write_and_stage("src.py", "x = '\u4e2d'\n")
        errors = validate(self.tmp)
        self.assertTrue(any("src.py" in e for e in errors))
        for rel in allowed_rels:
            self.assertFalse(any(rel in e for e in errors), rel)

    def test_binary_audio_extensions_allowlisted(self):
        # **/*.m4a, mp3, wav, etc. are allowlisted so committed audio
        # fixtures (e.g. POC demo clips) don't trip beta on U+FFFD noise.
        # Stage a 16-byte blob with the AAC/m4a magic so it looks plausible
        # but decodes to U+FFFD when read as UTF-8.
        audio_rels = [
            "poc/voice-to-text/demo_data/clip.m4a",
            "fixtures/sample.mp3",
            "tests/data/snippet.wav",
            "examples/voice.flac",
            "examples/voice.ogg",
            "examples/voice.opus",
            "examples/voice.webm",
        ]
        for rel in audio_rels:
            p = self.tmp / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"\x00\x00\x00\x20ftypM4A " + bytes(range(8)))
            subprocess.run(["git", "add", rel], cwd=self.tmp, check=True)
        # A non-audio binary should STILL be flagged (the "binary committed
        # as text" guard from spec 5.3 is preserved).
        (self.tmp / "stray.bin").write_bytes(b"\x89PNG\r\n\x1a\n\x00\xff\xfe")
        subprocess.run(["git", "add", "stray.bin"], cwd=self.tmp, check=True)
        errors = validate(self.tmp)
        self.assertTrue(any("stray.bin" in e for e in errors))
        for rel in audio_rels:
            self.assertFalse(any(rel in e for e in errors), rel)

    def test_binary_font_extensions_allowlisted(self):
        # **/*.ttf and **/*.otf are allowlisted so bundled app fonts (e.g.
        # the iOS app ships Fraunces.ttf) don't trip beta on U+FFFD noise.
        # Same class as the audio group: binary data, no reviewable text.
        font_rels = [
            "App/Resources/Fonts/Fraunces.ttf",
            "assets/fonts/Display.otf",
        ]
        for rel in font_rels:
            p = self.tmp / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            # TrueType magic (00 01 00 00) followed by bytes that decode to
            # U+FFFD when read as UTF-8.
            p.write_bytes(b"\x00\x01\x00\x00\x00\x0f\x00\x80" + bytes([0xC3, 0x28, 0xA0, 0xA1]))
            subprocess.run(["git", "add", rel], cwd=self.tmp, check=True)
        errors = validate(self.tmp)
        for rel in font_rels:
            self.assertFalse(any(rel in e for e in errors), rel)

    def test_static_ui_files_allowlisted(self):
        # Bilingual UI artifacts under any static/ dir can carry localized
        # labels / placeholders.
        ui_rels = [
            "poc/text-clean-expand/static/index.html",
            "app/static/main.css",
            "app/static/app.js",
            "examples/static/logo.svg",
            "deep/a/static/page.html",
        ]
        for rel in ui_rels:
            p = self.tmp / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("<p>\u4e2d\u6587 hint</p>\n")
            subprocess.run(["git", "add", rel], cwd=self.tmp, check=True)
        # Non-static .html with CJK must still be flagged.
        self._write_and_stage("public.html", "<p>\u4e2d\u6587</p>\n")
        errors = validate(self.tmp)
        self.assertTrue(any("public.html" in e for e in errors))
        for rel in ui_rels:
            self.assertFalse(any(rel in e for e in errors), rel)

    def test_demo_data_dir_allowlisted_text_too(self):
        # demo_data/ already covers binary audio (previous test); confirm
        # text files in the same dir are also allowlisted -- sample inputs,
        # README excerpts, etc.
        demo_rels = [
            "poc/text-clean-expand/demo_data/sample.txt",
            "poc/voice-to-text/demo_data/transcript.txt",
            "fixtures/demo_data/inputs.json",
        ]
        for rel in demo_rels:
            p = self.tmp / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("\u4eca\u5929\u5f00\u4f1a sample input\n")
            subprocess.run(["git", "add", rel], cwd=self.tmp, check=True)
        # A txt file outside demo_data must still be flagged.
        self._write_and_stage("notes.txt", "\u4eca\u5929\n")
        errors = validate(self.tmp)
        self.assertTrue(any("notes.txt" in e for e in errors))
        for rel in demo_rels:
            self.assertFalse(any(rel in e for e in errors), rel)

    def test_poc_readme_allowlisted_but_root_and_docs_ai_strict(self):
        # POC READMEs may include native-language curl examples.
        (self.tmp / "poc" / "text-clean-expand").mkdir(parents=True)
        (self.tmp / "poc" / "text-clean-expand" / "README.md").write_text(
            "# POC\n\n`-d '{\"text\": \"\u4eca\u5929\u5f00\u4f1a\"}'`\n"
        )
        subprocess.run(
            ["git", "add", "poc/text-clean-expand/README.md"],
            cwd=self.tmp, check=True,
        )
        # Nested poc/ should also work.
        (self.tmp / "apps" / "poc" / "x").mkdir(parents=True)
        (self.tmp / "apps" / "poc" / "x" / "README.md").write_text("\u4e2d\n")
        subprocess.run(
            ["git", "add", "apps/poc/x/README.md"], cwd=self.tmp, check=True,
        )
        # But root README and docs/ai/README must STAY strict.
        self._write_and_stage("README.md", "\u4e2d\n")
        (self.tmp / "docs" / "ai").mkdir(parents=True)
        (self.tmp / "docs" / "ai" / "README.md").write_text("\u4e2d\n")
        subprocess.run(
            ["git", "add", "docs/ai/README.md"], cwd=self.tmp, check=True,
        )
        errors = validate(self.tmp)
        # Allowlisted: NOT flagged
        self.assertFalse(any("poc/text-clean-expand/README.md" in e for e in errors))
        self.assertFalse(any("apps/poc/x/README.md" in e for e in errors))
        # Strict: STILL flagged
        self.assertTrue(any(e.startswith("README.md:") for e in errors))
        self.assertTrue(any("docs/ai/README.md" in e for e in errors))

    def test_corpus_json_with_cjk_is_allowlisted(self):
        # poc/*/corpus/*.json files are allowed to contain CJK characters
        # for bilingual quote / poetry corpora used in RAG POCs.
        (self.tmp / "poc" / "retrieval" / "corpus").mkdir(parents=True)
        (self.tmp / "poc" / "retrieval" / "corpus" / "quotes_zh.json").write_text(
            '[{"text": "\u5c71\u91cd\u6c34\u590d", "author": "\u9646\u6e38"}]',
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "add", "poc/retrieval/corpus/quotes_zh.json"],
            cwd=self.tmp, check=True,
        )
        # Non-corpus file with CJK must still be flagged.
        self._write_and_stage("src.py", "x = '\u4e2d'\n")
        errors = validate(self.tmp)
        self.assertTrue(any("src.py" in e for e in errors))
        self.assertFalse(any("corpus/quotes_zh.json" in e for e in errors))

    def test_corpus_md_with_cjk_is_allowlisted(self):
        # poc/*/corpus/*.md files (e.g. README, source docs) are allowed
        # to contain CJK characters for corpus documentation and citations.
        (self.tmp / "poc" / "retrieval" / "corpus").mkdir(parents=True)
        (self.tmp / "poc" / "retrieval" / "corpus" / "README.md").write_text(
            "Corpus sources: \u5168\u5510\u8bd7 (Complete Poems of the Tang Dynasty)",
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "add", "poc/retrieval/corpus/README.md"],
            cwd=self.tmp, check=True,
        )
        # Non-corpus file with CJK must still be flagged.
        self._write_and_stage("notes.md", "\u4e2d\n")
        errors = validate(self.tmp)
        self.assertTrue(any("notes.md" in e for e in errors))
        self.assertFalse(any("corpus/README.md" in e for e in errors))

    def test_poc_python_source_still_strict(self):
        # POC code is not exempt -- IME residue in .py is still a violation
        # even under poc/. This protects against inline-prompt-in-source
        # anti-pattern; the right place for CJK prompts is prompts/.
        (self.tmp / "poc" / "x").mkdir(parents=True)
        (self.tmp / "poc" / "x" / "main.py").write_text("# \u4e2d\n")
        subprocess.run(
            ["git", "add", "poc/x/main.py"], cwd=self.tmp, check=True,
        )
        errors = validate(self.tmp)
        self.assertTrue(any("poc/x/main.py" in e for e in errors))

    def test_python_test_files_allowlisted(self):
        # Test files (test_*.py / *_test.py, at any depth) may carry CJK: test
        # *inputs* often need real target-language content (e.g. Chinese prompts
        # exercising a bilingual model). Non-test .py source stays strict.
        test_rels = [
            "poc/image-generation/test_api.py",   # manual test catalog
            "checks/tests/test_thing.py",         # nested unit test
            "app/services/handlers_test.py",      # *_test.py convention
        ]
        for rel in test_rels:
            p = self.tmp / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("prompt = '" + chr(0x4e2d) + chr(0x6587) + "'\n")
            subprocess.run(["git", "add", rel], cwd=self.tmp, check=True)
        # A non-test .py with the same CJK must STILL be flagged.
        self._write_and_stage("poc/image-generation/main.py", "x = '" + chr(0x4e2d) + "'\n")
        errors = validate(self.tmp)
        self.assertTrue(any("poc/image-generation/main.py" in e for e in errors))
        for rel in test_rels:
            self.assertFalse(any(rel in e for e in errors), rel)

    def test_main_returns_2_when_not_a_git_repo(self):
        non_git = pathlib.Path(tempfile.mkdtemp())  # not a git repo
        rc = main([str(non_git)])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
