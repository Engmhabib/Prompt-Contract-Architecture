"""/v1/tests — run the in-memory test suite for a contract."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from pca.auth import CurrentUser, require_roles
from pca.test_gen import run_for_contract

router = APIRouter(prefix="/v1/tests", tags=["tests"])


@router.post("/run/{contract_id}", dependencies=[Depends(require_roles("admin", "developer"))])
async def run(contract_id: str, request: Request, version: str | None = None) -> dict:
    reg = request.app.state.registry
    try:
        contract = reg.resolve(contract_id, version)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    tools = request.app.state.tools
    report = await run_for_contract(contract, reg, tools)
    return report.to_dict()
