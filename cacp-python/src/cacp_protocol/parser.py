"""Reference CACP parser.

Implements the tolerance rules from the canonical spec:

- Whitespace between the colon and the value: zero or more spaces, or a tab.
  We deliberately use ``[ \\t]*`` rather than ``\\s*`` so newlines are not
  consumed — each field stays on its own line.
- Field names are case-insensitive (``STATUS:``, ``status:``, ``Status:``
  all denote the same field).
- Values for STATUS, TESTS, BUILD are normalized to lowercase.

The parser is deliberately small (~7 compiled regexes, one per field) and
has zero runtime dependencies outside the stdlib.
"""

from __future__ import annotations

import re

from cacp_protocol.models import (
    CACPResponse,
    CANONICAL_STATUS_VALUES,
    CANONICAL_TESTS_BUILD_VALUES,
)


# ---------------------------------------------------------------------------
# Shared regex fragments
# ---------------------------------------------------------------------------

# Whitespace-between-colon-and-value: spaces or a tab, but NEVER a newline.
# Using ``\s*`` here would let a blank line swallow the following field.
_SEP = r"[ \t]*"

_STATUS_ALT = "|".join(re.escape(v) for v in CANONICAL_STATUS_VALUES)
_TESTS_BUILD_ALT = "|".join(re.escape(v) for v in CANONICAL_TESTS_BUILD_VALUES)


# ---------------------------------------------------------------------------
# Compiled per-field regexes
# ---------------------------------------------------------------------------

_STATUS_RE = re.compile(
    rf"^{_SEP}STATUS:{_SEP}({_STATUS_ALT})\b",
    re.IGNORECASE | re.MULTILINE,
)

_TESTS_RE = re.compile(
    rf"^{_SEP}TESTS:{_SEP}((?:{_TESTS_BUILD_ALT})(?::\d+)?)\b",
    re.IGNORECASE | re.MULTILINE,
)

_BUILD_RE = re.compile(
    rf"^{_SEP}BUILD:{_SEP}({_TESTS_BUILD_ALT})\b",
    re.IGNORECASE | re.MULTILINE,
)

_FILES_CREATED_RE = re.compile(
    rf"^{_SEP}FILES_CREATED:{_SEP}([^\n]*)",
    re.IGNORECASE | re.MULTILINE,
)

_FILES_MODIFIED_RE = re.compile(
    rf"^{_SEP}FILES_MODIFIED:{_SEP}([^\n]*)",
    re.IGNORECASE | re.MULTILINE,
)

_ERROR_RE = re.compile(
    rf"^{_SEP}ERROR:{_SEP}([^\n]*)",
    re.IGNORECASE | re.MULTILINE,
)

_LEARNED_RE = re.compile(
    rf"^{_SEP}LEARNED:{_SEP}([^\n]*)",
    re.IGNORECASE | re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _split_paths(raw: str) -> list[str]:
    """Split a comma-separated FILES_* value into a clean list."""
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def _optional_capture(pattern: re.Pattern[str], text: str) -> str | None:
    m = pattern.search(text)
    if not m:
        return None
    value = m.group(1).strip()
    return value or None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse(text: str) -> CACPResponse | None:
    """Parse a CACP-formatted response into a typed record.

    Returns ``None`` if ``STATUS`` cannot be extracted — callers interpret
    that as "not a CACP response". All other fields are optional; missing
    fields become ``None`` / ``[]`` as appropriate.

    Tolerance rules (per the canonical CACP spec):

    - Whitespace between ``:`` and the value: zero or more spaces or a tab.
    - Field names are matched case-insensitively.
    - STATUS / TESTS / BUILD values are normalized to lowercase.
    """
    status_match = _STATUS_RE.search(text)
    if not status_match:
        return None
    status = status_match.group(1).lower()

    tests_match = _TESTS_RE.search(text)
    tests = tests_match.group(1).lower() if tests_match else None

    build_match = _BUILD_RE.search(text)
    build = build_match.group(1).lower() if build_match else None

    fc_match = _FILES_CREATED_RE.search(text)
    files_created = _split_paths(fc_match.group(1)) if fc_match else []

    fm_match = _FILES_MODIFIED_RE.search(text)
    files_modified = _split_paths(fm_match.group(1)) if fm_match else []

    error = _optional_capture(_ERROR_RE, text)
    learned = _optional_capture(_LEARNED_RE, text)

    return CACPResponse(
        status=status,
        files_created=files_created,
        files_modified=files_modified,
        tests=tests,
        build=build,
        error=error,
        learned=learned,
    )
