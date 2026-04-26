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


def parse_structured(data: dict) -> CACPResponse | None:
    """Parse a pre-structured CACP envelope (e.g. from `claude -p` JSON output).

    The structured-envelope path consumed by callers that already have the
    fields parsed out — typically because the upstream returns a JSON
    document with the canonical CACP field names. This avoids the
    text-regex round-trip when the input is already structured.

    Returns ``CACPResponse`` on success; returns ``None`` when ``data`` is
    not a dict, when ``status`` is missing, or when ``status`` is not one
    of the canonical values.

    Tolerance rules:

    - ``status`` / ``tests`` / ``build`` values are normalized to lowercase
      (mirrors the text-parse path).
    - ``files_created`` / ``files_modified`` accept either a list or a
      comma-separated string (per the spec's text serialization).
    - Empty strings on ``error`` / ``learned`` are coerced to ``None`` so
      consumers see the same "missing → None" shape as the text path.
    - Extra unknown fields in ``data`` are silently ignored (forward
      compat: a future CACP spec revision can add fields without
      breaking existing parser consumers).

    Failure modes (return ``None``):

    - ``data`` is not a dict
    - ``data["status"]`` is missing, empty, or not in CANONICAL_STATUS_VALUES
    - ``data["tests"]`` / ``data["build"]`` is set to a non-canonical value
      (after lowercase + optional ``:N`` strip) — these are spec-checked
      because they have a fixed vocabulary

    The strictness on STATUS / TESTS / BUILD mirrors what ``parse(text)``
    enforces via the regex alternation; structured callers shouldn't get
    a more permissive contract just because they bypass the text layer.

    Args:
        data: dict with the canonical CACP field names.

    Returns:
        Parsed CACPResponse, or None on unparseable input.
    """
    if not isinstance(data, dict):
        return None

    raw_status = data.get("status")
    if not isinstance(raw_status, str) or not raw_status.strip():
        return None
    status = raw_status.strip().lower()
    if status not in CANONICAL_STATUS_VALUES:
        return None

    tests = _coerce_tests_build(data.get("tests"), allow_count=True)
    if tests is _INVALID:
        return None

    build = _coerce_tests_build(data.get("build"), allow_count=False)
    if build is _INVALID:
        return None

    files_created = _coerce_path_list(data.get("files_created"))
    files_modified = _coerce_path_list(data.get("files_modified"))

    error = _coerce_optional_str(data.get("error"))
    learned = _coerce_optional_str(data.get("learned"))

    return CACPResponse(
        status=status,
        files_created=files_created,
        files_modified=files_modified,
        tests=tests,
        build=build,
        error=error,
        learned=learned,
    )


# Sentinel used by _coerce_tests_build to distinguish "missing" (None)
# from "present but malformed" (signal to reject the whole envelope).
_INVALID = object()


def _coerce_tests_build(value: object, *, allow_count: bool) -> str | None | object:
    """Normalise a TESTS or BUILD value from a structured envelope.

    Returns ``None`` when the field is missing, the lowercase string when
    valid, or ``_INVALID`` when the field is present but the value is not
    in ``CANONICAL_TESTS_BUILD_VALUES`` (optionally with ``:N`` suffix on
    TESTS).

    Strictness mirrors the regex-text path: the text parser only matches
    canonical values via alternation; the structured path enforces the
    same vocabulary so the contract is symmetric.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        return _INVALID
    stripped = value.strip()
    if not stripped:
        return None
    lower = stripped.lower()
    # Optional :N count is allowed on TESTS but not BUILD.
    base = lower
    if allow_count and ":" in lower:
        base, _, count = lower.partition(":")
        if not count.isdigit():
            return _INVALID
    if base not in CANONICAL_TESTS_BUILD_VALUES:
        return _INVALID
    return lower


def _coerce_path_list(value: object) -> list[str]:
    """Normalise a FILES_* value: list or comma-separated string → list[str]."""
    if value is None:
        return []
    if isinstance(value, str):
        return _split_paths(value)
    if isinstance(value, (list, tuple)):
        return [str(p).strip() for p in value if str(p).strip()]
    # Any other type (int, dict, etc.) treated as empty rather than
    # failing the whole envelope — these fields are advisory.
    return []


def _coerce_optional_str(value: object) -> str | None:
    """Normalise an ERROR or LEARNED value: empty string → None."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
