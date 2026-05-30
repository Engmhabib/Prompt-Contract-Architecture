from pathlib import Path

import pytest

from pca.contracts.loader import load_contract, parse_filename
from pca.contracts.registry import ContractRegistry
from pca.contracts.validator import find_duplicates, validate_contract


def test_parse_filename(tmp_path: Path) -> None:
    p = tmp_path / "customer.create@1.0.0.yaml"
    p.write_text("")
    assert parse_filename(p) == ("customer.create", "1.0.0")
    assert parse_filename(tmp_path / "bad.yaml") is None


def test_load_and_resolve(contracts_dir: Path) -> None:
    reg = ContractRegistry()
    reg.load_dir(contracts_dir)
    # Both versions of customer.create present
    versions = reg.versions("customer.create")
    assert versions == ["1.0.0", "2.0.0"]
    # Default resolves to latest
    assert reg.resolve("customer.create").version == "2.0.0"
    # Explicit version honored
    assert reg.resolve("customer.create", "1.0.0").version == "1.0.0"


def test_load_fails_on_filename_mismatch(tmp_path: Path) -> None:
    p = tmp_path / "x.create@1.0.0.yaml"
    p.write_text("contract_id: y.create\nversion: 1.0.0\nintent_examples: [a]\n")
    with pytest.raises(ValueError):
        load_contract(p)


def test_validator_catches_unknown_rule(registry) -> None:
    c = registry.resolve("customer.create", "1.0.0")
    with pytest.raises(Exception):
        validate_contract(c, known_rules=set(), known_tools={"customer_db"})


def test_no_duplicates(registry) -> None:
    assert find_duplicates(registry.list()) == []
