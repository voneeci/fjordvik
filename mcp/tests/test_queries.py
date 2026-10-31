"""Reconcile every tool's numbers against an independent calculation from the CSVs.

Since 31 October 2026 totals cover the four location-based emission tables
(fact_emissions plus the value-chain tables), so the expected values sum all four."""

from collections import defaultdict

import pytest


def by(rows, key):
    return {r[key]: r for r in rows}


def test_total_by_year_reconciles(wh, csv_rows):
    expected = defaultdict(float)
    for r in csv_rows["all_emissions"]:
        expected[int(r["date_key"][:4])] += float(r["tco2e"])
    got = by(wh.emissions_total(["year"])["rows"], "year")
    assert set(got) == {2023, 2024, 2025}
    for year, total in expected.items():
        assert got[year]["tco2e"] == pytest.approx(total, abs=0.001)


def test_total_by_scope_and_country_reconciles(wh, csv_rows):
    scope = {r["source_id"]: int(r["scope"]) for r in csv_rows["dim_source"]}
    country = {r["site_id"]: r["country"] for r in csv_rows["dim_site"]}
    expected = defaultdict(float)
    for r in csv_rows["all_emissions"]:
        if r["date_key"].startswith("2025"):
            expected[(country[r["site_id"]], scope[r["source_id"]])] += float(r["tco2e"])
    rows = wh.emissions_total(["country", "scope"], year=2025)["rows"]
    assert len(rows) == len(expected)
    for r in rows:
        assert r["tco2e"] == pytest.approx(expected[(r["country"], r["scope"])], abs=0.001)


def test_company_total_without_grouping(wh, csv_rows):
    total = sum(float(r["tco2e"]) for r in csv_rows["all_emissions"])
    rows = wh.emissions_total()["rows"]
    assert len(rows) == 1
    assert rows[0]["tco2e"] == pytest.approx(total, abs=0.001)
    assert rows[0]["fact_rows"] == len(csv_rows["all_emissions"])


def test_month_range_is_inclusive(wh, csv_rows):
    keys = {"20240601", "20240701", "20240801"}
    expected = sum(float(r["tco2e"]) for r in csv_rows["all_emissions"]
                   if r["date_key"] in keys and r["site_id"] == "FI01")
    rows = wh.emissions_total(site_id="FI01", start_month="2024-06", end_month="2024-08")["rows"]
    assert rows[0]["tco2e"] == pytest.approx(expected, abs=0.001)


def test_monthly_trend_for_new_site_starts_at_opening(wh):
    rows = wh.emissions_total(["month"], site_id="EE02")["rows"]
    assert rows[0]["month"] == "2024-07"
    assert len(rows) == 18


def test_intensity_per_fte_averages_fte_over_months(wh, csv_rows):
    """FTE is a level: sum across sites within a month, then average the months.
    Summing FTE over twelve months would make the divisor twelve times too big."""
    em = sum(float(r["tco2e"]) for r in csv_rows["all_emissions"] if r["date_key"].startswith("2024"))
    fte_by_month = defaultdict(float)
    for r in csv_rows["fact_site_metrics"]:
        if r["date_key"].startswith("2024"):
            fte_by_month[r["date_key"]] += float(r["fte"])
    average_fte = sum(fte_by_month.values()) / len(fte_by_month)
    row = wh.emissions_intensity("fte", year=2024)["rows"][0]
    assert row["months"] == 12
    assert row["intensity"] == pytest.approx(em / average_fte, abs=0.001)


def test_intensity_per_revenue_is_null_for_head_office(wh):
    rows = by(wh.emissions_intensity("million_eur_revenue", ["site"], year=2025)["rows"], "site_id")
    assert rows["FI02"]["intensity"] is None
    assert rows["FI02"]["tco2e"] > 0
    assert all(rows[s]["intensity"] > 0 for s in rows if s != "FI02")


def test_intensity_per_revenue_reconciles(wh, csv_rows):
    em = sum(float(r["tco2e"]) for r in csv_rows["all_emissions"] if r["site_id"] == "SE01")
    rev = sum(float(r["revenue_eur"]) for r in csv_rows["fact_site_metrics"] if r["site_id"] == "SE01")
    row = wh.emissions_intensity("million_eur_revenue", site_id="SE01")["rows"][0]
    assert row["intensity"] == pytest.approx(em / (rev / 1e6), abs=0.001)


@pytest.mark.parametrize("kwargs, message", [
    ({"site_id": "XX99"}, "Unknown site_id"),
    ({"country": "Norway"}, "Unknown country"),
    ({"scope": 4}, "Unknown scope"),
    ({"year": 2019}, "Unknown year"),
    ({"start_month": "2024-13"}, "start_month must look like"),
])
def test_bad_filters_explain_valid_values(wh, kwargs, message):
    with pytest.raises(ValueError, match=message):
        wh.emissions_total(**kwargs)


def test_unknown_group_is_refused(wh):
    with pytest.raises(ValueError, match="Unknown group_by"):
        wh.emissions_total(["site; DROP TABLE dim_site"])


def test_describe_lists_sites_with_first_month(wh):
    d = wh.describe()
    sites = by(d["sites"], "site_id")
    assert len(sites) == 6
    assert sites["EE02"]["first_month"] == "2024-07"
    assert sites["FI01"]["first_month"] == "2023-01"
    assert d["row_counts"]["fact_emissions"] == 1422
    assert len(d["row_counts"]) == 21
    assert any("illustrative" in c for c in d["caveats"])


def test_market_based_total_swaps_only_scope_2(wh, csv_rows):
    scope = {r["source_id"]: int(r["scope"]) for r in csv_rows["dim_source"]}
    in_2025 = [r for r in csv_rows["all_emissions"] if r["date_key"].startswith("2025")]
    other = sum(float(r["tco2e"]) for r in in_2025 if scope[r["source_id"]] != 2)
    market = sum(float(r["tco2e"]) for r in csv_rows["fact_scope2_market"]
                 if r["date_key"].startswith("2025"))
    rows = wh.emissions_total(["scope"], year=2025, scope2_method="market")["rows"]
    got = by(rows, "scope")
    assert got[2]["tco2e"] == pytest.approx(market, abs=0.001)
    assert got[1]["tco2e"] + got[3]["tco2e"] == pytest.approx(other, abs=0.001)


def test_total_by_scope3_category_reconciles(wh, csv_rows):
    category = {r["source_id"]: r["scope3_category"] for r in csv_rows["dim_source"]}
    expected = defaultdict(float)
    for r in csv_rows["all_emissions"]:
        if category[r["source_id"]] and r["date_key"].startswith("2024"):
            expected[int(category[r["source_id"]])] += float(r["tco2e"])
    rows = [r for r in wh.emissions_total(["scope3_category"], year=2024, scope=3)["rows"]]
    # Category 11 added with phase 2's sales (31 October 2026)
    assert {r["scope3_category"] for r in rows} == set(expected) == {1, 3, 4, 5, 6, 9, 11}
    for r in rows:
        assert r["tco2e"] == pytest.approx(expected[r["scope3_category"]], abs=0.001)


def test_bad_scope2_method_is_refused(wh):
    with pytest.raises(ValueError, match="scope2_method"):
        wh.emissions_total(scope2_method="hourly")


def test_scope3_inventory_lists_all_15_with_reasons(wh, csv_rows):
    inv = wh.scope3_inventory(2025)["categories"]
    assert [c["scope3_category"] for c in inv] == list(range(1, 16))
    cat = by(inv, "scope3_category")
    # Category 11 calculated in part since phase 2 (31 October 2026)
    assert cat[11]["status"] == "Calculated in part" and cat[11]["tco2e"] > 0
    assert cat[2]["status"] == "Not yet calculated" and cat[2]["tco2e"] is None
    assert cat[8]["status"] == "Not relevant" and cat[8]["reason"]
    spend = sum(float(r["tco2e"]) for r in csv_rows["fact_purchases"]
                if r["date_key"].startswith("2025"))
    assert cat[1]["tco2e"] == pytest.approx(spend, abs=0.001)


def test_sales_summary_reconciles_by_family(wh, csv_rows):
    family = {r["product_id"]: r["product_family"] for r in csv_rows["dim_product"]}
    expected = defaultdict(float)
    for r in csv_rows["fact_sales"]:
        if r["date_key"].startswith("2025"):
            expected[family[r["product_id"]]] += float(r["net_sales_eur"])
    rows = wh.sales_summary(["family"], year=2025)["rows"]
    assert {r["product_family"] for r in rows} == set(expected)
    for r in rows:
        assert r["net_sales_eur"] == pytest.approx(expected[r["product_family"]], abs=0.01)
        assert 0 < r["margin_pct"] < 1


def test_sales_summary_refuses_an_unknown_region(wh):
    with pytest.raises(ValueError, match="Unknown region_id"):
        wh.sales_summary(region_id="XX")
