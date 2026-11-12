"""Leakage (M2, D10, D12): a feature that looks ahead fails the point-in-time test, the
feature path opens only its four tables, and only evaluate.py names the answer key."""

import builtins
from pathlib import Path

import numpy as np
import pandas as pd

from fjordvik_service.ml import features, model, pipeline
from ml_fixtures import make_tables


def test_a_planted_centred_window_fails_the_point_in_time_test(ev_ml, allow):
    """The test must be able to fail: a 7-day median centred on t reads 3 days ahead."""
    tables = make_tables(260)

    def leaky(tb):
        f = features.build(tb, ev_ml, allow)
        f["vibration_centred7"] = (f.groupby("asset_id")["vibration_med7"]
                                   .transform(lambda s: s.rolling(7, center=True, min_periods=1).median()))
        return f

    days = [("P01", pd.Timestamp("2023-07-01")), ("P02", pd.Timestamp("2023-08-15"))]
    honest = features.check_point_in_time(lambda tb: features.build(tb, ev_ml, allow), tables, days,
                                          ["vibration_med7", "vibration_z"])
    assert honest == []
    changed = features.check_point_in_time(leaky, tables, days, ["vibration_med7", "vibration_centred7"])
    assert {c for _, _, c in changed} == {"vibration_centred7"}


def test_the_feature_path_opens_only_its_four_tables(data_dir, allow, monkeypatch):
    opened = []
    real_open = builtins.open

    def recorder(file, *args, **kwargs):
        opened.append(Path(file).resolve() if isinstance(file, (str, Path)) else file)
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", recorder)
    features.read_tables(data_dir, allow)
    monkeypatch.undo()
    files = {p.name for p in opened if isinstance(p, Path)}
    assert files == {"fact_asset_telemetry.csv", "dim_asset.csv", "dim_product.csv", "dim_customer.csv"}
    assert not any("generator-truth" in str(p) or "fact_service_event" in str(p) for p in opened)


def test_only_evaluate_names_the_answer_key_and_the_fitted_model_reads_only_allowlisted_columns(ev_ml, allow):
    assert pipeline.answer_key_readers() == ["src/fjordvik_service/ml/evaluate.py"]
    f = features.build(make_tables(300), ev_ml, allow)
    f["iforest_score"] = 0.0
    f["label"] = (np.arange(len(f)) % 17 == 0).astype(int)
    fitted = model.fit(f, features.feature_names(allow), {"max_iter": 10, "learning_rate": 0.1, "max_leaf_nodes": 15},
                       ev_ml["seed"]["value"])
    assert features.assert_inside_allowlist(list(fitted.feature_names_in_), allow)
    assert not set(fitted.feature_names_in_) & {"label", "asset_id", "date", "_no_running", "_baseline_readings"}
