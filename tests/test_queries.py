"""Reconcile every tool's numbers against an independent calculation from the CSVs."""

from collections import defaultdict

import pytest


def by(rows, key):
    return {r[key]: r for r in rows}


def test_total_by_year_reconciles(wh, csv_rows):
    expected = defaultdict(float)
    for r in csv_rows["fact_emissions"]:
        expected[int(r["date_key"][:4])] += float(r["tco2e"])
    got = by(wh.emissions_total(["year"])["rows"], "year")
    assert set(got) == {2023, 2024, 2025}
    for year, total in expected.items():
        assert got[year]["tco2e"] == pytest.approx(total, abs=0.001)


def test_total_by_scope_and_country_reconciles(wh, csv_rows):
    scope = {r["source_id"]: int(r["scope"]) for r in csv_rows["dim_source"]}
    country = {r["site_id"]: r["country"] for r in csv_rows["dim_site"]}
    expected = defaultdict(float)
    for r in csv_rows["fact_emissions"]:
        if r["date_key"].startswith("2025"):
            expected[(country[r["site_id"]], scope[r["source_id"]])] += float(r["tco2e"])
    rows = wh.emissions_total(["country", "scope"], year=2025)["rows"]
    assert len(rows) == len(expected)
    for r in rows:
        assert r["tco2e"] == pytest.approx(expected[(r["country"], r["scope"])], abs=0.001)


def test_company_total_without_grouping(wh, csv_rows):
    total = sum(float(r["tco2e"]) for r in csv_rows["fact_emissions"])
    rows = wh.emissions_total()["rows"]
    assert len(rows) == 1
    assert rows[0]["tco2e"] == pytest.approx(total, abs=0.001)
    assert rows[0]["fact_rows"] == len(csv_rows["fact_emissions"])


def test_month_range_is_inclusive(wh, csv_rows):
    keys = {"20240601", "20240701", "20240801"}
    expected = sum(float(r["tco2e"]) for r in csv_rows["fact_emissions"]
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
    em = sum(float(r["tco2e"]) for r in csv_rows["fact_emissions"] if r["date_key"].startswith("2024"))
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
    em = sum(float(r["tco2e"]) for r in csv_rows["fact_emissions"] if r["site_id"] == "SE01")
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
    assert any("illustrative" in c for c in d["caveats"])
