"""Dev-only convenience endpoints (token minting).

Disabled unless ``PCA_DEV_MODE=true``.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pca.auth import issue_token
from pca.config import get_settings

router = APIRouter(prefix="/v1/dev", tags=["dev"])


class TokenRequest(BaseModel):
    sub: str = "demo-user"
    roles: list[str] = ["sales_admin"]


class TokenResponse(BaseModel):
    token: str
    sub: str
    roles: list[str]


def _guard() -> None:
    if not get_settings().dev_mode:
        raise HTTPException(status_code=404, detail="not found")


@router.post("/token", response_model=TokenResponse)
async def mint_token(body: TokenRequest) -> TokenResponse:
    """Mint a JWT for the given subject/roles. Dev only."""
    _guard()
    return TokenResponse(
        token=issue_token(body.sub, body.roles),
        sub=body.sub,
        roles=body.roles,
    )
