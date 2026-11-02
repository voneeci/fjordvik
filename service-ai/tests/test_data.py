"""The service AI reads the repository's shared data folder, and that data is unedited."""

import hashlib
import json

import fjordvik_service


def test_shared_files_match_manifest_checksums(data_dir):
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["emission_factors"] == "illustrative, not for real reporting"
    for info in manifest["tables"].values():
        digest = hashlib.sha256((data_dir / info["file"]).read_bytes()).hexdigest()
        assert digest == info["sha256"], info["file"]


def test_service_ai_reads_the_shared_data_folder(data_dir):
    assert fjordvik_service.DEFAULT_DATA_DIR == data_dir
    assert (data_dir / "fact_asset_telemetry.csv").exists()
