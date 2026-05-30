"""Pluggable validation rule registry.

Rules receive the full input dict plus a context object and may raise
``ValidationError`` on failure. They are async to allow DB lookups.
"""

from __future__ import annotations

from dataclasses import dataclass
from email_validator import EmailNotValidError, validate_email
from typing import Any, Awaitable, Callable

from pca.runtime.errors import ValidationError

RuleFn = Callable[[dict[str, Any], "RuleContext"], Awaitable[None]]


@dataclass
class RuleContext:
    user_sub: str
    contract_id: str


class _RuleRegistry:
    def __init__(self) -> None:
        self._rules: dict[str, RuleFn] = {}

    def register(self, name: str, fn: RuleFn) -> None:
        self._rules[name] = fn

    def get(self, name: str) -> RuleFn:
        if name not in self._rules:
            raise KeyError(f"unknown validation rule: {name}")
        return self._rules[name]

    def names(self) -> set[str]:
        return set(self._rules)


rule_registry = _RuleRegistry()


def rule(name: str) -> Callable[[RuleFn], RuleFn]:
    """Decorator: register an async validation rule."""

    def _wrap(fn: RuleFn) -> RuleFn:
        rule_registry.register(name, fn)
        return fn

    return _wrap


# --- built-in rules ---


@rule("valid_email")
async def _valid_email(data: dict[str, Any], _ctx: RuleContext) -> None:
    email = data.get("email")
    if email is None:
        return
    try:
        validate_email(str(email), check_deliverability=False)
    except EmailNotValidError as e:
        raise ValidationError(
            "invalid email", [{"field": "email", "message": str(e)}]
        ) from e


@rule("unique_email")
async def _unique_email(data: dict[str, Any], _ctx: RuleContext) -> None:
    """Ensures the email is not already registered. Requires customer_db."""
    email = data.get("email")
    if not email:
        return
    # Imported lazily to avoid circulars
    from pca.tools.customer_db import CustomerDbTool
    from pca.tools.base import ToolContext

    tool = CustomerDbTool()
    res = await tool.run(
        {"action": "exists_email", "email": email},
        ToolContext(user_sub=_ctx.user_sub, contract_id=_ctx.contract_id, contract_version=""),
    )
    if res.get("exists"):
        raise ValidationError(
            "email already registered",
            [{"field": "email", "message": "duplicate"}],
        )


@rule("non_empty_name")
async def _non_empty_name(data: dict[str, Any], _ctx: RuleContext) -> None:
    name = data.get("name")
    if name is not None and not str(name).strip():
        raise ValidationError(
            "name must be non-empty", [{"field": "name", "message": "empty"}]
        )
