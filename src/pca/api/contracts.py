"""/v1/contracts — list, get, CRUD over the registry.

Writes are gated by the ``admin`` role AND the ``PCA_ALLOW_WRITES`` flag.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from pca.auth import CurrentUser, get_current_user, require_roles
from pca.config import get_settings
from pca.contracts.schema import Contract

router = APIRouter(prefix="/v1/contracts", tags=["contracts"])


@router.get("")
async def list_contracts(request: Request) -> list[dict]:
    reg = request.app.state.registry
    return [c.model_dump() for c in reg.list()]


@router.get("/{contract_id}")
async def get_contract(
    contract_id: str,
    request: Request,
    version: str | None = None,
) -> dict:
    reg = request.app.state.registry
    try:
        return reg.resolve(contract_id, version).model_dump()
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


def _writes_allowed(user: CurrentUser) -> None:
    if not get_settings().allow_writes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="writes disabled"
        )
    if "admin" not in user.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin only")


@router.post("", status_code=201)
async def create_contract(
    body: Contract,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    _writes_allowed(user)
    reg = request.app.state.registry
    if (body.contract_id, body.version) in {(c.contract_id, c.version) for c in reg.list()}:
        raise HTTPException(status_code=409, detail="contract already exists")
    path = _contract_path(body)
    path.write_text(yaml.safe_dump(body.model_dump(mode="json"), sort_keys=False))
    reg.reload()
    return body.model_dump()


@router.put("/{contract_id}")
async def update_contract(
    contract_id: str,
    body: Contract,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    _writes_allowed(user)
    if body.contract_id != contract_id:
        raise HTTPException(status_code=400, detail="contract_id mismatch")
    reg = request.app.state.registry
    path = _contract_path(body)
    if not path.exists():
        raise HTTPException(status_code=404, detail="contract not found")
    path.write_text(yaml.safe_dump(body.model_dump(mode="json"), sort_keys=False))
    reg.reload()
    return body.model_dump()


@router.delete(
    "/{contract_id}",
    status_code=204,
    response_class=Response,
    dependencies=[Depends(require_roles("admin"))],
)
async def delete_contract(
    contract_id: str,
    version: str,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    _writes_allowed(user)
    settings = get_settings()
    path = settings.contracts_dir / f"{contract_id}@{version}.yaml"
    if not path.exists():
        raise HTTPException(status_code=404, detail="contract not found")
    path.unlink()
    request.app.state.registry.reload()
    return Response(status_code=204)


def _contract_path(contract: Contract) -> Path:
    settings = get_settings()
    settings.contracts_dir.mkdir(parents=True, exist_ok=True)
    return settings.contracts_dir / f"{contract.contract_id}@{contract.version}.yaml"
