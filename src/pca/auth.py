"""JWT-based authentication and FastAPI dependencies."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt

from pca.config import get_settings


@dataclass
class CurrentUser:
    """The user identity extracted from a JWT."""

    sub: str
    roles: list[str]

    def has_any_role(self, required: list[str]) -> bool:
        if not required:
            return True
        return any(r in self.roles for r in required)


def issue_token(sub: str, roles: list[str]) -> str:
    """Helper to mint a JWT (test/dev only)."""
    settings = get_settings()
    return jwt.encode(
        {"sub": sub, "roles": roles},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> CurrentUser:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing sub")
    roles = payload.get("roles") or []
    if not isinstance(roles, list):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="bad roles claim")
    return CurrentUser(sub=sub, roles=list(roles))


async def get_current_user(
    authorization: str | None = Header(default=None),
) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
        )
    token = authorization.split(" ", 1)[1].strip()
    return decode_token(token)


def require_roles(*roles: str):
    """Dependency factory enforcing a role set."""

    async def _dep(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not user.has_any_role(list(roles)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return user

    return _dep
