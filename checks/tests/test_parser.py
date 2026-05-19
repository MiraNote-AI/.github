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
