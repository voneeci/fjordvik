"""Run the phase 2 forecast backtest.

    python scripts/run_forecast.py --period validation
        Backtests every candidate setting on data up to the end of validation only, picks
        the settings, writes results/forecast/validation/ and eval/forecast/split_lock.json.

    python scripts/run_forecast.py --period test
        Refuses unless the split lock matches evaluation.json and the code is committed.
        Backtests the frozen settings on all the data, writes results/forecast/ (with the
        forward forecast for the six months after the data ends) and logs the run.

Measured on synthetic data with planted signals: Fjordvik Manufacturing Oy is fictional.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SERVICE_AI = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_AI / "src"))

from fjordvik_service import DEFAULT_DATA_DIR  # noqa: E402
from fjordvik_service.forecast import backtest, report  # noqa: E402
from fjordvik_service.forecast.lock import LockError, check_lock, write_lock  # noqa: E402
from fjordvik_service.forecast.splits import EVALUATION_PATH, LOCK_PATH, load_evaluation  # noqa: E402
from fjordvik_service.forecast.stamps import (  # noqa: E402
    environment, git_commit, scores_sha256, sha256_file, sha256_json, stamp, uncommitted)

RESULTS_DIR = SERVICE_AI / "results" / "forecast"
RUN_LOG = SERVICE_AI / "eval" / "forecast" / "test_runs.jsonl"
CODE_PATHS = [SERVICE_AI / "src", SERVICE_AI / "scripts", SERVICE_AI / "pyproject.toml", EVALUATION_PATH]


def require_committed(paths):
    changed = uncommitted(SERVICE_AI, paths)
    if changed:
        raise SystemExit("Refusing to run: commit these first, so the results can name their commit:\n  "
                         + "\n  ".join(changed))
    return git_commit(SERVICE_AI)


def print_summary(summary):
    print(summary["statement"])
    print(f"settings: {summary['settings']}")
    for wh, by_len in summary["warehouses"].items():
        for name, item in by_len.items():
            print(f"{wh} {name}: origins {item['origins']}, MASE {item.get('mase')}, "
                  f"driver coverage {item.get('driver_coverage')}")
    if "verdict" in summary:
        print(f"verdict: {summary['verdict']}; all pass marks met: {summary['all_pass_marks_met']}")


def validation(data_dir):
    commit = require_committed(CODE_PATHS)
    ev = load_evaluation()
    last = ev["periods"]["validation"]["last_target_month"]
    inputs = backtest.load_inputs(data_dir, ev, last_month=last)
    candidates = {k: list(v) for k, v in ev["chosen_on_validation"]["candidates"].items()}
    forecasts, used = backtest.run(inputs, ev, candidates)
    by_series, by_origin = backtest.score(forecasts, ev, periods=["validation"])
    settings, pooled = backtest.choose(by_series, ev)
    stamps = stamp(data_dir, commit)
    summary = report.summarise(by_series, inputs, ev, settings, stamps, "validation")
    summary["candidates_overall_mase_6_month"] = pooled
    summary["data_used_up_to"] = last
    out = RESULTS_DIR / "validation"
    manifest = report.write_results(
        out, {"backtest_forecasts": forecasts, "metrics_by_series": by_series,
              "metrics_by_origin": by_origin, "drivers": used},
        summary, stamps, report.results_note(summary, by_origin, ev))
    chosen_from = sorted({str(o) for o in by_origin["origin"]})
    lock = write_lock(LOCK_PATH, EVALUATION_PATH, settings, {"period": "validation", "origins": chosen_from},
                      {**stamps, "environment": environment(),
                       "validation_manifest_sha256": sha256_file(out / "manifest.json"),
                       "written": datetime.now(timezone.utc).strftime("%Y-%m-%d")})
    print_summary(summary)
    print(f"candidates (overall 6-month MASE on validation): {pooled}")
    print(f"chosen: {settings}; lock settings_sha256 {lock['settings_sha256']}")
    print(f"wrote {len(manifest['files'])} files to {out} and {LOCK_PATH}")


def test(data_dir):
    try:
        settings = check_lock(LOCK_PATH, EVALUATION_PATH)
    except LockError as err:
        raise SystemExit(f"Refusing to run the test period: {err}")
    commit = require_committed(CODE_PATHS + [LOCK_PATH])
    ev = load_evaluation()
    inputs = backtest.load_inputs(data_dir, ev)
    forecasts, used = backtest.run(inputs, ev, settings)
    by_series, by_origin = backtest.score(forecasts, ev, periods=["validation", "test"])
    stamps = stamp(data_dir, commit)
    summary = report.summarise(by_series, inputs, ev, settings, stamps, "test")
    summary["validation"] = report.summarise(by_series, inputs, ev, settings, stamps, "validation")["warehouses"]
    forward_origin = backtest.month(ev["periods"]["forward"]["origin"])
    forward = forecasts[forecasts["origin"] == forward_origin]

    # A rerun with the same frozen settings and data must reproduce the scores (E1, G10). The
    # comparison leaves out the stamp columns, so a rerun at a later commit still compares.
    scores = scores_sha256(report.tidy(by_series).to_csv(index=False, lineterminator="\n"))
    settings_sha = sha256_json(settings)
    earlier = [json.loads(line) for line in RUN_LOG.read_text(encoding="utf-8").splitlines()] if RUN_LOG.exists() else []
    previous_file = RESULTS_DIR / "metrics_by_series.csv"
    for e in earlier:
        if (e["settings_sha256"], e["data_sha256"]) != (settings_sha, stamps["data_sha256"]):
            continue
        # Runs logged before scores_sha256 existed: compare with the results they left on disk.
        before = e.get("scores_sha256") or scores_sha256(previous_file.read_text(encoding="utf-8"))
        if before != scores:
            raise SystemExit(f"Test scores differ from the run of {e['time']} with the same settings and data (G10)")

    manifest = report.write_results(
        RESULTS_DIR, {"backtest_forecasts": forecasts, "metrics_by_series": by_series,
                      "metrics_by_origin": by_origin, "drivers": used, "forecast_2026h1": forward},
        summary, stamps, report.results_note(summary, by_origin, ev))
    entry = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "commit": commit,
             "data_sha256": stamps["data_sha256"], "settings_sha256": settings_sha,
             "metrics_by_series_sha256": manifest["files"]["metrics_by_series.csv"]["sha256"],
             "scores_sha256": scores}
    with RUN_LOG.open("a", encoding="utf-8", newline="\n") as log:
        log.write(json.dumps(entry) + "\n")
    print_summary(summary)
    reproduced = sum((e["settings_sha256"], e["data_sha256"]) == (settings_sha, stamps["data_sha256"]) for e in earlier)
    print(f"test run {len(earlier) + 1} logged in {RUN_LOG}"
          + (f"; scores identical to {reproduced} earlier run(s) with the same settings and data" if reproduced else "")
          + f"; wrote {len(manifest['files'])} files to {RESULTS_DIR}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--period", choices=["validation", "test"], required=True)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    args = parser.parse_args()
    (validation if args.period == "validation" else test)(args.data_dir)


if __name__ == "__main__":
    main()
