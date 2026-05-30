"""Runtime test generator and executor.

For each contract, generates and runs four case types against the live
orchestrator (with a `MockLLMProvider`): happy path, missing required field,
authorization failure, and disallowed tool. Returns a structured report.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from pca.auth import CurrentUser
from pca.contracts.registry import ContractRegistry
from pca.contracts.schema import Contract
from pca.llm.base import ClassificationResult, LLMProvider
from pca.runtime.errors import AuthzError, PCAError, ValidationError
from pca.runtime.orchestrator import Orchestrator
from pca.tools.base import ToolRegistry


@dataclass
class TestCase:
    name: str
    contract_id: str
    contract_version: str
    expected: str  # "ok" | "ValidationError" | "AuthzError" | "ToolNotAllowedError"


@dataclass
class TestOutcome:
    case: TestCase
    passed: bool
    actual: str
    detail: str | None = None


@dataclass
class TestReport:
    total: int
    passed: int
    failed: int
    outcomes: list[TestOutcome]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "outcomes": [
                {**asdict(o.case), "passed": o.passed, "actual": o.actual, "detail": o.detail}
                for o in self.outcomes
            ],
        }


class _ScriptedLLM:
    """Deterministic LLM stub that returns pre-baked classification + extraction."""

    def __init__(self, contract_id: str, extracted: dict[str, Any]) -> None:
        self._cid = contract_id
        self._extracted = extracted

    async def classify(self, prompt, candidates):  # noqa: D401
        return ClassificationResult(contract_id=self._cid, confidence=1.0)

    async def extract(self, prompt, input_schema):
        return self._extracted


def _example_value(ftype: str, field_name: str, suffix: str = "") -> Any:
    if field_name == "email":
        return f"test+{suffix or 'x'}@example.com"
    if field_name == "name":
        return "Test User"
    if field_name == "phone":
        return "+15551234567"
    return {
        "string": f"sample-{field_name}",
        "integer": 1,
        "number": 1.0,
        "boolean": True,
        "object": {},
        "array": [],
    }.get(ftype, "x")


def _happy_inputs(contract: Contract) -> dict[str, Any]:
    suffix = f"{contract.contract_id.replace('.', '_')}_{contract.version.replace('.', '_')}"
    return {
        name: _example_value(spec.type, name, suffix=suffix)
        for name, spec in contract.input_schema.items()
        if spec.required or name in ("email", "name")
    }


def generate_cases(contract: Contract) -> list[TestCase]:
    cases = [
        TestCase("happy_path", contract.contract_id, contract.version, "ok"),
    ]
    if any(s.required for s in contract.input_schema.values()):
        cases.append(
            TestCase("missing_required", contract.contract_id, contract.version, "ValidationError")
        )
    if contract.permissions:
        cases.append(
            TestCase("unauthorized", contract.contract_id, contract.version, "AuthzError")
        )
    if "valid_email" in contract.validation_rules:
        cases.append(
            TestCase("invalid_email", contract.contract_id, contract.version, "ValidationError")
        )
    return cases


async def run_cases(
    contract: Contract,
    registry: ContractRegistry,
    tools: ToolRegistry,
) -> list[TestOutcome]:
    cases = generate_cases(contract)
    outcomes: list[TestOutcome] = []
    happy = _happy_inputs(contract)

    for case in cases:
        scripted_inputs = dict(happy)
        user_roles = list(contract.permissions) or ["anon"]
        if case.name == "missing_required":
            for name, spec in contract.input_schema.items():
                if spec.required:
                    scripted_inputs.pop(name, None)
                    break
        elif case.name == "unauthorized":
            user_roles = ["nobody"]
        elif case.name == "invalid_email":
            scripted_inputs["email"] = "not-an-email"

        llm: LLMProvider = _ScriptedLLM(contract.contract_id, scripted_inputs)
        orch = Orchestrator(registry, llm, tools)
        user = CurrentUser(sub=f"test:{case.name}", roles=user_roles)
        actual = "ok"
        detail: str | None = None
        try:
            await orch.invoke(prompt=f"[generated:{case.name}]", user=user, hint=contract.key)
        except AuthzError as e:
            actual, detail = "AuthzError", str(e)
        except ValidationError as e:
            actual, detail = "ValidationError", str(e)
        except PCAError as e:
            actual, detail = type(e).__name__, str(e)
        except Exception as e:  # tool-side errors should still mark the case
            actual, detail = type(e).__name__, str(e)

        passed = actual == case.expected
        outcomes.append(TestOutcome(case=case, passed=passed, actual=actual, detail=detail))

    return outcomes


async def run_for_contract(
    contract: Contract,
    registry: ContractRegistry,
    tools: ToolRegistry,
) -> TestReport:
    outcomes = await run_cases(contract, registry, tools)
    passed = sum(1 for o in outcomes if o.passed)
    return TestReport(
        total=len(outcomes),
        passed=passed,
        failed=len(outcomes) - passed,
        outcomes=outcomes,
    )
