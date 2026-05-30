"""Canonical Pydantic model for a Prompt Contract.

A contract is the single source of truth for an intent: its inputs, validation
rules, permissions, allowed tools, and output shape.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


PRIMITIVE_TYPES = {"string", "integer", "number", "boolean", "object", "array"}


class FieldSpec(BaseModel):
    """Specification of a single input or output field."""

    model_config = ConfigDict(extra="forbid")

    type: str
    required: bool = False
    description: str | None = None
    enum: list[Any] | None = None
    default: Any | None = None

    @field_validator("type")
    @classmethod
    def _validate_type(cls, v: str) -> str:
        if v not in PRIMITIVE_TYPES:
            raise ValueError(f"unsupported field type: {v!r}")
        return v


class Contract(BaseModel):
    """A Prompt Contract."""

    model_config = ConfigDict(extra="forbid")

    contract_id: str = Field(..., pattern=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    description: str = ""
    intent_examples: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    input_schema: dict[str, FieldSpec] = Field(default_factory=dict)
    validation_rules: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    output_schema: dict[str, FieldSpec] = Field(default_factory=dict)

    @property
    def key(self) -> str:
        """Unique key combining id and version: ``customer.create@1.0.0``."""
        return f"{self.contract_id}@{self.version}"

    @field_validator("input_schema", "output_schema", mode="before")
    @classmethod
    def _coerce_field_specs(cls, value: Any) -> Any:
        """Allow shorthand: ``name: {type: string, required: true}``."""
        if not isinstance(value, dict):
            return value
        coerced: dict[str, Any] = {}
        for name, spec in value.items():
            if isinstance(spec, str):
                coerced[name] = {"type": spec}
            else:
                coerced[name] = spec
        return coerced
