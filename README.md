# Prompt Contract Architecture (PCA)

> **Make prompts first-class software artifacts.**

PCA is an open-source reference implementation of a new architecture pattern
where YAML **Prompt Contracts** sit between users and backend services and
become the source of truth for intent, input schemas, validation, permissions,
tool access, outputs, audit, documentation, and tests.

```
Client → FastAPI (PCA Runtime) → LLM → Tools → Services → Database
                       │
                       └── Contract Registry (YAML, source of truth)
```

## Why PCA?

Today's options force a choice:

- **Traditional APIs:** rigid, well-validated, hard for humans to use.
- **Agent stacks:** flexible, but lose contracts, auth, audit, and structure.

PCA keeps the rigor of an API while accepting natural-language input.
The contract — not the prompt — is canonical.

> **The contract is a deterministic envelope around a stochastic core.**
> The LLM is free to be weird. The system isn't: inputs are validated,
> outputs are schema-checked, callers are authorized, tool access is
> whitelisted, and every invocation is audited.

## How is this different from…?

Adjacent ideas exist; PCA's bet is the *synthesis*, not any single piece.

| Project | What it does well | What PCA adds |
|---|---|---|
| **DSPy** | Declarative LLM pipelines, prompt optimization | Permissions, audit, intent routing, generated docs/tests as part of the same artifact |
| **BAML** | Schema-first typed LLM functions | Role-based authz, audit log, tool whitelisting, hot-reloaded registry |
| **Semantic Kernel semantic functions** | Prompt + config bundle per skill | Intent classification, permissions, validation rules, audit, multi-version registry |
| **Instructor / Outlines / Guidance** | Structured/typed outputs | Input schema, permissions, tools, audit, docs, tests |
| **PromptOps / PromptLayer / Pezzo / Langfuse** | Version, test, observe prompts | Runtime enforcement of schema/permissions/tools; contract ≠ just a versioned string |
| **MCP** | Tool-server transport | A contract layer that *uses* tools (PCA can expose its tools over MCP) |

None of these unify **intent + input schema + permissions + tool access +
validation + output schema + audit + generated docs + generated tests** in
one artifact enforced by a runtime. That unification is the point.

## Quick start

```bash
poetry install
cp .env.example .env

# Run locally with SQLite + Mock LLM:
PCA_DATABASE_URL=sqlite+aiosqlite:///./pca.db \
PCA_LLM_PROVIDER=mock \
poetry run uvicorn pca.main:app --reload
```

Or with Docker Compose (Postgres included):

```bash
docker compose -f docker/docker-compose.yml --env-file .env up --build
```

Then open <http://localhost:8000/> for the playground UI (enabled by
`PCA_DEV_MODE=true`). API docs are at <http://localhost:8000/docs>.

Mint a dev JWT and invoke:

```bash
TOKEN=$(poetry run python -c "from pca.auth import issue_token; print(issue_token('alice', ['sales_admin']))")

curl -X POST http://localhost:8000/v1/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a customer named John Doe, john@example.com"}'
```

## A contract

```yaml
contract_id: customer.create
version: 1.0.0
description: Create a new customer
intent_examples:
  - Create a customer named John
  - Add a new customer
permissions: [sales_admin]
input_schema:
  name: {type: string, required: true}
  email: {type: string, required: true}
validation_rules: [valid_email, unique_email]
allowed_tools: [customer_db]
output_schema:
  customer_id: {type: string}
```

## Features

- **Contract registry** with semantic-version resolution and **hot reload** via watchdog.
- **JWT auth** with role-based permission checks against `contract.permissions`.
- **Pluggable LLM** layer: `LiteLLMProvider` (production) + `MockLLMProvider` (tests).
- **Pluggable tools** via a small `Tool` protocol.
- **Pluggable validation rules** via a decorator-registered registry (`valid_email`, `unique_email`, `non_empty_name`).
- **Persistent audit log** with every invocation (success or failure).
- **Documentation generator** — Markdown from contracts, consumed by MkDocs Material.
- **In-memory test generator** — `POST /v1/tests/run/{contract}` runs happy-path, validation, authz, and negative cases against the live orchestrator and returns a structured report.
- **GitHub Actions CI**: lint, type-check, pytest matrix, Docker build.
- **Web playground UI** at `/` when `PCA_DEV_MODE=true` — browse contracts, invoke prompts, mint dev JWTs, run tests, view docs and audit log.

## CLI

```bash
pca validate                       # static-check all contracts
pca docs mkdocs/docs/contracts     # emit per-contract Markdown
pca test                           # run generated cases for every contract
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/healthz` | Liveness |
| POST | `/v1/invoke` | Main runtime entrypoint |
| GET | `/v1/contracts` | List registered contracts |
| GET | `/v1/contracts/{id}?version=` | Resolve a contract |
| POST/PUT/DELETE | `/v1/contracts/...` | CRUD (gated by `admin` + `PCA_ALLOW_WRITES`) |
| GET | `/v1/audit` | Paginated audit log (admin/auditor) |
| GET | `/v1/docs[/{id}]` | Generated Markdown |
| POST | `/v1/tests/run/{id}` | Run in-memory test suite |

## Repository Layout

```
pca/
├── contracts/                  # YAML contracts (source of truth)
├── docker/                     # Dockerfile + compose
├── mkdocs/                     # Documentation site
├── src/pca/
│   ├── api/                    # FastAPI routers
│   ├── contracts/              # schema, loader, registry, validator
│   ├── llm/                    # provider protocol + LiteLLM/Mock
│   ├── runtime/                # orchestrator, classifier, rules
│   ├── tools/                  # tool protocol + built-ins
│   ├── auth.py
│   ├── audit.py
│   ├── config.py
│   ├── db.py
│   ├── docs_gen.py
│   ├── test_gen.py
│   ├── cli.py
│   └── main.py
└── tests/
```

## Roadmap (out of v1)

- Embedding-based intent retrieval
- Multi-tenant contract registries
- Contract signing / provenance
- OpenTelemetry tracing
- Streaming responses

## License

Apache-2.0.
