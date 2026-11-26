"""Independent recheck of the phase 3 headline metrics.

    python scripts/recheck_ml.py [--results results/ml]

Python standard library only; imports nothing from the fjordvik_service package. From the
saved scores, the raw tables, the planning inputs and (for the warned flag only, as
evaluation) the answer key, it rebuilds: the at-risk rows, the labels, average precision of
the classifier and the dummy, the alerts and what each one did, recall of warned failures,
and the cost of the three plans. Counts must match exactly, the rest within 1e-9 relative.

Measured on synthetic data with planted signals: Fjordvik Manufacturing Oy is fictional.
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

SERVICE_AI = Path(__file__).resolve().parents[1]
REPO = SERVICE_AI.parent
TABLES = REPO / "data" / "tables"
ANSWER_KEY = REPO / "data" / "generator-truth" / "failures.csv"
PLANNING = REPO / "data" / "scenarios" / "planning_inputs.json"
EVALUATION = SERVICE_AI / "eval" / "ml" / "evaluation.json"


def d(text):
    return date.fromisoformat(text)


def read_csv(path, columns=None):
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            yield row if columns is None else {c: row[c] for c in columns}


def at_risk_rows(tables, pumps, failures, ev, first, last, cut_off):
    """(pump, day) for every telemetry row in [first, last] that is at risk: no open failure
    ticket, a day with running, and at least the baseline's readings in days t-97 to t-8."""
    base = ev["model"]["features"]["baseline"]
    length, lag, need = base["length_days"], base["ends_days_before_t"], base["min_readings"]
    readings = defaultdict(dict)
    rows = []
    for r in read_csv(tables / "fact_asset_telemetry.csv"):
        if pumps is not None and r["asset_id"] not in pumps:
            continue
        k = r["date_key"]
        day = date(int(k[:4]), int(k[4:6]), int(k[6:]))
        if day > cut_off:
            continue
        ran = r["vibration_mm_s"] != ""
        readings[r["asset_id"]][day] = ran
        no_running = float(r["running_hours"]) == 0 and r["vibration_mm_s"] == "" and r["bearing_temp_c"] == ""
        if first <= day <= last:
            rows.append((r["asset_id"], day, no_running))
    out = set()
    for pump, day, no_running in rows:
        if any(rep <= day <= done for rep, done in failures.get(pump, [])) or no_running:
            continue
        n = sum(readings[pump].get(day - timedelta(days=i), False) for i in range(lag, lag + length))
        if n >= need:
            out.add((pump, day))
    return out


def average_precision(labels, scores):
    """Sum over distinct score thresholds of (recall gain) x precision, as scikit-learn defines it."""
    pairs = sorted(zip(scores, labels, strict=True), key=lambda p: -p[0])
    total = sum(labels)
    tp = seen = 0
    ap = prev_recall = 0.0
    i = 0
    while i < len(pairs):
        j = i
        while j < len(pairs) and pairs[j][0] == pairs[i][0]:
            tp += pairs[j][1]
            seen += 1
            j += 1
        recall = tp / total
        ap += (recall - prev_recall) * (tp / seen)
        prev_recall = recall
        i = j
    return ap


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results", type=Path, default=SERVICE_AI / "results" / "ml")
    parser.add_argument("--data-dir", type=Path, default=TABLES)
    parser.add_argument("--evaluation", type=Path, default=EVALUATION)
    args = parser.parse_args()
    ev = json.loads(args.evaluation.read_text(encoding="utf-8"))
    summary = json.loads((args.results / "summary.json").read_text(encoding="utf-8"))
    period = summary["period"]
    p = ev["periods"][period]
    first_scored, last_scored = d(p["first_scored_day"]), d(p["last_scored_day"])
    alert_first, alert_last = d(p["alert_window"]["first_day"]), d(p["alert_window"]["last_day"])
    cut_off, window_days = d(p["cut_off"]), p["alert_window"]["days"]
    threshold = summary["threshold"] if period == "test" else summary["threshold"]["threshold"]
    pumps = set(summary["pump_subset"]) if summary.get("pump_subset") else None
    planning = json.loads(PLANNING.read_text(encoding="utf-8"))
    cw = planning["wasted_visit"]["cost_eur_per_event"]
    cm = planning["missed_failure"]["cost_eur_per_event"]["central"]
    horizon = ev["periods"]["label_window_days"]
    lo, hi = ev["alerts"]["caught_days_before"]["min"], ev["alerts"]["caught_days_before"]["max"]
    quiet = ev["alerts"]["quiet_days"]

    failures = defaultdict(list)
    for r in read_csv(args.data_dir / "fact_service_event.csv", ["event_type", "asset_id", "reported_date", "completed_date"]):
        if r["event_type"] != "Failure" or (pumps is not None and r["asset_id"] not in pumps):
            continue
        rep = d(r["reported_date"])
        if rep <= cut_off:
            failures[r["asset_id"]].append((rep, min(d(r["completed_date"]), cut_off)))
    warned = {(r["asset_id"], d(r["failure_date"])): r["warned"] == "1"
              for r in read_csv(ANSWER_KEY, ["asset_id", "failure_date", "warned"])}

    name = "scores.csv" if period == "validation" else "scores_test.csv"
    saved = [(r["asset_id"], d(r["date"]), float(r["score"])) for r in read_csv(args.results / name)]
    problems = []
    expected_rows = at_risk_rows(args.data_dir, pumps, failures, ev, alert_first, alert_last, cut_off)
    if {(a, t) for a, t, _ in saved} != expected_rows or len(saved) != len(expected_rows):
        problems.append(f"at-risk rows: {len(saved)} saved, {len(expected_rows)} rebuilt, or a different set")

    labels, scores = [], []
    for a, t, s in saved:
        if first_scored <= t <= last_scored:
            labels.append(int(any(t < rep <= t + timedelta(days=horizon) for rep, _ in failures.get(a, []))))
            scores.append(s)
    got = {"classifier_ap": average_precision(labels, scores), "dummy_ap": sum(labels) / len(labels)}
    got["ap_ratio"] = got["classifier_ap"] / got["dummy_ap"]

    by_pump = defaultdict(list)
    for a, t, s in saved:
        by_pump[a].append((t, s))
    window_fails = {a: sorted(rep for rep, _ in f if alert_first <= rep <= alert_last) for a, f in failures.items()}
    n = {"alerts": 0, "caught": 0, "wasted": 0, "neither": 0}
    for a, days in sorted(by_pump.items()):
        next_ok = None
        caught = set()
        for t, s in sorted(days):
            if s < threshold or (next_ok is not None and t < next_ok):
                continue
            next_ok = t + timedelta(days=quiet)
            n["alerts"] += 1
            near = [rep for rep in window_fails.get(a, []) if 1 <= (rep - t).days <= horizon]
            catch = [rep for rep in near if lo <= (rep - t).days <= hi and warned[(a, rep)] and rep not in caught]
            if catch:
                caught.add(catch[0])
                n["caught"] += 1
            elif any(warned[(a, rep)] for rep in near):
                n["neither"] += 1
            else:
                n["wasted"] += 1
    all_window = [(a, rep) for a, reps in window_fails.items() for rep in reps]
    n_fail = len(all_window)
    n_warned = sum(warned[k] for k in all_window)
    got.update(n)
    got.update({"failures": n_fail, "warned_failures": n_warned, "unwarned_failures": n_fail - n_warned,
                "missed": n_fail - n["caught"]})
    got["recall_of_warned_failures"] = n["caught"] / n_warned if n_warned else None
    got["model_cost"] = (n_fail - n["caught"]) * cm + n["wasted"] * cw
    in_window = set()
    for r in read_csv(args.data_dir / "fact_asset_telemetry.csv", ["date_key", "asset_id"]):
        k = r["date_key"]
        day = date(int(k[:4]), int(k[4:6]), int(k[6:]))
        if alert_first <= day <= alert_last and (pumps is None or r["asset_id"] in pumps):
            in_window.add(r["asset_id"])
    visits = len(in_window) * (window_days // 30)
    got["visit_none_cost"] = n_fail * cm
    got["visit_every_cost"] = (n_fail - n_warned) * cm + (visits - n_warned) * cw

    e, pl, a = summary["alerts"]["evaluated"], summary["alerts"]["plans"], summary["average_precision"]
    want = {"classifier_ap": a["classifier"], "dummy_ap": a["dummy"], "ap_ratio": summary["ap_ratio_to_dummy"],
            "model_cost": e["cost_eur"], "visit_none_cost": pl["visit_none"]["cost_eur"],
            "visit_every_cost": pl["visit_every_pump"]["cost_eur"],
            "recall_of_warned_failures": e["recall_of_warned_failures"],
            **{k: e[k] for k in ["alerts", "caught", "wasted", "neither", "failures", "warned_failures",
                                 "unwarned_failures", "missed"]}}
    counts = {"alerts", "caught", "wasted", "neither", "failures", "warned_failures", "unwarned_failures", "missed"}
    print(f"Recheck of {args.results} ({period}); synthetic data with planted signals")
    print(f"{'metric':28} {'saved':>22} {'recomputed':>22}  result")
    for k, w in want.items():
        g = got[k]
        if k in counts:
            ok = g == w
        elif w is None or g is None:
            ok = g is None and w is None
        else:
            ok = abs(g - w) <= 1e-9 * max(1.0, abs(w))
        print(f"{k:28} {w!s:>22} {g!s:>22}  {'match' if ok else 'MISMATCH'}")
        if not ok:
            problems.append(k)
    print(f"at-risk rows rebuilt: {len(expected_rows)}; scored rows {len(labels)}, positive {sum(labels)}")
    if problems:
        print("FAIL: " + ", ".join(problems))
        sys.exit(1)
    print("OK: every headline metric matches the independent recomputation")


if __name__ == "__main__":
    main()
