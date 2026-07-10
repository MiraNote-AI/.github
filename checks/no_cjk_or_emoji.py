"""Rule 3 (beta): No CJK characters or emoji in committed files.

Scans every file returned by `git ls-files --cached --others --exclude-standard`
in the target repo. The `--others` flag is critical -- without it, locally
staged-but-not-committed files (or untracked-but-tracked-elsewhere files) slip
through local checks and only fail in CI. DASGPT learned this the hard way
(spec section 5.3, hands-on lesson 9.2).

Uses hardcoded Unicode block ranges; Python stdlib does not expose the
Emoji_Presentation property, and `re` does not support \\p{...}.
"""
from __future__ import annotations
import argparse
import fnmatch
import pathlib
import subprocess
import sys
from typing import List, Tuple


# (start, end, name) -- inclusive on both ends.
FORBIDDEN_RANGES: List[Tuple[int, int, str]] = [
    # CJK / fullwidth blocks
    (0x3040, 0x309F, "Hiragana"),
    (0x30A0, 0x30FF, "Katakana"),
    (0x4E00, 0x9FFF, "CJK Unified Ideographs"),
    (0x3400, 0x4DBF, "CJK Unified Ideographs Extension A"),
    (0x3000, 0x303F, "CJK Symbols and Punctuation"),
    (0xFF00, 0xFFEF, "Halfwidth and Fullwidth Forms"),
    # Emoji blocks
    (0x1F600, 0x1F64F, "Emoticons"),
    (0x1F300, 0x1F5FF, "Misc Symbols and Pictographs"),
    (0x1F680, 0x1F6FF, "Transport and Map Symbols"),
    (0x1F900, 0x1F9FF, "Supplemental Symbols and Pictographs"),
    (0x1FA70, 0x1FAFF, "Symbols and Pictographs Extended-A"),
    (0x1F1E6, 0x1F1FF, "Regional Indicator Symbols"),
    # Decoding-error sentinel -- spec section 5.3 declares this a violation, so a
    # binary file committed as text (which decodes to U+FFFD with errors=replace)
    # is caught here.
    (0xFFFD, 0xFFFD, "Replacement character (non-UTF-8 input)"),
]

# Filenames or globs to skip even if they would otherwise be scanned.
ALLOWLIST_PATTERNS: List[str] = [
    # Planning artifacts that legitimately discuss forbidden characters
    # (e.g., showing example test fixtures). User-facing docs/ai/ are NOT
    # allowlisted — they must stay clean.
    "docs/plans/*.md",
    "docs/specs/*.md",
    # Localized runtime data: LLM prompts under any `prompts/` directory
    # often need CJK content (e.g., few-shot examples for a Chinese model).
    # The directory name is the contract; if a file is not actually loaded
    # as a prompt, do not put it under `prompts/`.
    "**/prompts/*.txt",
    "**/prompts/*.md",
    # Binary audio fixtures used as test data (e.g. POC demo clips).
    # They decode to U+FFFD noise with errors="replace" and contain no
    # real text -- there is no value in scanning them for CJK. The
    # "binary mistakenly committed as text" guard is preserved for any
    # extension not listed here.
    "**/*.m4a",
    "**/*.mp3",
    "**/*.wav",
    "**/*.flac",
    "**/*.ogg",
    "**/*.opus",
    "**/*.webm",
    # Bundled font binaries (e.g. the iOS app ships Fraunces). Same
    # rationale as the audio group above: binary data decodes to U+FFFD
    # noise and carries no reviewable text.
    "**/*.ttf",
    "**/*.otf",
    # Content for a bilingual product. UI files under any `static/` directory
    # legitimately need localized labels / placeholders / SVG text. Demo data
    # under any `demo_data/` directory is sample input by definition.
    # Source code (.py/.ts/.js outside static/, config files, build scripts,
    # CLAUDE.md, docs/ai/, top-level README/CONTRIBUTING) all stay strict --
    # the original "no IME residue in code" rationale still applies there.
    "**/static/*.html",
    "**/static/*.css",
    "**/static/*.js",
    "**/static/*.svg",
    "**/demo_data/*",
    # Curated content datasets for retrieval / RAG POCs. Same rationale
    # as demo_data: this is data, not source code, and the CJK content
    # is the whole point (bilingual quotes / poetry).
    "poc/*/corpus/*.json",
    "poc/*/corpus/*.md",
    # POC READMEs may include native-language curl examples / sample inputs
    # so users can paste a representative payload. Top-level README and
    # docs/ai/README.md remain strict.
    "poc/*/README.md",
    "**/poc/*/README.md",
    # Test files. Test *inputs* frequently need real target-language content
    # (e.g. Chinese prompts exercising a bilingual model, or bilingual
    # fixtures), and test code is not a user-facing product surface. Matches
    # Python's unittest/pytest naming (test_*.py, *_test.py) at any depth.
    # Non-test source (main.py, handlers, config) stays strict, so IME residue
    # in production code is still caught.
    "**/test_*.py",
    "**/*_test.py",
]


def _classify(cp: int) -> str:
    for lo, hi, name in FORBIDDEN_RANGES:
        if lo <= cp <= hi:
            return name
    return ""


def scan_text(text: str) -> List[Tuple[int, int, int, str]]:
    """Return list of (line_no_1based, col_1based, codepoint, block_name) violations."""
    violations = []
    for line_no, line in enumerate(text.split("\n"), start=1):
        for col, ch in enumerate(line, start=1):
            cp = ord(ch)
            block = _classify(cp)
            if block:
                violations.append((line_no, col, cp, block))
    return violations


def _list_files(repo_root: pathlib.Path) -> List[pathlib.Path]:
    """Run git ls-files --cached --others --exclude-standard inside repo_root."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=repo_root, capture_output=True, text=True, check=True,
    )
    return [repo_root / line for line in result.stdout.splitlines() if line]


def _is_allowlisted(rel_path: str) -> bool:
    return any(fnmatch.fnmatchcase(rel_path, pat) for pat in ALLOWLIST_PATTERNS)


def validate(repo_root: pathlib.Path) -> List[str]:
    """Return list of error messages. Empty list == pass."""
    errors: List[str] = []
    for path in _list_files(repo_root):
        if not path.is_file():
            continue
        rel = path.relative_to(repo_root).as_posix()
        if _is_allowlisted(rel):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            errors.append(f"{rel}: cannot read ({e})")
            continue
        for line, col, cp, block in scan_text(text):
            errors.append(
                f"{rel}:{line}:{col}: forbidden character U+{cp:04X} "
                f"(block: {block})"
            )
    return errors


def main(argv=None) -> int:
    """Scan repo for CJK / emoji in committed files.

    Returns:
        0: no violations found
        1: violations found (errors printed to stderr)
        2: infrastructure error (git repo not found, git missing, or path doesn't exist)
    """
    parser = argparse.ArgumentParser(description="Scan for CJK / emoji in committed files (β).")
    parser.add_argument("repo", help="repo root to scan")
    args = parser.parse_args(argv)

    try:
        errors = validate(pathlib.Path(args.repo))
    except subprocess.CalledProcessError as e:
        print(
            f"error: git ls-files failed in {args.repo!r} "
            f"(exit {e.returncode}). Is this a git repository?",
            file=sys.stderr,
        )
        return 2
    except FileNotFoundError as e:
        # git binary not installed, or repo path doesn't exist
        print(f"error: {e}", file=sys.stderr)
        return 2
    for e in errors:
        print(e, file=sys.stderr)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
