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
    # 8 original checks plus 6 for the value-chain tables (31 October 2026)
    assert report["failed"] == 0 and report["passed"] == 14


def corrupt(tmp_path, data_dir, change, table="fact_emissions"):
    """Copy the data, apply one change to one table, and load the copy."""
    for f in data_dir.glob("*.csv"):
        shutil.copyfile(f, tmp_path / f.name)
    path = tmp_path / f"{table}.csv"
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


def test_customer_paid_freight_in_category_4_is_caught(tmp_path, data_dir):
    def wrong_category(rows):
        r = next(r for r in rows if r["paid_by"] == "Customer")
        r["source_id"] = "S12"
        return rows
    report = corrupt(tmp_path, data_dir, wrong_category, "fact_freight")
    assert not result(report, "freight_split_by_payer")["passed"]


def test_market_kwh_that_differs_from_location_kwh_is_caught(tmp_path, data_dir):
    def drop_residual(rows):
        return [r for r in rows if not (r["site_id"] == "FI01" and r["date_key"] == "20250301"
                                        and r["instrument"] == "Residual mix")]
    report = corrupt(tmp_path, data_dir, drop_residual, "fact_scope2_market")
    gaps = result(report, "market_kwh_matches_location_kwh")
    assert not gaps["passed"]
    assert gaps["examples"][0]["site_id"] == "FI01"


def test_scope3_category_without_a_reason_is_caught(tmp_path, data_dir):
    def blank(rows):
        rows[10]["reason"] = ""
        return rows
    report = corrupt(tmp_path, data_dir, blank, "dim_scope3_category")
    assert not result(report, "scope3_categories_have_reasons")["passed"]


def test_purchase_from_unknown_supplier_is_caught(tmp_path, data_dir):
    def orphan(rows):
        rows[0]["supplier_id"] = "SUP99"
        return rows
    report = corrupt(tmp_path, data_dir, orphan, "fact_purchases")
    assert not result(report, "value_chain_rows_join_dimensions")["passed"]
