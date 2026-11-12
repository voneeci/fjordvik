"""Features for each pump-day, from the four allowlisted tables only (D11, D12).

Every window ends on day t and includes it, so a feature for day t uses only rows recorded
on or before day t. `check_point_in_time` proves it: rebuilding with every row after day t
deleted must not change the row for day t. Nothing here reads fact_service_event or the
answer key.
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from ..common.checks import PipelineCheckError, check_frame

SENSORS = ["vibration", "bearing_temp", "power_per_rated_kw", "running_hours"]
# The robust z-score's scale: 1.4826 times the median absolute deviation estimates the
# standard deviation of normal readings (the allowlist's definition of the z column).
ROBUST_SCALE = 1.4826
# A day counts towards z_days_above_3_14d when z_max is above 3 (the allowlist's column).
Z_ABOVE = 3.0
# Fleet-adjusted readings are rounded to 9 decimal places. Every sensor is recorded to 0.1
# or 0.01 of its unit, so no reading changes; only floating-point noise goes.
FLEET_DECIMALS = 9
CHUNK_PUMPS = 100
KEYS = ["asset_id", "date"]


def source_columns(allow):
    s = allow["sources"]
    return {name: s[name]["keys"] + s[name]["columns_read"] for name in
            ["fact_asset_telemetry", "dim_asset", "dim_product", "dim_customer"]}


def read_tables(data_dir, allow, *, telemetry_path=None, cut_off=None, pumps=None):
    """Open exactly the four allowlisted tables, reading only their listed columns.

    telemetry_path swaps in a scenario's telemetry (the E2 control or a drift scenario).
    cut_off drops every telemetry row after that day, so a step reads nothing later.
    """
    cols = source_columns(allow)
    data_dir = Path(data_dir)
    telemetry_file = Path(telemetry_path) if telemetry_path else data_dir / "fact_asset_telemetry.csv"
    tel = pd.read_csv(telemetry_file, usecols=cols["fact_asset_telemetry"])
    assets = pd.read_csv(data_dir / "dim_asset.csv", usecols=cols["dim_asset"])
    products = pd.read_csv(data_dir / "dim_product.csv", usecols=cols["dim_product"])
    # pandas reads the service contract value "None" as missing, so blanks are kept as text.
    customers = pd.read_csv(data_dir / "dim_customer.csv", usecols=cols["dim_customer"], keep_default_na=False)
    tel["date"] = pd.to_datetime(tel["date_key"].astype(str), format="%Y%m%d")
    if cut_off is not None:
        tel = tel[tel["date"] <= cut_off]
    if pumps is not None:
        tel = tel[tel["asset_id"].isin(pumps)]
    return {"telemetry": tel.reset_index(drop=True), "assets": assets, "products": products, "customers": customers}


def pump_facts(tables):
    """One row per pump: application, install date, product group, rated kW, service contract."""
    a = tables["assets"].merge(tables["products"], on="product_id", how="left", validate="many_to_one")
    a = a.merge(tables["customers"], on="customer_id", how="left", validate="many_to_one")
    a["install_date"] = pd.to_datetime(a["install_date"])
    check_frame(a, "pump facts", ["asset_id"],
                required=["asset_id", "application", "install_date", "product_group", "rated_kw", "service_contract"])
    return a


def categories(tables):
    """Fixed category lists from the dimension tables, so every period codes them the same."""
    return {
        "product_group": sorted(tables["products"]["product_group"].unique()),
        "application": sorted(tables["assets"]["application"].unique()),
        "service_contract": sorted(tables["customers"]["service_contract"].unique()),
    }


def windows(panel, w, lag=0):
    """For each day t (rows) and pump (columns), the w values on days t-lag-w+1 to t-lag."""
    days, pumps = panel.shape
    pad = np.full((w - 1 + lag, pumps), np.nan)
    full = np.vstack([pad, panel])[: days + w - 1]
    return sliding_window_view(full, w, axis=0)


def _median(win):
    return np.nanmedian(win, axis=2)


def _count(win):
    return np.sum(~np.isnan(win), axis=2)


def _slope(win):
    """Least-squares slope per day over the window, blanks skipped; needs two readings."""
    x = np.arange(win.shape[2], dtype=float)
    m = ~np.isnan(win)
    n = m.sum(axis=2)
    y = np.where(m, win, 0.0)
    xm = np.where(n > 0, (m * x).sum(axis=2) / np.maximum(n, 1), np.nan)
    ym = np.where(n > 0, y.sum(axis=2) / np.maximum(n, 1), np.nan)
    dx = np.where(m, x - xm[..., None], 0.0)
    den = (dx * dx).sum(axis=2)
    num = (dx * (y - ym[..., None]) * m).sum(axis=2)
    return np.where((n >= 2) & (den > 0), num / np.where(den > 0, den, 1.0), np.nan)


def _by_chunk(panel, fn):
    out = np.empty(panel.shape)
    for start in range(0, panel.shape[1], CHUNK_PUMPS):
        out[:, start:start + CHUNK_PUMPS] = fn(panel[:, start:start + CHUNK_PUMPS])
    return out


def sensor_panels(panel, fleet_panel, wd, base):
    """The six allowlisted columns for one sensor, as day-by-pump panels."""
    w7, w30 = wd["median"]
    lag, length, need = base["ends_days_before_t"], base["length_days"], base["min_readings"]
    out = {}
    out["med7"] = _by_chunk(panel, lambda p: _median(windows(p, w7)))
    out["med30"] = _by_chunk(panel, lambda p: _median(windows(p, w30)))
    out["slope14"] = _by_chunk(panel, lambda p: _slope(windows(p, wd["slope"])))
    base_med = _by_chunk(panel, lambda p: _median(windows(p, length, lag)))
    base_n = _by_chunk(panel, lambda p: _count(windows(p, length, lag)))
    out["med7_vs_base"] = np.where(base_n >= need, out["med7"] - base_med, np.nan)
    out["fleet_adj_med7"] = _by_chunk(fleet_panel, lambda p: _median(windows(p, w7)))

    def mad(p):
        win = windows(p, length, lag)
        return np.nanmedian(np.abs(win - _median(win)[..., None]), axis=2)

    f_med = _by_chunk(fleet_panel, lambda p: _median(windows(p, length, lag)))
    f_mad = _by_chunk(fleet_panel, mad)
    f_n = _by_chunk(fleet_panel, lambda p: _count(windows(p, length, lag)))
    ok = (f_n >= need) & (f_mad > 0)
    out["z"] = np.where(ok, (out["fleet_adj_med7"] - f_med) / (ROBUST_SCALE * np.where(ok, f_mad, 1.0)), np.nan)
    return out


def build(tables, ev, allow):
    """One row per telemetry row: keys, the allowlisted features (bar iforest_score, added once
    the forest is fitted), and two row-filter helpers that never feed a model."""
    tel = tables["telemetry"]
    if len(tel) == 0:
        raise PipelineCheckError("features: telemetry is empty")
    check_frame(tel, "features: telemetry", ["date_key", "asset_id"],
                required=["date_key", "asset_id", "running_hours", "power_kw", "date"])
    facts = pump_facts(tables)
    t = tel.merge(facts[["asset_id", "application", "rated_kw"]], on="asset_id", how="left", validate="many_to_one")
    check_frame(t, "features: telemetry with pump facts", ["date_key", "asset_id"],
                rows=len(tel), required=["application", "rated_kw"])
    reading = t["vibration_mm_s"].notna()
    values = {
        "vibration": t["vibration_mm_s"],
        "bearing_temp": t["bearing_temp_c"],
        # A day with no running has no reading: its power of zero is not a reading.
        "power_per_rated_kw": (t["power_kw"] / t["rated_kw"]).where(reading),
        "running_hours": t["running_hours"].astype(float),
    }
    dates = pd.date_range(t["date"].min(), t["date"].max(), freq="D")
    pumps = sorted(t["asset_id"].unique())
    di = (t["date"] - dates[0]).dt.days.to_numpy()
    pi = pd.Categorical(t["asset_id"], categories=pumps).codes

    def to_panel(series):
        panel = np.full((len(dates), len(pumps)), np.nan)
        panel[di, pi] = series.to_numpy(dtype=float)
        return panel

    wd, base = ev["model"]["features"]["windows_days"], ev["model"]["features"]["baseline"]
    out = t[["asset_id", "date"]].copy()
    z_panels = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)   # all-blank windows give NaN, by design
        for s in SENSORS:
            fleet = values[s] - pd.Series(values[s]).groupby([t["date"], t["application"]]).transform("median")
            # Rounding removes floating-point noise (about 1e-16) left by the division by
            # rated kW, which would otherwise turn a zero spread into a huge z-score.
            fleet = fleet.round(FLEET_DECIMALS)
            panels = sensor_panels(to_panel(values[s]), to_panel(fleet), wd, base)
            for suffix, panel in panels.items():
                out[f"{s}_{suffix}"] = panel[di, pi]
            z_panels.append(panels["z"])
        z_stack = np.stack(z_panels)
        z_max = np.where(np.isnan(z_stack).all(axis=0), np.nan, np.nanmax(np.where(np.isnan(z_stack), -np.inf, z_stack), axis=0))
        above = np.where(z_max > Z_ABOVE, 1.0, 0.0)
        days_above = _by_chunk(above, lambda p: np.nansum(windows(p, wd["days_above_z_3"]), axis=2))
        base_n = _by_chunk(to_panel(t["vibration_mm_s"]),
                           lambda p: _count(windows(p, base["length_days"], base["ends_days_before_t"])))
    out["z_max"] = z_max[di, pi]
    out["z_days_above_3_14d"] = days_above[di, pi]

    f = facts.set_index("asset_id")
    cats = categories(tables)
    out["age_years"] = (t["date"] - t["asset_id"].map(f["install_date"])).dt.days / 365.25
    for col in ["product_group", "application", "service_contract"]:
        out[col] = pd.Categorical(t["asset_id"].map(f[col]), categories=cats[col])
    out["rated_kw"] = t["asset_id"].map(f["rated_kw"]).astype(float)
    # Row-filter helpers (never model features): a day with no running, and the readings
    # in the warm-up baseline (days t-97 to t-8).
    out["_no_running"] = (t["running_hours"] == 0) & t["vibration_mm_s"].isna() & t["bearing_temp_c"].isna()
    out["_baseline_readings"] = base_n[di, pi]
    check_frame(out, "features", KEYS, rows=len(tel), required=KEYS + ["age_years", "rated_kw"])
    return out


def feature_names(allow):
    return [c["name"] for c in allow["columns"]]


def assert_inside_allowlist(columns, allow):
    extra = sorted(set(columns) - set(feature_names(allow)))
    if extra:
        raise PipelineCheckError(f"features off the allowlist (D12): {extra}")
    return list(columns)


def check_point_in_time(build_fn, tables, pump_days, columns, *, full=None, lookback=None):
    """D11: rebuild with every telemetry row after day t deleted; the row for (pump, t) must
    not change. Returns the (pump, day, column) triples that changed: empty means it passes.

    The fleet adjustment uses only pumps of the same application on the same day, so each
    rebuild needs only that application's pumps. With `lookback`, rows more than that many
    days before t are left out too, which only makes the check stricter: a feature that
    reached further back would show as changed.
    """
    full = (build_fn(tables) if full is None else full).set_index(KEYS)
    app = tables["assets"].set_index("asset_id")["application"]
    changed = []
    for pump, t in pump_days:
        same_app = app.index[app == app[pump]]
        tel = tables["telemetry"]
        keep = (tel["date"] <= t) & tel["asset_id"].isin(same_app)
        if lookback is not None:
            keep &= tel["date"] > t - pd.Timedelta(days=lookback)
        cut = {**tables, "telemetry": tel[keep].reset_index(drop=True)}
        row = build_fn(cut).set_index(KEYS).loc[(pump, t), columns]
        before = full.loc[(pump, t), columns]
        for col in columns:
            a, b = before[col], row[col]
            same = (pd.isna(a) and pd.isna(b)) or a == b
            if not same:
                changed.append((pump, str(t.date()), col))
    return changed
