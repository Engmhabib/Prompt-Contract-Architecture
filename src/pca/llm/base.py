"""LLM provider protocol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass
class ClassificationResult:
    contract_id: str
    confidence: float = 0.0
    rationale: str | None = None


@runtime_checkable
class LLMProvider(Protocol):
    """LLM operations needed by the PCA runtime."""

    async def classify(
        self,
        prompt: str,
        candidates: list[dict[str, Any]],
    ) -> ClassificationResult:
        """Pick the best ``contract_id`` for ``prompt`` from ``candidates``.

        Each candidate is ``{"contract_id": str, "description": str, "examples": [str]}``.
        """
        ...

    async def extract(
        self,
        prompt: str,
        input_schema: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Extract structured fields from ``prompt`` per ``input_schema``."""
        ...
