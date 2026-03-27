# CACP — Compressed Agent Communication Protocol

> Structured I/O format for LLM coding agents. ~200 tokens vs ~2000 of prose.

## What is CACP?

CACP replaces free-form agent responses with typed fields that orchestrators parse programmatically — no LLM needed to understand the result.

### Dispatch (orchestrator → agent)

```
TASK: Implement JWT auth middleware
CONTEXT: Go backend, chi router
ACCEPTANCE: 1. Middleware validates Bearer tokens  2. Tests pass
SCOPE: src/middleware/
VERIFY: go test ./...
DONE: return STATUS format
```

### Response (agent → orchestrator)

```
STATUS:ok
FILES_CREATED:src/middleware/jwt.go,src/middleware/jwt_test.go
FILES_MODIFIED:go.mod
TESTS:pass:12
BUILD:pass
LEARNED:JWT tokens need 24h expiry for mobile clients
```

## Why?

Without CACP, agents return 2,000-token prose explaining what they did. With CACP, the same information is ~200 tokens. The orchestrator parses it programmatically.

| Without CACP | With CACP |
|---|---|
| "I've completed the task. I created two new files..." (2000 tokens) | `STATUS:ok\nFILES_CREATED:jwt.go,jwt_test.go` (200 tokens) |
| Need LLM to parse response | Regex/JSON parse |
| Ambiguous success/failure | Explicit STATUS field |
| No structured file tracking | FILES_CREATED/MODIFIED lists |

## Status

Spec in development. Used in production by [Switchyard](https://github.com/zenprocess) dispatcher.

See benchmark compliance rates on [ServingCard](https://servingcard.dev).

## License

MIT
