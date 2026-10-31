"""Portfolio data: sales reconcile to finance, the SQL catches every planted problem,
and category 11 follows its method."""

import csv
import hashlib
import io
import shutil
import zipfile
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from fjordvik_data import config as c
from fjordvik_data import portfolio

DATA = Path(__file__).resolve().parents[1]
CENT = Decimal("0.01")


def money(x) -> Decimal:
    return Decimal(x)


# ---------------------------------------------------------------------------
# The published tables
# ---------------------------------------------------------------------------

def test_sales_plus_quarantine_equals_finance_revenue_to_the_cent(tables):
    sales = defaultdict(Decimal)
    for r in tables["fact_sales"]:
        sales[(r["date_key"], r["site_id"])] += money(r["net_sales_eur"])
    for r in tables["fact_data_issue"]:
        if r["status"] == "Quarantined":
            sales[(r["date_key"], r["site_id"])] += money(r["amount_eur"])
    finance = {(r["date_key"], r["site_id"]): money(r["revenue_eur"])
               for r in tables["fact_site_metrics"] if money(r["revenue_eur"]) > 0}
    assert sales == finance


def test_margin_is_sales_minus_cost(tables):
    for r in tables["fact_sales"]:
        assert money(r["margin_eur"]) == money(r["net_sales_eur"]) - money(r["cost_of_sales_eur"])
        assert int(r["units"]) > 0


def test_sales_join_their_dimensions_and_follow_the_site_family(tables):
    products = {r["product_id"]: r for r in tables["dim_product"]}
    regions = {r["region_id"] for r in tables["dim_region"]}
    groups = {r["product_group"] for r in tables["dim_product_group"]}
    for p in products.values():
        assert p["product_group"] in groups
    for r in tables["fact_sales"]:
        assert r["region_id"] in regions
        assert products[r["product_id"]]["product_family"] == c.SITE_FAMILY[r["site_id"]]


def test_every_product_is_sold_every_month_its_site_ships(tables):
    """So the price/volume/mix bridge always has a prior year for each product."""
    sold = defaultdict(set)
    for r in tables["fact_sales"]:
        sold[(r["date_key"], r["product_id"])].add(r["site_id"])
    months = {r["date_key"] for r in tables["fact_site_metrics"]}
    for p in tables["dim_product"]:
        for m in months:
            assert sold[(m, p["product_id"])], (m, p["product_id"])


def test_the_planted_issues_are_listed_for_the_data_owner(tables):
    issues = {(r["date_key"], r["issue_type"], r["status"]) for r in tables["fact_data_issue"]}
    assert issues == {("20240801", "Duplicate lines", "Removed by rule"),
                      ("20250301", "Missing currency code", "Corrected by rule"),
                      ("20250601", "Unmapped item number", "Quarantined"),
                      ("20251101", "Unmapped item number", "Quarantined")}


def test_kronor_convert_at_the_ecb_rate(data_dir):
    """Recompute one Gothenburg month from the raw extract, independently of the SQL."""
    rates = portfolio.read_rates()
    zpath = DATA / "erp-extract" / "2025-06" / "SalesOrderLines_Gothenburg_202506.zip"
    with zipfile.ZipFile(zpath) as z:
        rows = list(csv.DictReader(io.StringIO(z.read("SalesOrderLines.csv").decode())))
    rate = Decimal(rates[20250601])
    expected = sum((Decimal(r["EXTENDED_AMOUNT"]) / rate).quantize(CENT, rounding=ROUND_HALF_UP)
                   for r in rows)
    with (data_dir / "fact_sales.csv").open(encoding="utf-8") as f:
        got = sum(Decimal(r["net_sales_eur"]) for r in csv.DictReader(f)
                  if r["date_key"] == "20250601" and r["site_id"] == "SE01")
    assert got == expected


def test_ecb_rates_cover_every_month_and_cite_their_series(tables):
    rates = portfolio.read_rates()
    assert set(rates) == {int(r["date_key"]) for r in tables["dim_date"]}
    with portfolio.ECB_RATES.open(encoding="utf-8") as f:
        assert {r["series_key"] for r in csv.DictReader(f)} == {"EXR.M.SEK.EUR.SP00.A"}


def test_use_phase_follows_the_direct_use_phase_method(tables):
    spec = {r["product_id"]: r for r in tables["dim_product"]}
    for r in tables["fact_use_phase"]:
        p = spec[r["product_id"]]
        assert int(p["kwh_per_year"]) > 0
        assert float(r["activity_amount"]) == int(r["units"]) * int(p["lifetime_years"]) * int(p["kwh_per_year"])
        assert float(r["emission_factor"]) == c.USE_PHASE_GRID_FACTOR[r["region_id"]]
        assert abs(float(r["tco2e"]) - float(r["activity_amount"]) * float(r["emission_factor"]) / 1000) < 1e-6
    assert "ROW" not in {r["region_id"] for r in tables["fact_use_phase"]}


def test_use_phase_covers_every_energy_using_sale_outside_rest_of_world(tables):
    spec = {r["product_id"]: int(r["kwh_per_year"]) for r in tables["dim_product"]}
    expected = {(r["date_key"], r["site_id"], r["product_id"], r["region_id"])
                for r in tables["fact_sales"] if spec[r["product_id"]] and r["region_id"] != "ROW"}
    got = {(r["date_key"], r["site_id"], r["product_id"], r["region_id"]) for r in tables["fact_use_phase"]}
    assert got == expected


def test_scorecard_ratings_and_weights(tables):
    weights = {r["criterion_id"]: int(r["weight"]) for r in tables["dim_score_criterion"]}
    assert all(w > 0 for w in weights.values())
    groups = {r["product_group"] for r in tables["dim_product_group"]}
    seen = defaultdict(int)
    for r in tables["fact_product_rating"]:
        assert 1 <= int(r["rating"]) <= 10
        assert r["criterion_id"] in weights and r["product_group"] in groups
        assert r["date_key"][4:6] in ("01", "04", "07", "10")
        seen[(r["date_key"], r["product_group"], r["criterion_id"])] += 1
    assert set(seen.values()) == {1} and len(seen) == 12 * len(groups) * len(weights)


# ---------------------------------------------------------------------------
# Planted problems: each one is caught by its own check
# ---------------------------------------------------------------------------

@pytest.fixture
def pipeline(tmp_path):
    """A copy of the extract, reference lists and tables, and a way to change one file."""
    for name in ("erp-extract", "reference", "tables"):
        shutil.copytree(DATA / name, tmp_path / name)

    def change(month, zip_name, edit):
        folder = tmp_path / "erp-extract" / month
        path = folder / zip_name
        with zipfile.ZipFile(path) as z:
            rows = list(csv.DictReader(io.StringIO(z.read("SalesOrderLines.csv").decode())))
        data = portfolio.zip_bytes("SalesOrderLines.csv", portfolio.csv_bytes(edit(rows)))
        path.write_bytes(data)
        lines = (folder / "manifest.mf").read_text(encoding="utf-8").splitlines()
        lines = [f"{n};{doc};{hashlib.sha256(data).hexdigest()}" if n == zip_name else f"{n};{doc};{h}"
                 for n, doc, h in (l.split(";") for l in lines)]
        (folder / "manifest.mf").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def run():
        return portfolio.run_sql(tmp_path / "erp-extract", tmp_path / "reference", tmp_path / "tables")

    return tmp_path, change, run


TAMPERE_2025_02 = ("2025-02", "SalesOrderLines_Tampere_202502.zip")


def failed(run):
    with pytest.raises(portfolio.ExtractError) as e:
        run()
    return str(e.value)


def test_clean_extract_passes_every_check(pipeline):
    _tmp, _change, run = pipeline
    checks = run()["check_results"]
    assert len(checks) == 9 and all(r["passed"] for r in checks)


def test_a_file_that_does_not_match_its_checksum_is_refused(pipeline):
    tmp, _change, run = pipeline
    path = tmp / "erp-extract" / TAMPERE_2025_02[0] / TAMPERE_2025_02[1]
    path.write_bytes(path.read_bytes() + b" ")
    assert "checksum does not match" in failed(run)


def test_a_file_missing_from_the_manifest_is_refused(pipeline):
    tmp, _change, run = pipeline
    shutil.copyfile(tmp / "erp-extract" / TAMPERE_2025_02[0] / TAMPERE_2025_02[1],
                    tmp / "erp-extract" / TAMPERE_2025_02[0] / "unexpected.zip")
    assert "not both in the folder and in the manifest" in failed(run)


def test_an_exact_duplicate_is_removed_and_logged(pipeline):
    _tmp, change, run = pipeline
    change(*TAMPERE_2025_02, lambda rows: rows + rows[:1])
    issues = run()["fact_data_issue"]
    assert any(i["issue_type"] == "Duplicate lines" and i["date_key"] == 20250201 for i in issues)


def test_a_conflicting_duplicate_stops_the_load(pipeline):
    _tmp, change, run = pipeline

    def conflict(rows):
        copy = dict(rows[0])
        copy["QUANTITY"] = str(int(copy["QUANTITY"]) + 1)
        return rows + [copy]
    change(*TAMPERE_2025_02, conflict)
    assert "duplicates_are_exact_copies" in failed(run)


def test_an_unmapped_code_is_quarantined_and_still_reconciles(pipeline):
    _tmp, change, run = pipeline

    def unmapped(rows):
        rows[0]["ITEM_NUMBER"] = "FI-NEW-TEST"
        return rows
    change(*TAMPERE_2025_02, unmapped)
    issues = run()["fact_data_issue"]
    assert any(i["status"] == "Quarantined" and "FI-NEW-TEST" in i["detail"] for i in issues)


def test_a_missing_currency_code_is_corrected_and_logged(pipeline):
    _tmp, change, run = pipeline

    def blank(rows):
        for r in rows:
            r["CURRENCY_CODE"] = ""
        return rows
    change("2024-02", "SalesOrderLines_Gothenburg_202402.zip", blank)
    issues = run()["fact_data_issue"]
    assert any(i["issue_type"] == "Missing currency code" and i["date_key"] == 20240201 for i in issues)


def test_kronor_labelled_as_euros_stops_the_load(pipeline):
    _tmp, change, run = pipeline

    def mislabel(rows):
        rows[0]["CURRENCY_CODE"] = "EUR"
        return rows
    change("2024-02", "SalesOrderLines_Gothenburg_202402.zip", mislabel)
    message = failed(run)
    assert "currency_matches_ledger" in message and "reconciles_to_finance" in message


def test_an_unknown_region_code_stops_the_load(pipeline):
    _tmp, change, run = pipeline

    def region(rows):
        rows[0]["CUSTOMER_REGION"] = "MARS"
        return rows
    change(*TAMPERE_2025_02, region)
    assert "regions_known" in failed(run)


def test_a_missing_line_does_not_reconcile(pipeline):
    _tmp, change, run = pipeline
    change(*TAMPERE_2025_02, lambda rows: rows[1:])
    assert "reconciles_to_finance" in failed(run)
