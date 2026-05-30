"""Customer database tool backed by SQLAlchemy."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from pca.db import Customer, get_sessionmaker
from pca.tools.base import Tool, ToolContext, ToolError


class CustomerDbTool:
    """CRUD-ish operations on the ``customers`` table.

    Supported actions: ``create``, ``get``, ``exists_email``.
    """

    name = "customer_db"

    async def run(self, payload: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
        action = payload.get("action", "create")
        sm = get_sessionmaker()

        if action == "create":
            name = payload.get("name")
            email = payload.get("email")
            phone = payload.get("phone")
            if not name or not email:
                raise ToolError("customer_db.create requires name and email")
            customer_id = f"cust_{uuid.uuid4().hex[:12]}"
            async with sm() as session, session.begin():
                session.add(Customer(id=customer_id, name=name, email=email, phone=phone))
            return {"customer_id": customer_id, "name": name, "email": email}

        if action == "get":
            cid = payload.get("id")
            async with sm() as session:
                obj = await session.get(Customer, cid)
                if obj is None:
                    raise ToolError(f"customer not found: {cid}")
                return {"id": obj.id, "name": obj.name, "email": obj.email}

        if action == "exists_email":
            email = payload.get("email")
            async with sm() as session:
                stmt = select(Customer.id).where(Customer.email == email)
                row = (await session.execute(stmt)).first()
                return {"exists": row is not None}

        raise ToolError(f"unsupported action: {action}")


__all__ = ["CustomerDbTool"]
