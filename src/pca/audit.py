"""Audit writer."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pca.db import AuditLog, get_sessionmaker


async def write_audit(
    *,
    user: str,
    intent_prompt: str,
    contract_id: str | None,
    contract_version: str | None,
    tool_calls: list[dict[str, Any]],
    result: dict[str, Any] | None,
    status: str,
    error: str | None = None,
) -> int:
    sm = get_sessionmaker()
    async with sm() as session, session.begin():
        entry = AuditLog(
            timestamp=datetime.utcnow(),
            user=user,
            intent_prompt=intent_prompt,
            contract_id=contract_id,
            contract_version=contract_version,
            tool_calls=tool_calls,
            result=result or {},
            status=status,
            error=error,
        )
        session.add(entry)
        await session.flush()
        return entry.id
