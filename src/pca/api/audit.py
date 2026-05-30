"""/v1/audit — paginated audit log listing."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select

from pca.auth import CurrentUser, require_roles
from pca.db import AuditLog, get_sessionmaker

router = APIRouter(prefix="/v1/audit", tags=["audit"])


@router.get("", dependencies=[Depends(require_roles("admin", "auditor"))])
async def list_audit(
    user: str | None = None,
    contract_id: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    sm = get_sessionmaker()
    stmt = select(AuditLog).order_by(desc(AuditLog.timestamp)).limit(limit).offset(offset)
    if user:
        stmt = stmt.where(AuditLog.user == user)
    if contract_id:
        stmt = stmt.where(AuditLog.contract_id == contract_id)
    async with sm() as session:
        rows = (await session.execute(stmt)).scalars().all()
        return [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "user": r.user,
                "intent_prompt": r.intent_prompt,
                "contract_id": r.contract_id,
                "contract_version": r.contract_version,
                "tool_calls": r.tool_calls,
                "result": r.result,
                "status": r.status,
                "error": r.error,
            }
            for r in rows
        ]
