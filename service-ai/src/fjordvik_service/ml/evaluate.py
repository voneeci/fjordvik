"""Evaluation only (D10): the one module in fjordvik_service that reads the answer key.

The answer key in data/generator-truth/ marks which planted failures gave a warning. It is
read here for the recall of warned failures, the count of unwarned ones and the
visit-every-pump plan, after the model, threshold and alerts are fixed. No feature, label,
setting or threshold comes from it.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from ..common.checks import PipelineCheckError
from .splits import REPO_DIR

ANSWER_KEY = REPO_DIR / "data" / "generator-truth" / "failures.csv"
ANSWER_KEY_COLUMNS = ["asset_id", "failure_date", "warned"]


def warned_flags(failures, path=ANSWER_KEY):
    """The answer key's warned flag for each failure row, matched on pump and date."""
    key = pd.read_csv(Path(path), usecols=ANSWER_KEY_COLUMNS, dtype={"warned": str})
    key = key.assign(failure_date=pd.to_datetime(key["failure_date"]), warned=key["warned"] == "1")
    if key.duplicated(["asset_id", "failure_date"]).any():
        raise PipelineCheckError("answer key: two failures share a pump and date")
    merged = failures[["asset_id", "reported_date"]].merge(
        key, left_on=["asset_id", "reported_date"], right_on=["asset_id", "failure_date"], how="left", validate="one_to_one")
    if merged["failure_date"].isna().any():
        raise PipelineCheckError("answer key: a failure event has no answer key row")
    return merged["warned"].to_numpy(dtype=bool)


def plans(fails, pumps_in_window, alert_days, c, missed_key="central"):
    """The cost of the visit-none and visit-every-pump plans over one alert window.

    Visit every pump: one visit per whole 30 days of the window for every pump with a
    telemetry row in it; it is given every warned failure (generous to it), misses the
    unwarned ones, and every other visit is wasted.
    """
    cm, cw = c["missed_failure"][missed_key], c["wasted_visit"]
    failures, warned = len(fails), int(fails["_warned"].sum())
    visits = pumps_in_window * (alert_days // 30)
    return {
        "visit_none": {"visits": 0, "caught": 0, "missed": failures, "wasted": 0, "cost_eur": failures * cm},
        "visit_every_pump": {"visits": visits, "caught": warned, "missed": failures - warned,
                             "wasted": visits - warned, "cost_eur": (failures - warned) * cm + (visits - warned) * cw},
    }


def per_pump(outcomes, fails, pumps, alert_days):
    """Additive counts per pump, for the pump resamples."""
    idx = pd.Index(pumps, name="asset_id")
    out = pd.DataFrame(index=idx)
    for k in ["caught", "wasted", "neither"]:
        out[k] = outcomes[outcomes["outcome"] == k].groupby("asset_id").size().reindex(idx, fill_value=0)
    out["failures"] = fails.groupby("asset_id").size().reindex(idx, fill_value=0)
    out["warned"] = fails[fails["_warned"]].groupby("asset_id").size().reindex(idx, fill_value=0)
    out["visits_every"] = alert_days // 30
    return out.astype(np.int64)
