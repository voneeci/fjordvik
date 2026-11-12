"""The results files: summary against the pass marks, stamped tables, a results note and a manifest.

The writer itself moved to fjordvik_service.common.results in phase 3; `tidy` and
`write_results` keep their phase 2 names and arguments here.
"""

import pandas as pd

from ..common import results as _results
from ..common.results import tidy  # noqa: F401  (re-exported for phase 2)
from . import DATA_BASIS
from .backtest import count_test_origins, driver_id, overall
from .splits import lengths
from .stamps import environment


def roles(settings):
    benchmarks = ["naive", "seasonal_naive", f"moving_average_w{settings['moving_average_window']}"]
    return benchmarks, driver_id(settings["driver_model_season_term"])


def summarise(by_series, inputs, ev, settings, stamps, period):
    """Each warehouse's scores for the period and, for test, the verdict on each pass mark."""
    benchmarks, driver = roles(settings)
    marks = ev["pass_marks"]
    minimum = ev["minimum_test_origins"]["value"]
    counts = count_test_origins(inputs, ev)
    warehouses, verdict = {}, {}
    for name in lengths(ev):
        scores = overall(by_series, period, name)
        rows = by_series[(by_series["period"] == period) & (by_series["length"] == name)]
        judged = []
        for wh in inputs.warehouses():
            entry = warehouses.setdefault(wh, {})
            origins_n = int(rows.loc[rows["warehouse"] == wh, "n_origins"].max()) if (rows["warehouse"] == wh).any() else 0
            item = {"origins": origins_n}
            if period == "test":
                item["test_origins"] = counts[wh][name]
                item["in_scope"] = counts[wh][name] >= minimum
                if not item["in_scope"]:
                    item["reported_apart"] = (
                        f"fewer than {minimum} test origins; not pooled into the pass mark. Its first months "
                        f"(from {inputs.first_month(wh)}) are in every scale q, so if trade was still ramping "
                        "up then, its ranges are wider and its MASE lower than they would otherwise be")
            if origins_n:
                mase = {m: float(scores[(wh, m)]) for m in benchmarks + [driver] if (wh, m) in scores.index}
                best = min(benchmarks, key=lambda m: mase[m])
                d = rows[(rows["warehouse"] == wh) & (rows["method"] == driver)]
                n_int, n_cov = int(d["n_interval"].sum()), int(d["n_covered"].sum())
                item.update({
                    "mase": mase, "best_benchmark": best,
                    "driver_coverage": (n_cov / n_int) if n_int else None, "driver_intervals": n_int,
                })
                if period == "test":
                    item["pass_mase"] = bool(mase[driver] < mase["seasonal_naive"] and mase[driver] < mase[best])
                    cov = item["driver_coverage"]
                    item["pass_coverage"] = bool(cov is not None and marks["coverage"]["low"] <= cov <= marks["coverage"]["high"])
                    if item["in_scope"]:
                        judged.append(item)
            entry[name] = item
        if period == "test":
            if not judged:
                verdict[name] = {"mase": "not judged", "coverage": "not judged"}
            else:
                verdict[name] = {
                    "mase": "pass" if all(i["pass_mase"] for i in judged) else "miss",
                    "coverage": "pass" if all(i["pass_coverage"] for i in judged) else "miss",
                }
    summary = {
        **stamps,
        "period": period,
        "statement": f"Measured on {DATA_BASIS}: Fjordvik Manufacturing Oy is fictional; these are not results on real pumps or warehouses.",
        "settings": settings,
        "benchmarks": benchmarks,
        "driver_model": driver,
        "minimum_test_origins": minimum,
        "pass_marks": marks,
        "environment": environment(),
        "warehouses": warehouses,
    }
    if period == "test":
        summary["verdict"] = verdict
        summary["all_pass_marks_met"] = all(v[k] == "pass" for v in verdict.values() for k in v)
    return summary


def write_results(out_dir, tables, summary, stamps, readme):
    """Phase 2's results writer: the shared writer with phase 2's library versions."""
    return _results.write_results(out_dir, tables, summary, stamps, readme, environment())


def fmt(value, digits=3):
    return "n/a" if value is None else f"{value:.{digits}f}"


def results_note(summary, by_origin, ev):
    """The results page, built from the summary so no figure is typed by hand."""
    period = summary["period"]
    benchmarks, driver = summary["benchmarks"], summary["driver_model"]
    lines = [
        f"# Phase 2 forecast results ({period})",
        "",
        f"> **{summary['statement']}** The demand drivers were planted by the data generator, so "
        "these scores show the method works on a known signal, not how it would do on live demand.",
        "",
        f"Data checksum `{summary['data_sha256']}`, commit `{summary['commit']}`, model version "
        f"`{summary['model_version']}`. Settings chosen on validation: moving average of "
        f"{summary['settings']['moving_average_window']} months; driver model "
        f"{'with' if summary['settings']['driver_model_season_term'] else 'without'} a season term.",
        "",
        "MASE is mean absolute scaled error: each method's error divided by seasonal naive's error "
        "on the origin's training months. Below 1 beats that scale.",
        "",
    ]
    for name in lengths(ev):
        lines += [f"## {name} forecast", ""]
        lines += ["| Warehouse | Origins | " + " | ".join(benchmarks + [driver]) + " | Driver 80% coverage |",
                  "| --- | --- | " + " | ".join("---" for _ in benchmarks + [driver]) + " | --- |"]
        for wh, by_len in summary["warehouses"].items():
            item = by_len[name]
            if not item["origins"]:
                lines.append(f"| {wh} | 0 | " + " | ".join("n/a" for _ in benchmarks + [driver]) + " | n/a |")
                continue
            cells = [fmt(item["mase"].get(m)) for m in benchmarks + [driver]]
            lines.append(f"| {wh} | {item['origins']} | " + " | ".join(cells) + f" | {fmt(item['driver_coverage'])} |")
        lines.append("")
        if period == "test":
            v = summary["verdict"][name]
            lines += [f"Pass marks: MASE {v['mase']}; coverage {v['coverage']}.", ""]
            for wh, by_len in summary["warehouses"].items():
                if not by_len[name].get("in_scope", True):
                    lines += [f"{wh} is reported apart: {by_len[name]['reported_apart']}.", ""]
        per_origin = by_origin[(by_origin["period"] == period) & (by_origin["length"] == name)
                               & (by_origin["method"] == driver)]
        if len(per_origin):
            lines += ["Driver model per origin:", "",
                      "| Warehouse | Origin | MASE | 80% coverage | Winkler (scaled) |", "| --- | --- | --- | --- | --- |"]
            for rec in per_origin.itertuples():
                cov = None if pd.isna(rec.coverage) else rec.coverage
                wk = None if pd.isna(rec.winkler_scaled) else rec.winkler_scaled
                lines.append(f"| {rec.warehouse} | {rec.origin} | {fmt(rec.mase)} | {fmt(cov)} | {fmt(wk)} |")
            lines.append("")
    return "\n".join(lines)
