"""Intent classifier: wraps an LLM provider with the contract registry."""

from __future__ import annotations

from pca.contracts.registry import ContractRegistry
from pca.llm.base import LLMProvider
from pca.runtime.errors import ClassificationError


class IntentClassifier:
    def __init__(self, llm: LLMProvider, registry: ContractRegistry) -> None:
        self._llm = llm
        self._registry = registry

    async def classify(self, prompt: str, hint: str | None = None) -> str:
        if hint:
            # Honor explicit caller hint (e.g. "contract_id" or "contract_id@version").
            return hint

        candidates = []
        for cid, contracts in self._registry.grouped().items():
            latest = contracts[-1]  # already sorted ascending
            candidates.append(
                {
                    "contract_id": cid,
                    "description": latest.description,
                    "examples": latest.intent_examples,
                }
            )

        if not candidates:
            raise ClassificationError("no contracts available")

        result = await self._llm.classify(prompt, candidates)
        if result.contract_id == "unknown" or result.contract_id not in {
            c["contract_id"] for c in candidates
        }:
            raise ClassificationError(
                f"could not classify prompt (best={result.contract_id})"
            )
        return result.contract_id
