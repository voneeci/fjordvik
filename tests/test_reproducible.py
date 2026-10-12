"""The committed files are exactly what the code produces, and the manifest proves it."""

import hashlib
import json

from fjordvik_data.generate import write_all

FILES = ["dim_date.csv", "dim_site.csv", "dim_source.csv",
         "fact_emissions.csv", "fact_site_metrics.csv", "manifest.json"]


def test_regenerating_gives_byte_identical_files(tmp_path, data_dir):
    write_all(tmp_path)
    for name in FILES:
        assert (tmp_path / name).read_bytes() == (data_dir / name).read_bytes(), name


def test_manifest_checksums_and_counts_match_files(data_dir, tables):
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["emission_factors"] == "illustrative, not for real reporting"
    for name, info in manifest["tables"].items():
        path = data_dir / info["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == info["sha256"], name
        assert len(tables[name]) == info["rows"], name
