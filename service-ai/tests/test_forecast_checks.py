"""D15: each pipeline step stops with an error on an empty input, a missing value or a duplicate key."""

import numpy as np
import pandas as pd
import pytest

from fjordvik_service.forecast.checks import PipelineCheckError
from fjordvik_service.forecast.demand import monthly_demand, order_months


def test_empty_input_raises(raw, ev):
    with pytest.raises(PipelineCheckError, match="rows"):
        order_months(raw["orders"].iloc[0:0], raw["parts"], ev["demand"]["families"])


def test_missing_value_raises(raw, ev):
    orders = raw["orders"].head(200).copy()
    orders.loc[orders.index[5], "quantity"] = np.nan
    with pytest.raises(PipelineCheckError, match="missing values"):
        monthly_demand(order_months(orders, raw["parts"], ev["demand"]["families"]), ev["demand"]["families"])


def test_duplicate_key_raises(raw, ev):
    orders = raw["orders"].head(200)
    doubled = pd.concat([orders, orders.iloc[[7]]], ignore_index=True)
    with pytest.raises(PipelineCheckError, match="duplicate keys"):
        order_months(doubled, raw["parts"], ev["demand"]["families"])
