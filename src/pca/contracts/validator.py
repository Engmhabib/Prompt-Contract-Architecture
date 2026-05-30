"""Static validation of contracts against the rule and tool registries."""

from __future__ import annotations

from collections import Counter

from pca.contracts.schema import Contract


class ContractValidationError(ValueError):
    """Raised when a contract fails static validation."""


def validate_contract(
    contract: Contract,
    *,
    known_rules: set[str] | None = None,
    known_tools: set[str] | None = None,
) -> None:
    """Validate a contract against rule and tool registries.

    Raises ``ContractValidationError`` on the first problem found.
    """
    known_rules = known_rules or set()
    known_tools = known_tools or set()

    if not contract.intent_examples:
        raise ContractValidationError(
            f"{contract.key}: at least one intent_example is required"
        )

    for rule in contract.validation_rules:
        if rule not in known_rules:
            raise ContractValidationError(
                f"{contract.key}: unknown validation_rule {rule!r}"
            )

    for tool in contract.allowed_tools:
        if tool not in known_tools:
            raise ContractValidationError(
                f"{contract.key}: unknown tool {tool!r}"
            )

    for perm in contract.permissions:
        if not isinstance(perm, str) or not perm.strip():
            raise ContractValidationError(
                f"{contract.key}: permissions must be non-empty strings"
            )


def find_duplicates(contracts: list[Contract]) -> list[str]:
    """Return a list of duplicate ``contract_id@version`` keys."""
    counts = Counter(c.key for c in contracts)
    return [k for k, n in counts.items() if n > 1]
