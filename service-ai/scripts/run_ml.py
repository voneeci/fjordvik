"""Run the phase 3 failure risk model.

    python scripts/run_ml.py --period validation
        Reads data up to the validation cut-off only. Chooses the classifier's settings, the
        alert threshold and the drift flag level; runs the shuffled-label and control checks;
        writes results/ml/validation/ and, when both checks are within their limits,
        eval/ml/split_lock.json.

    python scripts/run_ml.py --period test
        Refuses unless the split lock matches evaluation.json and this model version, no
        earlier test run used different settings, and the code is committed. Scores the test
        period once with the frozen settings and writes results/ml/.

Measured on synthetic data with planted signals: Fjordvik Manufacturing Oy is fictional.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SERVICE_AI = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_AI / "src"))

from fjordvik_service.common.lock import LockError, check_lock, write_lock  # noqa: E402
from fjordvik_service.common.results import tidy, write_results  # noqa: E402
from fjordvik_service.common.stamps import (  # noqa: E402
    environment, git_commit, scores_sha256, sha256_file, sha256_json, stamp, uncommitted)
from fjordvik_service.ml import DATA_BASIS, LIBRARIES, MODEL_VERSION, pipeline, report  # noqa: E402
from fjordvik_service.ml.splits import (  # noqa: E402
    ALLOWLIST_PATH, EVALUATION_PATH, LOCK_PATH, RUN_LOG, SCENARIO_DIR, TABLES_DIR, check_scenarios,
    load_allowlist, load_evaluation)

# Table reads and results writes use separate path variables (the guardrail hook asks for this).
RESULTS_OUT = SERVICE_AI / "results" / "ml"
VALIDATION_OUT = RESULTS_OUT / "validation"
CODE_PATHS = [SERVICE_AI / "src", SERVICE_AI / "scripts", SERVICE_AI / "pyproject.toml", EVALUATION_PATH, ALLOWLIST_PATH]
ROW_LEVEL = ("scores", "scores_test")


def require_committed(paths):
    changed = uncommitted(SERVICE_AI, paths)
    if changed:
        raise SystemExit("Refusing to run: commit these first, so the results can name their commit:\n  "
                         + "\n  ".join(changed))
    return git_commit(SERVICE_AI)


def score_table(scores):
    """Row-level scores; a label shows only on scored days, where its 30-day window is complete."""
    out = scores[["asset_id", "date", "scored", "label", "score", "z_max", "iforest_score"]].copy()
    out["label"] = out["label"].astype("Int8").where(out["scored"])
    return out


def metrics_table(s):
    rows = []
    a = s["average_precision"]
    for k in ["classifier", "dummy", "pump_facts_only", "robust_z_alone", "isolation_forest_alone"]:
        rows.append({"metric": f"average_precision_{k}", "value": a[k]})
    rows.append({"metric": "positive_share", "value": a["positive_share"]})
    rows.append({"metric": "ap_ratio_to_dummy", "value": s["ap_ratio_to_dummy"]})
    e = s["alerts"]["evaluated"]
    for k in ["alerts", "caught", "wasted", "neither", "failures", "warned_failures", "unwarned_failures", "missed",
              "recall_of_warned_failures", "cost_eur"]:
        rows.append({"metric": f"model_{k}", "value": e[k]})
    for plan, x in s["alerts"]["plans"].items():
        for k, v in x.items():
            rows.append({"metric": f"{plan}_{k}", "value": v})
    out = []
    names = {"average_precision_classifier": "classifier_ap", "average_precision_dummy": "dummy_ap",
             "ap_ratio_to_dummy": "ap_ratio", "model_recall_of_warned_failures": "recall", "model_cost_eur": "model_cost",
             "visit_none_cost_eur": "visit_none_cost", "visit_every_pump_cost_eur": "visit_every_cost"}
    for r in rows:
        rng = s.get("ranges", {}).get(names.get(r["metric"], ""), {})
        out.append({**r, "range_low": rng.get("low"), "range_high": rng.get("high")})
    import pandas as pd
    return pd.DataFrame(out)


def print_summary(s):
    print(s["statement"])
    a = s["average_precision"]
    print(f"rows scored {a['rows']}, positive share {a['positive_share']:.4%}")
    print(f"average precision: classifier {a['classifier']:.4f}, dummy {a['dummy']:.4f}, "
          f"ratio {s['ap_ratio_to_dummy']:.2f}; pump facts {a['pump_facts_only']:.4f}, "
          f"z alone {a['robust_z_alone']:.4f}, forest alone {a['isolation_forest_alone']:.4f}")
    if "evaluated" in s["alerts"]:
        e = s["alerts"]["evaluated"]
        print(f"alerts {e['alerts']}: caught {e['caught']}, wasted {e['wasted']}, neither {e['neither']}; "
              f"failures {e['failures']} (warned {e['warned_failures']}, unwarned {e['unwarned_failures']}); "
              f"recall of warned {e['recall_of_warned_failures']}")
        pl = s["alerts"]["plans"]
        print(f"cost EUR: model {e['cost_eur']:.2f}, visit none {pl['visit_none']['cost_eur']:.2f}, "
              f"visit every pump {pl['visit_every_pump']['cost_eur']:.2f}")
    if "verdict" in s:
        print(f"verdict: {s['verdict']}")
        print(f"all pass marks met: {s['all_pass_marks_met']}")


def validation():
    commit = require_committed(CODE_PATHS)
    ev, allow = load_evaluation(), load_allowlist()
    check_scenarios(SCENARIO_DIR)
    result, tables = pipeline.validation_step(TABLES_DIR, ev, allow, scenario_dir=SCENARIO_DIR)
    stamps = stamp(TABLES_DIR, commit, MODEL_VERSION, DATA_BASIS)
    env = environment(LIBRARIES)
    settings = {"model_version": MODEL_VERSION, "classifier": result["settings"],
                "threshold": result["threshold"]["threshold"], "drift_flag_level": result["drift_level"]["level"]}
    settings_sha = sha256_json(settings)
    summary = report.summary(result, stamps, env, ev)
    card = report.model_card(result["settings"], settings["threshold"], settings["drift_flag_level"], allow,
                             pipeline.feature_columns(allow), stamps, env, result["model_detail"], ev, settings_sha)
    manifest = write_results(
        VALIDATION_OUT, {"scores": score_table(tables["scores"]), "alerts": tables["alerts"],
                         "reliability": tables["reliability"], "grid": tables["grid"],
                         "metrics": metrics_table(summary)},
        summary, stamps, report.results_note(summary, ev), env, row_level=ROW_LEVEL,
        extra_json={"model_card.json": card})
    print_summary(summary)
    print(f"grid: {[(g['settings'], round(g['average_precision'], 4)) for g in result['grid']]}")
    print(f"chosen: {settings}")
    print(f"threshold sweep: {result['threshold']}")
    print(f"shuffled labels: {result['shuffled_labels']['ratio_to_dummy']:.3f} x dummy (limit {result['shuffled_labels']['limit']})")
    print(f"control (E2): {result['control']['ratio_to_dummy']} (limit {result['control']['limit']}); "
          f"pump facts only {result['control']['pump_facts_only_ratio']:.3f}")
    print(f"group check: {result['group_check']['mean_average_precision']:.4f} against {result['average_precision']['classifier']:.4f}")
    print(f"drift level {result['drift_level']}")
    print(f"leakage: {result['leakage']['pass']} {result['leakage']['point_in_time_changes']} {result['leakage']['answer_key_named_in']}")
    print(f"wrote {len(manifest['files'])} files to {VALIDATION_OUT}")
    if not (result["shuffled_labels"]["pass"] and result["control"]["pass"] and result["leakage"]["pass"]):
        raise SystemExit("A control is outside its limit on validation: no split lock written. Stop and ask Reece.")
    lock = write_lock(LOCK_PATH, EVALUATION_PATH, settings, {"period": "validation", "data_used_up_to": result["data_used_up_to"]},
                      {**stamps, "environment": env, "allowlist_sha256": sha256_file(ALLOWLIST_PATH),
                       "validation_manifest_sha256": sha256_file(VALIDATION_OUT / "manifest.json"),
                       "written": datetime.now(timezone.utc).strftime("%Y-%m-%d")})
    print(f"split lock written: {LOCK_PATH}, settings_sha256 {lock['settings_sha256']}")


def test():
    try:
        settings = check_lock(LOCK_PATH, EVALUATION_PATH)
    except LockError as err:
        raise SystemExit(f"Refusing to run the test period: {err}")
    if settings.get("model_version") != MODEL_VERSION:
        raise SystemExit(f"Refusing to run: the lock's threshold belongs to model version "
                         f"{settings.get('model_version')}, not {MODEL_VERSION} (M3)")
    settings_sha = sha256_json(settings)
    earlier = [json.loads(line) for line in RUN_LOG.read_text(encoding="utf-8").splitlines()] if RUN_LOG.exists() else []
    other = [e for e in earlier if e["settings_sha256"] != settings_sha]
    if other:
        raise SystemExit(f"Refusing to run: the run log already holds a test run with other settings "
                         f"({other[0]['settings_sha256'][:12]}), so the test period was already scored (E1)")
    commit = require_committed(CODE_PATHS + [LOCK_PATH])
    ev, allow = load_evaluation(), load_allowlist()
    check_scenarios(SCENARIO_DIR)
    result, tables = pipeline.test_step(TABLES_DIR, ev, allow, settings, scenario_dir=SCENARIO_DIR)
    stamps = stamp(TABLES_DIR, commit, MODEL_VERSION, DATA_BASIS)
    env = environment(LIBRARIES)

    # G10: the frozen model, trained again, must give the validation scores the lock was built on.
    saved = (VALIDATION_OUT / "scores.csv").read_text(encoding="utf-8")
    rerun = tidy(score_table(tables["scores_validation_rerun"])).to_csv(index=False, lineterminator="\n")
    same = scores_sha256(saved, drop=["stamp_id"]) == scores_sha256(rerun, drop=["stamp_id"])
    entry = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "commit": commit,
             "data_sha256": stamps["data_sha256"], "settings_sha256": settings_sha,
             "validation_scores_reproduced": same}
    if not same:
        with RUN_LOG.open("a", encoding="utf-8", newline="\n") as log:
            log.write(json.dumps({**entry, "status": "stopped: validation scores not reproduced"}) + "\n")
        raise SystemExit("Fault: the validation scores were not reproduced (G10). No test results written. Ask Reece.")

    validation_summary = json.loads((VALIDATION_OUT / "summary.json").read_text(encoding="utf-8"))
    summary = report.summary(result, stamps, env, ev, validation=validation_summary)
    card = json.loads((VALIDATION_OUT / "model_card.json").read_text(encoding="utf-8"))
    risk_name = f"risk_{result['risk_list']['date']}"
    manifest = write_results(
        RESULTS_OUT, {"scores_test": score_table(tables["scores_test"]), "alerts": tables["alerts"],
                      "metrics": metrics_table(summary), "reliability": tables["reliability"],
                      "drift": tables["drift"], risk_name: tables["risk"]},
        summary, stamps, report.results_note(summary, ev), env, row_level=ROW_LEVEL,
        extra_json={"model_card.json": card})
    scores_sha = scores_sha256((RESULTS_OUT / "scores_test.csv").read_text(encoding="utf-8"), drop=["stamp_id"])
    with RUN_LOG.open("a", encoding="utf-8", newline="\n") as log:
        log.write(json.dumps({**entry, "status": "complete", "scores_sha256": scores_sha,
                              "all_pass_marks_met": summary["all_pass_marks_met"]}) + "\n")
    print_summary(summary)
    print(f"control (E2) test: {result['control']['ratio_to_dummy']}; drift: {result['drift']}")
    print(f"leakage: {result['leakage']}")
    print(f"risk list: {result['risk_list']}")
    print(f"test run {len(earlier) + 1} logged in {RUN_LOG}; wrote {len(manifest['files'])} files to {RESULTS_OUT}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--period", choices=["validation", "test"], required=True)
    args = parser.parse_args()
    (validation if args.period == "validation" else test)()


if __name__ == "__main__":
    main()
