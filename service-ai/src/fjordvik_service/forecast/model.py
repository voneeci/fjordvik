"""The driver model: a Poisson regression per warehouse and part family.

log(expected units) = a + b x running hours + c x mean age (+ a yearly sine and cosine),
with the drivers standardised on the origin's training months.
"""

import warnings

import numpy as np
import pandas as pd
# Imported directly, not through statsmodels.api: this laptop's Windows Application
# Control blocks one of statsmodels' compiled files (robust/_qn) that the api loads.
from statsmodels.genmod import families
from statsmodels.genmod.generalized_linear_model import GLM
from statsmodels.tools.tools import add_constant

from .checks import PipelineCheckError
from .drivers import DRIVERS

SEASON = 12  # months in a year


def design(drivers, months, centre, spread, season):
    x = (drivers[DRIVERS] - centre) / spread
    if season:
        angle = 2 * np.pi * np.array([m.month for m in months]) / SEASON
        x = x.assign(season_sin=np.sin(angle), season_cos=np.cos(angle))
    return add_constant(x, has_constant="add")


def fit_predict(y_train, drivers_train, drivers_future, season):
    """Fit on the training months and return the expected units for the forecast months."""
    centre = drivers_train[DRIVERS].mean()
    spread = drivers_train[DRIVERS].std(ddof=0)
    if (spread <= 0).any():
        raise PipelineCheckError(f"driver model: a driver does not vary in training {spread.to_dict()}")
    x_train = design(drivers_train, drivers_train.index, centre, spread, season)
    x_future = design(drivers_future, drivers_future.index, centre, spread, season)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = GLM(np.asarray(y_train, dtype=float), x_train, family=families.Poisson()).fit()
    if not result.converged:
        raise PipelineCheckError("driver model: the fit did not converge")
    expected = np.asarray(result.predict(x_future), dtype=float)
    if not np.isfinite(expected).all():
        raise PipelineCheckError("driver model: forecast is not finite")
    return expected


def driver_forecast(y_train, blended, origin, horizons, season):
    months_train = y_train.index
    future = pd.PeriodIndex([origin + h for h in horizons], freq="M")
    return fit_predict(y_train.to_numpy(), blended.loc[months_train], blended.loc[future], season)
