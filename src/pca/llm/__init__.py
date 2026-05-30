"""LLM provider abstraction."""

from pca.llm.base import ClassificationResult, LLMProvider
from pca.llm.litellm_provider import LiteLLMProvider
from pca.llm.mock_provider import MockLLMProvider


def get_provider(name: str, model: str) -> LLMProvider:
    """Factory returning the configured provider."""
    if name == "mock":
        return MockLLMProvider()
    if name == "litellm":
        return LiteLLMProvider(model=model)
    raise ValueError(f"unknown LLM provider: {name!r}")


__all__ = ["ClassificationResult", "LLMProvider", "LiteLLMProvider", "MockLLMProvider", "get_provider"]
