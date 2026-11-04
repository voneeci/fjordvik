"""Monthly demand in units per warehouse and part family, from every order line."""

from pathlib import Path

import pandas as pd

from .checks import PipelineCheckError, check_frame


def month_of(date_keys):
    """Calendar month of YYYYMMDD date keys."""
    return pd.to_datetime(date_keys.astype(str), format="%Y%m%d").dt.to_period("M")


def read_orders(data_dir):
    orders = pd.read_csv(
        Path(data_dir) / "fact_parts_order.csv",
        usecols=["order_id", "order_line", "date_key", "site_id", "region_id", "part_id", "quantity"],
        dtype={"order_id": str, "site_id": str, "region_id": str, "part_id": str},
    )
    return check_frame(orders, "read orders", ["order_id", "order_line"])


def read_parts(data_dir):
    parts = pd.read_csv(
        Path(data_dir) / "dim_part.csv", usecols=["part_id", "part_family"], dtype=str
    )
    return check_frame(parts, "read parts", ["part_id"])


def order_months(orders, parts, families):
    """Each order line with its month and part family."""
    lines = orders.merge(parts, on="part_id", how="left", validate="many_to_one")
    check_frame(lines, "join part families", ["order_id", "order_line"], rows=len(orders))
    unknown = sorted(set(lines["part_family"]) - set(families))
    if unknown:
        raise PipelineCheckError(f"join part families: families not in the evaluation set {unknown}")
    return lines.assign(month=month_of(lines["date_key"]))


def monthly_demand(lines, families):
    """Units per warehouse, family and month, from each warehouse's first month (no backfilling).

    A family with no orders in a month is a zero, from the warehouse's first month to the
    data's last month.
    """
    last = lines["month"].max()
    sums = lines.groupby(["site_id", "part_family", "month"])["quantity"].sum()
    frames = []
    for warehouse, first in lines.groupby("site_id")["month"].min().sort_index().items():
        months = pd.period_range(first, last, freq="M")
        index = pd.MultiIndex.from_product(
            [[warehouse], families, months], names=["site_id", "part_family", "month"]
        )
        frames.append(sums.reindex(index, fill_value=0).rename("units").reset_index())
    demand = pd.concat(frames, ignore_index=True).rename(columns={"site_id": "warehouse"})
    demand["units"] = demand["units"].astype(int)
    expected = sum(len(families) * len(pd.period_range(f, last, freq="M"))
                   for f in lines.groupby("site_id")["month"].min())
    check_frame(demand, "monthly demand", ["warehouse", "part_family", "month"], rows=expected)
    if int(demand["units"].sum()) != int(lines["quantity"].sum()):
        raise PipelineCheckError("monthly demand: units do not add up to the order lines")
    return demand


def region_units(lines):
    """Units per warehouse, customer region and month, for blending the regional drivers."""
    units = (
        lines.groupby(["site_id", "region_id", "month"])["quantity"].sum().rename("units").reset_index()
        .rename(columns={"site_id": "warehouse", "region_id": "region"})
    )
    return check_frame(units, "region units", ["warehouse", "region", "month"])
