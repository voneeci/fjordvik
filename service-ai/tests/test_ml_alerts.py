"""Alerts, cost and the threshold (M3): one alert per 30 quiet days, caught 7 to 30 days ahead,
the costs read from the planning inputs, and the threshold sweep tries every candidate."""

import json

import numpy as np
import pandas as pd
import pytest

from fjordvik_service.common.stamps import sha256_file
from fjordvik_service.ml import alerts, evaluate
from fjordvik_service.ml.splits import PLANNING_INPUTS

C = {"wasted_visit": 100.0, "missed_failure": {"low": 300.0, "central": 1000.0, "high": 2000.0}}


def _scores(pump, first, values):
    return pd.DataFrame({"asset_id": pump, "date": pd.date_range(first, periods=len(values), freq="D"),
                         "score": values})


def _fails(items):
    return pd.DataFrame({"asset_id": [a for a, _ in items], "reported_date": [pd.Timestamp(d) for _, d in items],
                         "completed_date": [pd.Timestamp(d) for _, d in items]})


def test_a_daily_high_score_opens_one_alert_per_30_days(ev_ml):
    s = _scores("P1", "2025-01-01", [0.9] * 75)
    opened = alerts.alert_days(s, 0.5, ev_ml["alerts"]["quiet_days"])
    assert list(opened["date"].dt.strftime("%Y-%m-%d")) == ["2025-01-01", "2025-01-31", "2025-03-02"]


def test_caught_neither_and_wasted_and_an_unwarned_failure_counts_as_wasted(ev_ml):
    opened = pd.DataFrame({"asset_id": ["P1", "P2", "P3", "P4"],
                           "date": pd.to_datetime(["2025-01-01", "2025-01-01", "2025-01-01", "2025-01-01"])})
    fails = _fails([("P1", "2025-01-08"), ("P2", "2025-01-04"), ("P4", "2025-01-20")])
    plain, pf = alerts.classify(opened, fails, ev_ml)
    assert list(plain["outcome"]) == ["caught", "neither", "wasted", "caught"]
    judged, jf = alerts.classify(opened, fails, ev_ml, warned=[True, True, False])
    assert list(judged["outcome"]) == ["caught", "neither", "wasted", "wasted"]
    s = alerts.summarise(judged, jf, C)
    assert (s["caught"], s["wasted"], s["missed"], s["warned_failures"], s["unwarned_failures"]) == (1, 2, 2, 2, 1)
    assert s["recall_of_warned_failures"] == 0.5
    assert s["cost_eur"] == 2 * 1000.0 + 2 * 100.0
    jf = jf.assign(_warned=[True, True, False])
    plans = evaluate.plans(jf, pumps_in_window=4, alert_days=184, c=C)
    assert plans["visit_every_pump"] == {"visits": 24, "caught": 2, "missed": 1, "wasted": 22,
                                         "cost_eur": 1 * 1000.0 + 22 * 100.0}
    assert plans["visit_none"]["cost_eur"] == 3 * 1000.0


def test_the_threshold_sweep_matches_a_brute_force_over_every_candidate(ev_ml):
    gen = np.random.RandomState(np.random.PCG64(3))
    frames = [_scores(f"P{i}", "2025-01-01", np.round(gen.uniform(0, 1, 120), 2)) for i in range(6)]
    scores = pd.concat(frames, ignore_index=True)
    fails = _fails([("P0", "2025-02-10"), ("P2", "2025-03-01"), ("P3", "2025-01-20"), ("P5", "2025-04-15")])
    best = alerts.choose_threshold(scores, fails, ev_ml, C)
    brute = []
    for th in sorted(scores["score"].unique(), reverse=True):
        out, f = alerts.classify(alerts.alert_days(scores, th, 30), fails, ev_ml)
        s = alerts.summarise(out, f, C)
        brute.append((s["cost_eur"], s["alerts"], -th, s))
    cost, n, neg_th, s = min(brute, key=lambda b: b[:3])
    assert best["threshold"] == -neg_th and best["cost_eur"] == cost and best["alerts"] == n
    assert best["candidates"] == scores["score"].nunique()


def test_the_costs_come_from_the_planning_inputs_and_their_checksum(ev_ml, tmp_path):
    c = alerts.costs(ev_ml)
    data = json.loads(PLANNING_INPUTS.read_text(encoding="utf-8"))
    assert c["wasted_visit"] == data["wasted_visit"]["cost_eur_per_event"]
    assert c["missed_failure"] == data["missed_failure"]["cost_eur_per_event"]
    assert sha256_file(PLANNING_INPUTS) == ev_ml["cost"]["inputs"]["source_sha256"]
    changed = tmp_path / "planning_inputs.json"
    changed.write_text(PLANNING_INPUTS.read_text(encoding="utf-8").replace("190.34", "1.00"), encoding="utf-8")
    with pytest.raises(ValueError):
        alerts.costs(ev_ml, changed)
