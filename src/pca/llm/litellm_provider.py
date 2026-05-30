"""LiteLLM-backed provider with JSON-mode extraction."""

from __future__ import annotations

import json
import logging
from typing import Any

from pca.llm.base import ClassificationResult

logger = logging.getLogger(__name__)


class LiteLLMProvider:
    """Thin wrapper around ``litellm.acompletion``."""

    def __init__(self, model: str) -> None:
        self.model = model

    async def _complete(self, messages: list[dict[str, str]], *, json_mode: bool = False) -> str:
        import litellm  # local import: optional at install time

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = await litellm.acompletion(**kwargs)
        return resp["choices"][0]["message"]["content"]

    async def classify(
        self, prompt: str, candidates: list[dict[str, Any]]
    ) -> ClassificationResult:
        catalog = "\n".join(
            f"- {c['contract_id']}: {c.get('description', '')} "
            f"(examples: {'; '.join(c.get('examples', []))})"
            for c in candidates
        )
        sys = (
            "You are a router. Choose the SINGLE best contract_id for the user prompt. "
            "Respond as JSON: {\"contract_id\": \"...\", \"confidence\": 0..1, "
            "\"rationale\": \"...\"}. Return contract_id exactly as listed, or "
            "\"unknown\" if none fit."
        )
        user = f"Available contracts:\n{catalog}\n\nUser prompt:\n{prompt}"
        text = await self._complete(
            [{"role": "system", "content": sys}, {"role": "user", "content": user}],
            json_mode=True,
        )
        data = json.loads(text)
        return ClassificationResult(
            contract_id=data.get("contract_id", "unknown"),
            confidence=float(data.get("confidence", 0.0)),
            rationale=data.get("rationale"),
        )

    async def extract(
        self, prompt: str, input_schema: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        schema_desc = json.dumps(input_schema, indent=2)
        sys = (
            "Extract the requested fields from the user message. "
            "Respond as a flat JSON object matching the schema. "
            "Use null if a field is genuinely absent."
        )
        user = f"Schema:\n{schema_desc}\n\nUser message:\n{prompt}"
        text = await self._complete(
            [{"role": "system", "content": sys}, {"role": "user", "content": user}],
            json_mode=True,
        )
        return json.loads(text)
