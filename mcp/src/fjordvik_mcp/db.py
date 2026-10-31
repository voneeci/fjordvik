"""Load the Fjordvik CSV files into an in-memory DuckDB database, then lock it down.

After loading, the database can no longer touch the file system or the network
(`enable_external_access = false`), and that setting is locked so SQL cannot
switch it back on. Combined with the SELECT-only check in queries.py, the
run_sql tool can read the 22 tables and the all_emissions view, and nothing else.
"""

import os
from pathlib import Path

import duckdb

# The shared data folder of the fjordvik repository: fjordvik/data/tables.
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "tables"

# Explicit types, so nothing depends on DuckDB guessing them.
# DECIMAL keeps sums exact: 0.1 + 0.2 is 0.3, not 0.30000000000000004.
SCHEMA = {
    "dim_date": {"date_key": "INTEGER", "date": "DATE", "year": "INTEGER",
                 "quarter": "INTEGER", "month": "INTEGER", "month_name": "VARCHAR"},
    "dim_site": {"site_id": "VARCHAR", "site_name": "VARCHAR", "country": "VARCHAR",
                 "site_type": "VARCHAR"},
    "dim_source": {"source_id": "VARCHAR", "source_name": "VARCHAR", "scope": "INTEGER",
                   "category": "VARCHAR", "scope3_category": "INTEGER", "method": "VARCHAR"},
    "fact_emissions": {"date_key": "INTEGER", "site_id": "VARCHAR", "source_id": "VARCHAR",
                       "activity_amount": "DECIMAL(18,2)", "unit": "VARCHAR",
                       "emission_factor": "DECIMAL(12,3)", "tco2e": "DECIMAL(18,6)"},
    "fact_site_metrics": {"date_key": "INTEGER", "site_id": "VARCHAR",
                          "revenue_eur": "DECIMAL(18,2)", "fte": "DECIMAL(10,1)"},
    "dim_scope3_category": {"scope3_category": "INTEGER", "category_name": "VARCHAR",
                            "status": "VARCHAR", "reason": "VARCHAR"},
    "dim_contract": {"contract_id": "VARCHAR", "site_id": "VARCHAR", "source_id": "VARCHAR",
                     "supplier_name": "VARCHAR", "instrument": "VARCHAR",
                     "start_date_key": "INTEGER", "end_date_key": "INTEGER",
                     "covered_share": "DECIMAL(5,2)"},
    "fact_scope2_market": {"date_key": "INTEGER", "site_id": "VARCHAR", "source_id": "VARCHAR",
                           "contract_id": "VARCHAR", "instrument": "VARCHAR",
                           "activity_amount": "DECIMAL(18,2)", "unit": "VARCHAR",
                           "emission_factor": "DECIMAL(12,3)", "tco2e": "DECIMAL(18,6)"},
    "fact_energy_upstream": {"date_key": "INTEGER", "site_id": "VARCHAR",
                             "source_id": "VARCHAR", "based_on_source_id": "VARCHAR",
                             "activity_amount": "DECIMAL(18,2)", "unit": "VARCHAR",
                             "emission_factor": "DECIMAL(12,3)", "tco2e": "DECIMAL(18,6)"},
    "dim_supplier": {"supplier_id": "VARCHAR", "supplier_name": "VARCHAR",
                     "country": "VARCHAR", "spend_category": "VARCHAR"},
    "fact_purchases": {"date_key": "INTEGER", "site_id": "VARCHAR", "source_id": "VARCHAR",
                       "supplier_id": "VARCHAR", "spend_category": "VARCHAR",
                       "method": "VARCHAR", "activity_amount": "DECIMAL(18,2)",
                       "unit": "VARCHAR", "emission_factor": "DECIMAL(12,3)",
                       "tco2e": "DECIMAL(18,6)"},
    "fact_freight": {"date_key": "INTEGER", "site_id": "VARCHAR", "source_id": "VARCHAR",
                     "direction": "VARCHAR", "mode": "VARCHAR", "paid_by": "VARCHAR",
                     "tonnes": "DECIMAL(18,2)", "distance_km": "INTEGER",
                     "activity_amount": "DECIMAL(18,2)", "unit": "VARCHAR",
                     "emission_factor": "DECIMAL(12,3)", "tco2e": "DECIMAL(18,6)"},
    "dim_product_group": {"product_group": "VARCHAR", "product_family": "VARCHAR"},
    "dim_product": {"product_id": "VARCHAR", "product_name": "VARCHAR",
                    "product_group": "VARCHAR", "product_family": "VARCHAR",
                    "made_at_site_id": "VARCHAR", "rated_kw": "INTEGER",
                    "kwh_per_year": "INTEGER", "lifetime_years": "INTEGER",
                    "list_price_eur": "DECIMAL(18,2)", "standard_cost_eur": "DECIMAL(18,2)"},
    "dim_region": {"region_id": "VARCHAR", "region_name": "VARCHAR"},
    "dim_score_criterion": {"criterion_id": "VARCHAR", "criterion_name": "VARCHAR",
                            "weight": "INTEGER", "source": "VARCHAR"},
    "fact_product_rating": {"date_key": "INTEGER", "product_group": "VARCHAR",
                            "criterion_id": "VARCHAR", "rating": "INTEGER"},
    "dim_product_code": {"business_unit": "VARCHAR", "local_item_number": "VARCHAR",
                         "product_id": "VARCHAR"},
    "fact_sales": {"date_key": "INTEGER", "site_id": "VARCHAR", "product_id": "VARCHAR",
                   "region_id": "VARCHAR", "units": "INTEGER", "net_sales_eur": "DECIMAL(18,2)",
                   "cost_of_sales_eur": "DECIMAL(18,2)", "margin_eur": "DECIMAL(18,2)"},
    "fact_data_issue": {"issue_id": "INTEGER", "date_key": "INTEGER", "site_id": "VARCHAR",
                        "business_unit": "VARCHAR", "issue_type": "VARCHAR",
                        "detail": "VARCHAR", "line_count": "INTEGER",
                        "amount_eur": "DECIMAL(18,2)", "status": "VARCHAR",
                        "action": "VARCHAR"},
    "fact_use_phase": {"date_key": "INTEGER", "site_id": "VARCHAR", "source_id": "VARCHAR",
                       "product_id": "VARCHAR", "region_id": "VARCHAR", "units": "INTEGER",
                       "net_sales_eur": "DECIMAL(18,2)", "activity_amount": "DECIMAL(18,2)",
                       "unit": "VARCHAR", "emission_factor": "DECIMAL(12,3)",
                       "tco2e": "DECIMAL(18,6)"},
    "fact_budget": {"date_key": "INTEGER", "site_id": "VARCHAR", "product_group": "VARCHAR",
                    "region_id": "VARCHAR", "budget_units": "INTEGER",
                    "budget_net_sales_eur": "DECIMAL(18,2)", "budget_margin_eur": "DECIMAL(18,2)"},
}

# The tables that make up the location-based inventory. Market-based scope 2
# (fact_scope2_market) is a second view of scope 2, never added to these.
EMISSION_TABLES = ["fact_emissions", "fact_energy_upstream", "fact_purchases", "fact_freight",
                   "fact_use_phase"]
ALL_EMISSIONS = "CREATE VIEW all_emissions AS " + " UNION ALL ".join(
    f"SELECT '{t}' AS from_table, date_key, site_id, source_id, activity_amount, unit, "
    f"emission_factor, tco2e FROM {t}" for t in EMISSION_TABLES)


def data_dir() -> Path:
    """FJORDVIK_DATA_DIR overrides the shared data folder (see .env.example)."""
    return Path(os.environ.get("FJORDVIK_DATA_DIR") or DEFAULT_DATA_DIR)


def connect(folder: Path | None = None) -> duckdb.DuckDBPyConnection:
    folder = folder or data_dir()
    con = duckdb.connect(":memory:")
    for table, columns in SCHEMA.items():
        path = (folder / f"{table}.csv").as_posix()
        con.execute(
            f"CREATE TABLE {table} AS SELECT * FROM read_csv(?, header = true, columns = ?)",
            [path, columns],
        )
    con.execute(ALL_EMISSIONS)
    con.execute("SET enable_external_access = false")
    con.execute("SET lock_configuration = true")
    return con
