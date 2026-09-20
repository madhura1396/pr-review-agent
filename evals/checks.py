"""
Deterministic checks on agent output.

These run on output the eval already paid for, so they cost no extra LLM calls.
They cover the contract the prompts state literally ("SEVERITY | filename | line
number | description"), which is worth asserting exactly rather than judging.
"""

import re
from typing import List

SEVERITIES = ("CRITICAL", "WARNING", "SUGGESTION")

_FINDING_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(CRITICAL|WARNING|SUGGESTION)\s*\|([^|]*)\|([^|]*)\|(.+)$"
)


def parse_findings(text: str) -> List[re.Match]:
    """Return the lines of `text` that parse as well-formed findings."""
    return [m for m in (_FINDING_RE.match(line) for line in text.splitlines()) if m]


def assert_finding_format(text: str) -> None:
    """
    Assert the agent emitted at least one finding in the documented pipe format,
    and that no line starts with a severity token but then malforms the row.
    """
    parsed = parse_findings(text)
    assert parsed, (
        "no line matched 'SEVERITY | filename | line number | description'.\n"
        f"Got:\n{text}"
    )

    for line in text.splitlines():
        stripped = line.strip().lstrip("-* ")
        if not stripped.upper().startswith(SEVERITIES):
            continue
        assert _FINDING_RE.match(line), (
            f"line starts with a severity but is not a well-formed finding row: {line!r}"
        )


def assert_severities_valid(text: str) -> None:
    """Assert every parsed finding uses one of the three documented severities."""
    for match in parse_findings(text):
        assert match.group(1) in SEVERITIES, f"unexpected severity {match.group(1)!r}"
