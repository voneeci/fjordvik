"""Rolling-origin backtest (F1): every method forecasts from every origin, with only the past."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import benchmarks, drivers as drv
from .checks import PipelineCheckError, check_frame
from .demand import order_months, monthly_demand, read_orders, read_parts, region_units
from .intervals import add_intervals
from .metrics import covered, mase, scale_q, winkler
from .model import driver_forecast
from .splits import forecast_date, lengths, month, origins, period_for

FORECAST_KEYS = ["warehouse", "part_family", "method", "origin", "horizon"]


@dataclass
class Inputs:
    demand: pd.DataFrame
    region_units: pd.DataFrame
    hours: pd.DataFrame
    assets: pd.DataFrame
    families: list
    last_month: pd.Period

    def series(self, warehouse, family):
        rows = self.demand[(self.demand["warehouse"] == warehouse) & (self.demand["part_family"] == family)]
        return rows.set_index("month")["units"].sort_index()

    def warehouses(self):
        return sorted(self.demand["warehouse"].unique())

    def first_month(self, warehouse):
        return self.demand.loc[self.demand["warehouse"] == warehouse, "month"].min()


def build_inputs(orders, parts, assets, telemetry, ev):
    families = list(ev["demand"]["families"])
    lines = order_months(orders, parts, families)
    pumps = drv.with_regions(assets, ev)
    return Inputs(
        demand=monthly_demand(lines, families),
        region_units=region_units(lines),
        hours=drv.fleet_hours(telemetry, pumps),
        assets=pumps,
        families=families,
        last_month=lines["month"].max(),
    )


def load_inputs(data_dir, ev, last_month=None):
    """Read the tables; with `last_month`, keep only what was recorded by its end."""
    orders, parts = read_orders(data_dir), read_parts(data_dir)
    assets, telemetry = drv.read_assets(data_dir), drv.read_telemetry(data_dir)
    if last_month is not None:
        cut = (month(last_month) + 1).start_time
        cut_key = int(cut.strftime("%Y%m%d"))
        orders = orders[orders["date_key"] < cut_key]
        telemetry = telemetry[telemetry["date_key"] < cut_key]
        assets = assets[assets["install_date"] < cut]
    return build_inputs(orders, parts, assets, telemetry, ev)


def method_specs(settings):
    """Method id to (kind, parameter). Settings may list several candidates (validation)."""
    windows = settings["moving_average_window"]
    seasons = settings["driver_model_season_term"]
    specs = {"naive": ("naive", None), "seasonal_naive": ("seasonal_naive", None)}
    for w in windows if isinstance(windows, list) else [windows]:
        specs[f"moving_average_w{w}"] = ("moving_average", w)
    for s in seasons if isinstance(seasons, list) else [seasons]:
        specs[driver_id(s)] = ("driver", s)
    return specs


def driver_id(season):
    return "driver_season" if season else "driver_base"


def forecast_origin(inputs, warehouse, origin, specs, regional, horizons):
    """All methods' forecasts for one warehouse and origin, with each series' scale q."""
    first = inputs.first_month(warehouse)
    shares = drv.unit_shares(inputs.region_units, warehouse, first, origin)
    blended = drv.blend(regional, shares) if any(k == "driver" for k, _ in specs.values()) else None
    targets = [origin + h for h in horizons]
    rows = []
    for family in inputs.families:
        series = inputs.series(warehouse, family)
        train = series[series.index <= origin]
        q = scale_q(train)
        actual = [float(series.get(t, np.nan)) for t in targets]
        for method, (kind, param) in specs.items():
            if kind == "naive":
                f = benchmarks.naive(train, horizons)
            elif kind == "seasonal_naive":
                f = benchmarks.seasonal_naive(train, horizons)
            elif kind == "moving_average":
                f = benchmarks.moving_average(train, horizons, param)
            else:
                f = driver_forecast(train, blended, origin, horizons, param)
            for h, t, fv, av in zip(horizons, targets, f, actual):
                rows.append((warehouse, family, method, origin, h, t, float(fv), av, q))
    out = pd.DataFrame(rows, columns=FORECAST_KEYS + ["target_month", "forecast", "actual", "q"])
    shares_used = pd.DataFrame(
        [(warehouse, r, origin, "unit_share", s, "actual") for r, s in sorted(shares.items())],
        columns=["warehouse", "region", "month", "driver", "value", "kind"],
    )
    return out, shares_used


def count_test_origins(inputs, ev):
    """Origins each warehouse has in the test period, per forecast length."""
    counts = {}
    for wh in inputs.warehouses():
        all_origins = origins(inputs.first_month(wh), inputs.last_month, ev)
        counts[wh] = {name: sum(period_for(o, hs, ev) == "test" for o in all_origins)
                      for name, hs in lengths(ev).items()}
    return counts


def run(inputs, ev, settings):
    """Forecasts with intervals for every warehouse, method and origin, and the drivers used."""
    specs = method_specs(settings)
    max_h = ev["origins"]["max_horizon"]
    horizons = list(range(1, max_h + 1))
    per_wh = {wh: origins(inputs.first_month(wh), inputs.last_month, ev) for wh in inputs.warehouses()}
    needed = sorted({o for os in per_wh.values() for o in os})
    regional = {o: drv.drivers_at(inputs.hours, inputs.assets, o, max_h) for o in needed}
    frames, share_frames = [], []
    for wh, os in per_wh.items():
        for o in os:
            fc, shares = forecast_origin(inputs, wh, o, specs, regional[o], horizons)
            frames.append(fc)
            share_frames.append(shares.assign(origin=o, forecast_date=forecast_date(o), known_from=forecast_date(o)))
    if not frames:
        raise PipelineCheckError("backtest: no warehouse has enough history for an origin")
    forecasts = check_frame(pd.concat(frames, ignore_index=True), "backtest forecasts", FORECAST_KEYS,
                            required=FORECAST_KEYS + ["target_month", "forecast", "q"])
    forecasts["forecast_date"] = forecasts["origin"].map(forecast_date)
    forecasts = with_intervals(forecasts, inputs, ev)
    regional_rows = pd.concat(regional.values(), ignore_index=True).assign(warehouse="all")
    used = pd.concat([regional_rows, *share_frames], ignore_index=True)
    used = used[["origin", "forecast_date", "warehouse", "region", "month", "driver", "value", "kind", "known_from"]]
    used = check_frame(used, "drivers used", ["origin", "warehouse", "region", "month", "driver"])
    return forecasts, used


def with_intervals(forecasts, inputs, ev):
    """Own rolling errors for warehouses meeting the minimum; the others borrow from the
    warehouse with the most test origins, labelled so."""
    spec = ev["methods"]["intervals"]
    counts = count_test_origins(inputs, ev)
    minimum = ev["minimum_test_origins"]["value"]
    longest = max(lengths(ev), key=lambda name: len(lengths(ev)[name]))
    lender = max(counts, key=lambda wh: (counts[wh][longest], wh))
    parts = []
    for (wh, method), grp in forecasts.groupby(["warehouse", "method"], sort=True):
        if counts[wh][longest] >= minimum or wh == lender:
            parts.append(add_intervals(grp, spec["level"], spec["min_errors_per_horizon"]))
        else:
            errors = forecasts[(forecasts["warehouse"] == lender) & (forecasts["method"] == method)]
            parts.append(add_intervals(grp, spec["level"], spec["min_errors_per_horizon"], errors=errors,
                                       source=f"borrowed from {lender}"))
    return pd.concat(parts, ignore_index=True)


def score(forecasts, ev, periods):
    """MASE, coverage and Winkler per series and origin, for the given periods only."""
    level = ev["methods"]["intervals"]["level"]
    detail = []
    for (wh, family, method, origin), grp in forecasts.groupby(["warehouse", "part_family", "method", "origin"]):
        for name, hs in lengths(ev).items():
            period = period_for(origin, hs, ev)
            if period not in periods:
                continue
            sub = grp[grp["horizon"].isin(hs)]
            if sub["actual"].isna().any() or len(sub) != len(hs):
                raise PipelineCheckError(f"score: {wh} {family} {origin} lacks actuals for {period}")
            q = float(sub["q"].iloc[0])
            has = sub["lower80"].notna()
            w = winkler(sub.loc[has, "actual"], sub.loc[has, "lower80"], sub.loc[has, "upper80"], level)
            detail.append({
                "warehouse": wh, "part_family": family, "method": method, "period": period, "length": name,
                "origin": origin, "q": q,
                "mae": float(np.mean(np.abs(sub["actual"] - sub["forecast"]))),
                "mase": mase(sub["actual"], sub["forecast"], q),
                "n_interval": int(has.sum()),
                "n_covered": int(covered(sub.loc[has, "actual"], sub.loc[has, "lower80"], sub.loc[has, "upper80"]).sum()),
                "winkler_sum": float(w.sum()), "winkler_scaled_sum": float((w / q).sum()),
            })
    detail = pd.DataFrame(detail)
    keys = ["warehouse", "part_family", "method", "period", "length", "origin"]
    check_frame(detail, "score detail", keys)
    by_series = aggregate(detail, ["warehouse", "part_family", "method", "period", "length"], "n_origins")
    by_origin = aggregate(detail, ["warehouse", "method", "period", "length", "origin"], "n_series")
    return by_series, by_origin


def aggregate(detail, keys, count_name):
    g = detail.groupby(keys)
    out = g.agg(mase=("mase", "mean"), mae=("mae", "mean"), n_interval=("n_interval", "sum"),
                n_covered=("n_covered", "sum"), winkler_sum=("winkler_sum", "sum"),
                winkler_scaled_sum=("winkler_scaled_sum", "sum"))
    out.insert(0, count_name, g.size())
    with np.errstate(invalid="ignore", divide="ignore"):
        out["coverage"] = out["n_covered"] / out["n_interval"].where(out["n_interval"] > 0)
        out["winkler"] = out["winkler_sum"] / out["n_interval"].where(out["n_interval"] > 0)
        out["winkler_scaled"] = out["winkler_scaled_sum"] / out["n_interval"].where(out["n_interval"] > 0)
    return out.drop(columns=["winkler_sum", "winkler_scaled_sum"]).reset_index()


def overall(by_series, period, length):
    """Mean MASE over each warehouse's part family series, per warehouse and method."""
    rows = by_series[(by_series["period"] == period) & (by_series["length"] == length)]
    return rows.groupby(["warehouse", "method"])["mase"].mean()


def choose(by_series, ev):
    """The settings chosen on validation origins only: lowest overall 6-month MASE, ties to the simpler."""
    rule = ev["chosen_on_validation"]
    longest = max(lengths(ev), key=lambda name: len(lengths(ev)[name]))
    rows = by_series[(by_series["period"] == "validation") & (by_series["length"] == longest)]
    if rows.empty:
        raise PipelineCheckError("choose: no validation origins")
    pooled = rows.groupby("method")["mase"].mean()

    def pick(order, method_of):
        best = None
        for value in order:
            if best is None or pooled[method_of(value)] < pooled[method_of(best)]:
                best = value
        return best

    simpler = rule["simpler_first"]
    window = pick(simpler["moving_average_window"], lambda w: f"moving_average_w{w}")
    season = pick(simpler["driver_model_season_term"], driver_id)
    return {"moving_average_window": window, "driver_model_season_term": season}, pooled.to_dict()
