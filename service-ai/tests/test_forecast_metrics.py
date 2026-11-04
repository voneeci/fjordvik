"""Benchmarks, the MASE scale, coverage, the Winkler score and the rolling intervals, on toy values."""

import numpy as np
import pandas as pd
import pytest

from fjordvik_service.forecast import benchmarks
from fjordvik_service.forecast.backtest import Inputs, forecast_origin
from fjordvik_service.forecast.checks import PipelineCheckError
from fjordvik_service.forecast.intervals import add_intervals
from fjordvik_service.forecast.metrics import covered, mase, scale_q, winkler


def toy(n):
    months = pd.period_range("2023-01", periods=n, freq="M")
    return pd.Series(np.arange(1, n + 1, dtype=float) * 10, index=months)


def test_benchmarks_on_a_toy_series():
    train = toy(15)  # 10, 20, ... 150
    hs = [1, 2, 3]
    assert list(benchmarks.naive(train, hs)) == [150.0] * 3
    assert list(benchmarks.seasonal_naive(train, hs)) == [40.0, 50.0, 60.0]
    assert list(benchmarks.moving_average(train, hs, 3)) == [140.0] * 3
    with pytest.raises(PipelineCheckError):
        benchmarks.seasonal_naive(train, [13])


def toy_inputs(series):
    """A one-warehouse, one-family Inputs around a toy series, for the backtest's own path."""
    demand = pd.DataFrame({"warehouse": "W", "part_family": "A", "month": series.index, "units": series.to_numpy()})
    region_units = pd.DataFrame({"warehouse": "W", "region": "NOR", "month": series.index, "units": 1})
    return Inputs(demand=demand, region_units=region_units, hours=None, assets=None,
                  families=["A"], last_month=series.index[-1])


def test_the_backtest_scales_by_training_months_only():
    series = toy(20)  # 10, 20, ... 200
    origin = series.index[14]  # 15 training months
    specs = {"naive": ("naive", None)}
    fc, _ = forecast_origin(toy_inputs(series), "W", origin, specs, None, [1, 2, 3])
    assert set(fc["q"]) == {120.0}  # every y_t - y_(t-12) is 12 x 10
    later = series.copy()
    later[later.index > origin] = 1e6
    fc_later, _ = forecast_origin(toy_inputs(later), "W", origin, specs, None, [1, 2, 3])
    assert set(fc_later["q"]) == {120.0}
    assert scale_q(later) != 120.0  # the full series would give another scale
    assert mase([10, 20], [12, 16], 2.0) == 1.5
    with pytest.raises(PipelineCheckError):
        scale_q(toy(12))


def test_coverage_and_winkler_on_toy_values():
    actual, lower, upper = [5, 0, 30], [4, 2, 10], [8, 6, 20]
    assert list(covered(actual, lower, upper)) == [True, False, False]
    # widths 4, 4, 10; misses: 2 below (x 10 = 20), 10 above (x 10 = 100)
    assert list(winkler(actual, lower, upper, 0.8)) == pytest.approx([4.0, 24.0, 110.0])


def test_an_interval_uses_only_errors_already_known_at_its_origin():
    rows = []
    for o in range(1, 9):
        origin = pd.Period("2024-01", "M") + o
        for fam in ["A", "B"]:
            for h in [1, 2]:
                rows.append({"warehouse": "W", "part_family": fam, "method": "m", "origin": origin,
                             "horizon": h, "target_month": origin + h, "forecast": 100.0,
                             "actual": 100.0 + o * (1 if fam == "A" else -1), "q": 2.0})
    fc = pd.DataFrame(rows)
    out = add_intervals(fc, 0.8, 4)
    origin = pd.Period("2024-06", "M")
    known = fc[(fc["target_month"] <= origin) & (fc["horizon"] == 1)]
    e = ((known["actual"] - known["forecast"]) / known["q"]).to_numpy()
    row = out[(out["origin"] == origin) & (out["horizon"] == 1) & (out["part_family"] == "A")].iloc[0]
    assert row["lower80"] == pytest.approx(max(0.0, 100 + np.quantile(e, 0.1) * 2))
    assert row["upper80"] == pytest.approx(100 + np.quantile(e, 0.9) * 2)
    later = fc.copy()
    later.loc[later["target_month"] > origin, "actual"] = 1e6
    again = add_intervals(later, 0.8, 4)
    keep = out["origin"] <= origin
    pd.testing.assert_frame_equal(out.loc[keep, ["lower80", "upper80"]], again.loc[keep, ["lower80", "upper80"]])
    first = out[out["origin"] == out["origin"].min()]
    assert first["lower80"].isna().all()
