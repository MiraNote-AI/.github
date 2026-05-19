# MiraNote Harness Engineering Day-0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the day-0 verification infrastructure for MiraNote in `MiraNote-AI/.github`: a shared parser library, 7 Python rule-check scripts (α γ β δ ε ζ η) with stdlib-only unittest coverage, three GitHub Actions workflows (reusable + self-check + target stub), bootstrap content files (`CONTRIBUTING.md`, `docs/ai/skills.md`, refreshed `CLAUDE.md`), and sync-workflow expansion. After completion, all checks pass against the local `.github` clone (spec §7 Phase 1).

**Architecture:** All checks live in `checks/` as stdlib-only Python modules invoked as `python -m checks.X <repo_path> [flags]`. Each check is a pure validator function plus a thin CLI wrapper, allowing unit tests to call validators directly. A shared `checks/_meta/parser.py` library parses `CONTRIBUTING.md` once and feeds both γ (structural validation) and α (meta-mapping validation). CI uses a single reusable workflow that 4 target repos call via `uses:`; `.github` calls the same workflow against itself in `mode=source` (with `tools` symlinked to `code` to ensure PR-version checks validate PR-version checks, per spec §6.1 bug-fix).

**Tech Stack:** Python 3.9+ stdlib only (`unittest`, `re`, `fnmatch`, `subprocess`, `pathlib`, `argparse`, `sys`, `os`, `dataclasses`). GitHub Actions (`actions/checkout@v4`, `actions/setup-python@v5`). bash for `bin/sync-ai-docs.sh`. YAML for workflows.

**Reference:** `docs/superpowers/specs/2026-05-19-harness-engineering-day0-design.md` (commit `f414e90`).

**Working directory for all commands:** `/Users/mengjia/MiraNote/.github` unless otherwise stated.

---

## File structure

After this plan completes, `MiraNote-AI/.github` contains:

```
.github/
├── CLAUDE.md                              # MODIFIED: real day-0 entry, ≤ 80 lines
├── CONTRIBUTING.md                        # NEW: 7 rules registered
├── docs/
│   ├── ai/
│   │   ├── README.md                      # MODIFIED: point to docs
│   │   └── skills.md                      # NEW: Skill/MCP registry
│   └── superpowers/
│       ├── specs/                         # already populated
│       └── plans/                         # this file lives here
├── checks/
│   ├── __init__.py                        # NEW: empty
│   ├── _meta/
│   │   ├── __init__.py                    # NEW: empty
│   │   ├── parser.py                      # NEW: shared CONTRIBUTING.md parser
│   │   └── all_rules_have_checks.py       # NEW: α
│   ├── contributing_format.py             # NEW: γ
│   ├── no_cjk_or_emoji.py                 # NEW: β
│   ├── claude_md_size.py                  # NEW: δ
│   ├── skills_registry.py                 # NEW: ε
│   ├── pr_has_reference.py                # NEW: ζ
│   ├── protected_paths.py                 # NEW: η
│   └── tests/
│       ├── __init__.py                    # NEW: empty
│       ├── test_parser.py                 # NEW
│       ├── test_contributing_format.py    # NEW
│       ├── test_all_rules_have_checks.py  # NEW
│       ├── test_no_cjk_or_emoji.py        # NEW
│       ├── test_claude_md_size.py         # NEW
│       ├── test_skills_registry.py        # NEW
│       ├── test_pr_has_reference.py       # NEW
│       └── test_protected_paths.py        # NEW
├── .github/workflows/
│   ├── sync-ai-docs.yml                   # MODIFIED: expanded sync scope
│   ├── checks.yml                         # NEW: reusable
│   └── self-check.yml                     # NEW
├── templates/
│   └── target-workflow.yml                # NEW: stub for targets
└── bin/
    └── sync-ai-docs.sh                    # MODIFIED: expanded sync scope
```

Tests live inside `checks/tests/`, which is a subdirectory of `checks/` — the orphan check (§4.3) scans only direct children of `checks/`, so test files do not need rule registration.

Each check follows the same internal shape:

```python
# checks/<name>.py
"""Rule <N>: <one-line description>."""
from __future__ import annotations
import argparse, pathlib, sys

def validate(...) -> list[str]:
    """Return a list of error messages. Empty list == pass."""
    ...

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(...)
    args = parser.parse_args(argv)
    errors = validate(...)
    for e in errors:
        print(e, file=sys.stderr)
    return 0 if not errors else 1

if __name__ == "__main__":
    sys.exit(main())
```

Tests import `validate` directly, bypassing the CLI layer, so they're fast and don't need subprocess.

---

## Task 1: Package skeleton

**Files:**
- Create: `checks/__init__.py`
- Create: `checks/_meta/__init__.py`
- Create: `checks/tests/__init__.py`

- [ ] **Step 1: Create the three `__init__.py` files**

```bash
mkdir -p checks/_meta checks/tests
touch checks/__init__.py checks/_meta/__init__.py checks/tests/__init__.py
```

- [ ] **Step 2: Smoke-test that the package imports**

Run: `PYTHONPATH=. python3 -c "import checks, checks._meta, checks.tests; print('ok')"`
Expected: prints `ok` and exits 0.

- [ ] **Step 3: Commit**

```bash
git add checks/__init__.py checks/_meta/__init__.py checks/tests/__init__.py
git commit -m "chore: scaffold checks/ package skeleton"
```

---

## Task 2: Shared CONTRIBUTING.md parser (`checks/_meta/parser.py`)

The parser is the foundation for γ and α. It is tolerant — it collects ALL errors rather than raising on the first, so γ can report every violation in one PR cycle.

**Files:**
- Create: `checks/_meta/parser.py`
- Create: `checks/tests/test_parser.py`

- [ ] **Step 1: Write the test file**

```python
# checks/tests/test_parser.py
"""Tests for the shared CONTRIBUTING.md parser."""
from __future__ import annotations
import unittest
from checks._meta.parser import parse_contributing, Rule, ParseError


VALID_MINIMAL = """\
# Contributing

(prose)

## Rules

### Rule 1: Foo

Some prose explaining the rule.

**Rationale:** Because.
**Enforced by:** `checks/foo.py`
"""


VALID_TWO_RULES_MULTIPLE_ENFORCERS = """\
## Rules

### Rule 1: Foo

p

**Rationale:** r1
**Enforced by:** `checks/foo.py`

### Rule 5: Bar

p

**Rationale:** r2
**Enforced by:** `checks/bar.py`, `checks/bar_extra.py`
"""


NO_RULES_SECTION = """\
# Contributing

No rules section here.
"""


DUPLICATE_RULE_ID = """\
## Rules

### Rule 1: First

p

**Rationale:** r
**Enforced by:** `checks/a.py`

### Rule 1: Duplicate

p

**Rationale:** r
**Enforced by:** `checks/b.py`
"""


MISSING_RATIONALE = """\
## Rules

### Rule 1: Foo

p

**Enforced by:** `checks/foo.py`
"""


MISSING_ENFORCED_BY = """\
## Rules

### Rule 1: Foo

p

**Rationale:** r
"""


TWO_RATIONALE_LINES = """\
## Rules

### Rule 1: Foo

p

**Rationale:** r1
**Rationale:** r2
**Enforced by:** `checks/foo.py`
"""


EMPTY_ENFORCED_BY = """\
## Rules

### Rule 1: Foo

p

**Rationale:** r
**Enforced by:**
"""


class TestParser(unittest.TestCase):

    def test_valid_minimal_returns_one_rule(self):
        rules, errors = parse_contributing(VALID_MINIMAL)
        self.assertEqual(errors, [])
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].id, 1)
        self.assertEqual(rules[0].title, "Foo")
        self.assertEqual(rules[0].rationale, "Because.")
        self.assertEqual(rules[0].enforced_by, ["checks/foo.py"])

    def test_two_rules_with_gaps_and_multiple_enforcers(self):
        rules, errors = parse_contributing(VALID_TWO_RULES_MULTIPLE_ENFORCERS)
        self.assertEqual(errors, [])
        self.assertEqual([r.id for r in rules], [1, 5])
        self.assertEqual(rules[1].enforced_by, ["checks/bar.py", "checks/bar_extra.py"])

    def test_missing_rules_section(self):
        rules, errors = parse_contributing(NO_RULES_SECTION)
        self.assertEqual(rules, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("## Rules", errors[0].message)

    def test_duplicate_rule_id_reports_error_and_keeps_first(self):
        rules, errors = parse_contributing(DUPLICATE_RULE_ID)
        self.assertEqual(len(errors), 1)
        self.assertIn("Rule 1", errors[0].message)
        self.assertIn("duplicate", errors[0].message.lower())
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].title, "First")

    def test_missing_rationale(self):
        rules, errors = parse_contributing(MISSING_RATIONALE)
        self.assertEqual(len(errors), 1)
        self.assertIn("Rationale", errors[0].message)

    def test_missing_enforced_by(self):
        rules, errors = parse_contributing(MISSING_ENFORCED_BY)
        self.assertEqual(len(errors), 1)
        self.assertIn("Enforced by", errors[0].message)

    def test_two_rationale_lines_reports_error(self):
        rules, errors = parse_contributing(TWO_RATIONALE_LINES)
        self.assertEqual(len(errors), 1)
        self.assertIn("Rationale", errors[0].message)
        self.assertIn("exactly one", errors[0].message.lower())

    def test_empty_enforced_by_list_reports_error(self):
        rules, errors = parse_contributing(EMPTY_ENFORCED_BY)
        self.assertEqual(len(errors), 1)
        self.assertIn("Enforced by", errors[0].message)

    def test_path_tokens_stripped_of_backticks_and_whitespace(self):
        text = (
            "## Rules\n\n"
            "### Rule 1: Foo\n\np\n\n"
            "**Rationale:** r\n"
            "**Enforced by:**  `checks/a.py`  ,   `checks/b.py`\n"
        )
        rules, errors = parse_contributing(text)
        self.assertEqual(errors, [])
        self.assertEqual(rules[0].enforced_by, ["checks/a.py", "checks/b.py"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to confirm they all fail (import error)**

Run: `PYTHONPATH=. python3 -m unittest checks.tests.test_parser -v`
Expected: every test errors with `ModuleNotFoundError: No module named 'checks._meta.parser'`.

- [ ] **Step 3: Implement the parser**

```python
# checks/_meta/parser.py
"""Parse CONTRIBUTING.md into a list of Rule objects.

The parser is tolerant: it collects every violation it finds rather than
raising on the first. Callers use the (rules, errors) tuple to report all
violations in one pass.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Rule:
    id: int
    title: str
    body: str
    rationale: str
    enforced_by: List[str]
    line_no: int  # 1-based line where the heading appears


@dataclass
class ParseError:
    message: str
    line: Optional[int] = None


_RULES_SECTION_RE = re.compile(r"^##\s+Rules\s*$", re.MULTILINE)
_RULE_HEADING_RE = re.compile(r"^###\s+Rule\s+(\d+)\s*:\s*(.+?)\s*$")
_RATIONALE_RE = re.compile(r"^\*\*Rationale:\*\*\s*(.*)$")
_ENFORCED_BY_RE = re.compile(r"^\*\*Enforced by:\*\*\s*(.*)$")


def _strip_backticks_and_space(token: str) -> str:
    return token.strip().strip("`").strip()


def _split_enforced_by(value: str) -> List[str]:
    if not value.strip():
        return []
    return [_strip_backticks_and_space(p) for p in value.split(",")]


def parse_contributing(text: str) -> Tuple[List[Rule], List[ParseError]]:
    """Parse CONTRIBUTING.md text. Returns (rules, errors).

    rules may be partial when errors are present (e.g., a duplicate rule
    keeps the first occurrence and emits an error for the second).
    """
    errors: List[ParseError] = []
    rules: List[Rule] = []

    # Step 1: locate the ## Rules section
    section_match = _RULES_SECTION_RE.search(text)
    if not section_match:
        errors.append(ParseError("CONTRIBUTING.md must contain a `## Rules` section"))
        return rules, errors

    body = text[section_match.end():]
    lines_before_section = text[: section_match.start()].count("\n")

    # Step 2: split the rules section into per-rule chunks by ### Rule N: headings
    lines = body.split("\n")
    chunks: List[Tuple[int, str, str, List[str]]] = []  # (line_no, raw_heading, title_or_id, body_lines)
    current_heading: Optional[Tuple[int, str, int, str]] = None  # (line_no, raw, id_num, title)
    current_body: List[str] = []

    for offset, line in enumerate(lines):
        m = _RULE_HEADING_RE.match(line)
        if m:
            # flush previous
            if current_heading is not None:
                chunks.append((current_heading[0], current_heading[1], current_heading[3], current_body))
                current_body = []
            line_no = lines_before_section + 1 + offset + 1  # +1 because section heading consumed a line
            rule_id = int(m.group(1))
            title = m.group(2)
            current_heading = (line_no, line, rule_id, title)
        elif line.startswith("### "):
            # a non-Rule h3 — terminates the current rule body
            if current_heading is not None:
                chunks.append((current_heading[0], current_heading[1], current_heading[3], current_body))
                current_heading = None
                current_body = []
        else:
            if current_heading is not None:
                current_body.append(line)

    # flush trailing
    if current_heading is not None:
        chunks.append((current_heading[0], current_heading[1], current_heading[3], current_body))

    seen_ids = set()
    for line_no, raw_heading, title, body_lines in chunks:
        m = _RULE_HEADING_RE.match(raw_heading)
        rule_id = int(m.group(1))
        if rule_id in seen_ids:
            errors.append(ParseError(f"Rule {rule_id} is a duplicate (already seen)", line=line_no))
            continue
        seen_ids.add(rule_id)

        rationale_matches = []
        enforced_matches = []
        for body_line_no, line in enumerate(body_lines, start=line_no + 1):
            rm = _RATIONALE_RE.match(line)
            if rm:
                rationale_matches.append((body_line_no, rm.group(1).strip()))
            em = _ENFORCED_BY_RE.match(line)
            if em:
                enforced_matches.append((body_line_no, em.group(1).strip()))

        if len(rationale_matches) != 1:
            errors.append(
                ParseError(
                    f"Rule {rule_id} must contain exactly one `**Rationale:**` line "
                    f"(found {len(rationale_matches)})",
                    line=line_no,
                )
            )
            rationale = ""
        else:
            rationale = rationale_matches[0][1]

        if len(enforced_matches) != 1:
            errors.append(
                ParseError(
                    f"Rule {rule_id} must contain exactly one `**Enforced by:**` line "
                    f"(found {len(enforced_matches)})",
                    line=line_no,
                )
            )
            enforced_by: List[str] = []
        else:
            enforced_by = _split_enforced_by(enforced_matches[0][1])
            if not enforced_by:
                errors.append(
                    ParseError(
                        f"Rule {rule_id} has an empty `**Enforced by:**` value",
                        line=line_no,
                    )
                )

        # only add the rule if it had a rationale AND a usable enforced_by;
        # otherwise downstream consumers may misuse the partial record
        if len(rationale_matches) == 1 and len(enforced_matches) == 1 and enforced_by:
            rules.append(
                Rule(
                    id=rule_id,
                    title=title,
                    body="\n".join(body_lines).strip(),
                    rationale=rationale,
                    enforced_by=enforced_by,
                    line_no=line_no,
                )
            )

    return rules, errors
```

- [ ] **Step 4: Run the tests, expect all pass**

Run: `PYTHONPATH=. python3 -m unittest checks.tests.test_parser -v`
Expected: 9 tests, all PASS.

- [ ] **Step 5: Commit**

```bash
git add checks/_meta/parser.py checks/tests/test_parser.py
git commit -m "feat(checks): add shared CONTRIBUTING.md parser library"
```

---

## Task 3: γ — `contributing_format.py` (Rule 2)

γ validates the structural shape of `CONTRIBUTING.md`. In `mode=source` it also verifies each `Enforced by:` path resolves to an existing file; in `mode=target` path existence is skipped because the paths point to scripts that only exist in `.github`.

**Files:**
- Create: `checks/contributing_format.py`
- Create: `checks/tests/test_contributing_format.py`

- [ ] **Step 1: Write the test file**

```python
# checks/tests/test_contributing_format.py
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
```

- [ ] **Step 2: Run tests, confirm all fail**

Run: `PYTHONPATH=. python3 -m unittest checks.tests.test_contributing_format -v`
Expected: 8 tests error with `ModuleNotFoundError: No module named 'checks.contributing_format'`.

- [ ] **Step 3: Implement γ**

```python
# checks/contributing_format.py
"""Rule 2 (γ): CONTRIBUTING.md follows the canonical structure.

In source mode, every path on every `Enforced by:` line must resolve
relative to the repo root. In target mode, path resolution is skipped
(those scripts live only in MiraNote-AI/.github, not in target repos).
"""
from __future__ import annotations
import argparse
import pathlib
import sys
from typing import List

from checks._meta.parser import parse_contributing


def validate(repo_root: pathlib.Path, mode: str) -> List[str]:
    """Validate CONTRIBUTING.md under repo_root. Returns error messages."""
    if mode not in ("source", "target"):
        return [f"unknown mode: {mode!r} (expected 'source' or 'target')"]

    contributing = repo_root / "CONTRIBUTING.md"
    if not contributing.exists():
        return [f"CONTRIBUTING.md not found at {contributing}"]

    text = contributing.read_text(encoding="utf-8")
    rules, parse_errors = parse_contributing(text)
    errors: List[str] = []

    for pe in parse_errors:
        prefix = f"CONTRIBUTING.md:{pe.line}: " if pe.line else "CONTRIBUTING.md: "
        errors.append(prefix + pe.message)

    if mode == "source":
        for rule in rules:
            for path in rule.enforced_by:
                resolved = repo_root / path
                if not resolved.exists():
                    errors.append(
                        f"CONTRIBUTING.md:{rule.line_no}: Rule {rule.id}: "
                        f"`Enforced by:` path {path!r} does not exist"
                    )

    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Validate CONTRIBUTING.md structure (γ).")
    parser.add_argument("repo", help="path to the repo root containing CONTRIBUTING.md")
    parser.add_argument("--mode", choices=("source", "target"), default="source")
    args = parser.parse_args(argv)

    errors = validate(pathlib.Path(args.repo), args.mode)
    for e in errors:
        print(e, file=sys.stderr)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests, confirm all pass**

Run: `PYTHONPATH=. python3 -m unittest checks.tests.test_contributing_format -v`
Expected: 8 tests, all PASS.

- [ ] **Step 5: Commit**

```bash
git add checks/contributing_format.py checks/tests/test_contributing_format.py
git commit -m "feat(checks): add γ (CONTRIBUTING.md format check, Rule 2)"
```

---

## Task 4: α — `_meta/all_rules_have_checks.py` (Rule 1)

α verifies the doc-to-script mapping in both directions: forward (every referenced path exists) and reverse (every direct-child `.py` in `checks/` is registered by at least one rule).

**Files:**
- Create: `checks/_meta/all_rules_have_checks.py`
- Create: `checks/tests/test_all_rules_have_checks.py`

- [ ] **Step 1: Write the test file**

```python
# checks/tests/test_all_rules_have_checks.py
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

    def test_skips_when_parse_errors_exist(self):
        _write(self.tmp / "CONTRIBUTING.md", "no rules here")
        _write(self.tmp / "checks" / "__init__.py")
        errors = validate(self.tmp)
        # γ would catch the parse error; α reports it surfaced from parser
        self.assertTrue(errors)

    def test_main_returns_zero_on_pass(self):
        _make_valid_repo(self.tmp)
        self.assertEqual(main([str(self.tmp)]), 0)

    def test_main_returns_nonzero_on_fail(self):
        _make_valid_repo(self.tmp)
        _write(self.tmp / "checks" / "orphan.py")
        self.assertNotEqual(main([str(self.tmp)]), 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests, confirm all fail**

Run: `PYTHONPATH=. python3 -m unittest checks.tests.test_all_rules_have_checks -v`
Expected: 8 tests error with `ModuleNotFoundError`.

- [ ] **Step 3: Implement α**

```python
# checks/_meta/all_rules_have_checks.py
"""Rule 1 (α): Every rule has an enforcement mechanism.

Verifies the doc → script mapping in both directions:
- Forward: every path referenced in CONTRIBUTING.md's `Enforced by:` lines exists.
- Reverse: every `.py` file at the direct top level of `checks/` is referenced
  by at least one rule (orphan detection). Subdirectories like `_meta/` are
  intentionally not scanned — they're reserved for meta-tooling and library code.
"""
from __future__ import annotations
import argparse
import pathlib
import sys
from typing import List

from checks._meta.parser import parse_contributing


def _direct_check_files(checks_dir: pathlib.Path) -> List[pathlib.Path]:
    """Return all .py files at the direct top level of checks/, excluding __init__.py."""
    if not checks_dir.is_dir():
        return []
    return sorted(
        p for p in checks_dir.iterdir()
        if p.is_file() and p.suffix == ".py" and p.name != "__init__.py"
    )


def validate(repo_root: pathlib.Path) -> List[str]:
    """Return list of error messages. Empty list == pass."""
    contributing = repo_root / "CONTRIBUTING.md"
    if not contributing.exists():
        return [f"CONTRIBUTING.md not found at {contributing}"]

    text = contributing.read_text(encoding="utf-8")
    rules, parse_errors = parse_contributing(text)

    errors: List[str] = []
    for pe in parse_errors:
        prefix = f"CONTRIBUTING.md:{pe.line}: " if pe.line else "CONTRIBUTING.md: "
        errors.append(prefix + pe.message)

    # Forward: every referenced check path must exist
    referenced: set = set()
    for rule in rules:
        for path in rule.enforced_by:
            referenced.add(path)
            resolved = repo_root / path
            if not resolved.exists():
                errors.append(
                    f"Rule {rule.id}: referenced check {path!r} does not exist"
                )

    # Reverse: every direct-child .py under checks/ must be referenced
    for check_file in _direct_check_files(repo_root / "checks"):
        rel = check_file.relative_to(repo_root).as_posix()
        if rel not in referenced:
            errors.append(
                f"Orphan check: {rel} is not referenced by any rule's "
                f"`Enforced by:` line. Either register it in CONTRIBUTING.md "
                f"or move it under a subdirectory if it is library code."
            )

    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify rules-to-checks mapping (α).")
    parser.add_argument("repo", help="repo root containing CONTRIBUTING.md and checks/")
    args = parser.parse_args(argv)

    errors = validate(pathlib.Path(args.repo))
    for e in errors:
        print(e, file=sys.stderr)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests, confirm all pass**

Run: `PYTHONPATH=. python3 -m unittest checks.tests.test_all_rules_have_checks -v`
Expected: 8 tests, all PASS.

- [ ] **Step 5: Commit**

```bash
git add checks/_meta/all_rules_have_checks.py checks/tests/test_all_rules_have_checks.py
git commit -m "feat(checks): add α (meta-rule, all rules have checks, Rule 1)"
```

---

## Task 5: β — `no_cjk_or_emoji.py` (Rule 3)

β scans every committed and staged-or-untracked file for CJK/fullwidth characters and emoji code points within the explicit Unicode ranges listed in spec §5.3.

**Files:**
- Create: `checks/no_cjk_or_emoji.py`
- Create: `checks/tests/test_no_cjk_or_emoji.py`

- [ ] **Step 1: Write the test file**

```python
# checks/tests/test_no_cjk_or_emoji.py
from __future__ import annotations
import pathlib
import subprocess
import tempfile
import unittest
from checks.no_cjk_or_emoji import scan_text, validate, FORBIDDEN_RANGES


class TestScanText(unittest.TestCase):
    """Tests for the pure-function range scanner (no git involvement)."""

    def test_clean_ascii_text_returns_no_violations(self):
        self.assertEqual(scan_text("hello world\nplain text\n"), [])

    def test_chinese_character_is_flagged(self):
        violations = scan_text("hello 中 world")  # U+4E2D 中
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0][0], 1)  # line 1
        self.assertEqual(violations[0][2], 0x4E2D)

    def test_hiragana_is_flagged(self):
        violations = scan_text("あ")  # U+3042 あ
        self.assertEqual(len(violations), 1)

    def test_katakana_is_flagged(self):
        violations = scan_text("ア")  # U+30A2 ア
        self.assertEqual(len(violations), 1)

    def test_emoji_is_flagged(self):
        violations = scan_text("hi \U0001F600")  # 😀
        self.assertEqual(len(violations), 1)

    def test_text_presentation_symbols_NOT_flagged(self):
        # ✓ U+2713, → U+2192, box-drawing — all allowed per spec §5.3
        self.assertEqual(scan_text("✓ → ─"), [])

    def test_multiple_violations_on_different_lines(self):
        violations = scan_text("ok\n中\nあ\n")
        self.assertEqual(len(violations), 2)
        self.assertEqual(violations[0][0], 2)
        self.assertEqual(violations[1][0], 3)

    def test_fullwidth_punctuation_flagged(self):
        violations = scan_text("hi！")  # ！ fullwidth exclamation
        self.assertEqual(len(violations), 1)

    def test_cjk_extension_a_flagged(self):
        violations = scan_text("㐀")  # CJK Ext A start
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
        self._write_and_stage("a.py", "x = '中'\n")
        errors = validate(self.tmp)
        self.assertEqual(len(errors), 1)
        self.assertIn("a.py", errors[0])
        self.assertIn("U+4E2D", errors[0])

    def test_untracked_emoji_fails(self):
        # Critical: spec §5.3 requires --others so local-only files are caught.
        self._write_untracked("notes.md", "todo \U0001F600\n")
        errors = validate(self.tmp)
        self.assertEqual(len(errors), 1)
        self.assertIn("notes.md", errors[0])

    def test_gitignored_file_skipped(self):
        # --exclude-standard means .gitignore is honored
        (self.tmp / ".gitignore").write_text("ignored.txt\n")
        self._write_and_stage(".gitignore", "ignored.txt\n")
        self._write_untracked("ignored.txt", "中")
        self.assertEqual(validate(self.tmp), [])

    def test_binary_files_handled_gracefully(self):
        # spec §5.3: read with errors="replace"; replacement char is a violation.
        # We test by writing actual binary (PNG header bytes) — a real binary file
        # should produce a single line-1 violation, not crash.
        (self.tmp / "x.bin").write_bytes(b"\x89PNG\r\n\x1a\n\x00\xff\xfe")
        subprocess.run(["git", "add", "x.bin"], cwd=self.tmp, check=True)
        errors = validate(self.tmp)
        # Either flagged (if invalid UTF-8 yields replacement chars) or passed
        # (if bytes happen to be valid UTF-8). In this fixture, \x89 etc.
        # produce U+FFFD replacement chars → violation expected.
        self.assertTrue(any("x.bin" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests, confirm all fail**

Run: `PYTHONPATH=. python3 -m unittest checks.tests.test_no_cjk_or_emoji -v`
Expected: errors for `ModuleNotFoundError`.

- [ ] **Step 3: Implement β**

```python
# checks/no_cjk_or_emoji.py
"""Rule 3 (β): No CJK characters or emoji in committed files.

Scans every file returned by `git ls-files --cached --others --exclude-standard`
in the target repo. The `--others` flag is critical — without it, locally
staged-but-not-committed files (or untracked-but-tracked-elsewhere files) slip
through local checks and only fail in CI. DASGPT learned this the hard way
(spec §5.3, hands-on lesson 9.2).

Uses hardcoded Unicode block ranges; Python stdlib does not expose the
Emoji_Presentation property, and `re` does not support `\\p{...}`.
"""
from __future__ import annotations
import argparse
import fnmatch
import pathlib
import subprocess
import sys
from typing import List, Tuple


# (start, end, name) — inclusive on both ends.
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
    # Decoding-error sentinel — spec §5.3 declares this a violation, so a
    # binary file committed as text (which decodes to U+FFFD with errors=replace)
    # is caught here.
    (0xFFFD, 0xFFFD, "Replacement character (non-UTF-8 input)"),
]

# Filenames or globs to skip even if they would otherwise be scanned.
ALLOWLIST_PATTERNS: List[str] = []


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
    parser = argparse.ArgumentParser(description="Scan for CJK / emoji in committed files (β).")
    parser.add_argument("repo", help="repo root to scan")
    args = parser.parse_args(argv)

    errors = validate(pathlib.Path(args.repo))
    for e in errors:
        print(e, file=sys.stderr)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests, confirm all pass**

Run: `PYTHONPATH=. python3 -m unittest checks.tests.test_no_cjk_or_emoji -v`
Expected: 14 tests, all PASS.

- [ ] **Step 5: Commit**

```bash
git add checks/no_cjk_or_emoji.py checks/tests/test_no_cjk_or_emoji.py
git commit -m "feat(checks): add β (no CJK/emoji, Rule 3)"
```

---

## Task 6: δ — `claude_md_size.py` (Rule 4)

δ counts lines in `CLAUDE.md` and fails if over `--max` (default 80).

**Files:**
- Create: `checks/claude_md_size.py`
- Create: `checks/tests/test_claude_md_size.py`

- [ ] **Step 1: Write the test file**

```python
# checks/tests/test_claude_md_size.py
from __future__ import annotations
import pathlib
import tempfile
import unittest
from checks.claude_md_size import validate, main


class TestClaudeMdSize(unittest.TestCase):

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())

    def _write_claude_md(self, lines: int) -> None:
        (self.tmp / "CLAUDE.md").write_text("\n".join(f"line {i}" for i in range(lines)) + "\n")

    def test_exact_max_passes(self):
        self._write_claude_md(80)
        self.assertEqual(validate(self.tmp, max_lines=80), [])

    def test_one_under_max_passes(self):
        self._write_claude_md(79)
        self.assertEqual(validate(self.tmp, max_lines=80), [])

    def test_one_over_max_fails(self):
        self._write_claude_md(81)
        errors = validate(self.tmp, max_lines=80)
        self.assertEqual(len(errors), 1)
        self.assertIn("81", errors[0])
        self.assertIn("80", errors[0])

    def test_missing_file_fails(self):
        errors = validate(self.tmp, max_lines=80)
        self.assertTrue(errors)
        self.assertIn("CLAUDE.md", errors[0])

    def test_custom_max(self):
        self._write_claude_md(50)
        self.assertEqual(validate(self.tmp, max_lines=100), [])
        errors = validate(self.tmp, max_lines=40)
        self.assertTrue(errors)

    def test_main_returns_zero_when_under(self):
        self._write_claude_md(10)
        self.assertEqual(main([str(self.tmp), "--max", "80"]), 0)

    def test_main_returns_nonzero_when_over(self):
        self._write_claude_md(200)
        self.assertNotEqual(main([str(self.tmp), "--max", "80"]), 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests, confirm all fail (ModuleNotFoundError)**

Run: `PYTHONPATH=. python3 -m unittest checks.tests.test_claude_md_size -v`

- [ ] **Step 3: Implement δ**

```python
# checks/claude_md_size.py
"""Rule 4 (δ): CLAUDE.md is at most N lines (default 80).

Counts physical newlines. Trailing newline-only line is not counted as content
(a file ending in \\n has the same count whether or not the final line has text).
"""
from __future__ import annotations
import argparse
import pathlib
import sys
from typing import List


def validate(repo_root: pathlib.Path, max_lines: int) -> List[str]:
    claude_md = repo_root / "CLAUDE.md"
    if not claude_md.exists():
        return [f"CLAUDE.md not found at {claude_md}"]

    text = claude_md.read_text(encoding="utf-8")
    # Count non-empty trailing newlines as content boundaries: a file with N
    # lines ending in \n produces N "line N\n" entries when split by \n,
    # plus one empty string at the end. We discount that empty trailer.
    parts = text.split("\n")
    line_count = len(parts) - 1 if parts and parts[-1] == "" else len(parts)

    if line_count > max_lines:
        return [
            f"CLAUDE.md has {line_count} lines, exceeds maximum of {max_lines}. "
            f"Move detail to docs/ai/ and keep CLAUDE.md as a navigation entry."
        ]
    return []


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify CLAUDE.md line count (δ).")
    parser.add_argument("repo")
    parser.add_argument("--max", type=int, default=80)
    args = parser.parse_args(argv)

    errors = validate(pathlib.Path(args.repo), max_lines=args.max)
    for e in errors:
        print(e, file=sys.stderr)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests, confirm all pass**

Run: `PYTHONPATH=. python3 -m unittest checks.tests.test_claude_md_size -v`
Expected: 7 tests, all PASS.

- [ ] **Step 5: Commit**

```bash
git add checks/claude_md_size.py checks/tests/test_claude_md_size.py
git commit -m "feat(checks): add δ (CLAUDE.md size check, Rule 4)"
```

---

## Task 7: ε — `skills_registry.py` (Rule 5)

ε's day-0 implementation is narrow per spec §5.5: verify `docs/ai/skills.md` exists, is non-empty, and contains both required headers. The future ratchet (diffing against actual `.claude/settings.json`) is deferred.

**Files:**
- Create: `checks/skills_registry.py`
- Create: `checks/tests/test_skills_registry.py`

- [ ] **Step 1: Write the test file**

```python
# checks/tests/test_skills_registry.py
from __future__ import annotations
import pathlib
import tempfile
import unittest
from checks.skills_registry import validate, main


class TestSkillsRegistry(unittest.TestCase):

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / "docs" / "ai").mkdir(parents=True)

    def _write(self, content: str) -> None:
        (self.tmp / "docs" / "ai" / "skills.md").write_text(content)

    def test_valid_passes(self):
        self._write("# Skills and MCP\n\n## Skills\n\n(none yet)\n\n## MCP Servers\n\n(none yet)\n")
        self.assertEqual(validate(self.tmp), [])

    def test_missing_file_fails(self):
        errors = validate(self.tmp)
        self.assertTrue(errors)
        self.assertIn("docs/ai/skills.md", errors[0])

    def test_empty_file_fails(self):
        self._write("")
        errors = validate(self.tmp)
        self.assertTrue(errors)
        self.assertIn("empty", errors[0].lower())

    def test_missing_skills_header_fails(self):
        self._write("# Skills and MCP\n\n## MCP Servers\n\nstuff\n")
        errors = validate(self.tmp)
        self.assertTrue(any("## Skills" in e for e in errors))

    def test_missing_mcp_servers_header_fails(self):
        self._write("# Skills and MCP\n\n## Skills\n\nstuff\n")
        errors = validate(self.tmp)
        self.assertTrue(any("## MCP Servers" in e for e in errors))

    def test_both_missing_reports_both(self):
        self._write("# Skills and MCP\n\nbut no headers\n")
        errors = validate(self.tmp)
        self.assertEqual(len(errors), 2)

    def test_main_returns_zero_on_pass(self):
        self._write("## Skills\n\n## MCP Servers\n")
        self.assertEqual(main([str(self.tmp)]), 0)

    def test_main_returns_nonzero_on_fail(self):
        self.assertNotEqual(main([str(self.tmp)]), 0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests, confirm all fail**

Run: `PYTHONPATH=. python3 -m unittest checks.tests.test_skills_registry -v`

- [ ] **Step 3: Implement ε**

```python
# checks/skills_registry.py
"""Rule 5 (ε): Skills and MCP servers are registered in docs/ai/skills.md.

Day-0 narrow implementation per spec §5.5: verify the registry file exists,
is non-empty, and has the two required top-level section headers.

Future ratchet: when target repos introduce repo-level MCP/skill config
(e.g., .claude/settings.json with mcpServers), diff the configured set
against this registry.
"""
from __future__ import annotations
import argparse
import pathlib
import re
import sys
from typing import List


REQUIRED_HEADERS = ["## Skills", "## MCP Servers"]


def validate(repo_root: pathlib.Path) -> List[str]:
    skills_md = repo_root / "docs" / "ai" / "skills.md"
    if not skills_md.exists():
        return [f"docs/ai/skills.md not found at {skills_md}"]

    text = skills_md.read_text(encoding="utf-8")
    if not text.strip():
        return [f"docs/ai/skills.md is empty"]

    errors: List[str] = []
    for header in REQUIRED_HEADERS:
        pattern = re.compile(r"^" + re.escape(header) + r"\s*$", re.MULTILINE)
        if not pattern.search(text):
            errors.append(
                f"docs/ai/skills.md is missing required header `{header}`"
            )
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Validate skills/MCP registry (ε).")
    parser.add_argument("repo")
    args = parser.parse_args(argv)

    errors = validate(pathlib.Path(args.repo))
    for e in errors:
        print(e, file=sys.stderr)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests, confirm all pass**

Run: `PYTHONPATH=. python3 -m unittest checks.tests.test_skills_registry -v`
Expected: 8 tests, all PASS.

- [ ] **Step 5: Commit**

```bash
git add checks/skills_registry.py checks/tests/test_skills_registry.py
git commit -m "feat(checks): add ε (skills/MCP registry, Rule 5)"
```

---

## Task 8: ζ — `pr_has_reference.py` (Rule 6)

ζ reads PR metadata from environment variables (`PR_BODY`, `PR_BRANCH`) populated by the CI workflow. Bot PRs (`chore/sync-ai-docs-*`) are exempted. ζ is the only check that takes no path argument.

**Files:**
- Create: `checks/pr_has_reference.py`
- Create: `checks/tests/test_pr_has_reference.py`

- [ ] **Step 1: Write the test file**

```python
# checks/tests/test_pr_has_reference.py
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
        # E.g., on push event the workflow gates ζ off via `if:`.
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
```

- [ ] **Step 2: Run tests, confirm all fail**

Run: `PYTHONPATH=. python3 -m unittest checks.tests.test_pr_has_reference -v`

- [ ] **Step 3: Implement ζ**

```python
# checks/pr_has_reference.py
"""Rule 6 (ζ): PR description references an issue, spec, or URL.

Reads PR metadata from environment variables populated by the CI workflow:
- PR_BODY:   the pull request body text
- PR_BRANCH: the pull request head branch name (used for bot exemption)

Bot PRs (head branch matching `chore/sync-ai-docs-*`) are exempted; the sync
workflow always includes a source-commit link in its bodies anyway.

When run outside a PR context (e.g., push event), no env vars are set and the
check exits 0 — but the CI workflow already gates ζ on `pull_request` events.
"""
from __future__ import annotations
import argparse
import fnmatch
import os
import re
import sys
from typing import List


_HASH_INT = re.compile(r"#\d+")
_URL = re.compile(r"https?://\S+")
_KEYWORD = re.compile(r"\b(?:spec|design|adr|rfc):\s*\S+", re.IGNORECASE)


BOT_BRANCH_PATTERNS = ["chore/sync-ai-docs-*"]


def body_passes(body: str) -> bool:
    if _HASH_INT.search(body):
        return True
    if _URL.search(body):
        return True
    if _KEYWORD.search(body):
        return True
    return False


def _is_bot_branch(branch: str) -> bool:
    return any(fnmatch.fnmatchcase(branch, pat) for pat in BOT_BRANCH_PATTERNS)


def validate() -> List[str]:
    body = os.environ.get("PR_BODY")
    branch = os.environ.get("PR_BRANCH", "")

    if body is None:
        # No PR context; nothing to validate.
        return []

    if _is_bot_branch(branch):
        return []

    if not body_passes(body):
        return [
            "PR body must reference at least one of: "
            "`#<issue>`, a URL, or `spec:`/`design:`/`adr:`/`rfc:` followed by a token."
        ]
    return []


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify PR has issue/spec reference (ζ).")
    parser.parse_args(argv)
    errors = validate()
    for e in errors:
        print(e, file=sys.stderr)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests, confirm all pass**

Run: `PYTHONPATH=. python3 -m unittest checks.tests.test_pr_has_reference -v`
Expected: 17 tests, all PASS.

- [ ] **Step 5: Commit**

```bash
git add checks/pr_has_reference.py checks/tests/test_pr_has_reference.py
git commit -m "feat(checks): add ζ (PR reference check, Rule 6)"
```

---

## Task 9: η — `protected_paths.py` (Rule 7)

η fails the PR when changed files intersect with the protected list UNLESS the PR head branch matches the sync-bot pattern. Reads `BASE_SHA`, `HEAD_SHA`, `PR_BRANCH` from environment. Soft-enforcement only per spec §5.7.

**Files:**
- Create: `checks/protected_paths.py`
- Create: `checks/tests/test_protected_paths.py`

- [ ] **Step 1: Write the test file**

```python
# checks/tests/test_protected_paths.py
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

    def test_mixed_changes_returns_only_protected(self):
        changes = ["src/x.ts", "CLAUDE.md", "README.md", "docs/ai/skills.md"]
        self.assertEqual(set(paths_intersecting(changes)), {"CLAUDE.md", "docs/ai/skills.md"})


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
        # CI workflow gates η on `pull_request`; script should be tolerant if called otherwise.
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(validate(self.tmp), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests, confirm all fail**

Run: `PYTHONPATH=. python3 -m unittest checks.tests.test_protected_paths -v`

- [ ] **Step 3: Implement η**

```python
# checks/protected_paths.py
"""Rule 7 (η): Protected paths cannot be modified outside the sync flow.

Reads PR diff from environment (BASE_SHA, HEAD_SHA, PR_BRANCH) and fails the
check if changed files intersect with the PROTECTED_GLOBS list — unless the
PR head branch is a sync-bot branch (`chore/sync-ai-docs-*`).

This is **soft enforcement** per spec §5.7: branch names are spoofable. True
enforcement requires CODEOWNERS + branch protection (sub-project F).
"""
from __future__ import annotations
import argparse
import fnmatch
import os
import pathlib
import subprocess
import sys
from typing import List


PROTECTED_GLOBS: List[str] = [
    "CLAUDE.md",
    "CONTRIBUTING.md",
    "docs/ai/*",
    "docs/ai/**",
    ".github/workflows/checks.yml",
]


BOT_BRANCH_PATTERNS = ["chore/sync-ai-docs-*"]


def paths_intersecting(changed: List[str]) -> List[str]:
    """Return the subset of changed paths that match any PROTECTED_GLOBS entry."""
    hits = []
    for path in changed:
        for glob in PROTECTED_GLOBS:
            # fnmatch.fnmatchcase doesn't support ** natively; emulate by
            # checking both direct match and prefix match for ** patterns.
            if glob.endswith("/**"):
                prefix = glob[:-3]
                if path == prefix or path.startswith(prefix + "/"):
                    hits.append(path)
                    break
            elif fnmatch.fnmatchcase(path, glob):
                hits.append(path)
                break
    return hits


def _is_bot_branch(branch: str) -> bool:
    return any(fnmatch.fnmatchcase(branch, pat) for pat in BOT_BRANCH_PATTERNS)


def _git_diff_names(repo: pathlib.Path, base: str, head: str) -> List[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", base, head],
        cwd=repo, capture_output=True, text=True, check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def validate(repo_root: pathlib.Path) -> List[str]:
    base = os.environ.get("BASE_SHA")
    head = os.environ.get("HEAD_SHA")
    branch = os.environ.get("PR_BRANCH", "")

    if not base or not head:
        # Not invoked in a PR context — nothing to do. CI gates this on `pull_request`.
        return []

    changed = _git_diff_names(repo_root, base, head)
    hits = paths_intersecting(changed)
    if not hits:
        return []
    if _is_bot_branch(branch):
        return []

    return [
        f"Protected paths cannot be modified outside the sync flow: "
        f"{', '.join(hits)}. Edit these in MiraNote-AI/.github instead; "
        f"the sync workflow will propagate the change."
    ]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify protected paths (η).")
    parser.add_argument("repo")
    args = parser.parse_args(argv)
    errors = validate(pathlib.Path(args.repo))
    for e in errors:
        print(e, file=sys.stderr)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests, confirm all pass**

Run: `PYTHONPATH=. python3 -m unittest checks.tests.test_protected_paths -v`
Expected: 13 tests, all PASS.

- [ ] **Step 5: Commit**

```bash
git add checks/protected_paths.py checks/tests/test_protected_paths.py
git commit -m "feat(checks): add η (protected paths, Rule 7)"
```

---

## Task 10: Create `CONTRIBUTING.md` with all 7 rules registered

This is the content file that ties the framework to its rules. After this task, γ and α should pass when run against the local `.github` repo.

**Files:**
- Create: `CONTRIBUTING.md`

- [ ] **Step 1: Write `CONTRIBUTING.md`**

```markdown
# Contributing to MiraNote

MiraNote ships as five repos under `MiraNote-AI`. This file is the **single
source of truth** for engineering rules across all five. It lives in
`MiraNote-AI/.github` and is synced to each code repo via the
`sync-ai-docs.yml` workflow.

## How to propose a change

1. Branch from `main` in `MiraNote-AI/.github`.
2. Edit `CLAUDE.md`, `CONTRIBUTING.md`, or files under `docs/ai/`.
3. If you add a rule, follow the procedure below.
4. Open a PR; the self-check workflow must pass before merge.

## How to add a rule

Every rule in this document must have a corresponding check script. To add
a new rule:

1. Write a check script at `checks/<name>.py` following the existing
   patterns (validator function + thin CLI wrapper).
2. Add a `### Rule N: <title>` section below, with the required
   `**Rationale:**` and `**Enforced by:**` lines.
3. Locally run:
   ```bash
   PYTHONPATH=. python3 -m checks.contributing_format . --mode source
   PYTHONPATH=. python3 -m checks._meta.all_rules_have_checks .
   ```
4. PR into `MiraNote-AI/.github`.

Rule IDs are stable: do not renumber on deletion. Gaps are allowed.

## Rules

### Rule 1: Every rule has an enforcement mechanism

Every rule documented here must be paired with at least one executable check
script in `checks/`. Rules without programmatic enforcement do not belong in
this file; if a constraint cannot be checked, do not document it as a rule.

The α check also detects **orphan** check scripts — every `.py` file at the
direct top level of `checks/` (excluding `__init__.py`) must be referenced
by at least one rule's `Enforced by:` line.

**Rationale:** Without paired checks, rules degrade to wall-art over time.
**Enforced by:** `checks/_meta/all_rules_have_checks.py`

### Rule 2: CONTRIBUTING.md follows the canonical structure

This file must match the structure that the γ check parses: a `## Rules`
section, with each rule starting `### Rule N: <title>` (unique integers,
gaps allowed) and containing exactly one `**Rationale:**` line and one
`**Enforced by:**` line. Path tokens on the `Enforced by:` line are
comma-separated; surrounding backticks and whitespace are stripped.

In `mode=source` (running inside `MiraNote-AI/.github`), every path on
every `Enforced by:` line must resolve to an existing file. In
`mode=target` (running inside a code repo), path resolution is skipped
because the check scripts live only in the source repo.

**Rationale:** α and downstream automation depend on this file being
mechanically parseable; structural drift here would silently break the
entire framework.
**Enforced by:** `checks/contributing_format.py`

### Rule 3: No CJK characters or emoji in committed files

Source files, docs, and any other text committed to the repo must not
contain Chinese, Japanese, Korean, fullwidth-form, or emoji characters
within the Unicode ranges scanned by β. Text-presentation symbols (✓, →,
box-drawing) are allowed because they have legitimate use in tables and
diagrams.

The β check scans the file set returned by
`git ls-files --cached --others --exclude-standard` — including
locally-staged-but-untracked files, so local results match CI.

**Rationale:** A multilingual team can easily leak input-method residue
into committed source. DASGPT was bitten by this in production.
**Enforced by:** `checks/no_cjk_or_emoji.py`

### Rule 4: CLAUDE.md is at most 80 lines

The `CLAUDE.md` at the root of each repo is consumed by every Claude Code
session as part of its context. It must stay short — it is an entry point
and navigation aid, not the place for detailed rules. Detail belongs in
`docs/ai/` and in this `CONTRIBUTING.md`.

**Rationale:** Context budget is a finite resource; entry-point files that
grow unchecked degrade every downstream task.
**Enforced by:** `checks/claude_md_size.py`

### Rule 5: Skills and MCP servers are registered in `docs/ai/skills.md`

Any Claude Code skill, MCP server, or external tool integration adopted by
the team must be declared in `docs/ai/skills.md` under the `## Skills` or
`## MCP Servers` section. The day-0 check verifies only that the file
exists with both required headers; future iterations will diff this
registry against actual configuration.

**Rationale:** The "50 MCP servers running" anti-pattern destroys tool
discovery; a deliberate registry forces every adoption to be a conscious
decision.
**Enforced by:** `checks/skills_registry.py`

### Rule 6: PR descriptions reference an issue, spec, or URL

Every pull request body must contain at least one of:
- `#<integer>` referencing an issue or PR,
- a URL (`http://` or `https://`),
- one of `spec:`, `design:`, `adr:`, `rfc:` followed by a token.

PRs from the sync bot (branch matching `chore/sync-ai-docs-*`) are exempt.

**Rationale:** A PR without a reference is opaque to future readers; the
"why" must be discoverable from the PR itself.
**Enforced by:** `checks/pr_has_reference.py`

### Rule 7: Synced files cannot be modified inside a target repo

The files synced from `MiraNote-AI/.github` to each code repo
(`CLAUDE.md`, `CONTRIBUTING.md`, `docs/ai/**`,
`.github/workflows/checks.yml`) must be edited only at the source. Direct
edits to these paths inside a target repo will cause the η check to fail.

The bot's own sync PRs (branch matching `chore/sync-ai-docs-*`) are
exempt — those are the legitimate update path.

This is soft enforcement: branch names are spoofable. Hard enforcement
requires branch protection rules and CODEOWNERS, which are tracked
separately under sub-project F.

**Rationale:** Without this check, accidental local edits to synced files
silently diverge from the canonical source until the next sync round-trip,
producing confusion and lost edits.
**Enforced by:** `checks/protected_paths.py`
```

- [ ] **Step 2: Run γ against the local repo, confirm it passes in source mode**

Run: `PYTHONPATH=. python3 -m checks.contributing_format . --mode source`
Expected: exit 0, no output.

- [ ] **Step 3: Run α against the local repo, confirm it passes**

Run: `PYTHONPATH=. python3 -m checks._meta.all_rules_have_checks .`
Expected: exit 0, no output.

- [ ] **Step 4: Commit**

```bash
git add CONTRIBUTING.md
git commit -m "docs: add CONTRIBUTING.md with 7 rules registered"
```

---

## Task 11: Create `docs/ai/skills.md`

**Files:**
- Create: `docs/ai/skills.md`

- [ ] **Step 1: Write the registry skeleton**

```markdown
# Skills and MCP Servers

This file is the canonical registry of Claude Code skills and MCP servers
adopted across MiraNote-AI repos. Entries here are required by Rule 5 (ε)
in [CONTRIBUTING.md](../../CONTRIBUTING.md).

To add a skill or MCP server:

1. Add an entry to the relevant section below with a short description and
   a link to its configuration / source.
2. If the skill/MCP is configured at the repo level (e.g., in
   `.claude/settings.json`), reference that configuration here.
3. PR into `MiraNote-AI/.github`.

## Skills

_None yet. Day-0 baseline._

## MCP Servers

_None yet. Day-0 baseline._
```

- [ ] **Step 2: Run ε against the local repo, confirm it passes**

Run: `PYTHONPATH=. python3 -m checks.skills_registry .`
Expected: exit 0, no output.

- [ ] **Step 3: Commit**

```bash
git add docs/ai/skills.md
git commit -m "docs: add day-0 skills/MCP registry (required by ε)"
```

---

## Task 12: Rewrite `CLAUDE.md` as a real day-0 entry point

The current `CLAUDE.md` is an 11-line placeholder. Replace it with a real entry that satisfies δ (≤ 80 lines) and serves as the navigation hub for the AI rule system.

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Replace the file contents**

Overwrite `CLAUDE.md` with the following:

```markdown
# MiraNote — Rules for Claude Code

This file is the canonical entry point for AI coding assistants working in
any `MiraNote-AI/*` repo. Edit this file only in `MiraNote-AI/.github`;
the `sync-ai-docs.yml` workflow propagates changes to every code repo.

## Required reading order

1. [CONTRIBUTING.md](CONTRIBUTING.md) — the full rule set with rationale
   and enforcement. Every line in this file is enforced by a check script
   in `checks/`.
2. [docs/ai/README.md](docs/ai/README.md) — navigation for engineering
   docs (architecture, workflows, playbooks, ADRs as they're added).
3. [docs/ai/skills.md](docs/ai/skills.md) — registry of skills and MCP
   servers adopted across MiraNote-AI.

## The seven day-0 rules (summarised)

1. **Meta-rule (α)** — every rule has a check.
2. **CONTRIBUTING.md format (γ)** — registry structure is mechanically
   parseable.
3. **No CJK/emoji (β)** — committed text stays in ASCII-compatible
   ranges. Text-presentation symbols (✓, →) are OK.
4. **CLAUDE.md ≤ 80 lines (δ)** — entry point stays tight.
5. **Skills/MCP registry (ε)** — every adopted skill/MCP listed in
   `docs/ai/skills.md`.
6. **PR has reference (ζ)** — every PR body references an issue, URL,
   spec, design, ADR, or RFC.
7. **Protected paths (η)** — synced files (this file,
   `CONTRIBUTING.md`, `docs/ai/`, `.github/workflows/checks.yml`) are
   edited only in `MiraNote-AI/.github`.

Full text and enforcement details are in [CONTRIBUTING.md](CONTRIBUTING.md).

## Quick local commands

```bash
PYTHONPATH=. python3 -m checks.contributing_format . --mode source
PYTHONPATH=. python3 -m checks._meta.all_rules_have_checks .
PYTHONPATH=. python3 -m checks.no_cjk_or_emoji .
PYTHONPATH=. python3 -m checks.claude_md_size . --max 80
PYTHONPATH=. python3 -m checks.skills_registry .
PYTHONPATH=. python3 -m unittest discover checks/tests -v
```

## How to add a rule

See the procedure in [CONTRIBUTING.md](CONTRIBUTING.md). Briefly:
write the check, register the rule, run the two meta-validators locally,
PR.

## Out of scope (deferred)

- Branch protection / CODEOWNERS — sub-project F.
- Per-stack harness (web/api/ios linters, tests, settings.json hooks) —
  sub-project D.
- Shared org-level skills and memory — sub-project E.
- Local pre-commit hooks — nice-to-have, post-day-0.
```

- [ ] **Step 2: Run δ against the local repo, confirm CLAUDE.md is ≤ 80 lines**

Run: `PYTHONPATH=. python3 -m checks.claude_md_size . --max 80`
Expected: exit 0, no output. If it fails, trim the file until it passes.

- [ ] **Step 3: Run γ to confirm CONTRIBUTING.md still passes after CLAUDE.md changes**

Run: `PYTHONPATH=. python3 -m checks.contributing_format . --mode source`
Expected: exit 0.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: rewrite CLAUDE.md as real day-0 entry (replaces placeholder)"
```

---

## Task 13: Refresh `docs/ai/README.md` as the docs navigation hub

**Files:**
- Modify: `docs/ai/README.md`

- [ ] **Step 1: Replace the file contents**

Overwrite `docs/ai/README.md` with:

```markdown
# MiraNote AI Engineering Docs

Canonical engineering rules and supporting docs for AI-assisted development
across MiraNote-AI repos. Source of truth: `MiraNote-AI/.github`.

## Layout

| File | Purpose |
|---|---|
| [`../../CLAUDE.md`](../../CLAUDE.md) | Entry point for Claude Code in every repo. |
| [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md) | The 7 enforced rules with rationale. |
| [`skills.md`](skills.md) | Registry of adopted Claude skills and MCP servers (ε). |
| [`../superpowers/specs/`](../superpowers/) | Design specs for harness sub-projects. |
| [`../superpowers/plans/`](../superpowers/) | Implementation plans for harness sub-projects. |

## Future docs (added when needed, per Ratchet)

- `architecture.md` — when MiraNote's 5-repo topology stabilises.
- `workflow.md` — branching, commit, and PR conventions beyond Rule 6.
- `playbooks/` — recipes for common AI-driven tasks.
- `decisions/` — ADRs.

These do not exist yet. Add them only when a real need (or failure)
demands them — keeping with the Ratchet principle.
```

- [ ] **Step 2: Re-run δ and ε to confirm nothing breaks**

Run: `PYTHONPATH=. python3 -m checks.claude_md_size . --max 80 && PYTHONPATH=. python3 -m checks.skills_registry .`
Expected: both pass.

- [ ] **Step 3: Commit**

```bash
git add docs/ai/README.md
git commit -m "docs: refresh docs/ai/README.md as engineering-docs index"
```

---

## Task 14: Reusable CI workflow `.github/workflows/checks.yml`

**Files:**
- Create: `.github/workflows/checks.yml`

- [ ] **Step 1: Write the workflow**

```yaml
# .github/workflows/checks.yml — reusable: called by self-check.yml in this
# repo and by target stub workflows in the 4 code repos.
#
# In source mode, `tools` is symlinked to `code` so the PR's own check scripts
# validate the PR (not the older copy from main). In target mode, `tools` is
# checked out from `MiraNote-AI/.github@main`.

name: Checks

on:
  workflow_call:
    inputs:
      mode:
        type: string
        default: target  # 'source' for .github self-check

jobs:
  checks:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code under test
        uses: actions/checkout@v4
        with:
          path: code
          fetch-depth: 0  # β needs git ls-files; η needs PR diff range

      - name: Symlink tools = code (source mode)
        if: ${{ inputs.mode == 'source' }}
        run: ln -s "$GITHUB_WORKSPACE/code" "$GITHUB_WORKSPACE/tools"

      - name: Checkout tools from .github main (target mode)
        if: ${{ inputs.mode == 'target' }}
        uses: actions/checkout@v4
        with:
          repository: MiraNote-AI/.github
          ref: main
          path: tools

      - name: Setup Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: γ — CONTRIBUTING.md format
        if: ${{ !cancelled() }}
        working-directory: tools
        run: python -m checks.contributing_format "$GITHUB_WORKSPACE/code" --mode ${{ inputs.mode }}

      - name: α — Meta-rule
        if: ${{ !cancelled() && inputs.mode == 'source' }}
        working-directory: tools
        run: python -m checks._meta.all_rules_have_checks "$GITHUB_WORKSPACE/code"

      - name: β — No CJK / emoji
        if: ${{ !cancelled() }}
        working-directory: tools
        run: python -m checks.no_cjk_or_emoji "$GITHUB_WORKSPACE/code"

      - name: δ — CLAUDE.md size
        if: ${{ !cancelled() }}
        working-directory: tools
        run: python -m checks.claude_md_size "$GITHUB_WORKSPACE/code" --max 80

      - name: ε — Skills / MCP registry
        if: ${{ !cancelled() }}
        working-directory: tools
        run: python -m checks.skills_registry "$GITHUB_WORKSPACE/code"

      - name: ζ — PR has reference
        if: ${{ !cancelled() && github.event_name == 'pull_request' }}
        working-directory: tools
        env:
          PR_BODY: ${{ github.event.pull_request.body }}
          PR_BRANCH: ${{ github.event.pull_request.head.ref }}
        run: python -m checks.pr_has_reference

      - name: η — Protected paths
        if: ${{ !cancelled() && inputs.mode == 'target' && github.event_name == 'pull_request' }}
        working-directory: tools
        env:
          PR_BRANCH: ${{ github.event.pull_request.head.ref }}
          BASE_SHA: ${{ github.event.pull_request.base.sha }}
          HEAD_SHA: ${{ github.event.pull_request.head.sha }}
        run: python -m checks.protected_paths "$GITHUB_WORKSPACE/code"
```

- [ ] **Step 2: Validate YAML syntax locally**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/checks.yml'))" 2>&1 || echo "Note: yaml module may need 'pip install pyyaml' but the YAML is also valid by inspection"`

If pyyaml isn't installed, you can skip — the syntax will be re-validated by GitHub Actions at Phase 4. The structure has been hand-verified against the spec §6.1.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/checks.yml
git commit -m "ci: add reusable checks workflow (used by self-check + 4 targets)"
```

---

## Task 15: Self-check workflow `.github/workflows/self-check.yml`

**Files:**
- Create: `.github/workflows/self-check.yml`

- [ ] **Step 1: Write the workflow**

```yaml
# .github/workflows/self-check.yml — runs the reusable checks workflow
# against this repo (.github) in source mode on every PR and on every push
# to main that touches the rule-relevant paths.

name: Self-check

on:
  pull_request:
  push:
    branches: [main]
    paths:
      - 'CLAUDE.md'
      - 'CONTRIBUTING.md'
      - 'docs/ai/**'
      - 'checks/**'
      - 'templates/**'
      - '.github/workflows/checks.yml'
      - '.github/workflows/self-check.yml'

jobs:
  checks:
    uses: ./.github/workflows/checks.yml
    with:
      mode: source
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/self-check.yml
git commit -m "ci: add self-check workflow for .github repo (mode=source)"
```

---

## Task 16: Target stub template `templates/target-workflow.yml`

**Files:**
- Create: `templates/target-workflow.yml`

- [ ] **Step 1: Write the template**

```yaml
# templates/target-workflow.yml — synced verbatim into each target repo as
# `.github/workflows/checks.yml`. Targets call the reusable workflow in
# MiraNote-AI/.github@main; their entire CI gate is these 6 lines.

name: Checks

on:
  pull_request:
  push:
    branches: [main]

jobs:
  checks:
    uses: MiraNote-AI/.github/.github/workflows/checks.yml@main
    with:
      mode: target
```

- [ ] **Step 2: Commit**

```bash
git add templates/target-workflow.yml
git commit -m "ci: add target stub template for code repos"
```

---

## Task 17: Expand `sync-ai-docs.yml` to cover new synced assets

Current sync workflow only handles `CLAUDE.md` and `docs/ai/`. We need to also sync `CONTRIBUTING.md` and the rendered target stub (placed at `.github/workflows/checks.yml` in each target).

**Files:**
- Modify: `.github/workflows/sync-ai-docs.yml`

- [ ] **Step 1: Read the current workflow to understand the mirror step**

Run: `cat .github/workflows/sync-ai-docs.yml`

The current "Mirror" step copies `CLAUDE.md` and rsyncs `docs/ai/`. We extend it to also handle `CONTRIBUTING.md` and the template render.

- [ ] **Step 2: Update the mirror step**

Replace the existing `Mirror CLAUDE.md and docs/ai/` step with this extended version (find the step by its `name:` line and replace its `run:` block):

```yaml
      - name: Mirror docs and target stub
        run: |
          set -euo pipefail
          cp source/CLAUDE.md target/CLAUDE.md
          cp source/CONTRIBUTING.md target/CONTRIBUTING.md
          mkdir -p target/docs/ai
          rsync -a --delete source/docs/ai/ target/docs/ai/
          mkdir -p target/.github/workflows
          cp source/templates/target-workflow.yml target/.github/workflows/checks.yml
```

The path-trigger filter at the top of the workflow should also be updated so changes to `CONTRIBUTING.md` or `templates/` trigger a sync. Find the `paths:` block under the `push:` trigger and update it to:

```yaml
    paths:
      - 'CLAUDE.md'
      - 'CONTRIBUTING.md'
      - 'docs/ai/**'
      - 'templates/**'
```

- [ ] **Step 3: Validate YAML syntax**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/sync-ai-docs.yml'))" 2>&1 || echo "yaml module unavailable; verify by inspection"`

Check by eye that the modified `paths:` block sits under `push:` and that the new step replaces the old `Mirror CLAUDE.md and docs/ai/` step entirely.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/sync-ai-docs.yml
git commit -m "ci(sync): expand mirror scope to CONTRIBUTING.md and target stub"
```

---

## Task 18: Expand `bin/sync-ai-docs.sh` to match

Keep the local script in lockstep with the workflow so manual bootstrap/emergency runs mirror the same files.

**Files:**
- Modify: `bin/sync-ai-docs.sh`

- [ ] **Step 1: Read the current script**

Run: `cat bin/sync-ai-docs.sh`

Find the `mirror_files()` function — it currently copies `CLAUDE.md` and rsyncs `docs/ai/`.

- [ ] **Step 2: Update `mirror_files()`**

Replace the body of `mirror_files()` with:

```bash
mirror_files() {
  local target="$1"
  cp "$SOURCE_DIR/CLAUDE.md" "$target/CLAUDE.md"
  cp "$SOURCE_DIR/CONTRIBUTING.md" "$target/CONTRIBUTING.md"
  mkdir -p "$target/docs/ai"
  rsync -a --delete "$SOURCE_DIR/docs/ai/" "$target/docs/ai/"
  mkdir -p "$target/.github/workflows"
  cp "$SOURCE_DIR/templates/target-workflow.yml" "$target/.github/workflows/checks.yml"
}
```

- [ ] **Step 3: Sanity-check the script syntax**

Run: `bash -n bin/sync-ai-docs.sh && echo "syntax ok"`
Expected: prints `syntax ok`.

- [ ] **Step 4: Commit**

```bash
git add bin/sync-ai-docs.sh
git commit -m "chore(sync): expand local mirror scope to CONTRIBUTING.md and target stub"
```

---

## Task 19: Final local self-check pass (spec §7 Phase 1)

Run every check against the local `.github` repo as a final integration test. Anything that fails here would have failed in CI; fix locally before push.

**Files:** none modified in steady state; this task is verification.

- [ ] **Step 1: Run all checks and the full test suite**

```bash
PYTHONPATH=. python3 -m checks.contributing_format . --mode source
PYTHONPATH=. python3 -m checks._meta.all_rules_have_checks .
PYTHONPATH=. python3 -m checks.no_cjk_or_emoji .
PYTHONPATH=. python3 -m checks.claude_md_size . --max 80
PYTHONPATH=. python3 -m checks.skills_registry .
PYTHONPATH=. python3 -m unittest discover checks/tests -v
```

Expected: every command exits 0. The unittest discover step should run ~70 tests across 8 test files, all passing.

- [ ] **Step 2: If any check fails**

Read the error message — every check is designed to print exact file:line:reason. Common cases and remedies:

| Failure | Likely cause | Fix |
|---|---|---|
| `β: ... forbidden character U+....` | Stray CJK or emoji in a doc | Replace the character with ASCII equivalent |
| `δ: CLAUDE.md has N lines, exceeds 80` | Edits pushed CLAUDE.md over the limit | Move content to `docs/ai/` or trim |
| `γ: CONTRIBUTING.md:LINE: Rule N: path ... does not exist` | New rule registered but check script missing | Add the script or remove the rule |
| `α: Orphan check: checks/X.py is not referenced` | Check exists but no rule mentions it | Register a rule for it in CONTRIBUTING.md |
| `ε: ... missing required header` | `docs/ai/skills.md` lost a header | Restore `## Skills` and `## MCP Servers` headers |

Fix the underlying issue, then re-run Step 1.

- [ ] **Step 3: No commit needed (verification only)**

If you made fixes in Step 2, commit them individually with appropriate scoped messages (`fix(checks): ...`, `docs: ...`, etc.). Do not commit anything that wasn't a real fix.

---

## Task 20: Summary status check

**Files:** none modified.

- [ ] **Step 1: Print git log and verify everything landed**

Run: `git log --oneline | head -30`

Expected to see (newest first, exact messages may vary slightly):

```
chore(sync): expand local mirror scope to CONTRIBUTING.md and target stub
ci(sync): expand mirror scope to CONTRIBUTING.md and target stub
ci: add target stub template for code repos
ci: add self-check workflow for .github repo (mode=source)
ci: add reusable checks workflow (used by self-check + 4 targets)
docs: refresh docs/ai/README.md as engineering-docs index
docs: rewrite CLAUDE.md as real day-0 entry (replaces placeholder)
docs: add day-0 skills/MCP registry (required by ε)
docs: add CONTRIBUTING.md with 7 rules registered
feat(checks): add η (protected paths, Rule 7)
feat(checks): add ζ (PR reference check, Rule 6)
feat(checks): add ε (skills/MCP registry, Rule 5)
feat(checks): add δ (CLAUDE.md size check, Rule 4)
feat(checks): add β (no CJK/emoji, Rule 3)
feat(checks): add α (meta-rule, all rules have checks, Rule 1)
feat(checks): add γ (CONTRIBUTING.md format check, Rule 2)
feat(checks): add shared CONTRIBUTING.md parser library
chore: scaffold checks/ package skeleton
docs(spec): fix 2 design bugs + 2 refinements
docs: add harness engineering day-0 design spec
chore: bootstrap CLAUDE.md sync infrastructure
```

- [ ] **Step 2: Verify directory tree matches the file-structure section**

Run: `find . -type f -not -path './.git/*' | sort`

Expected output (in some order matching §"File structure" above): CLAUDE.md, CONTRIBUTING.md, bin/sync-ai-docs.sh, docs/ai/README.md, docs/ai/skills.md, docs/superpowers/specs/2026-05-19-harness-engineering-day0-design.md, docs/superpowers/plans/2026-05-19-harness-engineering-day0.md, .github/workflows/checks.yml, .github/workflows/self-check.yml, .github/workflows/sync-ai-docs.yml, templates/target-workflow.yml, checks/__init__.py, checks/_meta/__init__.py, checks/_meta/parser.py, checks/_meta/all_rules_have_checks.py, checks/contributing_format.py, checks/no_cjk_or_emoji.py, checks/claude_md_size.py, checks/skills_registry.py, checks/pr_has_reference.py, checks/protected_paths.py, checks/tests/__init__.py, checks/tests/test_parser.py, checks/tests/test_contributing_format.py, checks/tests/test_all_rules_have_checks.py, checks/tests/test_no_cjk_or_emoji.py, checks/tests/test_claude_md_size.py, checks/tests/test_skills_registry.py, checks/tests/test_pr_has_reference.py, checks/tests/test_protected_paths.py.

- [ ] **Step 3: Plan is complete**

Phase 0 deliverables are in place. The next steps (Phases 2–5: PAT setup, target bootstrap, push, smoke test) are user-driven operational steps captured in spec §7 and are out of scope for this implementation plan.

---

## What's not in this plan (explicit)

- **Phases 2–5 of the spec bootstrap** (PAT creation, target repo permission settings, running `bin/sync-ai-docs.sh direct`, pushing `.github` to GitHub, opening the smoke-test PR) — these are operational steps performed by the user after this plan completes.
- **Sub-projects F, D, E** (branch protection, per-stack harness, shared skills) — separate brainstorm sessions per the spec §7 Phase 6.
- **Local pre-commit hook** — explicitly post-day-0 per spec §2.
- **Running unit tests in CI** — spec doesn't require; checks themselves are the CI gate. Tests stay as a local TDD discipline.
