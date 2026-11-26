"""Results through the real path: stamped files with Unix line endings, the independent
recheck, the test step on a copy of the dates placed before the validation cut-off, and the
run script's refusals (E1, M3, G10, W8)."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from fjordvik_service.common.lock import write_lock
from fjordvik_service.common.results import write_results
from fjordvik_service.common.stamps import STAMP_FIELDS, environment, sha256_file, sha256_json, stamp
from fjordvik_service.ml import DATA_BASIS, LIBRARIES, MODEL_VERSION, pipeline, report
from ml_fixtures import shifted

SERVICE_AI = Path(__file__).resolve().parents[1]
RECHECK = SERVICE_AI / "scripts" / "recheck_ml.py"
RUN_ML = SERVICE_AI / "scripts" / "run_ml.py"


def _run_ml_module():
    spec = importlib.util.spec_from_file_location("run_ml", RUN_ML)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def written(validation_subset_run, data_dir, ev_ml, allow, tmp_path_factory):
    result, tables = validation_subset_run
    run_ml = _run_ml_module()
    stamps = stamp(data_dir, "test-commit", MODEL_VERSION, DATA_BASIS)
    env = environment(LIBRARIES)
    summary = report.summary(result, stamps, env, ev_ml)
    out = tmp_path_factory.mktemp("ml-validation")
    manifest = write_results(out, {"scores": run_ml.score_table(tables["scores"]), "alerts": tables["alerts"],
                                   "reliability": tables["reliability"], "grid": tables["grid"],
                                   "metrics": run_ml.metrics_table(summary)},
                             summary, stamps, report.results_note(summary, ev_ml), env, row_level=run_ml.ROW_LEVEL)
    return out, manifest, summary


def test_every_results_file_is_stamped_says_synthetic_and_keeps_unix_line_endings(written, data_dir):
    out, manifest, summary = written
    assert manifest["data_sha256"] == sha256_file(Path(data_dir) / "manifest.json")
    assert manifest["model_version"] == MODEL_VERSION and manifest["data_basis"] == DATA_BASIS
    (sid, resolved), = manifest["stamp_ids"].items()
    assert resolved == {k: manifest[k] for k in STAMP_FIELDS}
    for name, info in manifest["files"].items():
        assert sha256_file(out / name) == info["sha256"], name
        if name == "scores.csv":
            assert set(pd.read_csv(out / name)["stamp_id"]) == {sid}
        elif name.endswith(".csv"):
            t = pd.read_csv(out / name)
            assert len(t) == info["rows"] and all(set(t[f].astype(str)) == {str(manifest[f])} for f in STAMP_FIELDS)
    note = (out / "README.md").read_text(encoding="utf-8")
    assert DATA_BASIS in note and "Accuracy and the area under the ROC" in note
    assert summary["average_precision"]["positive_share"] > 0 and summary["pass_marks"]
    for path in out.iterdir():
        assert b"\r" not in path.read_bytes(), path.name


def test_the_independent_recheck_matches_every_headline_metric(written, data_dir):
    out, _, _ = written
    run = subprocess.run([sys.executable, str(RECHECK), "--results", str(out), "--data-dir", str(data_dir)],
                         capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "OK: every headline metric matches" in run.stdout
    assert "MISMATCH" not in run.stdout


def test_the_test_step_runs_on_dates_before_the_validation_cut_off(data_dir, ev_ml, allow, subset_pumps):
    """The real test step, end to end, on a copy of the dates shifted before 30 June 2025,
    so no real test row is scored outside the one locked run. Without the git-ignored
    scenario files (a fresh clone), the control and drift parts are left out."""
    ev = shifted(ev_ml)
    cut = pd.Timestamp(ev_ml["periods"]["validation"]["cut_off"])
    v, _ = pipeline.validation_step(data_dir, ev, allow, pumps=subset_pumps, expected=False)
    locked = {"model_version": MODEL_VERSION, "classifier": v["settings"], "threshold": v["threshold"]["threshold"],
              "drift_flag_level": v["drift_level"]["level"]}
    t, tables = pipeline.test_step(data_dir, ev, allow, locked, scenario_dir=None, pumps=subset_pumps,
                                   expected=False, cut_off=cut)
    assert tables["scores_test"]["date"].max() <= cut
    assert tables["risk"]["date"].eq(pd.Timestamp("2025-06-30")).all()
    assert t["leakage"]["pass"] and t["threshold"] == v["threshold"]["threshold"]
    e = t["alerts"]["evaluated"]
    assert e["caught"] + e["wasted"] + e["neither"] == e["alerts"]
    assert e["missed"] == e["failures"] - e["caught"]
    assert t["ranges"]["classifier_ap"]["resamples"] > 0


def test_the_run_script_refuses_a_second_lock_and_a_threshold_from_another_version(tmp_path, monkeypatch, ev_ml):
    run_ml = _run_ml_module()
    ev_copy = tmp_path / "evaluation.json"
    ev_copy.write_text(json.dumps(ev_ml), encoding="utf-8")
    lock = tmp_path / "split_lock.json"
    log = tmp_path / "test_runs.jsonl"
    monkeypatch.setattr(run_ml, "LOCK_PATH", lock)
    monkeypatch.setattr(run_ml, "EVALUATION_PATH", ev_copy)
    monkeypatch.setattr(run_ml, "RUN_LOG", log)
    with pytest.raises(SystemExit, match="no split lock"):
        run_ml.test()
    other = {"model_version": "ml-0.9.0", "classifier": {}, "threshold": 0.5, "drift_flag_level": 3.0}
    write_lock(lock, ev_copy, other, {"period": "validation"}, {})
    with pytest.raises(SystemExit, match="model version"):
        run_ml.test()
    mine = {**other, "model_version": MODEL_VERSION}
    write_lock(lock, ev_copy, mine, {"period": "validation"}, {})
    log.write_text(json.dumps({"settings_sha256": sha256_json(other), "time": "earlier"}) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="already holds a test run with other settings"):
        run_ml.test()
