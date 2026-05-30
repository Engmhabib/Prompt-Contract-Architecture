import time
from pathlib import Path

from pca.contracts.registry import ContractRegistry


def test_hot_reload(tmp_path: Path) -> None:
    src = tmp_path / "x.test@1.0.0.yaml"
    src.write_text(
        "contract_id: x.test\nversion: 1.0.0\nintent_examples: [hi]\n"
    )
    reg = ContractRegistry()
    reg.load_dir(tmp_path)
    assert reg.resolve("x.test").version == "1.0.0"

    reg.start_watching()
    try:
        # Add a new version on disk and trigger reload manually for determinism.
        (tmp_path / "x.test@2.0.0.yaml").write_text(
            "contract_id: x.test\nversion: 2.0.0\nintent_examples: [hi]\n"
        )
        reg.reload()
        assert reg.resolve("x.test").version == "2.0.0"
    finally:
        reg.stop_watching()
