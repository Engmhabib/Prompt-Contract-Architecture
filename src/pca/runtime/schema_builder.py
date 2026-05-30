"""Build dynamic Pydantic models from a contract's input/output schema."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, EmailStr, Field, create_model

from pca.contracts.schema import Contract, FieldSpec

_PYTHON_TYPES: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "object": dict,
    "array": list,
}


def _field_type(spec: FieldSpec) -> type:
    return _PYTHON_TYPES.get(spec.type, str)


def build_input_model(contract: Contract) -> type[BaseModel]:
    fields: dict[str, tuple[type, Any]] = {}
    for name, spec in contract.input_schema.items():
        py_t = _field_type(spec)
        # email rule? still keep type as str; rules engine handles semantics
        if spec.required:
            default = ...
        else:
            default = spec.default
        fields[name] = (py_t if spec.required else (py_t | None), Field(default))
    model_name = f"{contract.contract_id.replace('.', '_').title()}Input"
    return create_model(model_name, **fields)  # type: ignore[call-overload]


def build_output_model(contract: Contract) -> type[BaseModel]:
    fields: dict[str, tuple[type, Any]] = {}
    for name, spec in contract.output_schema.items():
        py_t = _field_type(spec)
        fields[name] = (py_t | None, Field(default=None))
    model_name = f"{contract.contract_id.replace('.', '_').title()}Output"
    return create_model(model_name, **fields)  # type: ignore[call-overload]
