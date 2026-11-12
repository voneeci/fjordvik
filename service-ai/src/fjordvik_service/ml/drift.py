"""Drift monitors (M5): each sensor's 7-day median against the same pump's readings in the
same calendar month of earlier years, never the last few weeks, so the season can't look
like drift.

The measure for pump p, sensor s on day t: |7-day median - reference median| divided by
1.4826 times the reference median absolute deviation, where the reference is every reading
of p and s in t's calendar month in years before t's year. A pump-month with no earlier
year (or no spread in it) is not monitored. Monitored sensors: vibration, bearing
temperature and power, the three readings a sensor takes; running hours is a duty figure,
not a sensor reading.
"""

import warnings

import numpy as np
import pandas as pd

from ..common.checks import PipelineCheckError
from .features import ROBUST_SCALE
from .labels import open_ticket

DRIFT_SENSORS = {"vibration": "vibration_mm_s", "bearing_temp": "bearing_temp_c", "power": "power_kw"}


def measures(tel, min_share, failures=None):
    """One row per telemetry row: the drift measure per sensor (blank when not monitored).

    A reference needs readings on at least min_share of the month's days (summed over the
    earlier years); the run passes the baseline's own completeness share, 60 of 90 days.
    The monitor doesn't run on a day the pump has an open failure ticket (known on the day):
    a failure explains its own readings, as in the at-risk rows."""
    if len(tel) == 0:
        raise PipelineCheckError("drift: telemetry is empty")
    t = tel[["asset_id", "date"] + list(DRIFT_SENSORS.values())].copy()
    reading = t["vibration_mm_s"].notna()
    t["power_kw"] = t["power_kw"].where(reading)   # a day with no running has no reading
    t = t.sort_values(["asset_id", "date"]).reset_index(drop=True)
    t["year"], t["month"] = t["date"].dt.year, t["date"].dt.month
    out = t[["asset_id", "date", "year", "month"]].copy()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for name, col in DRIFT_SENSORS.items():
            med7 = t.groupby("asset_id")[col].transform(lambda s: s.rolling(7, min_periods=1).median())
            ref_med = np.full(len(t), np.nan)
            ref_mad = np.full(len(t), np.nan)
            for (pump, month), g in t.groupby(["asset_id", "month"]):
                years = g["year"].to_numpy()
                vals = g[col].to_numpy(dtype=float)
                for y in np.unique(years):
                    ref = vals[(years < y) & ~np.isnan(vals)]
                    days_in_month = pd.Timestamp(year=int(y), month=int(month), day=1).days_in_month
                    if len(ref) == 0 or len(ref) < min_share * days_in_month:
                        continue
                    m = np.median(ref)
                    rows = g.index[years == y]
                    ref_med[rows] = m
                    ref_mad[rows] = np.median(np.abs(ref - m))
            ok = ~np.isnan(ref_mad) & (ref_mad > 0)
            out[name] = np.where(ok, np.abs(med7.to_numpy() - ref_med) / (ROBUST_SCALE * np.where(ok, ref_mad, 1.0)), np.nan)
    if failures is not None:
        ticket = open_ticket(out, failures)
        out.loc[ticket, list(DRIFT_SENSORS)] = np.nan
    out["drift_max"] = out[list(DRIFT_SENSORS)].max(axis=1, skipna=True)
    return out


def _no_failure_after(m, failures, horizon, data_end):
    """True on days with no failure of the pump reported in (t, t+horizon] up to data_end."""
    out = np.ones(len(m), dtype=bool)
    rep = {p: g["reported_date"].to_numpy(dtype="datetime64[ns]") for p, g in failures.groupby("asset_id")}
    span = np.timedelta64(horizon, "D")
    end = np.datetime64(data_end, "ns")
    for pump, idx in m.groupby("asset_id").indices.items():
        r = rep.get(pump)
        if r is None:
            continue
        t = m["date"].to_numpy(dtype="datetime64[ns]")[idx]
        upper = np.minimum(t + span, end)
        n = np.searchsorted(r, upper, side="right") - np.searchsorted(r, t, side="right")
        out[idx] = n == 0
    return out


def pump_months(m, failures, horizon, data_end, first, last):
    """Per monitored pump-month between first and last: the highest measure on a day with no
    failure in the following horizon days (the false-flag measure). A flag with fewer than
    horizon days of data after it counts as false when no failure follows by data_end."""
    sel = m[(m["date"] >= first) & (m["date"] <= last)].copy()
    sel["_clear"] = _no_failure_after(sel, failures, horizon, data_end)
    sel["_false_measure"] = sel["drift_max"].where(sel["_clear"])
    g = sel.groupby(["asset_id", "year", "month"])
    pm = pd.DataFrame({"monitored": g["drift_max"].count() > 0, "false_measure": g["_false_measure"].max()})
    return pm[pm["monitored"]]


def false_share(pm, level):
    return float((pm["false_measure"] >= level).sum() / len(pm)) if len(pm) else float("nan")


def choose_level(pm, max_share):
    """The lowest level whose false-flag share is at most max_share, over the distinct
    false-flag measures (and one above them all, should none qualify)."""
    measured = np.sort(pm["false_measure"].dropna().to_numpy())
    values = np.unique(measured)
    counts = len(measured) - np.searchsorted(measured, values, side="left")   # months at or above each value
    ok = counts / len(pm) <= max_share
    if ok.any():
        return float(values[np.argmax(ok)])
    return float(np.nextafter(values[-1], np.inf))


def detection(m, scenarios, level, within_days):
    """Per changed pump: the first day its changed sensor is flagged, from its start date."""
    name_of = {v: k for k, v in DRIFT_SENSORS.items()}
    rows = []
    for rec in scenarios.itertuples():
        sensor = name_of.get(rec.sensor, rec.sensor)
        start = pd.Timestamp(rec.start_date)
        g = m[(m["asset_id"] == rec.asset_id) & (m["date"] >= start)]
        monitored = bool(g[sensor].notna().any()) if sensor in g else False
        flagged = g[g[sensor] >= level] if sensor in g else g.iloc[0:0]
        first = flagged["date"].min() if len(flagged) else pd.NaT
        days = int((first - start).days) if pd.notna(first) else None
        rows.append({"scenario": rec.scenario, "asset_id": rec.asset_id, "sensor": rec.sensor,
                     "start_date": start, "monitored": monitored, "first_flag_date": first,
                     "days_to_flag": days, "flagged_within_limit": days is not None and days <= within_days})
    return pd.DataFrame(rows)
