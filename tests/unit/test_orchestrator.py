import pytest

from pca.auth import CurrentUser
from pca.runtime.errors import AuthzError, ValidationError


@pytest.mark.asyncio
async def test_invoke_happy_path(orchestrator, db) -> None:
    user = CurrentUser(sub="alice", roles=["sales_admin"])
    res = await orchestrator.invoke(
        prompt="Create a customer named John Doe, john@example.com",
        user=user,
    )
    assert res.contract_id == "customer.create"
    assert res.output["customer_id"].startswith("cust_")
    assert res.audit_id is not None


@pytest.mark.asyncio
async def test_invoke_unauthorized(orchestrator, db) -> None:
    user = CurrentUser(sub="bob", roles=["nobody"])
    with pytest.raises(AuthzError):
        await orchestrator.invoke(
            prompt="Create a customer named John, john@example.com",
            user=user,
        )


@pytest.mark.asyncio
async def test_invoke_invalid_email(orchestrator, db) -> None:
    user = CurrentUser(sub="alice", roles=["sales_admin"])
    # Mock extractor latches onto "named X" + email regex; supply bad email.
    with pytest.raises(ValidationError):
        await orchestrator.invoke(
            prompt="Create a customer named Jane, email = not-an-email",
            user=user,
            hint="customer.create@1.0.0",
        )


@pytest.mark.asyncio
async def test_invoke_explicit_version(orchestrator, db) -> None:
    user = CurrentUser(sub="alice", roles=["sales_admin"])
    res = await orchestrator.invoke(
        prompt="Create a customer named Alice, alice@example.com",
        user=user,
        hint="customer.create@1.0.0",
    )
    assert res.contract_version == "1.0.0"


@pytest.mark.asyncio
async def test_report_contract(orchestrator, db) -> None:
    user = CurrentUser(sub="alice", roles=["analyst"])
    res = await orchestrator.invoke(
        prompt="Generate a summary report with 100 rows",
        user=user,
    )
    assert res.contract_id == "report.generate"
    assert res.output["url"].startswith("https://")
