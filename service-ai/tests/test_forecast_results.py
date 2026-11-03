"""Results files: independent recheck, Tartu apart, stamps and the synthetic-data line, pass marks, G10.

The fresh runs here use data up to the end of validation only, so no test score is computed
outside the one locked test run.
"""

import csv
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pandas.testing as pdt
import pytest

from fjordvik_service.forecast import DATA_BASIS, MODEL_VERSION, backtest, report
from fjordvik_service.forecast.lock import check_lock
from fjordvik_service.forecast.splits import EVALUATION_PATH, LOCK_PATH
from fjordvik_service.forecast.stamps import STAMP_FIELDS, environment, sha256_file, stamp

SERVICE_AI = Path(__file__).resolve().parents[1]
RECHECK = SERVICE_AI / "scripts" / "recheck_forecast.py"
COMMITTED = SERVICE_AI / "results" / "forecast"
SETTINGS = {"moving_average_window": 6, "driver_model_season_term": False}


def validation_run(data_dir, ev):
    inputs = backtest.load_inputs(data_dir, ev, last_month=ev["periods"]["validation"]["last_target_month"])
    forecasts, used = backtest.run(inputs, ev, SETTINGS)
    by_series, by_origin = backtest.score(forecasts, ev, periods=["validation"])
    return inputs, forecasts, used, by_series, by_origin


@pytest.fixture(scope="module")
def written(data_dir, ev, tmp_path_factory):
    inputs, forecasts, used, by_series, by_origin = validation_run(data_dir, ev)
    stamps = stamp(data_dir, "test-commit")
    summary = report.summarise(by_series, inputs, ev, SETTINGS, stamps, "validation")
    out = tmp_path_factory.mktemp("forecast")
    manifest = report.write_results(
        out, {"backtest_forecasts": forecasts, "metrics_by_series": by_series,
              "metrics_by_origin": by_origin, "drivers": used},
        summary, stamps, report.results_note(summary, by_origin, ev))
    return out, manifest, summary


def recheck(results_dir, data_dir):
    return subprocess.run([sys.executable, str(RECHECK), "--results", str(results_dir), "--data-dir", str(data_dir)],
                          capture_output=True, text=True)


def test_independent_recheck_matches_the_saved_mase(written, data_dir):
    out, _, _ = written
    run = recheck(out, data_dir)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "OK: saved MASE matches" in run.stdout


def test_a_warehouse_below_the_minimum_is_reported_apart(full_inputs, ev):
    rows = []
    for wh, driver_mase in [("FI03", 0.8), ("EE02", 5.0)]:
        for method, value in [("naive", 1.2), ("seasonal_naive", 1.0), ("moving_average_w6", 0.9), ("driver_base", driver_mase)]:
            for length in ["3-month", "6-month"]:
                rows.append({"warehouse": wh, "part_family": "Bearings", "method": method, "period": "test",
                             "length": length, "n_origins": 7, "mase": value,
                             "n_interval": 10, "n_covered": 8 if wh == "FI03" else 1})
    summary = report.summarise(pd.DataFrame(rows), full_inputs, ev, SETTINGS, {}, "test")
    for length in ["3-month", "6-month"]:
        assert summary["warehouses"]["EE02"][length]["in_scope"] is False
        assert "reported_apart" in summary["warehouses"]["EE02"][length]
        assert summary["verdict"][length] == {"mase": "pass", "coverage": "pass"}
    assert summary["warehouses"]["FI03"]["6-month"]["in_scope"] is True


def test_every_results_file_is_stamped_and_says_synthetic(written, data_dir):
    out, manifest, summary = written
    assert manifest["data_sha256"] == sha256_file(Path(data_dir) / "manifest.json")
    assert manifest["model_version"] == MODEL_VERSION and manifest["data_basis"] == DATA_BASIS
    for name, info in manifest["files"].items():
        assert sha256_file(out / name) == info["sha256"], name
        if name.endswith(".csv"):
            with open(out / name, encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
            assert len(rows) == info["rows"]
            for field in STAMP_FIELDS:
                assert {r[field] for r in rows} == {manifest[field]}, (name, field)
    assert all(summary[f] == manifest[f] for f in STAMP_FIELDS)
    note = (out / "README.md").read_text(encoding="utf-8")
    assert DATA_BASIS in note and manifest["data_sha256"] in note and MODEL_VERSION in note
    assert manifest["environment"] == environment() == summary["environment"]
    for path in sorted(out.iterdir()):
        assert b"\r" not in path.read_bytes(), f"{path.name} has Windows line endings, so its checksum breaks on checkout"


def test_the_summary_carries_the_pass_marks_unchanged(written, ev):
    _, _, summary = written
    assert summary["pass_marks"] == ev["pass_marks"]
    assert ev["pass_marks"]["coverage"]["low"] == 0.70 and ev["pass_marks"]["coverage"]["high"] == 0.90
    assert ev["minimum_test_origins"]["value"] == 6


def test_two_runs_give_identical_metrics(data_dir, ev):
    first = validation_run(data_dir, ev)
    second = validation_run(data_dir, ev)
    pdt.assert_frame_equal(first[3], second[3])
    pdt.assert_frame_equal(first[1], second[1])


def test_committed_test_results_match_their_manifest_and_recheck(data_dir):
    manifest = json.loads((COMMITTED / "manifest.json").read_text(encoding="utf-8"))
    for name, info in manifest["files"].items():
        assert sha256_file(COMMITTED / name) == info["sha256"], name
    for folder in [COMMITTED, COMMITTED / "validation", LOCK_PATH.parent]:
        for path in sorted(p for p in folder.iterdir() if p.is_file()):
            assert b"\r" not in path.read_bytes(), f"{path} has Windows line endings"
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    assert lock["validation_manifest_sha256"] == sha256_file(COMMITTED / "validation" / "manifest.json")
    assert manifest["data_sha256"] == sha256_file(Path(data_dir) / "manifest.json")
    summary = json.loads((COMMITTED / "summary.json").read_text(encoding="utf-8"))
    assert summary["period"] == "test" and summary["settings"] == check_lock(LOCK_PATH, EVALUATION_PATH)
    run = recheck(COMMITTED, data_dir)
    assert run.returncode == 0, run.stdout + run.stderr
