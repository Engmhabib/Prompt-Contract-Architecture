"""Shared pytest fixtures."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import pytest_asyncio

# Force test config BEFORE importing pca modules.
os.environ.setdefault("PCA_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("PCA_JWT_SECRET", "test-secret")
os.environ.setdefault("PCA_LLM_PROVIDER", "mock")
os.environ.setdefault("PCA_CONTRACTS_DIR", str(Path(__file__).parent.parent / "contracts"))

from pca.config import reset_settings  # noqa: E402
from pca.contracts.registry import ContractRegistry  # noqa: E402
from pca.db import init_db, reset_engine  # noqa: E402
from pca.llm.mock_provider import MockLLMProvider  # noqa: E402
from pca.runtime.orchestrator import Orchestrator  # noqa: E402
from pca.tools import register_builtin_tools  # noqa: E402
from pca.tools.base import default_registry  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_settings():
    reset_settings()
    yield
    reset_settings()


@pytest_asyncio.fixture
async def db():
    await reset_engine()
    await init_db()
    yield
    await reset_engine()


@pytest.fixture
def contracts_dir() -> Path:
    return Path(__file__).parent.parent / "contracts"


@pytest.fixture
def registry(contracts_dir: Path) -> ContractRegistry:
    reg = ContractRegistry()
    reg.load_dir(contracts_dir)
    return reg


@pytest.fixture
def tools():
    reg = default_registry()
    reg.clear()
    register_builtin_tools(reg)
    return reg


@pytest.fixture
def orchestrator(registry, tools):
    return Orchestrator(registry, MockLLMProvider(), tools)
