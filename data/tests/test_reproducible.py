"""The committed files are exactly what the code produces, and the manifest proves it."""

import hashlib
import json

from fjordvik_data.generate import COLUMNS, write_all

FILES = [f"{name}.csv" for name in COLUMNS] + ["manifest.json"]


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


def test_value_chain_change_left_the_original_tables_unchanged(data_dir):
    """Adding the value-chain tables (31 October 2026) must not move any reported
    figure: these four files keep the checksums they had at commit 43ca8da."""
    before = {
        "dim_date.csv": "ad3e1ac9325c691e43bde6c0734bc3c0f529be789a549d115fea0027e532397d",
        "dim_site.csv": "a2573541e5cb89e239bd6fd6a21f157d7cd982e933d0eb6674334c7719d288c2",
        "fact_emissions.csv": "4a1d16b1fbd00afe3beed92489466f43e592cd56732c79537136cad031ceed56",
        "fact_site_metrics.csv": "b8d42f7af1259eafbe3884b9bb296eee3a213353bafaec04f93567c391c4c22e",
    }
    for name, digest in before.items():
        assert hashlib.sha256((data_dir / name).read_bytes()).hexdigest() == digest, name
