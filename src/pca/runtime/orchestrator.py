"""PCA orchestrator: the 9-step pipeline that turns a prompt into a structured result."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from pca.audit import write_audit
from pca.auth import CurrentUser
from pca.contracts.registry import ContractRegistry
from pca.contracts.schema import Contract
from pca.llm.base import LLMProvider
from pca.runtime.classifier import IntentClassifier
from pca.runtime.errors import (
    AuthzError,
    PCAError,
    ToolNotAllowedError,
    ValidationError,
)
from pca.runtime.rules import RuleContext, rule_registry
from pca.runtime.schema_builder import build_input_model, build_output_model
from pca.tools.base import ToolContext, ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class InvocationResult:
    contract_id: str
    contract_version: str
    inputs: dict[str, Any]
    output: dict[str, Any]
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    audit_id: int | None = None


class Orchestrator:
    """The PCA runtime."""

    def __init__(
        self,
        registry: ContractRegistry,
        llm: LLMProvider,
        tools: ToolRegistry,
    ) -> None:
        self._registry = registry
        self._llm = llm
        self._tools = tools
        self._classifier = IntentClassifier(llm, registry)

    # ---------------------------------------------------------------------
    async def invoke(
        self,
        *,
        prompt: str,
        user: CurrentUser,
        hint: str | None = None,
    ) -> InvocationResult:
        """Execute the full pipeline. Always emits an audit log."""
        contract: Contract | None = None
        tool_calls: list[dict[str, Any]] = []
        try:
            # 1. Classify intent → contract_id (+ optional explicit @version).
            cid_token = await self._classifier.classify(prompt, hint=hint)
            contract_id, version = _split_id_version(cid_token)

            # 2. Resolve contract.
            contract = self._registry.resolve(contract_id, version)

            # 3. Check permissions.
            if contract.permissions and not user.has_any_role(contract.permissions):
                raise AuthzError(
                    f"user {user.sub} lacks any of {contract.permissions}"
                )

            # 4. Extract inputs (LLM).
            raw_inputs = await self._llm.extract(
                prompt,
                {k: v.model_dump() for k, v in contract.input_schema.items()},
            )

            # 5. Validate against dynamic Pydantic schema.
            InputModel = build_input_model(contract)
            try:
                validated = InputModel.model_validate(raw_inputs)
            except PydanticValidationError as e:
                errs = [
                    {"field": ".".join(str(x) for x in err["loc"]), "message": err["msg"]}
                    for err in e.errors()
                ]
                raise ValidationError("input schema validation failed", errs) from e

            inputs = validated.model_dump()

            # 6. Run pluggable validation rules.
            rule_ctx = RuleContext(user_sub=user.sub, contract_id=contract.contract_id)
            for rname in contract.validation_rules:
                fn = rule_registry.get(rname)
                await fn(inputs, rule_ctx)

            # 7. Invoke tools — only those explicitly allowed.
            output = await self._dispatch(contract, inputs, user, tool_calls)

            # 8. Shape output via output_schema (drops unknown keys).
            OutputModel = build_output_model(contract)
            shaped = OutputModel.model_validate(output).model_dump(exclude_none=False)

            # 9. Audit.
            audit_id = await write_audit(
                user=user.sub,
                intent_prompt=prompt,
                contract_id=contract.contract_id,
                contract_version=contract.version,
                tool_calls=tool_calls,
                result=shaped,
                status="ok",
            )
            return InvocationResult(
                contract_id=contract.contract_id,
                contract_version=contract.version,
                inputs=inputs,
                output=shaped,
                tool_calls=tool_calls,
                audit_id=audit_id,
            )

        except PCAError as e:
            await write_audit(
                user=user.sub,
                intent_prompt=prompt,
                contract_id=contract.contract_id if contract else None,
                contract_version=contract.version if contract else None,
                tool_calls=tool_calls,
                result=None,
                status=type(e).__name__,
                error=str(e),
            )
            raise

    # ---------------------------------------------------------------------
    async def _dispatch(
        self,
        contract: Contract,
        inputs: dict[str, Any],
        user: CurrentUser,
        tool_calls: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Default dispatch: invoke the first allowed tool with the inputs.

        For MVP the contract → tool mapping is implicit: the first entry in
        ``allowed_tools`` receives the validated inputs. Specialized contracts
        can override this in future versions via an explicit ``workflow`` block.
        """
        if not contract.allowed_tools:
            return {}

        tool_name = contract.allowed_tools[0]
        if tool_name not in self._tools.names():
            raise ToolNotAllowedError(f"tool not registered: {tool_name}")

        tool = self._tools.get(tool_name)
        payload = _build_tool_payload(contract, inputs)
        ctx = ToolContext(
            user_sub=user.sub,
            contract_id=contract.contract_id,
            contract_version=contract.version,
        )
        result = await tool.run(payload, ctx)
        tool_calls.append({"tool": tool_name, "payload": payload, "result": result})
        return result


def _split_id_version(token: str) -> tuple[str, str | None]:
    if "@" in token:
        cid, ver = token.split("@", 1)
        return cid, ver
    return token, None


def _build_tool_payload(contract: Contract, inputs: dict[str, Any]) -> dict[str, Any]:
    """Build the payload for the first allowed tool.

    For ``customer_db`` we pass an explicit ``action=create`` and forward the
    relevant input fields. For other tools we forward inputs verbatim.
    """
    if contract.allowed_tools[0] == "customer_db" and "create" in contract.contract_id:
        return {"action": "create", **inputs}
    return dict(inputs)
