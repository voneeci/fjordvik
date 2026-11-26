"""Summaries against the pass marks, the model card and the results note (W8, M4)."""

from . import DATA_BASIS, MODEL_VERSION

STATEMENT = (f"Measured on {DATA_BASIS}: Fjordvik Manufacturing Oy is fictional, and these are not results "
             "on real pumps or a real service team.")


def verdict(test, validation, ev):
    """Each pass mark, judged on the test period (the shuffled-label control on validation)."""
    marks = ev["pass_marks"]
    e = test["alerts"]["evaluated"]
    pl = test["alerts"]["plans"]
    recall = e["recall_of_warned_failures"]
    d = test["drift"]
    items = {
        "average_precision": test["ap_ratio_to_dummy"] >= marks["average_precision"]["min_ratio_to_dummy"],
        "recall_of_warned_failures": recall is not None and recall >= marks["recall_of_warned_failures"]["min"],
        "cost_below_visit_none": e["cost_eur"] < pl["visit_none"]["cost_eur"],
        "cost_below_visit_every_pump": e["cost_eur"] < pl["visit_every_pump"]["cost_eur"],
        "unwarned_failures_reported_apart": True,
        "leakage_test": bool(test["leakage"]["pass"]),
        "shuffled_labels": bool(validation["shuffled_labels"]["pass"]),
        "control_telemetry_validation": bool(validation["control"]["pass"]),
        "control_telemetry_test": bool(test["control"]["pass"]),
        "drift_detection": all(v >= d["detection_limit"] for v in d["detection_share"].values()),
        "drift_false_flags": d["false_flag_share"] <= d["false_flag_limit"],
    }
    return {k: "pass" if v else "miss" for k, v in items.items()}


def summary(result, stamps, environment, ev, *, validation=None):
    out = {**stamps, "statement": STATEMENT, "pass_marks": ev["pass_marks"], "environment": environment, **result}
    if result["period"] == "test":
        out["validation_summary"] = {k: validation[k] for k in
                                     ["settings", "threshold", "drift_level", "shuffled_labels", "control",
                                      "group_check", "average_precision", "ap_ratio_to_dummy"]}
        out["verdict"] = verdict(result, validation, ev)
        out["all_pass_marks_met"] = all(v == "pass" for v in out["verdict"].values())
    return out


def model_card(settings, threshold, level, allow, columns, stamps, environment, detail, ev, settings_sha256):
    return {
        **stamps, "statement": STATEMENT, "model_version": MODEL_VERSION,
        "what_a_score_means": ev["score"]["meaning"],
        "ceiling": ev["score"]["ceiling"],
        "classifier": "scikit-learn HistGradientBoostingClassifier, no class weights",
        "settings_chosen_on_validation": settings, "settings_sha256": settings_sha256,
        "outside_the_grid": "library defaults, listed under params, including early stopping on a held-out 10% of training rows",
        "params": detail["params"], "iterations_fitted": detail["n_iter"],
        "isolation_forest_params": detail["iforest_params"],
        "threshold": threshold, "threshold_rule": ev["threshold"],
        "drift_flag_level": level,
        "features": columns, "allowlist": "eval/ml/feature_allowlist.json",
        "blank_counts_in_training_rows": detail["blank_counts_train"],
        "data_handling": [
            "A day with no running has no reading: its power of zero is treated as blank.",
            "Fleet-adjusted readings are rounded to 9 decimal places before the baseline spread is taken, "
            "removing floating-point noise; every sensor is recorded to 0.1 or 0.01 of its unit.",
            "A robust z-score with a zero baseline spread, or fewer than 60 baseline readings, is blank.",
            "The isolation forest reads a blank input as 0, no change from the baseline.",
            "Used alone, the robust z-score ranks rows with no z-score lowest.",
        ],
        "environment": environment,
        "random_generators": "numpy RandomState(PCG64(seed)), made fresh for each fit (G10)",
        "seed": ev["seed"]["value"],
    }


def _f(x, d=3):
    return "n/a" if x is None else f"{x:,.{d}f}"


def _eur(x):
    return f"EUR {x:,.0f}"


def results_note(s, ev):
    """The results page, built from the summary so no figure is typed by hand."""
    period = s["period"]
    a = s["average_precision"]
    e = s["alerts"]["evaluated"]
    pl = s["alerts"]["plans"]
    thr = s["threshold"] if period == "test" else s["threshold"]["threshold"]
    lines = [
        f"# Phase 3 failure risk results ({period})",
        "",
        f"> **{s['statement']}** The warning rise before most failures was planted by the data "
        "generator, so these scores show the method finds a known signal, not how it would do on "
        "live pumps.",
        "",
        f"Data checksum `{s['data_sha256']}`, commit `{s['commit']}`, model version `{s['model_version']}`.",
        "",
        "A score is the model's estimate of the chance that the pump has a failure in the 30 days "
        "after the day, from readings up to the end of that day.",
        "",
        "## Ranking (average precision)",
        "",
        f"Scored pump-days: {a['rows']:,}, of which {a['positive_rows']:,} ({a['positive_share']:.2%}) "
        "have a failure in the next 30 days. The dummy model's average precision equals that share.",
        "",
        "| Model | Average precision | Times the dummy's |",
        "| --- | --- | --- |",
    ]
    for key, label in [("classifier", "Classifier"), ("pump_facts_only", "Pump facts only"),
                       ("robust_z_alone", "Robust z-score alone"), ("isolation_forest_alone", "Isolation forest alone"),
                       ("dummy", "Dummy (positive share)")]:
        lines.append(f"| {label} | {_f(a[key])} | {_f(a[key] / a['dummy'], 2)} |")
    lines += ["", f"Alert threshold {thr:.6f} (chosen on validation from the costs, no answer key).", "",
              "## Alerts and cost (central missed-failure cost)", "",
              f"Failures in the alert window: {e['failures']}. Warned (from the answer key, evaluation only): "
              f"{e['warned_failures']}; unwarned: {e['unwarned_failures']}, which no plan can prevent, so the "
              f"ceiling on catching failures is {e['warned_failures'] / e['failures']:.0%} of them." if e["failures"] else
              "No failures in the alert window.", "",
              f"Alerts: {e['alerts']} ({e['caught']} caught a warned failure 7 to 30 days ahead, {e['wasted']} wasted, "
              f"{e['neither']} came 1 to 6 days before a failure). Recall of warned failures: "
              f"{_f(e['recall_of_warned_failures'])}.", "",
              "| Plan | Visits | Failures caught | Missed | Wasted visits | Cost |", "| --- | --- | --- | --- | --- | --- |",
              f"| Model alerts | {e['alerts']} | {e['caught']} | {e['missed']} | {e['wasted']} | {_eur(e['cost_eur'])} |"]
    for key, label in [("visit_none", "Visit none"), ("visit_every_pump", "Visit every pump every 30 days")]:
        x = pl[key]
        lines.append(f"| {label} | {x['visits']:,} | {x['caught']} | {x['missed']} | {x['wasted']:,} | {_eur(x['cost_eur'])} |")
    if "sensitivity" in s:
        lines += ["", "Sensitivity to the missed-failure cost (alerts unchanged):", "",
                  "| Missed-failure cost | Model | Visit none | Visit every pump |", "| --- | --- | --- | --- |"]
        for key in ["low", "central", "high"]:
            x = s["sensitivity"][key]
            lines.append(f"| {key}, {_eur(x['missed_failure_cost_eur'])} | {_eur(x['model'])} | "
                         f"{_eur(x['visit_none'])} | {_eur(x['visit_every_pump'])} |")
    if "ranges" in s:
        r = s["ranges"]
        lines += ["", "90% ranges from 1,000 resamples of pumps:", ""]
        for key, label in [("classifier_ap", "Classifier average precision"), ("ap_ratio", "Times the dummy's"),
                           ("recall", "Recall of warned failures"), ("model_cost", "Model cost"),
                           ("visit_every_cost", "Visit-every-pump cost")]:
            fmt = _eur if key.endswith("cost") else _f
            lines.append(f"- {label}: {fmt(r[key]['low'])} to {fmt(r[key]['high'])}")
    lines += ["", "## Controls", ""]
    if period == "test":
        v = s["validation_summary"]
        sh = v["shuffled_labels"]
        lines.append(f"- Shuffled labels (validation): {_f(sh['ratio_to_dummy'], 2)} times the dummy, limit {sh['limit']}.")
        for label, ctl in [("validation", v["control"]), ("test", s["control"])]:
            r = ctl["ratio_to_dummy"]
            lines.append(f"- Warnings switched off ({label}): classifier {_f(r['classifier'], 2)}, robust z-score "
                         f"{_f(r['robust_z_alone'], 2)}, isolation forest {_f(r['isolation_forest_alone'], 2)} times the "
                         f"dummy, limit {ctl['limit']}; pump facts only {_f(ctl['pump_facts_only_ratio'], 2)}.")
        g = v["group_check"]
        lines.append(f"- Grouped by pump (5 folds, train and validation): mean average precision "
                     f"{_f(g['mean_average_precision'])} against {_f(g['time_split_average_precision'])} on the time split.")
        d = s["drift"]
        shares = ", ".join(f"{k} {v:.0%}" for k, v in d["detection_share"].items())
        lines.append(f"- Drift: flagged within {d['within_days']} days: {shares} (limit {d['detection_limit']:.0%}); "
                     f"false flags {d['false_flag_share']:.2%} of {d['pump_months_monitored']} pump-months "
                     f"(limit {d['false_flag_limit']:.0%}).")
        lines.append(f"- Leakage test: {'pass' if s['leakage']['pass'] else 'miss'} "
                     f"({s['leakage']['pump_days_checked']} pump-days rebuilt with later rows deleted).")
        lines += ["", "## Pass marks", "", "| Mark | Result |", "| --- | --- |"]
        for k, val in s["verdict"].items():
            lines.append(f"| {k.replace('_', ' ')} | {val} |")
        lines += ["", f"All pass marks met: {'yes' if s['all_pass_marks_met'] else 'no'}."]
        if s.get("missed_controls_accepted"):
            acc = s["missed_controls_accepted"]
            lines += ["", f"Missed on validation and carried to this single test run by decision: "
                      f"{', '.join(acc['controls'])}. {acc['decision']}"]
    else:
        sh = s["shuffled_labels"]
        lines.append(f"- Shuffled labels: {_f(sh['ratio_to_dummy'], 2)} times the dummy, limit {sh['limit']}.")
        if "control" in s:
            r = s["control"]["ratio_to_dummy"]
            lines.append(f"- Warnings switched off: classifier {_f(r['classifier'], 2)}, robust z-score "
                         f"{_f(r['robust_z_alone'], 2)}, isolation forest {_f(r['isolation_forest_alone'], 2)} times "
                         f"the dummy, limit {s['control']['limit']}.")
        g = s["group_check"]
        lines.append(f"- Grouped by pump (5 folds): mean average precision {_f(g['mean_average_precision'])} "
                     f"against {_f(g['time_split_average_precision'])} on the time split.")
        lines.append(f"- Drift flag level chosen on base data to the cut-off: {_f(s['drift_level']['level'])}.")
    lines += ["", "Accuracy and the area under the ROC (receiver operating characteristic) curve are not shown: "
              "with so few positive rows they flatter any model (M4).", ""]
    return "\n".join(lines)
