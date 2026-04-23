"""CACP response model and canonical vocabulary constants.

The data model is a plain dataclass — zero runtime dependencies, cheap to
construct, and trivial to serialize. Callers that want Pydantic-style
validation can wrap it.
"""

from __future__ import annotations

from dataclasses import dataclass, field


CANONICAL_STATUS_VALUES: tuple[str, ...] = (
    "ok",
    "fail",
    "partial",
    "needs_decision",
    "no_changes",
    "decomposed",
    "rejected",
    "retry",
    "fixture_gap",
)
"""The 9 canonical STATUS values per the CACP spec."""


CANONICAL_TESTS_BUILD_VALUES: tuple[str, ...] = ("pass", "fail", "skip")
"""The 3 canonical TESTS/BUILD values per the CACP spec."""


@dataclass(slots=True)
class CACPResponse:
    """Parsed CACP response record.

    All fields except ``status`` are optional — missing fields remain ``None``
    or an empty list. ``tests`` preserves the optional ``:N`` count suffix
    (e.g. ``"pass:12"``) verbatim so callers can choose whether to split it.
    """

    status: str
    files_created: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    tests: str | None = None
    build: str | None = None
    error: str | None = None
    learned: str | None = None
