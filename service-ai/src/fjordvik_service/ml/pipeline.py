"""The validation and test steps, end to end. run_ml.py calls these; the tests call them on a
few pumps with data cut at the end of validation.

Validation reads nothing after its cut-off (30 June 2025). It chooses the classifier's
settings, the alert threshold and the drift flag level, and runs the shuffled-label and
control checks. The test step uses only what the split lock froze.
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

from ..common.checks import PipelineCheckError
from . import alerts, anomaly, drift, evaluate, features, labels, model
from .splits import SERVICE_AI_DIR, check_rests_on, no_label_window, periods

IFOREST = "iforest_score"


def feature_columns(allow):
    return features.feature_names(allow)


def load(data_dir, ev, allow, *, cut_off, telemetry_path=None, pumps=None):
    tables = features.read_tables(data_dir, allow, telemetry_path=telemetry_path, cut_off=cut_off, pumps=pumps)
    feats = features.build(tables, ev, allow)
    fails = labels.read_failures(data_dir, ev, cut_off=cut_off, pumps=pumps)
    rows, keep, counts = labels.at_risk(feats, fails, ev)
    return {"tables": tables, "rows": rows, "keep": keep, "counts": counts, "failures": fails}


def masks(rows, keep, ev):
    p = periods(ev)
    d = rows["date"]
    out = {"train": keep & (d <= p["train"]["last_scored"]).to_numpy()}
    for name in ["validation", "test"]:
        out[f"{name}_scored"] = keep & d.between(p[name]["first_scored"], p[name]["last_scored"]).to_numpy()
        out[f"{name}_alert"] = keep & d.between(p[name]["alert_first"], p[name]["alert_last"]).to_numpy()
    return out


def add_iforest(data, ev):
    """Fit the forest on training rows only and score every row."""
    rows, m = data["rows"], masks(data["rows"], data["keep"], ev)
    forest = anomaly.fit_iforest(rows[m["train"]], ev["seed"]["value"])
    rows[IFOREST] = anomaly.iforest_score(forest, rows)
    data["masks"], data["forest"] = m, forest
    return data


def counts_check(data, ev, available, *, full, expected):
    by_period = labels.period_counts(data["rows"], ev, available)
    fails = labels.failure_counts(data["failures"], ev, available)
    if expected:
        labels.check_expected(data["counts"], by_period, fails, ev, full=full)
    return {"overall": data["counts"], "by_period": by_period, "failures": fails}


def fit_classifier(data, settings, columns, ev):
    rows = data["rows"]
    fitted = model.fit(rows[data["masks"]["train"]], columns, settings, ev["seed"]["value"])
    features.assert_inside_allowlist(list(fitted.feature_names_in_), data["allow"])
    return fitted


def period_scores(data, fitted, columns, name):
    """The at-risk rows of a period's alert window with the classifier's score; `scored`
    marks the rows in its scored days, which average precision uses."""
    rows, m = data["rows"], data["masks"]
    sel = rows[m[f"{name}_alert"]]
    out = sel[["asset_id", "date", "label"]].copy()
    out["scored"] = m[f"{name}_scored"][m[f"{name}_alert"]]
    out["score"] = model.score(fitted, sel, columns)
    out["z_max"] = sel["z_max"].to_numpy()
    out[IFOREST] = sel[IFOREST].to_numpy()
    return out.reset_index(drop=True)


def average_precisions(data, fitted, dummy, facts, scores, columns, facts_cols):
    """Each model's average precision on the period's scored rows, and the positive share."""
    s = scores[scores["scored"]]
    rows = data["rows"].loc[data["masks"]["_scored_now"]]
    y = s["label"].to_numpy()
    return {
        "rows": len(s), "positive_rows": int(y.sum()), "positive_share": float(y.mean()),
        "classifier": model.ap(y, s["score"]),
        "dummy": model.ap(y, dummy.predict_proba(rows[["age_years"]])[:, 1]),
        "pump_facts_only": model.ap(y, model.score(facts, rows, facts_cols)),
        "robust_z_alone": model.ap(y, anomaly.as_ranking(s["z_max"])),
        "isolation_forest_alone": model.ap(y, s[IFOREST]),
    }


def control_run(data_dir, ev, allow, settings, period_name, *, telemetry_path, cut_off, pumps=None):
    """E2: rebuild features on the control telemetry, train again with the same settings,
    and score the three models that read telemetry on the period's scored rows."""
    data = load(data_dir, ev, allow, cut_off=cut_off, telemetry_path=telemetry_path, pumps=pumps)
    data["allow"] = allow
    add_iforest(data, ev)
    columns = feature_columns(allow)
    facts_cols = allow["pump_facts_only_model"]["columns"]
    fitted = fit_classifier(data, settings, columns, ev)
    train = data["rows"][data["masks"]["train"]]
    dummy = model.fit_dummy(train)
    facts = model.fit(train, facts_cols, settings, ev["seed"]["value"])
    scores = period_scores(data, fitted, columns, period_name)
    data["masks"]["_scored_now"] = data["masks"][f"{period_name}_scored"]
    aps = average_precisions(data, fitted, dummy, facts, scores, columns, facts_cols)
    limit = ev["controls"]["control_telemetry"]["max_ratio_to_dummy"]
    ratios = {k: aps[k] / aps["dummy"] for k in ["classifier", "robust_z_alone", "isolation_forest_alone"]}
    return {"period": period_name, "average_precision": aps, "ratio_to_dummy": ratios, "limit": limit,
            "pass": all(r <= limit for r in ratios.values()),
            "pump_facts_only_ratio": aps["pump_facts_only"] / aps["dummy"]}


def leakage_check(data, ev, allow, n=20):
    """M2 in the run: point-in-time rebuilds at 20 random pump-days (D11), the fitted model's
    columns inside the allowlist (D12), and only evaluate.py naming the answer key (D10)."""
    rows = data["rows"][data["keep"]]
    pick = anomaly.rng(ev["seed"]["value"]).choice(len(rows), size=min(n, len(rows)), replace=False)
    pump_days = [(r.asset_id, r.date) for r in rows.iloc[np.sort(pick)].itertuples()]
    columns = [c for c in feature_columns(allow) if c != IFOREST]
    changed = features.check_point_in_time(lambda tb: features.build(tb, ev, allow), data["tables"], pump_days,
                                           columns, full=data["rows"], lookback=lookback_days(ev))
    readers = answer_key_readers()
    return {"pump_days_checked": len(pump_days), "point_in_time_changes": changed,
            "answer_key_named_in": readers,
            "pass": not changed and readers == ["src/fjordvik_service/ml/evaluate.py"]}


def reference_share(ev):
    """The drift reference's completeness: the baseline's own share, 60 readings of 90 days."""
    b = ev["model"]["features"]["baseline"]
    return b["min_readings"] / b["length_days"]


def lookback_days(ev):
    """How far back any feature reaches: the baseline plus the longest window."""
    f = ev["model"]["features"]
    return f["baseline"]["length_days"] + f["baseline"]["ends_days_before_t"] + max(f["windows_days"]["median"])


def answer_key_readers():
    """Files in the package and run script that name the answer key's folder."""
    paths = sorted((SERVICE_AI_DIR / "src").rglob("*.py")) + [SERVICE_AI_DIR / "scripts" / "run_ml.py"]
    pattern = re.compile("generator" + "-truth")
    return [p.relative_to(SERVICE_AI_DIR).as_posix() for p in paths
            if p.exists() and pattern.search(p.read_text(encoding="utf-8"))]


def pumps_with_telemetry(tables, first, last):
    t = tables["telemetry"]
    return sorted(t.loc[t["date"].between(first, last), "asset_id"].unique())


def judge_alerts(data, scores, threshold, ev, c, name, *, answer_key=True):
    """Alerts at the threshold over the period's alert window, in both views."""
    p = periods(ev)[name]
    opened = alerts.alert_days(scores[["asset_id", "date", "score"]], threshold, ev["alerts"]["quiet_days"])
    fails = alerts.failures_in_window(data["failures"], p["alert_first"], p["alert_last"])
    plain, plain_fails = alerts.classify(opened, fails, ev)
    out = {"threshold_view": alerts.summarise(plain, plain_fails, c)}
    if answer_key:
        warned = evaluate.warned_flags(fails)
        judged, judged_fails = alerts.classify(opened, fails, ev, warned=warned)
        pumps = pumps_with_telemetry(data["tables"], p["alert_first"], p["alert_last"])
        out.update({"outcomes": judged, "fails": judged_fails, "pumps_in_window": pumps,
                    "evaluated": alerts.summarise(judged, judged_fails, c),
                    "plans": evaluate.plans(judged_fails, len(pumps), p["alert_days"], c)})
    return out


def sensitivity(judged, plans_by_cost):
    s = judged["evaluated"]
    out = {}
    for key, (c, pl) in plans_by_cost.items():
        out[key] = {"missed_failure_cost_eur": c["missed_failure"][key],
                    "model": s["missed"] * c["missed_failure"][key] + s["wasted"] * c["wasted_visit"],
                    "visit_none": pl["visit_none"]["cost_eur"], "visit_every_pump": pl["visit_every_pump"]["cost_eur"]}
    return out


def ranges(scores, judged, c, ev, alert_days):
    """90% ranges from 1,000 seeded resamples of pumps with replacement (5th to 95th percentile)."""
    text = ev["metrics"]["range"]
    if "1,000 resamples of pumps" not in text or "5th to 95th percentile" not in text:
        raise PipelineCheckError(f"ranges: the evaluation set's range rule is not the one coded: {text}")
    n_res = 1000
    pumps = judged["pumps_in_window"]
    per = evaluate.per_pump(judged["outcomes"], judged["fails"], pumps, alert_days)
    s = scores[scores["scored"]]
    pump_index = pd.Index(pumps)
    row_pump = pump_index.get_indexer(s["asset_id"])
    if (row_pump < 0).any():
        raise PipelineCheckError("ranges: a scored row's pump has no telemetry in the window")
    y, score = s["label"].to_numpy(), s["score"].to_numpy()
    cm, cw = c["missed_failure"]["central"], c["wasted_visit"]
    gen = anomaly.rng(ev["seed"]["value"])
    out = {k: [] for k in ["classifier_ap", "dummy_ap", "ap_ratio", "recall", "model_cost", "visit_none_cost",
                           "visit_every_cost"]}
    arr = per.to_numpy()
    cols = {k: i for i, k in enumerate(per.columns)}
    for _ in range(n_res):
        mult = np.bincount(gen.randint(0, len(pumps), size=len(pumps)), minlength=len(pumps))
        w = mult[row_pump].astype(float)
        if (w * y).sum() == 0:
            continue
        cap = model.ap(y, score, w)
        dap = float((w * y).sum() / w.sum())
        tot = mult @ arr
        caught, wasted, failures, warned = (tot[cols[k]] for k in ["caught", "wasted", "failures", "warned"])
        visits = int(mult.sum()) * int(per["visits_every"].iloc[0])
        out["classifier_ap"].append(cap)
        out["dummy_ap"].append(dap)
        out["ap_ratio"].append(cap / dap)
        out["recall"].append(caught / warned if warned else np.nan)
        out["model_cost"].append((failures - caught) * cm + wasted * cw)
        out["visit_none_cost"].append(failures * cm)
        out["visit_every_cost"].append((failures - warned) * cm + (visits - warned) * cw)
    return {k: {"low": float(np.nanpercentile(v, 5)), "high": float(np.nanpercentile(v, 95)), "resamples": len(v)}
            for k, v in out.items()}


def reliability(scores, groups=10):
    s = scores[scores["scored"]].copy()
    s["group"] = pd.qcut(s["score"].rank(method="first"), groups, labels=False) + 1
    g = s.groupby("group")
    return pd.DataFrame({"rows": g.size(), "mean_score": g["score"].mean(), "min_score": g["score"].min(),
                         "max_score": g["score"].max(), "observed_failure_rate": g["label"].mean()}).reset_index()


def validation_step(data_dir, ev, allow, *, scenario_dir=None, pumps=None, expected=True, answer_key=True):
    """Choose the settings, threshold and drift level on data up to the validation cut-off."""
    if expected:
        check_rests_on(ev)
    p = periods(ev)
    cut = p["validation"]["cut_off"]
    seed = ev["seed"]["value"]
    data = load(data_dir, ev, allow, cut_off=cut, pumps=pumps)
    data["allow"] = allow
    add_iforest(data, ev)
    counts = counts_check(data, ev, ["train", "validation"], full=False, expected=expected)
    columns = feature_columns(allow)
    facts_cols = allow["pump_facts_only_model"]["columns"]
    rows, m = data["rows"], data["masks"]
    train, val = rows[m["train"]], rows[m["validation_scored"]]

    grid = []
    for settings in model.grid(ev):
        fitted = model.fit(train, columns, settings, seed)
        grid.append({"settings": settings, "average_precision": model.ap(val["label"], model.score(fitted, val, columns))})
    chosen = model.choose(grid, ev)
    fitted = fit_classifier(data, chosen, columns, ev)
    dummy = model.fit_dummy(train)
    facts = model.fit(train, facts_cols, chosen, seed)
    scores = period_scores(data, fitted, columns, "validation")
    m["_scored_now"] = m["validation_scored"]
    aps = average_precisions(data, fitted, dummy, facts, scores, columns, facts_cols)

    c = alerts.costs(ev)
    fails = alerts.failures_in_window(data["failures"], p["validation"]["alert_first"], p["validation"]["alert_last"])
    choice = alerts.choose_threshold(scores[["asset_id", "date", "score"]], fails, ev, c)
    judged = judge_alerts(data, scores, choice["threshold"], ev, c, "validation", answer_key=answer_key)
    tv = judged["threshold_view"]
    if (tv["alerts"], tv["caught"], tv["wasted"]) != (choice["alerts"], choice["caught"], choice["wasted"]):
        raise PipelineCheckError("threshold: the sweep and the alert count disagree")

    sh = model.shuffled_labels(train, val, columns, chosen, ev)
    sh_mean = float(np.mean([s["average_precision"] for s in sh]))
    sh_limit = ev["controls"]["shuffled_labels"]["max_ratio_to_dummy"]
    group = model.group_check(rows[m["train"] | m["validation_scored"]], columns, chosen, ev)

    d = ev["controls"]["drift"]
    meas = drift.measures(data["tables"]["telemetry"], reference_share(ev), data["failures"])
    pm = drift.pump_months(meas, data["failures"], d["false_flags"]["no_failure_within_days"], cut,
                           meas["date"].min(), cut)
    level = drift.choose_level(pm, d["false_flags"]["max_share"])

    result = {
        "period": "validation", "data_used_up_to": str(cut.date()), "pump_subset": pumps, "counts": counts,
        "grid": grid, "settings": chosen, "average_precision": aps,
        "ap_ratio_to_dummy": aps["classifier"] / aps["dummy"],
        "threshold": choice, "alerts": {k: v for k, v in judged.items() if k in ("threshold_view", "evaluated", "plans")},
        "shuffled_labels": {"runs": sh, "mean_average_precision": sh_mean, "ratio_to_dummy": sh_mean / aps["dummy"],
                            "limit": sh_limit, "pass": sh_mean / aps["dummy"] <= sh_limit},
        "group_check": {"folds": group, "mean_average_precision": float(np.mean([f["average_precision"] for f in group])),
                        "time_split_average_precision": aps["classifier"]},
        "drift_level": {"level": level, "pump_months": len(pm), "false_flag_share": drift.false_share(pm, level),
                        "chosen_on": f"base data to {cut.date()}"},
        "model_detail": {"n_iter": int(fitted.n_iter_), "params": {k: repr(v) for k, v in fitted.get_params().items()},
                         "iforest_params": {k: repr(v) for k, v in data["forest"].get_params().items()},
                         "blank_counts_train": {k: int(v) for k, v in train[columns].isna().sum().items() if v}},
    }
    if answer_key:
        result["sensitivity"] = sensitivity(judged, {k: (c, evaluate.plans(judged["fails"], len(judged["pumps_in_window"]),
                                                                           p["validation"]["alert_days"], c, k))
                                                     for k in ["low", "central", "high"]})
        result["ranges"] = ranges(scores, judged, c, ev, p["validation"]["alert_days"])
        result["leakage"] = leakage_check(data, ev, allow)
    if scenario_dir is not None:
        result["control"] = control_run(data_dir, ev, allow, chosen, "validation",
                                        telemetry_path=Path(scenario_dir) / "control" / "fact_asset_telemetry.csv",
                                        cut_off=cut, pumps=pumps)
    tables = {"scores": scores, "reliability": reliability(scores),
              "alerts": judged["outcomes"] if answer_key else pd.DataFrame(),
              "grid": pd.DataFrame([{**g["settings"], "average_precision": g["average_precision"]} for g in grid])}
    return result, tables


def test_step(data_dir, ev, allow, locked, *, scenario_dir, pumps=None, expected=True, cut_off=None):
    """Score the test period once with the frozen settings, threshold and drift level.

    cut_off is for the tests only: they run this step on a copy of the evaluation set whose
    "test" window lies before the validation cut-off, so no real test row is ever scored
    outside the one locked run (E1)."""
    if expected:
        check_rests_on(ev)
    p = periods(ev)
    seed = ev["seed"]["value"]
    data = load(data_dir, ev, allow, cut_off=cut_off, pumps=pumps)
    data["allow"], data["data_dir"] = allow, data_dir
    add_iforest(data, ev)
    counts = counts_check(data, ev, ["train", "validation", "test"], full=pumps is None, expected=expected)
    columns = feature_columns(allow)
    facts_cols = allow["pump_facts_only_model"]["columns"]
    settings, threshold = locked["classifier"], locked["threshold"]
    rows, m = data["rows"], data["masks"]
    train = rows[m["train"]]
    fitted = fit_classifier(data, settings, columns, ev)
    dummy = model.fit_dummy(train)
    facts = model.fit(train, facts_cols, settings, seed)
    val_scores = period_scores(data, fitted, columns, "validation")
    scores = period_scores(data, fitted, columns, "test")
    m["_scored_now"] = m["test_scored"]
    aps = average_precisions(data, fitted, dummy, facts, scores, columns, facts_cols)

    c = alerts.costs(ev)
    judged = judge_alerts(data, scores, threshold, ev, c, "test")
    plans_by_cost = {k: (c, evaluate.plans(judged["fails"], len(judged["pumps_in_window"]), p["test"]["alert_days"], c, k))
                     for k in ["low", "central", "high"]}

    d = ev["controls"]["drift"]
    level = locked["drift_flag_level"]
    drift_result, detect = (None, pd.DataFrame()) if scenario_dir is None else _drift_test(
        data, ev, allow, level, d, p, scenario_dir, pumps, cut_off)

    first, last = no_label_window(ev)
    risk = scores[scores["date"] == last][["asset_id", "date", "score"]].copy()
    risk["alert_level_reached"] = risk["score"] >= threshold
    risk["note"] = "no complete label window"
    risk = risk.sort_values("score", ascending=False, kind="mergesort").reset_index(drop=True)

    result = {
        "period": "test", "pump_subset": pumps, "counts": counts, "settings": settings, "threshold": threshold,
        "average_precision": aps, "ap_ratio_to_dummy": aps["classifier"] / aps["dummy"],
        "alerts": {k: v for k, v in judged.items() if k in ("threshold_view", "evaluated", "plans")},
        "sensitivity": sensitivity(judged, plans_by_cost),
        "ranges": ranges(scores, judged, c, ev, p["test"]["alert_days"]),
        "leakage": leakage_check(data, ev, allow),
        **({} if scenario_dir is None else {"control": control_run(
            data_dir, ev, allow, settings, "test", telemetry_path=Path(scenario_dir) / "control" / "fact_asset_telemetry.csv",
            cut_off=cut_off, pumps=pumps)}),
        **({} if drift_result is None else {"drift": drift_result}),
        "risk_list": {"date": str(last.date()), "pumps_scored": len(risk), "at_or_above_threshold": int(risk["alert_level_reached"].sum()),
                      "no_complete_label_window": f"{first.date()} to {last.date()}"},
    }
    tables = {"scores_test": scores, "scores_validation_rerun": val_scores, "alerts": judged["outcomes"],
              "reliability": reliability(scores), "drift": detect, "risk": risk}
    return result, tables


def _drift_test(data, ev, allow, level, d, p, scenario_dir, pumps, cut_off):
    """M5 in the test step: detection on the two scenarios, false flags on the base data."""
    meas = drift.measures(data["tables"]["telemetry"], reference_share(ev), data["failures"])
    ff_first, ff_last = (pd.Timestamp(x) for x in _months(d["false_flags"]["measured_on"], p))
    pm = drift.pump_months(meas, data["failures"], d["false_flags"]["no_failure_within_days"], p["test"]["cut_off"],
                           ff_first, ff_last)
    scen = pd.read_csv(Path(scenario_dir) / "drift_scenarios.csv")
    detect = []
    for name in ["drift_recalibration", "drift_unit_change"]:
        tb = features.read_tables(data["data_dir"], allow, telemetry_path=Path(scenario_dir) / name / "fact_asset_telemetry.csv",
                                  cut_off=cut_off, pumps=pumps)
        sc = scen[scen["scenario"] == name]
        if pumps is not None:
            sc = sc[sc["asset_id"].isin(pumps)]
        scen_meas = drift.measures(tb["telemetry"], reference_share(ev), data["failures"])
        detect.append(drift.detection(scen_meas, sc, level, d["detection"]["within_days"]))
    detect = pd.concat(detect, ignore_index=True)
    share = detect.groupby("scenario")["flagged_within_limit"].mean().to_dict()

    return {"level": level, "detection_share": share,
            "detection_limit": d["detection"]["min_share_flagged"], "within_days": d["detection"]["within_days"],
            "not_monitored_changed_pumps": int((~detect["monitored"]).sum()),
            "false_flag_share": drift.false_share(pm, level), "false_flag_limit": d["false_flags"]["max_share"],
            "pump_months_monitored": len(pm), "false_flags_measured_on": d["false_flags"]["measured_on"],
            "pumps_not_monitored_in_window": int(len(set(meas.loc[meas["date"].between(ff_first, ff_last), "asset_id"]))
                                                 - pm.index.get_level_values(0).nunique())}, detect


def _months(text, p):
    """The drift false-flag months, which the evaluation set names as the test alert window's
    months ('July to December 2025'); stop if the two ever disagree."""
    first, last = p["test"]["alert_first"], p["test"]["alert_last"]
    if text != f"{first:%B} to {last:%B %Y}":
        raise PipelineCheckError(f"drift false flags: '{text}' is not the test alert window")
    return first, last
