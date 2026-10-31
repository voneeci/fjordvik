"""The model reads the repository's shared data folder, and that data is unedited."""

import hashlib
import json
import re
from pathlib import Path

EXPRESSIONS = (Path(__file__).resolve().parents[1] / "FjordvikEmissions.SemanticModel"
               / "definition" / "expressions.tmdl")


def test_shared_files_match_manifest_checksums(data_dir):
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["emission_factors"] == "illustrative, not for real reporting"
    for info in manifest["tables"].values():
        digest = hashlib.sha256((data_dir / info["file"]).read_bytes()).hexdigest()
        assert digest == info["sha256"], info["file"]


def test_data_folder_parameter_points_at_the_shared_folder():
    text = EXPRESSIONS.read_text(encoding="utf-8")
    folder = re.search(r'expression DataFolder = "([^"]+)"', text).group(1)
    assert folder.endswith(r"\data\tables"), folder
