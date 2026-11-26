"""Anomaly scores: the robust z-scores come from features.py; here, the isolation forest.

The forest is fitted on training rows only, on the four z-scores, the four 14-day slopes and
the four changes against the baseline, with scikit-learn's default settings, the seed and
n_jobs=1. A blank input is read as 0, no change from the baseline. Its score is turned round
so a higher score means a more unusual pump-day.
"""

import numpy as np
from scipy.stats import rankdata
from sklearn.ensemble import IsolationForest

from .features import SENSORS

IFOREST_INPUTS = ([f"{s}_z" for s in SENSORS] + [f"{s}_slope14" for s in SENSORS]
                  + [f"{s}_med7_vs_base" for s in SENSORS])


def rng(seed):
    """An explicit bit generator (G10)."""
    return np.random.RandomState(np.random.PCG64(seed))


def _inputs(frame):
    return frame[IFOREST_INPUTS].fillna(0.0).to_numpy(dtype=float)


def fit_iforest(train_rows, seed):
    forest = IsolationForest(random_state=rng(seed), n_jobs=1)
    forest.fit(_inputs(train_rows))
    return forest


def iforest_score(forest, frame):
    return -forest.score_samples(_inputs(frame))


def as_ranking(scores):
    """A score used alone, as a ranking: blank rows rank lowest, ties stay tied."""
    s = np.asarray(scores, dtype=float)
    out = np.zeros(len(s))
    ok = ~np.isnan(s)
    out[ok] = rankdata(s[ok], method="dense")
    return out
