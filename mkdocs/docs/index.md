# Prompt Contract Architecture (PCA)

> **Make prompts first-class software artifacts.**

PCA sits between users and backend services. A YAML **Prompt Contract**
becomes the source of truth for intent, inputs, validation, authorization,
tool access, output schema, audit, docs, and tests.

```mermaid
flowchart LR
  C[Client] --> A[FastAPI + JWT]
  A --> R[PCA Runtime]
  R --> L[LLM]
  R --> Reg[(Contract Registry)]
  R --> T[Tool Broker]
  T --> DB[(Postgres)]
  R --> Au[Audit] --> DB
```

See [Architecture](architecture.md) and [Contracts](contracts/index.md).
