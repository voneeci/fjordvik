"""Small built fixtures for the phase 3 tests: a few pumps, a few hundred days, with a
seasonal wave, a one-day spike or a slow rise planted where a test asks for one."""

import copy

import numpy as np
import pandas as pd

START = pd.Timestamp("2023-01-01")


def make_tables(n_days=400, pumps=None, seed=7):
    """pumps: {asset_id: {"application": ..., "events": [callable(day_index, values)]}}."""
    pumps = pumps or {f"P{i:02d}": {"application": "A" if i % 2 else "B"} for i in range(8)}
    gen = np.random.RandomState(np.random.PCG64(seed))
    days = pd.date_range(START, periods=n_days, freq="D")
    season = np.sin(2 * np.pi * np.arange(n_days) / 365.25)
    rows = []
    for pid, spec in pumps.items():
        vib = 2.5 + 0.4 * season + gen.normal(0, 0.05, n_days)
        temp = 45 + 6 * season + gen.normal(0, 0.3, n_days)
        power = 20 + 2 * season + gen.normal(0, 0.2, n_days)
        hours = np.clip(12 + 3 * season + gen.normal(0, 0.5, n_days), 0, 24)
        values = {"vibration_mm_s": vib, "bearing_temp_c": temp, "power_kw": power, "running_hours": hours}
        for event in spec.get("events", []):
            event(values)
        for i, day in enumerate(days):
            rows.append({"date_key": int(day.strftime("%Y%m%d")), "asset_id": pid,
                         "running_hours": round(float(values["running_hours"][i]), 1),
                         "vibration_mm_s": round(float(values["vibration_mm_s"][i]), 2),
                         "bearing_temp_c": round(float(values["bearing_temp_c"][i]), 1),
                         "power_kw": round(float(values["power_kw"][i]), 1)})
    tel = pd.DataFrame(rows)
    for col in ["vibration_mm_s", "bearing_temp_c"]:
        tel.loc[tel["running_hours"] == 0, col] = np.nan
    tel.loc[tel["running_hours"] == 0, "power_kw"] = 0.0
    tel["date"] = pd.to_datetime(tel["date_key"].astype(str), format="%Y%m%d")
    assets = pd.DataFrame([{"asset_id": pid, "product_id": "PR1", "customer_id": "C1",
                            "application": spec["application"], "install_date": "2015-01-01"}
                           for pid, spec in pumps.items()])
    products = pd.DataFrame([{"product_id": "PR1", "product_group": "End-suction pumps", "rated_kw": 30}])
    customers = pd.DataFrame([{"customer_id": "C1", "service_contract": "None"}])
    return {"telemetry": tel, "assets": assets, "products": products, "customers": customers}


def rise(column, start, days, amount):
    """A slow rise over `days` days from day index `start`, held afterwards."""
    def event(values):
        n = len(values[column])
        ramp = np.clip((np.arange(n) - start) / days, 0, 1) * amount
        values[column] = values[column] + ramp
    return event


def spike(column, day, amount):
    def event(values):
        values[column] = values[column].copy()
        values[column][day] += amount
    return event


def step(column, start, amount=None, factor=None):
    def event(values):
        v = values[column].copy()
        if amount is not None:
            v[start:] += amount
        if factor is not None:
            v[start:] *= factor
        values[column] = v
    return event


def shifted(ev):
    """A copy of the evaluation set with every period moved before the real validation
    cut-off, so tests can run the test step without scoring a real test row (E1)."""
    ev = copy.deepcopy(ev)
    p = ev["periods"]
    p["train"].update(last_scored_day="2024-08-01", cut_off="2024-08-31")
    p["validation"].update(first_scored_day="2024-09-01", last_scored_day="2024-12-01", cut_off="2024-12-31",
                           alert_window={"first_day": "2024-09-01", "last_day": "2024-12-31", "days": 122})
    p["test"].update(first_scored_day="2025-01-01", last_scored_day="2025-06-01", cut_off="2025-06-30",
                     alert_window={"first_day": "2025-01-01", "last_day": "2025-06-30", "days": 181})
    p["no_complete_label_window"].update(first_day="2025-06-02", last_day="2025-06-30")
    ev["controls"]["drift"]["false_flags"]["measured_on"] = "January to June 2025"
    return ev
