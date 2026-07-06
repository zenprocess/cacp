"""Tests for ``parse_structured(data: dict)`` — issue #8.

The structured-envelope path mirrors ``parse(text)`` for callers that
already have the CACP fields parsed out (e.g. ``claude -p`` JSON
output). Strictness on STATUS / TESTS / BUILD vocabularies matches the
text path so the two paths can be A/B compared without false
divergence on tolerable input.
"""

from __future__ import annotations

import pytest

from cacp_protocol import (
    CANONICAL_STATUS_VALUES,
    CACPResponse,
    parse_structured,
)


# ─────────────────────────────────────────────────────────────────────
# Happy path
# ─────────────────────────────────────────────────────────────────────


def test_minimal_envelope_with_only_status() -> None:
    r = parse_structured({"status": "ok"})
    assert r is not None
    assert isinstance(r, CACPResponse)
    assert r.status == "ok"
    assert r.files_created == []
    assert r.files_modified == []
    assert r.tests is None
    assert r.build is None
    assert r.error is None
    assert r.learned is None


@pytest.mark.parametrize("value", CANONICAL_STATUS_VALUES)
def test_all_canonical_status_values(value: str) -> None:
    r = parse_structured({"status": value})
    assert r is not None
    assert r.status == value


def test_full_envelope() -> None:
    """The shape a typical CLI orchestrator's claude -p JSON envelope sends."""
    r = parse_structured(
        {
            "status": "ok",
            "files_created": ["a.py", "b.py"],
            "files_modified": ["c.py"],
            "tests": "pass:42",
            "build": "pass",
            "error": "",
            "learned": "summary text",
        }
    )
    assert r is not None
    assert r.status == "ok"
    assert r.files_created == ["a.py", "b.py"]
    assert r.files_modified == ["c.py"]
    assert r.tests == "pass:42"
    assert r.build == "pass"
    assert r.error is None  # empty string coerced to None
    assert r.learned == "summary text"


# ─────────────────────────────────────────────────────────────────────
# Lowercase normalization
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("status", ["OK", "Ok", " ok ", "Partial"])
def test_status_lowercased_and_stripped(status: str) -> None:
    r = parse_structured({"status": status})
    assert r is not None
    assert r.status == status.strip().lower()


@pytest.mark.parametrize("value", ["PASS", "Fail", " skip "])
def test_tests_build_lowercased(value: str) -> None:
    r = parse_structured({"status": "ok", "tests": value, "build": value})
    assert r is not None
    assert r.tests == value.strip().lower()
    assert r.build == value.strip().lower()


# ─────────────────────────────────────────────────────────────────────
# files_created / files_modified — list OR comma-separated string
# ─────────────────────────────────────────────────────────────────────


def test_files_as_list() -> None:
    r = parse_structured({"status": "ok", "files_created": ["a.py", "b.py"]})
    assert r is not None
    assert r.files_created == ["a.py", "b.py"]


def test_files_as_comma_string() -> None:
    """Spec text-serialization form: 'FILES_CREATED: a.py, b.py'."""
    r = parse_structured({"status": "ok", "files_created": "a.py, b.py"})
    assert r is not None
    assert r.files_created == ["a.py", "b.py"]


def test_files_strip_whitespace_in_list() -> None:
    r = parse_structured({"status": "ok", "files_modified": ["  a.py  ", "b.py"]})
    assert r is not None
    assert r.files_modified == ["a.py", "b.py"]


def test_files_drop_empty_entries() -> None:
    r = parse_structured(
        {"status": "ok", "files_created": ["a.py", "", "  ", "b.py"]}
    )
    assert r is not None
    assert r.files_created == ["a.py", "b.py"]


def test_files_default_empty_when_missing() -> None:
    r = parse_structured({"status": "ok"})
    assert r is not None
    assert r.files_created == []
    assert r.files_modified == []


def test_files_default_empty_when_none() -> None:
    r = parse_structured(
        {"status": "ok", "files_created": None, "files_modified": None}
    )
    assert r is not None
    assert r.files_created == []


def test_files_default_empty_on_unexpected_type() -> None:
    """Non-list / non-string → treat as empty (advisory field)."""
    r = parse_structured({"status": "ok", "files_created": 42})
    assert r is not None
    assert r.files_created == []


# ─────────────────────────────────────────────────────────────────────
# error / learned coercion
# ─────────────────────────────────────────────────────────────────────


def test_empty_error_coerced_to_none() -> None:
    r = parse_structured({"status": "ok", "error": ""})
    assert r is not None
    assert r.error is None


def test_whitespace_error_coerced_to_none() -> None:
    r = parse_structured({"status": "ok", "error": "   "})
    assert r is not None
    assert r.error is None


def test_real_error_preserved() -> None:
    r = parse_structured({"status": "fail", "error": "something broke"})
    assert r is not None
    assert r.error == "something broke"


def test_non_string_error_treated_as_none() -> None:
    """error must be str — anything else treated as missing rather than failing."""
    r = parse_structured({"status": "ok", "error": 42})
    assert r is not None
    assert r.error is None


# ─────────────────────────────────────────────────────────────────────
# Failure modes — return None
# ─────────────────────────────────────────────────────────────────────


def test_non_dict_returns_none() -> None:
    assert parse_structured("not a dict") is None  # type: ignore[arg-type]
    assert parse_structured([1, 2, 3]) is None  # type: ignore[arg-type]
    assert parse_structured(None) is None  # type: ignore[arg-type]


def test_missing_status_returns_none() -> None:
    assert parse_structured({}) is None
    assert parse_structured({"files_created": ["x.py"]}) is None


def test_empty_status_returns_none() -> None:
    assert parse_structured({"status": ""}) is None
    assert parse_structured({"status": "   "}) is None


def test_non_string_status_returns_none() -> None:
    assert parse_structured({"status": 42}) is None  # type: ignore[arg-type]
    assert parse_structured({"status": ["ok"]}) is None  # type: ignore[arg-type]


def test_non_canonical_status_returns_none() -> None:
    """STATUS strictness mirrors the text path's regex alternation."""
    assert parse_structured({"status": "succeeded"}) is None
    assert parse_structured({"status": "broken"}) is None


def test_invalid_tests_returns_none() -> None:
    """TESTS / BUILD vocabularies are spec-checked; invalid value rejects."""
    assert parse_structured({"status": "ok", "tests": "running"}) is None
    assert parse_structured({"status": "ok", "tests": "pass:abc"}) is None  # bad count


def test_invalid_build_returns_none() -> None:
    assert parse_structured({"status": "ok", "build": "succeeded"}) is None


def test_build_does_not_accept_count_suffix() -> None:
    """`pass:42` is valid for TESTS but NOT for BUILD per spec."""
    assert parse_structured({"status": "ok", "build": "pass:42"}) is None


def test_non_string_tests_returns_none() -> None:
    """TESTS as int / list / etc is malformed."""
    assert parse_structured({"status": "ok", "tests": 1}) is None  # type: ignore[arg-type]


# ─────────────────────────────────────────────────────────────────────
# Forward compat — extra fields ignored
# ─────────────────────────────────────────────────────────────────────


def test_extra_fields_silently_ignored() -> None:
    """Future spec revisions can add fields without breaking parser consumers."""
    r = parse_structured(
        {
            "status": "ok",
            "future_field_1": "anything",
            "future_field_2": [1, 2, 3],
            "deeply_nested": {"key": "value"},
        }
    )
    assert r is not None
    assert r.status == "ok"


# ─────────────────────────────────────────────────────────────────────
# Symmetry with parse(text)
# ─────────────────────────────────────────────────────────────────────


def test_symmetry_with_text_parse() -> None:
    """A roundtrip parse(text) → asdict → parse_structured produces an
    equivalent CACPResponse. The two paths agree on canonical input.
    """
    from cacp_protocol import parse
    from dataclasses import asdict

    text = (
        "STATUS:partial\n"
        "FILES_CREATED:a.py, b.py\n"
        "FILES_MODIFIED:c.py\n"
        "TESTS:pass:5\n"
        "BUILD:pass\n"
        "ERROR:partial completion\n"
        "LEARNED:figured out the api shape\n"
    )

    r_text = parse(text)
    assert r_text is not None
    r_struct = parse_structured(asdict(r_text))
    assert r_struct is not None
    assert r_struct == r_text
