"""The classifier, its controls (D12 shuffled labels, E2) and the loud steps (D15, G10)."""

import numpy as np
import pandas as pd
import pytest

from fjordvik_service.common.checks import PipelineCheckError
from fjordvik_service.ml import alerts, features, labels, model
from ml_fixtures import make_tables, rise

SMALL = {"max_iter": 30, "learning_rate": 0.1, "max_leaf_nodes": 15}


def _signal_rows(ev_ml, allow, warning=True, n_pumps=24, n_days=420):
    """Pumps that fail at planned days; with warning=True a vibration rise comes first."""
    pumps, fails = {}, []
    gen = np.random.RandomState(np.random.PCG64(11))
    for i in range(n_pumps):
        pid = f"P{i:02d}"
        day = int(gen.randint(150, n_days - 10))
        events = [rise("vibration_mm_s", day - 25, 20, 2.5)] if warning else []
        pumps[pid] = {"application": "A" if i % 2 else "B", "events": events}
        fails.append((pid, pd.Timestamp("2023-01-01") + pd.Timedelta(days=day)))
    f = features.build(make_tables(n_days, pumps), ev_ml, allow)
    fl = pd.DataFrame({"asset_id": [a for a, _ in fails], "reported_date": [d for _, d in fails],
                       "completed_date": [d for _, d in fails]})
    f["label"] = labels.label(f, fl, 30)
    f["iforest_score"] = 0.0
    return f[f["_baseline_readings"] >= 60].reset_index(drop=True)


def test_the_grid_runs_simplest_first_and_ties_go_to_the_simpler(ev_ml):
    g = model.grid(ev_ml)
    assert len(g) == ev_ml["model"]["candidates"] == 8
    assert g[0] == {"max_leaf_nodes": 15, "max_iter": 100, "learning_rate": 0.05}
    assert g[-1] == {"max_leaf_nodes": 31, "max_iter": 200, "learning_rate": 0.1}
    tied = [{"settings": s, "average_precision": 0.5} for s in g]
    assert model.choose(tied, ev_ml) == g[0]
    tied[3]["average_precision"] = 0.6
    assert model.choose(tied, ev_ml) == g[3]


def test_shuffled_labels_fall_to_the_dummy_and_the_true_labels_do_not(ev_ml, allow):
    rows = _signal_rows(ev_ml, allow)
    cols = features.feature_names(allow)
    train, val = rows[rows["date"] < "2023-12-01"], rows[rows["date"] >= "2023-12-01"]
    dummy = float(val["label"].mean())
    true_ap = model.ap(val["label"], model.score(model.fit(train, cols, SMALL, 1), val, cols))
    shuffled = model.shuffled_labels(train, val, cols, SMALL, ev_ml)
    mean = np.mean([s["average_precision"] for s in shuffled])
    # The evaluation set's limits apply to the real run (summary.json); on this small fixture
    # the test only shows the shuffled model loses the signal the true labels carry.
    assert true_ap > 3 * dummy
    assert mean < true_ap / 3


def test_with_the_warning_switched_off_the_telemetry_scores_fall_to_the_dummy(ev_ml, allow):
    """E2 on a fixture: the same failures with no rise give the z-score no edge."""
    on, off = _signal_rows(ev_ml, allow, warning=True), _signal_rows(ev_ml, allow, warning=False)
    y_on, y_off = on["label"], off["label"]
    from fjordvik_service.ml.anomaly import as_ranking
    ap_on = model.ap(y_on, as_ranking(on["z_max"]))
    ap_off = model.ap(y_off, as_ranking(off["z_max"]))
    assert ap_on > 3 * y_on.mean()
    assert ap_off < ap_on / 3


def test_training_twice_gives_identical_scores(ev_ml, allow):
    rows = _signal_rows(ev_ml, allow, n_pumps=12, n_days=300)
    cols = features.feature_names(allow)
    a = model.score(model.fit(rows, cols, SMALL, ev_ml["seed"]["value"]), rows, cols)
    b = model.score(model.fit(rows, cols, SMALL, ev_ml["seed"]["value"]), rows, cols)
    assert np.array_equal(a, b)


def test_empty_or_blank_inputs_stop_the_step(ev_ml, allow, tmp_path):
    tables = make_tables(30)
    with pytest.raises(PipelineCheckError):
        features.build({**tables, "telemetry": tables["telemetry"].iloc[0:0]}, ev_ml, allow)
    events = tmp_path / "fact_service_event.csv"
    events.write_text("event_type,asset_id,reported_date,completed_date\nFailure,P1,2024-01-02,\n", encoding="utf-8")
    with pytest.raises(PipelineCheckError):
        labels.read_failures(tmp_path, ev_ml)
    with pytest.raises(PipelineCheckError):
        alerts.choose_threshold(pd.DataFrame({"asset_id": ["P1"], "date": [pd.Timestamp("2025-01-01")], "score": [np.nan]}),
                                pd.DataFrame(columns=["asset_id", "reported_date"]), ev_ml,
                                {"wasted_visit": 1.0, "missed_failure": {"central": 2.0}})


def test_a_training_set_with_one_label_value_stops_the_fit(ev_ml, allow):
    rows = _signal_rows(ev_ml, allow, n_pumps=6, n_days=250).assign(label=0)
    with pytest.raises(PipelineCheckError):
        model.fit(rows, features.feature_names(allow), SMALL, 1)
