"""D11 and F2: a forecast uses only what was known at its forecast date."""

import pandas as pd
import pandas.testing as pdt

from fjordvik_service.forecast import drivers as drv
from fjordvik_service.forecast.backtest import build_inputs, forecast_origin, method_specs
from fjordvik_service.forecast.splits import forecast_date

SETTINGS = {"moving_average_window": 6, "driver_model_season_term": [False, True]}


def before(raw, made):
    """The four tables with every row recorded on or after `made` deleted."""
    key = int(made.strftime("%Y%m%d"))
    return (raw["orders"][raw["orders"]["date_key"] < key], raw["parts"],
            raw["assets"][raw["assets"]["install_date"] < made],
            raw["telemetry"][raw["telemetry"]["date_key"] < key])


def test_rebuilding_with_later_rows_deleted_changes_no_driver(raw, full_inputs, ev):
    for text in ["2024-03", "2024-09", "2025-03", "2025-09"]:
        origin = pd.Period(text, "M")
        cut = build_inputs(*before(raw, forecast_date(origin)), ev)
        full = drv.drivers_at(full_inputs.hours, full_inputs.assets, origin, 6)
        pdt.assert_frame_equal(drv.drivers_at(cut.hours, cut.assets, origin, 6), full)
        for wh in ["FI03", "EE02"]:
            first = full_inputs.first_month(wh)
            if first > origin:
                continue
            assert drv.unit_shares(cut.region_units, wh, first, origin) == \
                drv.unit_shares(full_inputs.region_units, wh, first, origin)


def test_changing_later_data_moves_no_forecast(raw, full_inputs, ev):
    origin = pd.Period("2024-09", "M")
    made = forecast_date(origin)
    key = int(made.strftime("%Y%m%d"))
    orders, telemetry = raw["orders"].copy(), raw["telemetry"].copy()
    orders.loc[orders["date_key"] >= key, "quantity"] *= 5
    telemetry.loc[telemetry["date_key"] >= key, "running_hours"] *= 3
    extra = raw["assets"].iloc[[0]].assign(asset_id="A9999", install_date=made + pd.Timedelta(days=3))
    changed = build_inputs(orders, raw["parts"], pd.concat([raw["assets"], extra]), telemetry, ev)
    specs = method_specs(SETTINGS)
    horizons = list(range(1, 7))
    a, _ = forecast_origin(full_inputs, "FI03", origin, specs,
                           drv.drivers_at(full_inputs.hours, full_inputs.assets, origin, 6), horizons)
    b, _ = forecast_origin(changed, "FI03", origin, specs,
                           drv.drivers_at(changed.hours, changed.assets, origin, 6), horizons)
    pdt.assert_frame_equal(a.drop(columns="actual"), b.drop(columns="actual"))
    assert not a["actual"].equals(b["actual"])


def test_every_driver_value_was_known_by_the_forecast_date(full_inputs):
    for text in ["2024-03", "2024-12", "2025-06", "2025-12"]:
        origin = pd.Period(text, "M")
        d = drv.drivers_at(full_inputs.hours, full_inputs.assets, origin, 6)
        assert (d["known_from"] <= d["forecast_date"]).all()
        assert set(d.loc[d["month"] > origin, "kind"]) == {"forecast"}
        assert set(d.loc[d["month"] <= origin, "kind"]) == {"actual"}
        rh = d[d["driver"] == "running_hours"].set_index(["region", "month"])["value"]
        for (region, m), value in rh.items():
            if m > origin:
                assert value == rh[(region, m - 12)]
