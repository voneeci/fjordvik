"""The telemetry schema (phase rule D13): every column has a type, a unit, an
allowed range and an allowed share of blanks, and the table keeps to them."""

import csv
from collections import Counter
from datetime import date

from fjordvik_data import config as c
from fjordvik_data.generate import COLUMNS

TELEMETRY_FILE = "fact_asset_telemetry.csv"
SCHEMA = c.TELEMETRY_SCHEMA
DECIMALS = [name for name, entry in SCHEMA.items() if entry["type"] == "decimal"]


def problems(path, tables) -> tuple[Counter, Counter, int]:
    """Read a telemetry file against the schema: how many values break each
    column's type or range, how many are blank, and how many rows there are."""
    assets = {a["asset_id"]: a for a in tables["dim_asset"]}
    rated = {p["product_id"]: float(p["rated_kw"]) for p in tables["dim_product"]}
    first, last = SCHEMA["date_key"]["range"]
    broken, blank, rows = Counter(), Counter(), 0
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows += 1
            for name in SCHEMA:
                if row[name] == "":
                    blank[name] += 1
            try:
                day = date(int(row["date_key"][:4]), int(row["date_key"][4:6]),
                           int(row["date_key"][6:]))
                broken["date_key"] += not first <= day <= last
            except ValueError:
                broken["date_key"] += 1
            if row["asset_id"] not in assets:
                broken["asset_id"] += 1
                continue
            for name in DECIMALS:
                if row[name] == "":
                    continue
                low, high = SCHEMA[name]["range"]
                if SCHEMA[name].get("range_times") == "rated_kw":
                    high *= rated[assets[row["asset_id"]]["product_id"]]
                try:
                    broken[name] += not low <= float(row[name]) <= high
                except ValueError:
                    broken[name] += 1
    return broken, blank, rows


def test_every_telemetry_column_has_a_schema_entry():
    assert list(SCHEMA) == COLUMNS["fact_asset_telemetry"]
    for name, entry in SCHEMA.items():
        assert entry["type"] in {"date as YYYYMMDD", "text", "decimal"}, name
        assert entry["unit"], name
        assert entry["range"], name
        assert 0 <= entry["max_missing_share"] < 1, name
    for name in DECIMALS:
        low, high = SCHEMA[name]["range"]
        assert low < high, name
    # the unit is part of the column's meaning, and its name says so
    assert "mm/s" in SCHEMA["vibration_mm_s"]["unit"]
    assert "Celsius" in SCHEMA["bearing_temp_c"]["unit"]
    assert "kW" in SCHEMA["power_kw"]["unit"]
    assert c.TELEMETRY_TIME_ZONE in SCHEMA["date_key"]["unit"]


def test_telemetry_keeps_to_its_schema(tables, data_dir):
    broken, blank, rows = problems(data_dir / TELEMETRY_FILE, tables)
    assert rows > 0
    assert not +broken, dict(broken)
    for name, entry in SCHEMA.items():
        assert blank[name] / rows <= entry["max_missing_share"], name
    # a reading is blank only on a day the pump did not run
    assert blank["vibration_mm_s"] == blank["bearing_temp_c"] > 0


def test_a_silent_unit_change_breaks_the_schema(scenario_files, tables):
    """D13: a unit change needs a new column. The unit-change scenario puts inches
    per second in the mm/s column, and the schema's range catches it."""
    broken, _blank, _rows = problems(
        scenario_files[0] / "drift_unit_change" / TELEMETRY_FILE, tables)
    assert set(+broken) == {"vibration_mm_s"}
    assert broken["vibration_mm_s"] > 0
