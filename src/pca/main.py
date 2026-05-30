"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pca.api import audit, contracts, dev, docs_gen, invoke, tests_gen
from pca.config import get_settings
from pca.contracts.registry import ContractRegistry
from pca.contracts.validator import find_duplicates, validate_contract
from pca.db import init_db
from pca.llm import get_provider
from pca.runtime.orchestrator import Orchestrator
from pca.runtime.rules import rule_registry
from pca.tools import register_builtin_tools
from pca.tools.base import default_registry as default_tool_registry

logger = logging.getLogger("pca")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # Tools first so contract validation can check tool names.
    tools = register_builtin_tools()
    app.state.tools = tools

    # Registry + hot reload.
    registry = ContractRegistry()
    registry.load_dir(settings.contracts_dir)

    # Static validation pass.
    dups = find_duplicates(registry.list())
    if dups:
        raise RuntimeError(f"duplicate contracts: {dups}")
    for c in registry.list():
        validate_contract(c, known_rules=rule_registry.names(), known_tools=tools.names())

    registry.start_watching()
    app.state.registry = registry

    # LLM + orchestrator.
    llm = get_provider(settings.llm_provider, settings.llm_model)
    app.state.orchestrator = Orchestrator(registry, llm, tools)

    # Database.
    await init_db()

    try:
        yield
    finally:
        registry.stop_watching()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Prompt Contract Architecture",
        version="0.1.0",
        description="Prompts as first-class software artifacts.",
        lifespan=lifespan,
    )

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict:
        return {"status": "ok"}

    # All API routers must be registered BEFORE any static mount, otherwise
    # a Mount("/") will shadow them and they will 404.
    app.include_router(invoke.router)
    app.include_router(contracts.router)
    app.include_router(audit.router)
    app.include_router(docs_gen.router)
    app.include_router(tests_gen.router)
    app.include_router(dev.router)

    # Playground UI: mount /static for assets and serve index.html explicitly
    # at /. We never mount at "/" because Mount("/") swallows API paths.
    if get_settings().dev_mode:
        ui_dir = Path(__file__).parent / "ui"
        if ui_dir.exists():
            static_dir = ui_dir / "static"
            if static_dir.exists():
                app.mount(
                    "/static",
                    StaticFiles(directory=str(static_dir)),
                    name="static",
                )
            index_file = ui_dir / "index.html"
            if index_file.exists():
                @app.get("/", include_in_schema=False)
                async def _index() -> FileResponse:
                    return FileResponse(str(index_file))

    return app


app = create_app()
