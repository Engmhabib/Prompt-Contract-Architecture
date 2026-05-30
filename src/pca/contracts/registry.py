"""In-memory contract registry with semver resolution and hot reload."""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import semver
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from pca.contracts.loader import load_contract, parse_filename
from pca.contracts.schema import Contract

logger = logging.getLogger(__name__)


class ContractRegistry:
    """Thread-safe registry keyed by ``(contract_id, version)``."""

    def __init__(self, contracts_dir: Path | None = None) -> None:
        self._contracts: dict[tuple[str, str], Contract] = {}
        self._lock = threading.RLock()
        self._dir = contracts_dir
        self._observer: Observer | None = None

    # ----- loading -----
    def load_dir(self, directory: Path) -> None:
        """Load all contract YAMLs from a directory (replaces in-memory state)."""
        self._dir = directory
        with self._lock:
            self._contracts.clear()
            if not directory.exists():
                logger.warning("contracts directory does not exist: %s", directory)
                return
            for path in sorted(directory.glob("*.y*ml")):
                if parse_filename(path) is None:
                    logger.warning("skipping unrecognized filename: %s", path.name)
                    continue
                try:
                    contract = load_contract(path)
                    self.register(contract)
                except Exception:  # pragma: no cover - logged for visibility
                    logger.exception("failed to load contract: %s", path)

    def register(self, contract: Contract) -> None:
        with self._lock:
            self._contracts[(contract.contract_id, contract.version)] = contract

    def remove(self, contract_id: str, version: str) -> None:
        with self._lock:
            self._contracts.pop((contract_id, version), None)

    # ----- access -----
    def list(self) -> list[Contract]:
        with self._lock:
            return list(self._contracts.values())

    def list_ids(self) -> list[str]:
        with self._lock:
            return sorted({cid for cid, _ in self._contracts})

    def versions(self, contract_id: str) -> list[str]:
        with self._lock:
            return sorted(
                (v for cid, v in self._contracts if cid == contract_id),
                key=semver.Version.parse,
            )

    def resolve(self, contract_id: str, version: str | None = None) -> Contract:
        """Resolve a contract by id; if ``version`` is None, return latest semver."""
        with self._lock:
            if version is not None:
                key = (contract_id, version)
                if key not in self._contracts:
                    raise KeyError(f"contract not found: {contract_id}@{version}")
                return self._contracts[key]
            versions = [v for cid, v in self._contracts if cid == contract_id]
            if not versions:
                raise KeyError(f"contract not found: {contract_id}")
            latest = max(versions, key=semver.Version.parse)
            return self._contracts[(contract_id, latest)]

    def grouped(self) -> dict[str, list[Contract]]:
        """Return contracts grouped by ``contract_id``."""
        out: dict[str, list[Contract]] = defaultdict(list)
        with self._lock:
            for c in self._contracts.values():
                out[c.contract_id].append(c)
        for v in out.values():
            v.sort(key=lambda c: semver.Version.parse(c.version))
        return dict(out)

    # ----- hot reload -----
    def start_watching(self) -> None:
        """Start a watchdog observer that reloads on YAML changes."""
        if self._dir is None or self._observer is not None:
            return
        handler = _ReloadHandler(self)
        observer = Observer()
        observer.schedule(handler, str(self._dir), recursive=False)
        observer.daemon = True
        observer.start()
        self._observer = observer
        logger.info("watching contracts dir: %s", self._dir)

    def stop_watching(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._observer = None

    def reload(self) -> None:
        if self._dir is not None:
            self.load_dir(self._dir)

    # ----- iteration -----
    def __iter__(self) -> Iterable[Contract]:
        return iter(self.list())

    def __len__(self) -> int:
        with self._lock:
            return len(self._contracts)


class _ReloadHandler(FileSystemEventHandler):
    def __init__(self, registry: ContractRegistry) -> None:
        self._registry = registry

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() in {".yml", ".yaml"}:
            logger.info("contract change detected: %s — reloading", path.name)
            try:
                self._registry.reload()
            except Exception:  # pragma: no cover
                logger.exception("reload failed")
