# checks/_meta/parser.py
"""Parse CONTRIBUTING.md into a list of Rule objects.

The parser is tolerant: it collects every violation it finds rather than
raising on the first. Callers use the (rules, errors) tuple to report all
violations in one pass.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
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


def _split_enforced_by(value: str) -> Tuple[List[str], List[str]]:
    """Split and strip a comma-separated enforced-by value.

    Design choice: emit an error string for every empty slot (option b).
    A sparse comma such as ``a.py``, , ``b.py`` is a typo — silently dropping
    it would hide the mistake from the author. Callers receive the filtered
    list of valid tokens *and* a list of error messages for the empty slots.
    """
    if not value.strip():
        return [], []
    tokens = [_strip_backticks_and_space(p) for p in value.split(",")]
    valid: List[str] = []
    slot_errors: List[str] = []
    for i, tok in enumerate(tokens):
        if tok == "":
            slot_errors.append(f"empty token at slot {i} in `**Enforced by:**` value")
        else:
            valid.append(tok)
    return valid, slot_errors


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
    chunks: List[Tuple[int, str, str, List[str]]] = []  # (line_no, raw_heading, title, body_lines)
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
            enforced_by, slot_errors = _split_enforced_by(enforced_matches[0][1])
            for msg in slot_errors:
                errors.append(
                    ParseError(
                        f"Rule {rule_id}: {msg}",
                        line=line_no,
                    )
                )
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
