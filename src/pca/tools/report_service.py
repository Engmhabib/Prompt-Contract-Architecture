"""Mock report generation tool."""

from __future__ import annotations

import uuid
from typing import Any

from pca.tools.base import ToolContext


class ReportServiceTool:
    name = "report_service"

    async def run(self, payload: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
        report_id = f"rpt_{uuid.uuid4().hex[:10]}"
        return {
            "report_id": report_id,
            "kind": payload.get("kind", "summary"),
            "rows": payload.get("rows", 0),
            "url": f"https://reports.example.com/{report_id}",
        }
