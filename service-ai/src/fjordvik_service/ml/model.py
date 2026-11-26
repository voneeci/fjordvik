"""The failure classifier, its baselines and its controls.

HistGradientBoostingClassifier, no class weights (the threshold handles the imbalance, so
the output stays a usable probability). Settings come from the evaluation set's grid,
chosen on validation by average precision, ties to the simpler. Every random generator is
an explicit PCG64 bit generator (G10), made fresh for each fit.
"""

import itertools

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupKFold

from ..common.checks import PipelineCheckError
from .anomaly import rng


def grid(ev):
    """The 8 candidates, simplest first, in the evaluation set's tie order."""
    m = ev["model"]["chosen_on_validation"]
    order, simpler = m["tie_order"], m["simpler_first"]
    if sorted(simpler) != sorted(ev["model"]["grid"]) or any(
            sorted(simpler[k]) != sorted(ev["model"]["grid"][k]) for k in simpler):
        raise PipelineCheckError("the grid and its simpler-first order disagree")
    return [dict(zip(order, values, strict=True)) for values in itertools.product(*(simpler[k] for k in order))]


def classifier(settings, seed):
    return HistGradientBoostingClassifier(**settings, categorical_features="from_dtype", random_state=rng(seed))


def _xy(frame, columns, labels=None):
    x = frame[columns]
    y = frame["label"].to_numpy() if labels is None else np.asarray(labels)
    if len(x) == 0 or len(np.unique(y)) < 2:
        raise PipelineCheckError(f"training rows: {len(x)} rows with {len(np.unique(y))} label values")
    return x, y


def fit(frame, columns, settings, seed, labels=None):
    x, y = _xy(frame, columns, labels)
    return classifier(settings, seed).fit(x, y)


def score(model, frame, columns):
    p = model.predict_proba(frame[columns])[:, 1]
    if not np.isfinite(p).all():
        raise PipelineCheckError("scores: non-finite values")
    return p


def fit_dummy(frame):
    x, y = _xy(frame, ["age_years"])
    return DummyClassifier(strategy="prior").fit(x, y)


def ap(labels, scores, weights=None):
    return float(average_precision_score(labels, scores, sample_weight=weights))


def choose(results, ev):
    """The candidate with the highest validation average precision; on an exact tie, the one
    earlier in the simpler-first order (results are in that order)."""
    best = None
    for item in results:
        if best is None or item["average_precision"] > best["average_precision"]:
            best = item
    return best["settings"]


def shuffled_labels(train, val, columns, settings, ev):
    """D12 control: train on shuffled labels (seeds seed+1 to seed+5), score on validation."""
    seed = ev["seed"]["value"]
    out = []
    for k in range(1, ev["controls"]["shuffled_labels"]["shuffles"] + 1):
        y = rng(seed + k).permutation(train["label"].to_numpy())
        model = fit(train, columns, settings, seed, labels=y)
        out.append({"seed": seed + k, "average_precision": ap(val["label"], score(model, val, columns))})
    return out


def group_check(rows, columns, settings, ev):
    """M1: 5-fold GroupKFold by pump over train and validation rows, with the chosen settings."""
    seed = ev["seed"]["value"]
    folds = []
    splitter = GroupKFold(n_splits=5)
    for i, (tr, te) in enumerate(splitter.split(rows, rows["label"], groups=rows["asset_id"])):
        model = fit(rows.iloc[tr], columns, settings, seed)
        folds.append({"fold": i + 1, "rows": len(te), "pumps": int(rows["asset_id"].iloc[te].nunique()),
                      "average_precision": ap(rows["label"].iloc[te], score(model, rows.iloc[te], columns)),
                      "positive_share": float(rows["label"].iloc[te].mean())})
    return folds
