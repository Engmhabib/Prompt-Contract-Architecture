import pytest

from pca.test_gen import run_for_contract


@pytest.mark.asyncio
async def test_generated_cases_pass(registry, tools, db) -> None:
    for c in registry.list():
        report = await run_for_contract(c, registry, tools)
        # Every generated case should hit its expected outcome.
        assert report.failed == 0, [
            (o.case.name, o.case.expected, o.actual, o.detail)
            for o in report.outcomes
            if not o.passed
        ]
