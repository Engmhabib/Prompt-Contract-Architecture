"""Typed runtime errors."""

from __future__ import annotations


class PCAError(Exception):
    """Base PCA runtime error."""


class ClassificationError(PCAError):
    """Raised when no contract could be selected for a prompt."""


class AuthzError(PCAError):
    """Raised when the caller lacks required permissions."""


class ValidationError(PCAError):
    """Raised when inputs fail schema or rule validation."""

    def __init__(self, message: str, errors: list[dict] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []


class ToolNotAllowedError(PCAError):
    """Raised when a tool is invoked that the contract does not allow."""
