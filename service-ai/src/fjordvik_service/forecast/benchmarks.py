"""The simple forecasts every model must beat: naive, seasonal naive and moving average."""

import numpy as np

from .checks import PipelineCheckError

SEASON = 12  # months in a year


def naive(train, horizons):
    """Every month ahead equals the last training month."""
    return np.full(len(horizons), float(train.iloc[-1]))


def seasonal_naive(train, horizons):
    """Each month ahead equals the same month a year earlier."""
    origin = train.index[-1]
    out = []
    for h in horizons:
        last_year = origin + h - SEASON
        if last_year not in train.index:
            raise PipelineCheckError(f"seasonal naive: no actual for {last_year}")
        out.append(float(train.loc[last_year]))
    return np.array(out)


def moving_average(train, horizons, window):
    """Every month ahead equals the mean of the last `window` training months."""
    if len(train) < window:
        raise PipelineCheckError(f"moving average: {len(train)} months, window {window}")
    return np.full(len(horizons), float(train.iloc[-window:].mean()))
