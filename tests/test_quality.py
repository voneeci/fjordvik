"""The data quality checks pass on clean data and catch planted problems."""

import csv
import shutil

import pytest

from fjordvik_mcp import db
from fjordvik_mcp.queries import Warehouse


def result(report, name):
    return next(c for c in report["checks"] if c["check"] == name)


def test_clean_data_passes_every_check(wh):
    report = wh.data_quality_report()
    assert report["failed"] == 0 and report["passed"] == 8


def corrupt(tmp_path, data_dir, change):
    """Copy the data, apply one change to fact_emissions, and load the copy."""
    for f in data_dir.glob("*.csv"):
        shutil.copyfile(f, tmp_path / f.name)
    path = tmp_path / "fact_emissions.csv"
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    rows = change(rows)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return Warehouse(db.connect(tmp_path)).data_quality_report()


def test_duplicate_row_is_caught(tmp_path, data_dir):
    report = corrupt(tmp_path, data_dir, lambda rows: rows + [rows[0]])
    assert not result(report, "unique_emission_keys")["passed"]


def test_missing_month_is_caught(tmp_path, data_dir):
    def drop(rows):
        return [r for r in rows if not (r["site_id"] == "SE01" and r["date_key"] == "20240301")]
    report = corrupt(tmp_path, data_dir, drop)
    gaps = result(report, "complete_monthly_grid")
    assert not gaps["passed"]
    assert {e["site_id"] for e in gaps["examples"]} == {"SE01"}
    assert not result(report, "metrics_match_emissions")["passed"]


def test_unit_error_breaks_the_formula_check(tmp_path, data_dir):
    """kWh entered as MWh: the activity shrinks a thousandfold but tco2e was not
    recalculated, so the stored tco2e no longer matches the formula."""
    def to_mwh(rows):
        r = rows[0]
        r["activity_amount"] = f"{float(r['activity_amount']) / 1000:.2f}"
        return rows
    report = corrupt(tmp_path, data_dir, to_mwh)
    assert not result(report, "tco2e_matches_formula")["passed"]


def test_unknown_site_is_caught(tmp_path, data_dir):
    def orphan(rows):
        rows[0]["site_id"] = "XX99"
        return rows
    report = corrupt(tmp_path, data_dir, orphan)
    assert not result(report, "fact_rows_join_dimensions")["passed"]


@pytest.mark.parametrize("value", ["-5.00"])
def test_negative_activity_is_caught(tmp_path, data_dir, value):
    def negative(rows):
        rows[0]["activity_amount"] = value
        rows[0]["tco2e"] = f"{float(value) * float(rows[0]['emission_factor']) / 1000:.6f}"
        return rows
    report = corrupt(tmp_path, data_dir, negative)
    assert not result(report, "no_negative_values")["passed"]
    assert result(report, "tco2e_matches_formula")["passed"]
