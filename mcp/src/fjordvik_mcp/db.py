"""Load the Fjordvik CSV files into an in-memory DuckDB database, then lock it down.

After loading, the database can no longer touch the file system or the network
(`enable_external_access = false`), and that setting is locked so SQL cannot
switch it back on. Combined with the SELECT-only check in queries.py, the
run_sql tool can read the five tables and nothing else.
"""

import os
from pathlib import Path

import duckdb

# The shared data folder of the fjordvik repository: fjordvik/data/data.
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "data"

# Explicit types, so nothing depends on DuckDB guessing them.
# DECIMAL keeps sums exact: 0.1 + 0.2 is 0.3, not 0.30000000000000004.
SCHEMA = {
    "dim_date": {"date_key": "INTEGER", "date": "DATE", "year": "INTEGER",
                 "quarter": "INTEGER", "month": "INTEGER", "month_name": "VARCHAR"},
    "dim_site": {"site_id": "VARCHAR", "site_name": "VARCHAR", "country": "VARCHAR",
                 "site_type": "VARCHAR"},
    "dim_source": {"source_id": "VARCHAR", "source_name": "VARCHAR", "scope": "INTEGER",
                   "category": "VARCHAR"},
    "fact_emissions": {"date_key": "INTEGER", "site_id": "VARCHAR", "source_id": "VARCHAR",
                       "activity_amount": "DECIMAL(18,2)", "unit": "VARCHAR",
                       "emission_factor": "DECIMAL(12,3)", "tco2e": "DECIMAL(18,6)"},
    "fact_site_metrics": {"date_key": "INTEGER", "site_id": "VARCHAR",
                          "revenue_eur": "DECIMAL(18,2)", "fte": "DECIMAL(10,1)"},
}


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
    con.execute("SET enable_external_access = false")
    con.execute("SET lock_configuration = true")
    return con
