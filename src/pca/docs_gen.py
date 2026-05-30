"""Generate Markdown documentation from contracts."""

from __future__ import annotations

from pca.contracts.schema import Contract, FieldSpec


def _field_table(title: str, fields: dict[str, FieldSpec]) -> str:
    if not fields:
        return f"### {title}\n\n_None._\n"
    rows = ["| Field | Type | Required | Description |", "|---|---|---|---|"]
    for name, spec in fields.items():
        rows.append(
            f"| `{name}` | `{spec.type}` | {'yes' if spec.required else 'no'} "
            f"| {spec.description or ''} |"
        )
    return f"### {title}\n\n" + "\n".join(rows) + "\n"


def contract_to_markdown(contract: Contract) -> str:
    """Render a single contract as Markdown."""
    lines: list[str] = []
    lines.append(f"# `{contract.contract_id}` — v{contract.version}\n")
    if contract.description:
        lines.append(f"{contract.description}\n")

    lines.append("## Permissions\n")
    if contract.permissions:
        lines.append("\n".join(f"- `{p}`" for p in contract.permissions) + "\n")
    else:
        lines.append("_Public._\n")

    lines.append("## Allowed Tools\n")
    if contract.allowed_tools:
        lines.append("\n".join(f"- `{t}`" for t in contract.allowed_tools) + "\n")
    else:
        lines.append("_None._\n")

    lines.append("## Validation Rules\n")
    if contract.validation_rules:
        lines.append("\n".join(f"- `{r}`" for r in contract.validation_rules) + "\n")
    else:
        lines.append("_None._\n")

    lines.append("## Schemas\n")
    lines.append(_field_table("Input", contract.input_schema))
    lines.append(_field_table("Output", contract.output_schema))

    lines.append("## Example Intents\n")
    if contract.intent_examples:
        lines.append("\n".join(f"- {ex}" for ex in contract.intent_examples) + "\n")
    else:
        lines.append("_None._\n")

    return "\n".join(lines)


def registry_index_markdown(contracts: list[Contract]) -> str:
    """Render an index page listing all contracts."""
    lines = ["# Contract Reference\n"]
    grouped: dict[str, list[Contract]] = {}
    for c in contracts:
        grouped.setdefault(c.contract_id, []).append(c)
    for cid, versions in sorted(grouped.items()):
        latest = max(versions, key=lambda c: c.version)
        lines.append(f"- **`{cid}`** — _{latest.description}_ ")
        lines.append(
            "  versions: " + ", ".join(f"`{c.version}`" for c in versions)
        )
    return "\n".join(lines) + "\n"
