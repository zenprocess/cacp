"""Conformance tests for the canonical CACP parser.

These tests implement the test vector published in the parent README.md
and the surrounding tolerance rules. A conformant implementation in any
language should pass an equivalent suite.
"""

from __future__ import annotations

import pytest

from cacp_protocol import (
    CANONICAL_STATUS_VALUES,
    CANONICAL_TESTS_BUILD_VALUES,
    parse,
)


# ---------------------------------------------------------------------------
# 1. All 9 STATUS values parse
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", CANONICAL_STATUS_VALUES)
def test_all_canonical_status_values_parse(value: str) -> None:
    response = parse(f"STATUS:{value}\n")
    assert response is not None
    assert response.status == value


# ---------------------------------------------------------------------------
# 2. Tolerance vector from the canonical spec (README.md §"Conformance
#    test vector")
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "line, expected",
    [
        ("STATUS:ok", "ok"),
        ("STATUS: ok", "ok"),
        ("STATUS:  ok", "ok"),
        ("STATUS:\tok", "ok"),
        ("status: ok", "ok"),
        ("Status:OK", "ok"),
    ],
)
def test_tolerance_vector(line: str, expected: str) -> None:
    response = parse(line + "\n")
    assert response is not None
    assert response.status == expected


# ---------------------------------------------------------------------------
# 3. TESTS values (pass/fail/skip + optional :N count)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "line, expected",
    [
        ("TESTS:pass", "pass"),
        ("TESTS:fail", "fail"),
        ("TESTS:skip", "skip"),
        ("TESTS:pass:42", "pass:42"),
    ],
)
def test_tests_values(line: str, expected: str) -> None:
    response = parse(f"STATUS:ok\n{line}\n")
    assert response is not None
    assert response.tests == expected


@pytest.mark.parametrize("value", CANONICAL_TESTS_BUILD_VALUES)
def test_tests_tolerance_whitespace(value: str) -> None:
    """TESTS field must tolerate the same whitespace as STATUS."""
    for sep in ("", " ", "  ", "\t"):
        text = f"STATUS:ok\nTESTS:{sep}{value}\n"
        response = parse(text)
        assert response is not None
        assert response.tests == value


# ---------------------------------------------------------------------------
# 4. BUILD values (pass/fail/skip, no count)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", CANONICAL_TESTS_BUILD_VALUES)
def test_build_values(value: str) -> None:
    response = parse(f"STATUS:ok\nBUILD:{value}\n")
    assert response is not None
    assert response.build == value


@pytest.mark.parametrize("value", CANONICAL_TESTS_BUILD_VALUES)
def test_build_tolerance_whitespace(value: str) -> None:
    for sep in ("", " ", "  ", "\t"):
        text = f"STATUS:ok\nBUILD:{sep}{value}\n"
        response = parse(text)
        assert response is not None
        assert response.build == value


# ---------------------------------------------------------------------------
# 5. Negative: no STATUS → not a CACP response → parse returns None
# ---------------------------------------------------------------------------


def test_no_status_returns_none() -> None:
    assert parse("hello world") is None


def test_empty_string_returns_none() -> None:
    assert parse("") is None


def test_dispatch_format_returns_none() -> None:
    """The dispatch (input) format has no STATUS field — parse must reject."""
    dispatch = (
        "TASK: Implement JWT auth middleware\n"
        "CONTEXT: Go backend, chi router\n"
        "ACCEPTANCE: 1. Middleware validates Bearer tokens\n"
        "SCOPE: src/middleware/\n"
    )
    assert parse(dispatch) is None


# ---------------------------------------------------------------------------
# 6. Case-insensitivity across field names
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field_name",
    ["STATUS", "status", "Status", "STATus", "sTaTuS"],
)
def test_status_field_name_case_insensitive(field_name: str) -> None:
    response = parse(f"{field_name}:ok\n")
    assert response is not None
    assert response.status == "ok"
