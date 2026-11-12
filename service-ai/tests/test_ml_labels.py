"""Labels and at-risk rows: the label looks 30 days ahead, the three drops come in order and
are counted, and the real counts match the evaluation set (D15)."""

import pandas as pd

from fjordvik_service.ml import labels, pipeline


def _rows(pump, first, n):
    return pd.DataFrame({"asset_id": pump, "date": pd.date_range(first, periods=n, freq="D")})


def test_the_label_is_a_failure_in_the_next_30_days_not_today():
    rows = _rows("P1", "2024-01-01", 60)
    fails = pd.DataFrame({"asset_id": ["P1"], "reported_date": [pd.Timestamp("2024-02-10")],
                          "completed_date": [pd.Timestamp("2024-02-12")]})
    y = pd.Series(labels.label(rows, fails, 30), index=rows["date"])
    assert y[pd.Timestamp("2024-01-10")] == 0          # 31 days before: outside (t, t+30]
    assert y[pd.Timestamp("2024-01-11")] == 1          # exactly 30 days before
    assert y[pd.Timestamp("2024-02-09")] == 1          # the day before
    assert y[pd.Timestamp("2024-02-10")] == 0          # the failure day itself is not ahead


def test_open_ticket_then_no_running_then_warm_up_are_dropped_and_counted(ev_ml):
    rows = _rows("P1", "2024-01-01", 10)
    rows["_no_running"] = [False, False, True, True, False, False, False, False, False, False]
    rows["_baseline_readings"] = [10, 60, 60, 60, 60, 60, 60, 60, 59, 60]
    fails = pd.DataFrame({"asset_id": ["P1"], "reported_date": [pd.Timestamp("2024-01-03")],
                          "completed_date": [pd.Timestamp("2024-01-05")]})
    out, keep, counts = labels.at_risk(rows, fails, ev_ml)
    assert counts == {"telemetry_rows": 10, "open_failure_ticket": 3, "no_running_with_no_open_ticket": 0,
                      "warm_up": 2, "at_risk_rows": 5}
    assert list(keep) == [False, True, False, False, False, True, True, True, False, True]


def test_a_cut_off_reads_no_later_event_and_keeps_an_open_ticket_open(ev_ml, data_dir):
    cut = pd.Timestamp(ev_ml["periods"]["validation"]["cut_off"])
    f = labels.read_failures(data_dir, ev_ml, cut_off=cut)
    assert f["reported_date"].max() <= cut and f["completed_date"].max() <= cut
    assert list(f.columns) == ["asset_id", "reported_date", "completed_date"]
    full = labels.read_failures(data_dir, ev_ml)
    still_open = full[(full["reported_date"] <= cut) & (full["completed_date"] > cut)]
    assert len(still_open) > 0
    assert (f.set_index(["asset_id", "reported_date"]).loc[
        list(zip(still_open["asset_id"], still_open["reported_date"], strict=True)), "completed_date"] == cut).all()


def test_real_counts_to_the_validation_cut_off_match_the_evaluation_set(data_dir, ev_ml, allow):
    """Builds features for all 600 pumps (about a minute): every count the evaluation set
    records for train and validation must come out exactly (D15)."""
    cut = pd.Timestamp(ev_ml["periods"]["validation"]["cut_off"])
    data = pipeline.load(data_dir, ev_ml, allow, cut_off=cut)
    counts = pipeline.counts_check(data, ev_ml, ["train", "validation"], full=False, expected=True)
    assert counts["failures"] == {"train": 199, "validation": 70}
    assert counts["by_period"]["validation"]["at_risk_rows"] == 85085
    assert int(data["keep"].sum()) == data["counts"]["at_risk_rows"]
    assert data["rows"].loc[data["keep"], "_baseline_readings"].min() >= ev_ml["model"]["features"]["baseline"]["min_readings"]
