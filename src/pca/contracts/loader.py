"""Load YAML contract files from disk."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from pca.contracts.schema import Contract

# Matches: customer.create@1.0.0.yaml
_FILENAME_RE = re.compile(
    r"^(?P<id>[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*)@(?P<version>\d+\.\d+\.\d+)\.ya?ml$"
)


def parse_filename(path: Path) -> tuple[str, str] | None:
    """Parse a contract filename. Returns ``(contract_id, version)`` or None."""
    m = _FILENAME_RE.match(path.name)
    if not m:
        return None
    return m.group("id"), m.group("version")


def load_contract(path: Path) -> Contract:
    """Load a single YAML contract file.

    The ``contract_id`` and ``version`` are derived from the filename if
    not present in the YAML body, and verified to match if they are.
    """
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"contract file must be a YAML mapping: {path}")

    parsed = parse_filename(path)
    if parsed is not None:
        file_id, file_version = parsed
        raw.setdefault("contract_id", file_id)
        raw.setdefault("version", file_version)
        if raw["contract_id"] != file_id or raw["version"] != file_version:
            raise ValueError(
                f"filename {path.name} does not match contract "
                f"{raw['contract_id']}@{raw['version']}"
            )

    return Contract.model_validate(raw)
