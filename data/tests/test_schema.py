"""The shared schema: table and column names are a contract with the other repos."""

import csv

from fjordvik_data.generate import COLUMNS

EXPECTED = {
    "dim_date": ["date_key", "date", "year", "quarter", "month", "month_name"],
    "dim_site": ["site_id", "site_name", "country", "site_type"],
    "dim_source": ["source_id", "source_name", "scope", "category"],
    "fact_emissions": ["date_key", "site_id", "source_id", "activity_amount",
                       "unit", "emission_factor", "tco2e"],
    "fact_site_metrics": ["date_key", "site_id", "revenue_eur", "fte"],
}


def test_generator_columns_match_contract():
    assert COLUMNS == EXPECTED


def test_csv_headers_match_contract(data_dir):
    for name, columns in EXPECTED.items():
        with (data_dir / f"{name}.csv").open(encoding="utf-8", newline="") as f:
            assert next(csv.reader(f)) == columns, name


def test_dim_date_covers_36_months(tables):
    rows = tables["dim_date"]
    assert len(rows) == 36
    assert rows[0]["date"] == "2023-01-01"
    assert rows[-1]["date"] == "2025-12-01"
    for r in rows:
        y, m, d = r["date"].split("-")
        assert r["date_key"] == f"{y}{m}{d}"
        assert int(r["year"]) == int(y)
        assert int(r["month"]) == int(m)
        assert int(r["quarter"]) == (int(m) - 1) // 3 + 1


def test_dimensions_have_expected_members(tables):
    assert len(tables["dim_site"]) == 6
    assert {r["country"] for r in tables["dim_site"]} == {"Finland", "Sweden", "Estonia"}
    assert len(tables["dim_source"]) == 8
    assert {r["scope"] for r in tables["dim_source"]} == {"1", "2", "3"}


def test_numbers_parse(tables):
    for r in tables["fact_emissions"]:
        float(r["activity_amount"]), float(r["emission_factor"]), float(r["tco2e"])
    for r in tables["fact_site_metrics"]:
        float(r["revenue_eur"]), float(r["fte"])
