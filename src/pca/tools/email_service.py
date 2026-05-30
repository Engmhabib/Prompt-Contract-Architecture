"""Mock email tool — logs delivery for demo purposes."""

from __future__ import annotations

import logging
from typing import Any

from pca.tools.base import ToolContext

logger = logging.getLogger(__name__)


class EmailServiceTool:
    name = "email_service"

    async def run(self, payload: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
        to = payload.get("to")
        subject = payload.get("subject", "")
        body = payload.get("body", "")
        logger.info("[email_service] -> %s | %s", to, subject)
        return {"sent": True, "to": to, "subject": subject, "body_len": len(body)}
