"""/v1/docs — contract documentation."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from pca.docs_gen import contract_to_markdown, registry_index_markdown

router = APIRouter(prefix="/v1/docs", tags=["docs"])


@router.get("", response_class=PlainTextResponse)
async def index(request: Request) -> str:
    return registry_index_markdown(request.app.state.registry.list())


@router.get("/{contract_id}", response_class=PlainTextResponse)
async def one(contract_id: str, request: Request, version: str | None = None) -> str:
    try:
        c = request.app.state.registry.resolve(contract_id, version)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return contract_to_markdown(c)
