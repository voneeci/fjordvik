"""Drivers from the connected fleet, as they were known at each forecast date (D11, F2).

Two drivers per customer region: the fleet's mean running hours per pump-day, and its
mean age. Each value carries `kind` (actual, or forecast at the forecast date) and
`known_from`, the first day it could have been known.
"""

from pathlib import Path

import pandas as pd

from .checks import PipelineCheckError, check_frame
from .demand import month_of
from .splits import forecast_date

DRIVERS = ["running_hours", "mean_age_years"]
DAYS_PER_YEAR = 365.25  # calendar convention for ages in years


def region_of_country(ev):
    return {c: r for r, countries in ev["methods"]["drivers"]["regions"].items() for c in countries}


def read_assets(data_dir):
    assets = pd.read_csv(
        Path(data_dir) / "dim_asset.csv", usecols=["asset_id", "country", "install_date"], dtype=str
    )
    assets["install_date"] = pd.to_datetime(assets["install_date"], format="%Y-%m-%d")
    return check_frame(assets, "read assets", ["asset_id"])


def read_telemetry(data_dir):
    telemetry = pd.read_csv(
        Path(data_dir) / "fact_asset_telemetry.csv",
        usecols=["date_key", "asset_id", "running_hours"],
        dtype={"asset_id": str},
    )
    return check_frame(telemetry, "read telemetry", ["date_key", "asset_id"])


def with_regions(assets, ev):
    mapping = region_of_country(ev)
    out = assets.assign(region=assets["country"].map(mapping))
    return check_frame(out, "pump regions", ["asset_id"])


def fleet_hours(telemetry, assets):
    """Running hours and pump-days per region and month."""
    joined = telemetry.merge(assets[["asset_id", "region"]], on="asset_id", how="left", validate="many_to_one")
    check_frame(joined, "telemetry regions", ["date_key", "asset_id"], rows=len(telemetry))
    joined["month"] = month_of(joined["date_key"])
    hours = (
        joined.groupby(["region", "month"])["running_hours"]
        .agg(hours="sum", pump_days="count").reset_index()
    )
    return check_frame(hours, "fleet hours", ["region", "month"])


def mean_age(assets, region, installed_before, at):
    """Mean age in years at `at` of the region's pumps installed before `installed_before`."""
    pumps = assets[(assets["region"] == region) & (assets["install_date"] < installed_before)]
    if pumps.empty:
        raise PipelineCheckError(f"mean age: no pumps in {region} before {installed_before.date()}")
    return float(((at - pumps["install_date"]).dt.days / DAYS_PER_YEAR).mean())


def drivers_at(hours, assets, origin, max_horizon):
    """Every driver value a forecast from `origin` may use, as known at its forecast date.

    Training months (up to the origin) carry actual values. Forecast months carry
    forecasts: running hours from the same month a year earlier, and the age of the
    pumps registered by the forecast date, aged forward.
    """
    made = forecast_date(origin)
    known = hours[hours["month"] <= origin]
    rows = []
    for region, grp in known.groupby("region"):
        by_month = grp.set_index("month")
        for m, rec in by_month.iterrows():
            next_month = (m + 1).start_time
            rows.append((region, m, "running_hours", rec["hours"] / rec["pump_days"], "actual", next_month))
            rows.append((region, m, "mean_age_years", mean_age(assets, region, next_month, next_month),
                         "actual", next_month))
        for h in range(1, max_horizon + 1):
            m = origin + h
            last_year = m - 12
            if last_year not in by_month.index:
                raise PipelineCheckError(f"drivers at {origin}: no running hours for {last_year} in {region}")
            rec = by_month.loc[last_year]
            rows.append((region, m, "running_hours", rec["hours"] / rec["pump_days"], "forecast",
                         (last_year + 1).start_time))
            rows.append((region, m, "mean_age_years", mean_age(assets, region, made, (m + 1).start_time),
                         "forecast", made))
    out = pd.DataFrame(rows, columns=["region", "month", "driver", "value", "kind", "known_from"])
    out.insert(0, "forecast_date", made)
    out.insert(0, "origin", origin)
    check_frame(out, f"drivers at {origin}", ["region", "month", "driver"])
    if (out["known_from"] > made).any():
        raise PipelineCheckError(f"drivers at {origin}: a value known only after the forecast date")
    return out


def unit_shares(region_units, warehouse, first_month, origin):
    """The warehouse's share of units per region over its training months."""
    train = region_units[(region_units["warehouse"] == warehouse)
                         & (region_units["month"] >= first_month) & (region_units["month"] <= origin)]
    totals = train.groupby("region")["units"].sum()
    if totals.sum() <= 0:
        raise PipelineCheckError(f"unit shares: no units for {warehouse} by {origin}")
    return (totals / totals.sum()).to_dict()


def blend(drivers, shares):
    """One value per month and driver for a warehouse: the regions weighted by its unit shares."""
    wide = drivers.pivot(index=["month", "driver"], columns="region", values="value")
    used = [r for r, w in shares.items() if w > 0]
    check_frame(wide[used].reset_index(), "regional drivers", ["month", "driver"])
    blended = sum(wide[r] * shares[r] for r in used).unstack("driver")[DRIVERS]
    return check_frame(blended.reset_index(), "blended drivers", ["month"]).set_index("month")
