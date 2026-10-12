"""The bundled data is an unedited copy of a known fjordvik-data commit."""

import hashlib
import json


def test_bundled_files_match_manifest_checksums(data_dir):
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["emission_factors"] == "illustrative, not for real reporting"
    for info in manifest["tables"].values():
        digest = hashlib.sha256((data_dir / info["file"]).read_bytes()).hexdigest()
        assert digest == info["sha256"], info["file"]


def test_source_commit_is_recorded(data_dir):
    source = json.loads((data_dir / "SOURCE.json").read_text(encoding="utf-8"))
    assert source["source_repository"] == "fjordvik-data"
    assert len(source["commit"]) == 40
