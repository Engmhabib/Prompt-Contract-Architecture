"""Tool protocol and registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


class ToolError(RuntimeError):
    """Raised when a tool execution fails or is not permitted."""


@dataclass
class ToolContext:
    """Per-invocation context passed to a tool."""

    user_sub: str
    contract_id: str
    contract_version: str
    extra: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Tool(Protocol):
    """Tool protocol. Implementations must expose a unique ``name``."""

    name: str

    async def run(self, payload: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
        ...


class ToolRegistry:
    """Singleton-friendly tool registry."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if not getattr(tool, "name", None):
            raise ValueError("tool must have a non-empty `name`")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise ToolError(f"unknown tool: {name}")
        return self._tools[name]

    def names(self) -> set[str]:
        return set(self._tools)

    def clear(self) -> None:
        self._tools.clear()


_default = ToolRegistry()


def default_registry() -> ToolRegistry:
    return _default
