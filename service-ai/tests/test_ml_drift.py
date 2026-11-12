"""Drift monitors (M5): same calendar month in earlier years, so the season is not flagged,
while a recalibration step and a unit change are flagged within 14 days."""

import numpy as np
import pandas as pd

from fjordvik_service.ml import drift
from ml_fixtures import make_tables, step

SHARE = 60 / 90


def test_a_step_and_a_unit_change_are_flagged_within_14_days_and_the_season_is_not(ev_ml):
    start = 800   # 11 March 2025, with two earlier years of the same months
    pumps = {f"P{i:02d}": {"application": "A"} for i in range(8)}
    pumps["P00"]["events"] = [step("bearing_temp_c", start, amount=3.0)]
    pumps["P01"]["events"] = [step("vibration_mm_s", start, factor=1 / 25.4)]
    tel = make_tables(1000, pumps)["telemetry"]
    m = drift.measures(tel, SHARE)
    first = pd.Timestamp("2023-01-01") + pd.Timedelta(days=start)
    clean = m[(m["asset_id"] != "P00") & (m["asset_id"] != "P01") & (m["date"] >= "2024-01-01")]
    pm = drift.pump_months(clean, pd.DataFrame(columns=["asset_id", "reported_date"]), 42, m["date"].max(),
                           clean["date"].min(), clean["date"].max())
    level = drift.choose_level(pm, ev_ml["controls"]["drift"]["false_flags"]["max_share"])
    scen = pd.DataFrame({"asset_id": ["P00", "P01"], "scenario": ["recal", "unit"], "start_date": [first, first],
                         "sensor": ["bearing_temp_c", "vibration_mm_s"]})
    found = drift.detection(m, scen, level, ev_ml["controls"]["drift"]["detection"]["within_days"])
    assert found["flagged_within_limit"].all(), found
    assert drift.false_share(pm, level) <= ev_ml["controls"]["drift"]["false_flags"]["max_share"]
    assert m.loc[m["date"] < "2024-01-01", "drift_max"].isna().all()   # no earlier year: not monitored


def test_the_flag_level_counts_months_with_no_measure_and_skips_open_tickets():
    pm = pd.DataFrame({"false_measure": list(np.arange(1.0, 100.0)) + [np.nan] * 100})
    level = drift.choose_level(pm, 0.01)
    assert drift.false_share(pm, level) <= 0.01 and level == 99.0   # 1 of 199 months; 98 would flag 2
    tel = make_tables(800)["telemetry"]
    fails = pd.DataFrame({"asset_id": ["P01"], "reported_date": [pd.Timestamp("2025-01-10")],
                          "completed_date": [pd.Timestamp("2025-01-20")]})
    m = drift.measures(tel, SHARE, fails)
    p = m[(m["asset_id"] == "P01") & m["date"].between("2025-01-10", "2025-01-20")]
    assert p[list(drift.DRIFT_SENSORS)].isna().all().all()
    assert m[(m["asset_id"] == "P01") & (m["date"] == "2025-01-21")]["bearing_temp"].notna().all()
