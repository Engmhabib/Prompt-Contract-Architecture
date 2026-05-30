"""Pluggable tool layer.

A Tool is a callable unit exposed to the runtime. The orchestrator only
invokes tools listed in a contract's ``allowed_tools``.
"""

from pca.tools.base import Tool, ToolContext, ToolError, ToolRegistry, default_registry
from pca.tools.customer_db import CustomerDbTool
from pca.tools.email_service import EmailServiceTool
from pca.tools.report_service import ReportServiceTool


def register_builtin_tools(registry: ToolRegistry | None = None) -> ToolRegistry:
    """Register all built-in tools into the given (or default) registry."""
    reg = registry or default_registry()
    reg.register(CustomerDbTool())
    reg.register(EmailServiceTool())
    reg.register(ReportServiceTool())
    return reg


__all__ = [
    "Tool",
    "ToolContext",
    "ToolError",
    "ToolRegistry",
    "default_registry",
    "register_builtin_tools",
    "CustomerDbTool",
    "EmailServiceTool",
    "ReportServiceTool",
]
