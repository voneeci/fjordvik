"""Recheck the phase 2 MASE from the saved forecasts, independently (phase rule F1).

Uses the Python standard library only and imports nothing from the forecast package. It
rebuilds monthly demand from the raw order lines, each origin's seasonal naive scale from
its training months, and each origin's period from evaluation.json, then recomputes mean
absolute scaled error (MASE) per series from backtest_forecasts.csv and compares it with
metrics_by_series.csv. Exit code 1 on any mismatch.

    python scripts/recheck_forecast.py [--results results/forecast] [--data-dir ../data/tables]
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

SERVICE_AI = Path(__file__).resolve().parents[1]
TOLERANCE = 1e-9


def month_index(text):
    year, mon = text.split("-")
    return int(year) * 12 + int(mon) - 1


def read_demand(data_dir):
    family = {}
    with open(Path(data_dir) / "dim_part.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            family[row["part_id"]] = row["part_family"]
    units, first, last = defaultdict(int), {}, None
    with open(Path(data_dir) / "fact_parts_order.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            m = month_index(f"{row['date_key'][:4]}-{row['date_key'][4:6]}")
            wh = row["site_id"]
            units[(wh, family[row["part_id"]], m)] += int(row["quantity"])
            first[wh] = min(first.get(wh, m), m)
            last = m if last is None else max(last, m)
    return units, first, last


def period_of(origin, horizons, periods):
    for name in ("validation", "test"):
        lo = month_index(periods[name]["first_target_month"])
        hi = month_index(periods[name]["last_target_month"])
        if all(lo <= origin + h <= hi for h in horizons):
            return name
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=SERVICE_AI / "results" / "forecast")
    parser.add_argument("--data-dir", type=Path, default=SERVICE_AI.parent / "data" / "tables")
    parser.add_argument("--evaluation", type=Path, default=SERVICE_AI / "eval" / "forecast" / "evaluation.json")
    args = parser.parse_args()

    ev = json.loads(args.evaluation.read_text(encoding="utf-8"))
    units, first, last = read_demand(args.data_dir)
    forecasts = defaultdict(dict)
    actual_mismatches = 0
    with open(args.results / "backtest_forecasts.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            key = (row["warehouse"], row["part_family"], row["method"], month_index(row["origin"]))
            target = month_index(row["target_month"])
            forecasts[key][int(row["horizon"])] = float(row["forecast"])
            if target <= last and row["actual"] != "":
                if float(row["actual"]) != units[(row["warehouse"], row["part_family"], target)]:
                    actual_mismatches += 1

    scores = defaultdict(list)
    for (wh, fam, method, origin), by_h in forecasts.items():
        start = first[wh]
        train = [units[(wh, fam, m)] for m in range(start, origin + 1)]
        diffs = [abs(train[i] - train[i - 12]) for i in range(12, len(train))]
        q = sum(diffs) / len(diffs)
        for name, horizons in ev["origins"]["forecast_lengths"].items():
            period = period_of(origin, horizons, ev["periods"])
            if period is None or origin + max(horizons) > last:
                continue
            errors = [abs(units[(wh, fam, origin + h)] - by_h[h]) for h in horizons]
            scores[(wh, fam, method, period, name)].append(sum(errors) / len(errors) / q)

    checked, mismatches = 0, []
    saved = {}
    with open(args.results / "metrics_by_series.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            saved[(row["warehouse"], row["part_family"], row["method"], row["period"], row["length"])] = row
    for key, values in sorted(scores.items()):
        if key not in saved:
            mismatches.append(f"{key}: recomputed but not saved")
            continue
        row = saved[key]
        mine = sum(values) / len(values)
        theirs = float(row["mase"])
        checked += 1
        if abs(mine - theirs) > TOLERANCE * max(1.0, abs(theirs)) or len(values) != int(row["n_origins"]):
            mismatches.append(f"{key}: recomputed {mine:.12f} over {len(values)} origins, saved {theirs:.12f} over {row['n_origins']}")
    for key in saved:
        if key not in scores:
            mismatches.append(f"{key}: saved but not recomputed")

    overall = defaultdict(list)
    for (wh, fam, method, period, name), values in scores.items():
        overall[(wh, method, period, name)].append(sum(values) / len(values))
    print("Independent MASE recheck (synthetic data with planted signals)")
    print(f"results: {args.results}")
    for (wh, method, period, name), values in sorted(overall.items()):
        print(f"  {period:10s} {name:8s} {wh} {method:22s} overall MASE {sum(values) / len(values):.6f} ({len(values)} series)")
    print(f"series checked: {checked}; actual values differing from the order lines: {actual_mismatches}; "
          f"MASE mismatches: {len(mismatches)}")
    for line in mismatches:
        print("  " + line)
    ok = not mismatches and actual_mismatches == 0 and checked > 0
    print("OK: saved MASE matches the independent recomputation" if ok else "MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
