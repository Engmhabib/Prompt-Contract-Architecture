"""PCA command-line interface."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from pca.config import get_settings
from pca.contracts.registry import ContractRegistry
from pca.contracts.validator import find_duplicates, validate_contract
from pca.docs_gen import contract_to_markdown, registry_index_markdown
from pca.runtime.rules import rule_registry
from pca.test_gen import run_for_contract
from pca.tools import register_builtin_tools


def _registry() -> ContractRegistry:
    reg = ContractRegistry()
    reg.load_dir(get_settings().contracts_dir)
    return reg


def cmd_validate() -> int:
    reg = _registry()
    tools = register_builtin_tools()
    dups = find_duplicates(reg.list())
    if dups:
        print(f"ERROR: duplicate contracts: {dups}")
        return 1
    for c in reg.list():
        try:
            validate_contract(c, known_rules=rule_registry.names(), known_tools=tools.names())
            print(f"ok   {c.key}")
        except Exception as e:
            print(f"FAIL {c.key}: {e}")
            return 1
    return 0


def cmd_docs(out: Path) -> int:
    reg = _registry()
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.md").write_text(registry_index_markdown(reg.list()))
    for c in reg.list():
        (out / f"{c.contract_id}@{c.version}.md").write_text(contract_to_markdown(c))
    print(f"wrote {len(reg.list()) + 1} files to {out}")
    return 0


def cmd_test() -> int:
    reg = _registry()
    tools = register_builtin_tools()

    async def _run() -> int:
        # ensure DB is initialized (sqlite default)
        from pca.db import init_db

        await init_db()
        total = passed = 0
        for c in reg.list():
            report = await run_for_contract(c, reg, tools)
            total += report.total
            passed += report.passed
            mark = "OK" if report.failed == 0 else "FAIL"
            print(f"[{mark}] {c.key}: {report.passed}/{report.total}")
            for o in report.outcomes:
                if not o.passed:
                    print(f"   - {o.case.name}: expected {o.case.expected}, got {o.actual}")
        print(f"\n{passed}/{total} cases passed")
        return 0 if passed == total else 1

    return asyncio.run(_run())


def main() -> None:
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print("Usage: pca {validate|docs <out>|test}")
        sys.exit(0)
    cmd = argv[0]
    if cmd == "validate":
        sys.exit(cmd_validate())
    if cmd == "docs":
        out = Path(argv[1]) if len(argv) > 1 else Path("./mkdocs/docs/contracts")
        sys.exit(cmd_docs(out))
    if cmd == "test":
        sys.exit(cmd_test())
    print(f"unknown command: {cmd}")
    sys.exit(2)


if __name__ == "__main__":
    main()
