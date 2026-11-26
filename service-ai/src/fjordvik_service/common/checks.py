"""Loud pipeline steps (phase rule D15): each step checks its rows, keys and missing values."""

import numpy as np
import pandas as pd


class PipelineCheckError(ValueError):
    """A pipeline step's output failed its row, key or missing-value check."""


def check_frame(df, step, keys, *, rows=None, min_rows=1, required=None):
    """Return df unchanged, or raise PipelineCheckError naming the step and the failure.

    keys: columns that must be unique together. required: columns that may hold no
    missing or infinite value (all columns when None).
    """
    if not isinstance(df, pd.DataFrame):
        raise PipelineCheckError(f"{step}: expected a table, got {type(df).__name__}")
    if len(df) < min_rows:
        raise PipelineCheckError(f"{step}: {len(df)} rows, expected at least {min_rows}")
    if rows is not None and len(df) != rows:
        raise PipelineCheckError(f"{step}: {len(df)} rows, expected {rows}")
    absent = [c for c in list(keys) + list(required or []) if c not in df.columns]
    if absent:
        raise PipelineCheckError(f"{step}: missing columns {absent}")
    if keys:
        duplicates = int(df.duplicated(list(keys)).sum())
        if duplicates:
            raise PipelineCheckError(f"{step}: {duplicates} duplicate keys on {list(keys)}")
    columns = list(df.columns) if required is None else list(required)
    counts = df[columns].isna().sum()
    if counts.any():
        raise PipelineCheckError(f"{step}: missing values {counts[counts > 0].to_dict()}")
    numbers = df[columns].select_dtypes("number")
    if len(numbers.columns) and not np.isfinite(numbers.to_numpy(dtype=float)).all():
        raise PipelineCheckError(f"{step}: infinite values")
    return df
