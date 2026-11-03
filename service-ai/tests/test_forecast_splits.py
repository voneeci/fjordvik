"""F1 and E1: rolling origins, periods fixed by date, and a test run that needs the split lock."""

import json
import shutil

import pandas as pd
import pytest

from fjordvik_service.forecast.backtest import choose, count_test_origins
from fjordvik_service.forecast.lock import LockError, check_lock, write_lock
from fjordvik_service.forecast.splits import EVALUATION_PATH, gap_months, lengths, origins, period_for, period_ranges


def test_each_origin_forecasts_only_months_after_its_training(full_inputs, ev):
    for wh in full_inputs.warehouses():
        first = full_inputs.first_month(wh)
        all_origins = origins(first, full_inputs.last_month, ev)
        assert (all_origins[0] - first).n + 1 == ev["origins"]["min_training_months"]
        for o in all_origins:
            for name, hs in lengths(ev).items():
                assert min(o + h for h in hs) > o
                period = period_for(o, hs, ev)
                if period:
                    lo, hi = period_ranges(ev)[period]
                    assert all(lo <= o + h <= hi for h in hs)
    counts = count_test_origins(full_inputs, ev)
    assert counts == {"FI03": {"3-month": 10, "6-month": 7}, "EE02": {"3-month": 1, "6-month": 0}}
    fi = origins(full_inputs.first_month("FI03"), full_inputs.last_month, ev)
    assert sum(period_for(o, lengths(ev)["6-month"], ev) == "validation" for o in fi) == 3
    assert sum(period_for(o, lengths(ev)["3-month"], ev) == "validation" for o in fi) == 6


def test_validation_gap_and_test_are_disjoint_and_in_order(full_inputs, ev):
    (v_lo, v_hi), (t_lo, t_hi) = period_ranges(ev)["validation"], period_ranges(ev)["test"]
    gap = gap_months(ev)
    assert v_lo <= v_hi < min(gap) <= max(gap) < t_lo <= t_hi
    assert all(g == v_hi + 1 + i for i, g in enumerate(gap)) and max(gap) + 1 == t_lo
    for o in origins(full_inputs.first_month("FI03"), full_inputs.last_month, ev):
        for hs in lengths(ev).values():
            if period_for(o, hs, ev):
                assert not set(o + h for h in hs) & set(gap)


def test_the_test_run_refuses_without_a_valid_lock(tmp_path):
    evaluation = tmp_path / "evaluation.json"
    shutil.copyfile(EVALUATION_PATH, evaluation)
    lock = tmp_path / "split_lock.json"
    with pytest.raises(LockError, match="no split lock"):
        check_lock(lock, evaluation)
    settings = {"moving_average_window": 6, "driver_model_season_term": False}
    write_lock(lock, evaluation, settings, {"period": "validation"}, {})
    assert check_lock(lock, evaluation) == settings
    tampered = json.loads(lock.read_text(encoding="utf-8"))
    tampered["settings"]["moving_average_window"] = 3
    lock.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(LockError, match="hash"):
        check_lock(lock, evaluation)
    write_lock(lock, evaluation, settings, {"period": "validation"}, {})
    changed = json.loads(evaluation.read_text(encoding="utf-8"))
    changed["pass_marks"]["coverage"]["low"] = 0.5
    evaluation.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(LockError, match="evaluation.json has changed"):
        check_lock(lock, evaluation)


def test_settings_are_chosen_on_validation_origins_only(ev):
    rows = []
    for period, scores in [("validation", {"moving_average_w3": 1.2, "moving_average_w6": 1.1, "moving_average_w12": 1.1,
                                           "driver_base": 1.0, "driver_season": 1.3}),
                           ("test", {"moving_average_w3": 0.1, "moving_average_w6": 9.0, "moving_average_w12": 9.0,
                                     "driver_base": 9.0, "driver_season": 0.1})]:
        for method, value in scores.items():
            rows.append({"warehouse": "FI03", "part_family": "Bearings", "method": method, "period": period,
                         "length": "6-month", "mase": value})
    settings, _ = choose(pd.DataFrame(rows), ev)
    assert settings == {"moving_average_window": 12, "driver_model_season_term": False}
