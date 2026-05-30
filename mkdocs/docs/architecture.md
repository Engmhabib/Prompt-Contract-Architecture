# Architecture

PCA is a runtime sandwiched between clients and tools/services. Every
invocation is gated by a contract.

## Runtime Pipeline

```mermaid
sequenceDiagram
  autonumber
  participant U as User
  participant API as FastAPI
  participant O as Orchestrator
  participant L as LLM
  participant R as Registry
  participant V as Validator/Rules
  participant T as Tool
  participant DB as Postgres
  U->>API: POST /v1/invoke {prompt}
  API->>O: invoke(prompt, user)
  O->>L: classify(prompt, candidates)
  L-->>O: contract_id
  O->>R: resolve(contract_id, version?)
  R-->>O: Contract
  O->>O: check user.roles ⊇ permissions
  O->>L: extract(prompt, input_schema)
  L-->>O: raw inputs
  O->>V: validate schema + rules
  O->>T: run(payload) (only if in allowed_tools)
  T->>DB: ...
  T-->>O: result
  O->>DB: write AuditLog
  O-->>API: shaped output
  API-->>U: 200 {output}
```

## Modules

| Module | Responsibility |
|---|---|
| `pca.contracts` | YAML schema, loader, registry (hot reload), static validator |
| `pca.runtime` | Orchestrator, classifier, schema builder, rules |
| `pca.llm` | Provider protocol + LiteLLM and Mock implementations |
| `pca.tools` | Tool protocol + registry + built-ins |
| `pca.auth` | JWT decode + FastAPI dependencies |
| `pca.audit` | Persistent audit log |
| `pca.api` | FastAPI routers (`/v1/invoke`, `/v1/contracts`, `/v1/audit`, `/v1/docs`, `/v1/tests`) |
| `pca.docs_gen` | Contract → Markdown |
| `pca.test_gen` | Contract → in-memory test cases + executor |
