import pytest
from httpx import ASGITransport, AsyncClient

from pca.auth import issue_token
from pca.main import create_app


@pytest.mark.asyncio
async def test_invoke_endpoint_e2e() -> None:
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Trigger lifespan startup.
        async with app.router.lifespan_context(app):
            token = issue_token("alice", ["sales_admin"])

            # Healthz
            r = await client.get("/healthz")
            assert r.status_code == 200

            # Invoke
            r = await client.post(
                "/v1/invoke",
                json={"prompt": "Create a customer named John Doe, john@example.com"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["contract_id"] == "customer.create"
            assert body["output"]["customer_id"].startswith("cust_")

            # Listing contracts
            r = await client.get(
                "/v1/contracts", headers={"Authorization": f"Bearer {token}"}
            )
            assert r.status_code == 200
            assert any(c["contract_id"] == "customer.create" for c in r.json())

            # Docs
            r = await client.get("/v1/docs/customer.create")
            assert r.status_code == 200
            assert "customer.create" in r.text

            # Unauthorized invoke
            bad = issue_token("bob", ["nobody"])
            r = await client.post(
                "/v1/invoke",
                json={"prompt": "Create a customer named John, john@example.com"},
                headers={"Authorization": f"Bearer {bad}"},
            )
            assert r.status_code == 403
