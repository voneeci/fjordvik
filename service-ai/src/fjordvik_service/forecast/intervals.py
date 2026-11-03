"""80% prediction intervals from rolling backtest errors.

At each origin, the errors of earlier forecasts whose target months are already known
(on or before the origin) are divided by their series' scale q and pooled over the part
families, per horizon. Their percentiles, times this series' q, set the range.
"""

import numpy as np

from .checks import check_frame

KEYS = ["warehouse", "part_family", "method", "origin", "horizon"]


def add_intervals(forecasts, level, min_errors, errors=None, source="own"):
    """Add lower80, upper80 and interval_source to one warehouse and method's forecasts.

    errors: the forecasts whose errors set the range (default: the same forecasts).
    Tartu borrows Oulu's, labelled through `source`.
    """
    out = forecasts.copy()
    pool = (forecasts if errors is None else errors).dropna(subset=["actual"])
    scaled = (pool["actual"] - pool["forecast"]) / pool["q"]
    low_p, high_p = (1 - level) / 2, 1 - (1 - level) / 2
    out["lower80"] = np.nan
    out["upper80"] = np.nan
    for origin in out["origin"].unique():
        known = pool["target_month"] <= origin
        for h in out["horizon"].unique():
            e = scaled[known & (pool["horizon"] == h)].to_numpy()
            if len(e) < min_errors:
                continue
            rows = (out["origin"] == origin) & (out["horizon"] == h)
            lo, hi = np.quantile(e, [low_p, high_p])
            out.loc[rows, "lower80"] = np.maximum(0.0, out.loc[rows, "forecast"] + lo * out.loc[rows, "q"])
            out.loc[rows, "upper80"] = out.loc[rows, "forecast"] + hi * out.loc[rows, "q"]
    out["interval_source"] = np.where(out["lower80"].notna(), source, "none: too few earlier errors")
    return check_frame(out, "intervals", KEYS, required=KEYS + ["forecast", "q", "interval_source"])
