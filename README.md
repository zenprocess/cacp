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

Spec in development. Used in production for multi-agent AI coding dispatch.

See benchmark compliance rates on [ServingCard](https://servingcard.dev).

## Ecosystem

CACP is part of the [standra.ai](https://standra.ai) open standards stack:

- **[Axiom](https://github.com/zenprocess/axiom)** — Rule Definition Language; CACP is one of two normative serializations (alongside TOON). Axiom §17 standardizes orchestration shape vocabulary, complexity tier vocabulary, `fixture_gap` status, `verification_runs[]`, and `artifact_quality` schemas that CACP responses can carry.
- **[Pawbench](https://github.com/zenprocess/pawbench)** — reference benchmark that scores LLMs against CACP-formatted prompts and responses, including the orchestration × complexity matrix.
- **[ServingCard](https://servingcard.dev)** — model serving config standard.

## Additive fields for orchestration & complexity reporting

CACP responses can carry these additional fields for runners that report multi-dimensional dispatch results. Vocabularies are normative in [Axiom §17](https://github.com/zenprocess/axiom/blob/main/spec.md):

- `complexity_tier` — `display` / `crud` / `transactional` / `cross_cutting`. Stratifies aggregate scores so display-tier passes don't mask transactional-tier cliffs.
- `verification_runs[]` — N-run AC re-verification, one record per run with `verdict`, `prompt_hash`, `elapsed_ms`. Surfaces verifier flake.
- `artifact_quality` — static-analysis score over the *changed files only*; orthogonal to AC pass.
- `fixture_gap` (terminal status) — AC un-evaluable due to missing setup (seed data, env, services). **Not counted against the agent** — counts against the scenario author.

[Pawbench](https://github.com/zenprocess/pawbench) is the reference implementation of these fields end-to-end.

## License

MIT
