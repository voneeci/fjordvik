"""Forecast scores: mean absolute scaled error (MASE), interval coverage and the Winkler score."""

import numpy as np

from .checks import PipelineCheckError

SEASON = 12  # months in a year


def scale_q(train):
    """Mean absolute error of seasonal naive on the training months: the MASE denominator."""
    values = np.asarray(train, dtype=float)
    if len(values) <= SEASON:
        raise PipelineCheckError(f"scale: {len(values)} training months, need more than {SEASON}")
    q = float(np.mean(np.abs(values[SEASON:] - values[:-SEASON])))
    if q <= 0:
        raise PipelineCheckError("scale: seasonal naive has no error on the training months")
    return q


def mase(actual, forecast, q):
    return float(np.mean(np.abs(np.asarray(actual, float) - np.asarray(forecast, float))) / q)


def covered(actual, lower, upper):
    actual = np.asarray(actual, float)
    return (actual >= np.asarray(lower, float)) & (actual <= np.asarray(upper, float))


def winkler(actual, lower, upper, level):
    """Interval width, plus 2 / alpha times any miss beyond either end (alpha = 1 - level)."""
    actual, lower, upper = (np.asarray(v, float) for v in (actual, lower, upper))
    alpha = 1 - level
    score = upper - lower
    score = score + np.where(actual < lower, (2 / alpha) * (lower - actual), 0.0)
    score = score + np.where(actual > upper, (2 / alpha) * (actual - upper), 0.0)
    return score
