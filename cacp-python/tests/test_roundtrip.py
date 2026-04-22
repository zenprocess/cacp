"""Round-trip tests against the literal example blocks in the parent spec.

The canonical README.md carries an example response block. Per the spec's
"prompt round-trip test" recommendation, the parser MUST accept everything
the spec teaches an agent to emit.
"""

from __future__ import annotations

from cacp import parse


# Verbatim copy of the response example in the parent README.md (§"Response
# (agent → orchestrator)"). If the spec's example changes, this test fails
# and the parser (or the spec) must be updated in lockstep.
RESPONSE_EXAMPLE = """STATUS:ok
FILES_CREATED:src/middleware/jwt.go,src/middleware/jwt_test.go
FILES_MODIFIED:go.mod
TESTS:pass:12
BUILD:pass
LEARNED:JWT tokens need 24h expiry for mobile clients
"""


# Verbatim copy of the dispatch example (§"Dispatch (orchestrator → agent)").
# This is the INPUT format; none of its fields are CACP response fields,
# so the parser MUST reject it (no STATUS → returns None).
DISPATCH_EXAMPLE = """TASK: Implement JWT auth middleware
CONTEXT: Go backend, chi router
ACCEPTANCE: 1. Middleware validates Bearer tokens  2. Tests pass
SCOPE: src/middleware/
VERIFY: go test ./...
DONE: return STATUS format
"""


def test_readme_response_example_roundtrips() -> None:
    response = parse(RESPONSE_EXAMPLE)
    assert response is not None
    assert response.status == "ok"
    assert response.files_created == [
        "src/middleware/jwt.go",
        "src/middleware/jwt_test.go",
    ]
    assert response.files_modified == ["go.mod"]
    assert response.tests == "pass:12"
    assert response.build == "pass"
    assert response.learned is not None
    assert response.learned.startswith("JWT tokens")
    # No error field in the example.
    assert response.error is None


def test_readme_dispatch_example_returns_none() -> None:
    """Dispatch format has no STATUS → parser strictly rejects it."""
    assert parse(DISPATCH_EXAMPLE) is None


def test_fail_response_with_error_field() -> None:
    """A failing response carries the ERROR field."""
    text = (
        "STATUS:fail\n"
        "ERROR:compilation failed in jwt.go line 42\n"
    )
    response = parse(text)
    assert response is not None
    assert response.status == "fail"
    assert response.error == "compilation failed in jwt.go line 42"


def test_files_list_whitespace_stripped() -> None:
    """Comma-split lists tolerate whitespace around entries."""
    text = "STATUS:ok\nFILES_CREATED: a.py ,  b.py , c.py\n"
    response = parse(text)
    assert response is not None
    assert response.files_created == ["a.py", "b.py", "c.py"]


def test_empty_files_field_is_empty_list() -> None:
    text = "STATUS:ok\nFILES_CREATED:\n"
    response = parse(text)
    assert response is not None
    assert response.files_created == []


def test_mixed_case_fields_all_parse() -> None:
    """Every field name is case-insensitive, not just STATUS."""
    text = (
        "status:OK\n"
        "Files_Created:a.py\n"
        "FILES_modified:b.py\n"
        "Tests:pass:3\n"
        "build:PASS\n"
        "Learned:pattern worked\n"
    )
    response = parse(text)
    assert response is not None
    assert response.status == "ok"
    assert response.files_created == ["a.py"]
    assert response.files_modified == ["b.py"]
    assert response.tests == "pass:3"
    assert response.build == "pass"
    assert response.learned == "pattern worked"
