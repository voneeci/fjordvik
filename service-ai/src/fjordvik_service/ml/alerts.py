"""Alerts, caught and wasted visits, cost, and the threshold (M3, no answer key).

One alert is one visit: it opens when the score reaches the threshold on a pump with no open
alert, and the pump then stays quiet for 30 days (the alert day and the 29 after it), so a
daily alert can't be counted as many visits. An alert catches a failure reported 7 to 30
days later; with no failure in the next 30 days it is wasted; a failure 1 to 6 days later
is neither caught nor wasted. The costs are read from data/scenarios/planning_inputs.json
when the code runs; no cost is typed here.
"""

import bisect
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..common.checks import PipelineCheckError, check_frame
from ..common.stamps import sha256_file
from .splits import PLANNING_INPUTS


def costs(ev, path=PLANNING_INPUTS):
    """The two costs, in euros per event, read from the planning inputs and checked by SHA-256."""
    inputs = ev["cost"]["inputs"]
    if sha256_file(path) != inputs["source_sha256"]:
        raise PipelineCheckError("planning_inputs.json differs from the evaluation set's checksum")
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    def get(key):
        value = data
        for part in key.split("."):
            value = value[part]
        return float(value)

    m = inputs["missed_failure"]
    return {"wasted_visit": get(inputs["wasted_visit"]["key"]),
            "missed_failure": {name: get(m[name]["key"]) for name in ["low", "central", "high"]}}


def _days(dates):
    return (pd.to_datetime(dates).to_numpy(dtype="datetime64[D]")).astype(np.int64)


def alert_days(scores, threshold, quiet):
    """Alert openings: (asset_id, date) where the score reaches the threshold on a quiet pump."""
    check_frame(scores, "alerts: scores", ["asset_id", "date"], min_rows=0, required=["asset_id", "date", "score"])
    hot = scores[scores["score"] >= threshold].sort_values(["asset_id", "date"])
    out = []
    for pump, g in hot.groupby("asset_id", sort=True):
        next_ok = None
        for d, day_n in zip(g["date"], _days(g["date"]), strict=True):
            if next_ok is None or day_n >= next_ok:
                out.append((pump, d))
                next_ok = day_n + quiet
    return pd.DataFrame(out, columns=["asset_id", "date"])


def _classify_pump(alert_days_n, fail_days, fail_warned, lo, hi, horizon):
    """Outcome per alert day for one pump, and which failures it caught."""
    caught_idx, outcomes = set(), []
    for d in alert_days_n:
        gaps = [(f - d, i) for i, f in enumerate(fail_days) if 1 <= f - d <= horizon]
        catch = [i for g, i in gaps if lo <= g <= hi and fail_warned[i] and i not in caught_idx]
        if catch:
            caught_idx.add(catch[0])
            outcomes.append(("caught", catch[0]))
        elif any(fail_warned[i] for _, i in gaps):
            outcomes.append(("neither", None))
        else:
            outcomes.append(("wasted", None))
    return outcomes, caught_idx


def classify(alerts, failures, ev, warned=None):
    """Each alert's outcome. warned: a flag per failure row (the answer key's view); None
    counts every failure as preventable, the view the threshold is chosen in."""
    a = ev["alerts"]
    lo, hi = a["caught_days_before"]["min"], a["caught_days_before"]["max"]
    horizon = ev["periods"]["label_window_days"]
    flags = np.ones(len(failures), dtype=bool) if warned is None else np.asarray(warned, dtype=bool)
    fails = failures.assign(_warned=flags, _day=_days(failures["reported_date"]))
    rows, caught_rows = [], set()
    by_pump = {p: g for p, g in fails.groupby("asset_id")}
    for pump, g in alerts.groupby("asset_id", sort=True):
        f = by_pump.get(pump, fails.iloc[0:0])
        outcomes, caught = _classify_pump(list(_days(g["date"])), list(f["_day"]), list(f["_warned"]), lo, hi, horizon)
        for d, (outcome, i) in zip(g["date"], outcomes, strict=True):
            rows.append({"asset_id": pump, "date": d, "outcome": outcome,
                         "caught_failure_date": f["reported_date"].iloc[i] if i is not None else pd.NaT})
        caught_rows |= {f.index[i] for i in caught}
    out = pd.DataFrame(rows, columns=["asset_id", "date", "outcome", "caught_failure_date"])
    return out, fails.assign(_caught=fails.index.isin(caught_rows))


def summarise(outcomes, fails, c, missed_cost_key="central"):
    """Counts, recall of warned failures and the model plan's cost."""
    n = {k: int((outcomes["outcome"] == k).sum()) for k in ["caught", "wasted", "neither"]}
    failures, warned = len(fails), int(fails["_warned"].sum())
    caught = int(fails["_caught"].sum())
    missed = failures - caught
    return {"alerts": len(outcomes), **n, "failures": failures, "warned_failures": warned,
            "unwarned_failures": failures - warned, "missed": missed,
            "recall_of_warned_failures": (caught / warned) if warned else None,
            "cost_eur": missed * c["missed_failure"][missed_cost_key] + n["wasted"] * c["wasted_visit"]}


def failures_in_window(failures, first, last):
    r = failures["reported_date"]
    return failures[(r >= first) & (r <= last)].reset_index(drop=True)


def choose_threshold(scores, failures, ev, c):
    """M3: the lowest-cost threshold over every distinct score, every failure counted as
    preventable, at the central missed-failure cost. Ties go to fewer visits, then to the
    higher threshold. Works down the scores one at a time, recomputing only the pump whose
    hot days changed, so all candidates are tried exactly."""
    a = ev["alerts"]
    lo, hi, quiet = a["caught_days_before"]["min"], a["caught_days_before"]["max"], a["quiet_days"]
    horizon = ev["periods"]["label_window_days"]
    cm, cw = c["missed_failure"]["central"], c["wasted_visit"]
    check_frame(scores, "threshold: scores", ["asset_id", "date"], required=["asset_id", "date", "score"])
    fail_days = {p: list(_days(g["reported_date"])) for p, g in failures.groupby("asset_id")}
    total_failures = len(failures)
    s = scores.assign(_day=_days(scores["date"])).sort_values("score", ascending=False, kind="mergesort")
    hot = {}
    stats = {}
    totals = {"alerts": 0, "caught": 0, "wasted": 0}
    best = None
    values, pumps, days = s["score"].to_numpy(), s["asset_id"].to_numpy(), s["_day"].to_numpy()
    i, n = 0, len(s)
    candidates = 0
    while i < n:
        th = values[i]
        changed = set()
        while i < n and values[i] == th:
            bisect.insort(hot.setdefault(pumps[i], []), int(days[i]))
            changed.add(pumps[i])
            i += 1
        candidates += 1
        for p in changed:
            opened, next_ok = [], None
            for d in hot[p]:
                if next_ok is None or d >= next_ok:
                    opened.append(d)
                    next_ok = d + quiet
            f = fail_days.get(p, [])
            outcomes, _ = _classify_pump(opened, f, [True] * len(f), lo, hi, horizon)
            new = {"alerts": len(opened), "caught": sum(o == "caught" for o, _ in outcomes),
                   "wasted": sum(o == "wasted" for o, _ in outcomes)}
            old = stats.get(p, {"alerts": 0, "caught": 0, "wasted": 0})
            for k in totals:
                totals[k] += new[k] - old[k]
            stats[p] = new
        cost = (total_failures - totals["caught"]) * cm + totals["wasted"] * cw
        key = (cost, totals["alerts"])
        if best is None or key < best["key"]:
            best = {"key": key, "threshold": float(th), "cost_eur": cost, **totals}
    best.pop("key")
    best["candidates"] = candidates
    return best
