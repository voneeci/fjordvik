"""The committed files are exactly what the code produces, and the manifest proves it."""

import csv
import hashlib
import json

import shutil
from pathlib import Path

from fjordvik_data.generate import COLUMNS, REFERENCE_COLUMNS, write_all

FILES = [f"{name}.csv" for name in COLUMNS] + ["manifest.json"]
# Outputs written beside tables/: the simulated ERP extract, the service documents
# and the failure answer key (the last two added 2 November 2026).
OUTPUT_FOLDERS = ["erp-extract", "corpus", "generator-truth"]


def test_regenerating_gives_byte_identical_files(tmp_path, data_dir):
    """Tables, the simulated ERP extract, the service documents, the answer key and
    the reference lists the generator writes."""
    shutil.copytree(data_dir.parent / "reference", tmp_path / "reference")
    write_all(tmp_path / "tables")
    for name in FILES:
        assert (tmp_path / "tables" / name).read_bytes() == (data_dir / name).read_bytes(), name
    for name in REFERENCE_COLUMNS:
        path = Path("reference") / f"{name}.csv"
        assert (tmp_path / path).read_bytes() == (data_dir.parent / path).read_bytes(), name
    for folder in OUTPUT_FOLDERS:
        made = sorted(p.relative_to(tmp_path) for p in (tmp_path / folder).rglob("*") if p.is_file())
        committed = sorted(p.relative_to(data_dir.parent)
                           for p in (data_dir.parent / folder).rglob("*") if p.is_file())
        assert made == committed, folder
        for rel in made:
            assert (tmp_path / rel).read_bytes() == (data_dir.parent / rel).read_bytes(), rel


def test_manifest_checksums_and_counts_match_files(data_dir):
    """Row counts are read by streaming each file (the telemetry is too big to hold
    as dicts); the check is the same as before."""
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["emission_factors"] == "illustrative, not for real reporting"
    assert set(manifest["tables"]) == set(COLUMNS)
    for name, info in manifest["tables"].items():
        path = data_dir / info["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == info["sha256"], name
        with path.open(encoding="utf-8", newline="") as f:
            rows = sum(1 for _ in csv.reader(f)) - 1
        assert rows == info["rows"], name


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


def test_service_tables_left_the_22_earlier_tables_unchanged(data_dir):
    """Adding the after-sales service tables (2 November 2026) must not move any
    figure in Power BI, mcp or power-automate: all 22 earlier tables keep the
    checksums they had at commit 484a158 (GUARDRAILS.md rule D5)."""
    before = {
        "dim_date.csv": "ad3e1ac9325c691e43bde6c0734bc3c0f529be789a549d115fea0027e532397d",
        "dim_site.csv": "a2573541e5cb89e239bd6fd6a21f157d7cd982e933d0eb6674334c7719d288c2",
        "dim_source.csv": "7ee85a96cfb60aad62c3e2488a4f28d67e18be3f3a15e46f33e34ea57786c8ac",
        "fact_emissions.csv": "4a1d16b1fbd00afe3beed92489466f43e592cd56732c79537136cad031ceed56",
        "fact_site_metrics.csv": "b8d42f7af1259eafbe3884b9bb296eee3a213353bafaec04f93567c391c4c22e",
        "dim_scope3_category.csv": "c42df42cd1f5593d1907526ad305b0b6abbdc0b5d2508ada792e76b1ef0fb1f9",
        "dim_contract.csv": "2a5f5064a91afef07502bf8853e82969f081311846167c0416703d3583014f90",
        "fact_scope2_market.csv": "2ba2750f01dbe0ae2d6c69dd4cccbc023936c66fda4425bc34ad9a62fbc8987e",
        "fact_energy_upstream.csv": "6c0d2c715ddec68f58fc061247470c5cc8cdde79d2467f88fd4f9d7a9bc9ff18",
        "dim_supplier.csv": "e143e9e034ba26dd7386943ce42441ca78ed7619615b51a53f69d6615cd22d2e",
        "fact_purchases.csv": "9d6d7046e1c510b4bf656ebfb811d1675fbebeda01ed303a484429eb70ba5598",
        "fact_freight.csv": "2c0acc987a859eb10033005e7529863103fbde4d980f9471991c78027e64c837",
        "dim_product_group.csv": "9a4c133e8f125103fdb9a93044840b2b2663e7187d3bbce7117d8bc38fa618b1",
        "dim_product.csv": "44d81bf920d09d4e59e275bd3cf110fc49c2d45d1fd1da62d74a0b3724de45e3",
        "dim_region.csv": "8110ca8d1580bd0fcabc7ab41a416dccc67f2a19e1d514337c41904fe2d7769f",
        "dim_score_criterion.csv": "24fb0ffcc06f89f0a655faa824e105dabe9efa57045cf2cadef08b53c0c9c125",
        "fact_product_rating.csv": "9d648cc2a21f0237cda71ca234a1407dbb47cfcb55aca9755757e459735698d3",
        "dim_product_code.csv": "6e89deff3fe61e651c00a3f2a6d314fd72234df954f1ff4b142f423b3ac264e9",
        "fact_sales.csv": "d85f65e829cf6706bbec0a1f8b85ae064babccb07fe5da45f5db329e74f545e2",
        "fact_data_issue.csv": "48ddf0edec2f189818681a1b976992a00ca92b2a2b1b646c023d7865753de5e5",
        "fact_use_phase.csv": "50f7facc1eb1e33ed191c2b92418733120a5251cf95b6022289a50539ca4b8af",
        "fact_budget.csv": "5ef0713734d6f9c0b8ba2ed6f9b206f6c5938bb236571a218621b225856d5acf",
    }
    assert len(before) == 22
    for name, digest in before.items():
        assert hashlib.sha256((data_dir / name).read_bytes()).hexdigest() == digest, name


def test_town_coordinates_are_cited_from_geonames(data_dir):
    """Every town the service data uses comes from the GeoNames file, with its
    source, date read and checksum on every row (GUARDRAILS.md rule D6)."""
    from fjordvik_data import config as c
    with (data_dir.parent / "reference" / "geonames_towns.csv").open(encoding="utf-8") as f:
        towns = list(csv.DictReader(f))
    wanted = {gid for ids in c.SERVICE_TOWNS.values() for gid in ids}
    assert {int(t["geonameid"]) for t in towns} == wanted
    for t in towns:
        assert t["source"].startswith("GeoNames cities15000.zip (CC BY 4.0)")
        assert "read 2026-11-02" in t["source"] and "sha256 " in t["source"]
        assert t["country_code"] in c.COUNTRY_NAME


def test_every_data_file_is_under_50_mb(data_dir):
    for path in data_dir.parent.rglob("*"):
        if path.is_file() and ".venv" not in path.parts:
            assert path.stat().st_size < 50 * 1024 * 1024, path
