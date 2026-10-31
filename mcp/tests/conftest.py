import csv
from pathlib import Path

import pytest

from fjordvik_mcp import db
from fjordvik_mcp.queries import Warehouse

DATA = Path(__file__).resolve().parents[2] / "data" / "tables"


@pytest.fixture(scope="session")
def data_dir() -> Path:
    return DATA


@pytest.fixture(scope="session")
def wh() -> Warehouse:
    return Warehouse(db.connect(DATA))


@pytest.fixture(scope="session")
def csv_rows():
    """The raw CSV files read with Python's csv module: an independent path to
    the same numbers, so the DuckDB results can be reconciled against it."""
    def read(name):
        with (DATA / f"{name}.csv").open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    rows = {n: read(n) for n in db.SCHEMA}
    # The location-based inventory: the four emission tables stacked, as the
    # all_emissions view does in DuckDB.
    rows["all_emissions"] = [r for t in db.EMISSION_TABLES for r in rows[t]]
    return rows
