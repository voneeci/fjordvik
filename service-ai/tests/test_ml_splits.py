"""Phase 3 splits and gaps (E1, A9): dates come from the evaluation set, and every period's
label window ends by its cut-off."""

import json
import shutil

import pandas as pd
import pytest

from fjordvik_service.common.lock import LockError, check_lock, write_lock
from fjordvik_service.ml.splits import EVALUATION_PATH, RestsOnError, check_rests_on, periods


def test_train_and_test_label_windows_end_by_their_cut_off(ev_ml):
    p = periods(ev_ml)
    days = pd.Timedelta(days=ev_ml["periods"]["label_window_days"])
    assert p["train"]["last_scored"] + days <= p["train"]["cut_off"]
    assert p["test"]["last_scored"] + days <= p["test"]["cut_off"]
    # Validation's last scored day (1 June) looks one day past its cut-off (30 June); its
    # step reads no event after the cut-off, which the handover records.
    assert p["validation"]["last_scored"] + days == p["validation"]["cut_off"] + pd.Timedelta(days=1)


def test_periods_follow_each_other_with_each_cut_off_before_the_next_period(ev_ml):
    p = periods(ev_ml)
    assert p["train"]["cut_off"] < p["validation"]["first_scored"] <= p["validation"]["last_scored"]
    assert p["validation"]["cut_off"] < p["test"]["first_scored"] <= p["test"]["last_scored"]
    for name in ["validation", "test"]:
        span = (p[name]["alert_last"] - p[name]["alert_first"]).days + 1
        assert span == p[name]["alert_days"]
        assert p[name]["alert_last"] == p[name]["cut_off"]


def test_a_changed_file_the_evaluation_rests_on_stops_the_run(ev_ml, tmp_path):
    check_rests_on(ev_ml)   # the real files hold
    for rel in ev_ml["rests_on"]["sha256"]:
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(EVALUATION_PATH.parents[3] / rel, target)
    check_rests_on(ev_ml, tmp_path)
    first = next(iter(ev_ml["rests_on"]["sha256"]))
    (tmp_path / first).write_bytes((tmp_path / first).read_bytes() + b" ")
    with pytest.raises(RestsOnError):
        check_rests_on(ev_ml, tmp_path)


def test_the_test_step_refuses_without_a_matching_lock(tmp_path):
    lock, ev_copy = tmp_path / "split_lock.json", tmp_path / "evaluation.json"
    shutil.copyfile(EVALUATION_PATH, ev_copy)
    with pytest.raises(LockError):
        check_lock(lock, ev_copy)
    settings = {"model_version": "ml-1.0.0", "classifier": {"max_iter": 100}, "threshold": 0.5}
    write_lock(lock, ev_copy, settings, {"period": "validation"}, {})
    assert check_lock(lock, ev_copy) == settings
    changed = json.loads(ev_copy.read_text(encoding="utf-8"))
    changed["periods"]["test"]["cut_off"] = "2026-01-31"
    ev_copy.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(LockError):
        check_lock(lock, ev_copy)
