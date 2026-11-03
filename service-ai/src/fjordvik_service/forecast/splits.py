"""The evaluation set: dates, origins and periods, read from eval/forecast/evaluation.json (A9, E1, F1)."""

import json
from pathlib import Path

import pandas as pd

SERVICE_AI_DIR = Path(__file__).resolve().parents[3]
EVALUATION_PATH = SERVICE_AI_DIR / "eval" / "forecast" / "evaluation.json"
LOCK_PATH = SERVICE_AI_DIR / "eval" / "forecast" / "split_lock.json"


def load_evaluation(path=EVALUATION_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def month(text):
    return pd.Period(text, freq="M")


def forecast_date(origin):
    """The day a forecast from this origin is made: the first day after its last training month."""
    return (origin + 1).start_time


def lengths(ev):
    return {name: list(hs) for name, hs in ev["origins"]["forecast_lengths"].items()}


def period_ranges(ev):
    p = ev["periods"]
    return {
        "validation": (month(p["validation"]["first_target_month"]), month(p["validation"]["last_target_month"])),
        "test": (month(p["test"]["first_target_month"]), month(p["test"]["last_target_month"])),
    }


def gap_months(ev):
    return [month(m) for m in ev["periods"]["gap"]["months"]]


def period_for(origin, horizons, ev):
    """The period an origin is scored in for a forecast length, or None.

    An origin counts only if every target month of the length lies inside one period.
    """
    targets = [origin + h for h in horizons]
    for name, (first, last) in period_ranges(ev).items():
        if all(first <= t <= last for t in targets):
            return name
    return None


def origins(first_month, last_month, ev):
    """Every origin a series allows: at least the minimum training months, up to the data's last month."""
    first_origin = first_month + (ev["origins"]["min_training_months"] - 1)
    if first_origin > last_month:
        return []
    return list(pd.period_range(first_origin, last_month, freq="M"))
