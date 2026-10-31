"""The server reads the repository's shared data folder, and that data is unedited."""

import hashlib
import json
from pathlib import Path

from fjordvik_mcp import db

SHARED = Path(__file__).resolve().parents[2] / "data" / "tables"


def test_shared_files_match_manifest_checksums(data_dir):
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["emission_factors"] == "illustrative, not for real reporting"
    for info in manifest["tables"].values():
        digest = hashlib.sha256((data_dir / info["file"]).read_bytes()).hexdigest()
        assert digest == info["sha256"], info["file"]


def test_server_defaults_to_the_shared_data_folder():
    assert db.DEFAULT_DATA_DIR == SHARED
    assert (SHARED / "manifest.json").exists()
