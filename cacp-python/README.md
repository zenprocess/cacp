# cacp-protocol — Reference Python parser for CACP

Canonical Python reference implementation of [CACP (Compressed Agent
Communication Protocol)](https://github.com/zenprocess/cacp). The spec
lives in the parent [`README.md`](../README.md); this package implements
the parser against it.

> **Naming**: distributed on PyPI as `cacp-protocol` (the unprefixed
> `cacp` slot was already taken by an unrelated project — Classification
> Algorithms Comparison Pipeline). Imports as `cacp_protocol`.

## Install

```
pip install cacp-protocol
```

Zero runtime dependencies — pure stdlib.

## Usage

```python
from cacp_protocol import parse

text = open("agent_response.txt").read()
response = parse(text)

if response is None:
    print("not a CACP response")
elif response.status == "ok":
    print(f"agent created {len(response.files_created)} files")
    print(f"files: {response.files_created}")
else:
    print(f"agent reported {response.status}: {response.error}")
```

`parse()` returns `None` when no `STATUS:` field is found — treat that as
"not a CACP response" rather than an error.

## Conformance

The parser passes the [conformance test vector](../README.md#conformance-test-vector)
from the parent spec, plus round-trip tests against the literal response
example block. Tolerance rules honored:

- Whitespace between `:` and value: zero or more spaces, or a tab
- Field names: case-insensitive
- STATUS / TESTS / BUILD values: normalized to lowercase

## Design

- Pure stdlib — no Pydantic, no external deps. A dataclass-based
  `CACPResponse` keeps the dep tree empty; callers that want validation
  can wrap it.
- ~100 LOC in the parser. If it grows past 200 LOC it has probably
  absorbed orchestrator-specific complexity that belongs upstream.

## Status

This is the canonical Python reference. Other language implementations
(Rust, TypeScript, Go, ...) should pass an equivalent port of
[`tests/test_conformance.py`](tests/test_conformance.py).

## License

MIT
