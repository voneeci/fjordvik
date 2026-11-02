"""The shared schema: table and column names are a contract with the other repos."""

import csv

from fjordvik_data.generate import COLUMNS

EXPECTED = {
    "dim_date": ["date_key", "date", "year", "quarter", "month", "month_name"],
    "dim_site": ["site_id", "site_name", "country", "site_type"],
    # scope3_category and method added for the value chain, 31 October 2026
    "dim_source": ["source_id", "source_name", "scope", "category",
                   "scope3_category", "method"],
    "fact_emissions": ["date_key", "site_id", "source_id", "activity_amount",
                       "unit", "emission_factor", "tco2e"],
    "fact_site_metrics": ["date_key", "site_id", "revenue_eur", "fte"],
    "dim_scope3_category": ["scope3_category", "category_name", "status", "reason"],
    "dim_contract": ["contract_id", "site_id", "source_id", "supplier_name", "instrument",
                     "start_date_key", "end_date_key", "covered_share"],
    "fact_scope2_market": ["date_key", "site_id", "source_id", "contract_id", "instrument",
                           "activity_amount", "unit", "emission_factor", "tco2e"],
    "fact_energy_upstream": ["date_key", "site_id", "source_id", "based_on_source_id",
                             "activity_amount", "unit", "emission_factor", "tco2e"],
    "dim_supplier": ["supplier_id", "supplier_name", "country", "spend_category"],
    "fact_purchases": ["date_key", "site_id", "source_id", "supplier_id", "spend_category",
                       "method", "activity_amount", "unit", "emission_factor", "tco2e"],
    "fact_freight": ["date_key", "site_id", "source_id", "direction", "mode", "paid_by",
                     "tonnes", "distance_km", "activity_amount", "unit", "emission_factor",
                     "tco2e"],
    # Product portfolio and sales, added for phase 2 (31 October 2026)
    "dim_product_group": ["product_group", "product_family"],
    "dim_product": ["product_id", "product_name", "product_group", "product_family",
                    "made_at_site_id", "rated_kw", "kwh_per_year", "lifetime_years",
                    "list_price_eur", "standard_cost_eur"],
    "dim_region": ["region_id", "region_name"],
    "dim_score_criterion": ["criterion_id", "criterion_name", "weight", "source"],
    "fact_product_rating": ["date_key", "product_group", "criterion_id", "rating"],
    "dim_product_code": ["business_unit", "local_item_number", "product_id"],
    "fact_sales": ["date_key", "site_id", "product_id", "region_id", "units", "net_sales_eur",
                   "cost_of_sales_eur", "margin_eur"],
    "fact_data_issue": ["issue_id", "date_key", "site_id", "business_unit", "issue_type",
                        "detail", "line_count", "amount_eur", "status", "action"],
    "fact_use_phase": ["date_key", "site_id", "source_id", "product_id", "region_id", "units",
                       "net_sales_eur", "activity_amount", "unit", "emission_factor", "tco2e"],
    "fact_budget": ["date_key", "site_id", "product_group", "region_id", "budget_units",
                    "budget_net_sales_eur", "budget_margin_eur"],
    # After-sales service, added 2 November 2026
    "dim_customer": ["customer_id", "customer_name", "segment", "country", "region_id", "town",
                     "latitude", "longitude", "service_contract", "customer_since"],
    "dim_asset": ["asset_id", "serial_number", "product_id", "customer_id", "country", "town",
                  "latitude", "longitude", "application", "install_date", "telemetry_from_date"],
    "dim_part": ["part_id", "part_name", "part_family", "sales_product_id", "list_price_eur",
                 "lead_time_days"],
    "bridge_part_compatibility": ["part_id", "product_group"],
    "dim_technician": ["technician_id", "technician_name", "home_site_id", "home_town",
                       "latitude", "longitude", "countries_served", "skills", "weekly_hours"],
    "fact_asset_telemetry": ["date_key", "asset_id", "running_hours", "vibration_mm_s",
                             "bearing_temp_c", "power_kw"],
    "fact_service_event": ["event_id", "asset_id", "event_type", "failure_mode",
                           "reported_date", "completed_date", "technician_id", "downtime_hours",
                           "labour_hours", "parts_used", "technician_note"],
    "fact_parts_order": ["order_id", "order_line", "order_date", "date_key", "site_id",
                         "region_id", "customer_id", "part_id", "sales_product_id", "quantity",
                         "net_amount_eur", "channel", "service_event_id", "asset_id"],
    "fact_portal_event": ["event_id", "event_date", "session_id", "customer_id", "product_id",
                          "part_id", "rank", "clicked"],
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
    # 8 site-reported sources, 5 value-chain sources (S09 to S13) and use of sold
    # products (S14, phase 2), 31 October 2026
    assert len(tables["dim_source"]) == 14
    assert {r["scope"] for r in tables["dim_source"]} == {"1", "2", "3"}
    assert [r["scope3_category"] for r in tables["dim_scope3_category"]] ==         [str(n) for n in range(1, 16)]


def test_numbers_parse(tables):
    for r in tables["fact_emissions"]:
        float(r["activity_amount"]), float(r["emission_factor"]), float(r["tco2e"])
    for r in tables["fact_site_metrics"]:
        float(r["revenue_eur"]), float(r["fte"])
    for name in ("fact_scope2_market", "fact_energy_upstream", "fact_purchases",
                 "fact_freight"):
        for r in tables[name]:
            float(r["activity_amount"]), float(r["emission_factor"]), float(r["tco2e"])
