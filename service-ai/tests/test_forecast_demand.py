"""The demand is every order line, per warehouse, part family and month, with no backfilling."""

import pandas as pd


def test_monthly_units_add_up_to_the_order_lines(raw, full_inputs, ev):
    demand = full_inputs.demand
    raw_units = raw["orders"].groupby("site_id")["quantity"].sum()
    assert demand.groupby("warehouse")["units"].sum().to_dict() == raw_units.to_dict()
    families = ev["demand"]["families"]
    assert sorted(demand["part_family"].unique()) == sorted(families)
    assert full_inputs.first_month("FI03") == pd.Period("2023-01", "M")
    assert full_inputs.first_month("EE02") == pd.Period("2024-07", "M")
    assert full_inputs.last_month == pd.Period("2025-12", "M")
    assert len(demand[demand["warehouse"] == "FI03"]) == len(families) * 36
    assert len(demand[demand["warehouse"] == "EE02"]) == len(families) * 18
