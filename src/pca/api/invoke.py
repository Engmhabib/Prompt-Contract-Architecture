"""POST /v1/invoke — the main runtime entrypoint."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from pca.auth import CurrentUser, get_current_user
from pca.runtime.errors import (
    AuthzError,
    ClassificationError,
    PCAError,
    ToolNotAllowedError,
    ValidationError,
)

router = APIRouter(prefix="/v1", tags=["invoke"])


class InvokeRequest(BaseModel):
    prompt: str
    hint: str | None = None  # explicit contract_id or contract_id@version


class InvokeResponse(BaseModel):
    contract_id: str
    contract_version: str
    inputs: dict[str, Any]
    output: dict[str, Any]
    tool_calls: list[dict[str, Any]]
    audit_id: int | None


@router.post("/invoke", response_model=InvokeResponse)
async def invoke(
    body: InvokeRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> InvokeResponse:
    orch = request.app.state.orchestrator
    try:
        result = await orch.invoke(prompt=body.prompt, user=user, hint=body.hint)
    except AuthzError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(e), "errors": e.errors},
        ) from e
    except ClassificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except ToolNotAllowedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(e)
        ) from e
    except PCAError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return InvokeResponse(
        contract_id=result.contract_id,
        contract_version=result.contract_version,
        inputs=result.inputs,
        output=result.output,
        tool_calls=result.tool_calls,
        audit_id=result.audit_id,
    )
