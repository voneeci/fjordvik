from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def data_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "tables"


@pytest.fixture(scope="session")
def ev():
    from fjordvik_service.forecast.splits import load_evaluation

    return load_evaluation()


@pytest.fixture(scope="session")
def raw(data_dir):
    """The four tables the forecast reads, unchanged."""
    from fjordvik_service.forecast import demand, drivers

    return {
        "orders": demand.read_orders(data_dir),
        "parts": demand.read_parts(data_dir),
        "assets": drivers.read_assets(data_dir),
        "telemetry": drivers.read_telemetry(data_dir),
    }


@pytest.fixture(scope="session")
def ev_ml():
    from fjordvik_service.ml.splits import load_evaluation

    return load_evaluation()


@pytest.fixture(scope="session")
def allow():
    from fjordvik_service.ml.splits import load_allowlist

    return load_allowlist()


@pytest.fixture(scope="session")
def subset_pumps(data_dir):
    """Every tenth pump: enough for real-path tests that stay quick."""
    import pandas as pd

    return sorted(pd.read_csv(data_dir / "dim_asset.csv", usecols=["asset_id"])["asset_id"])[::10]


@pytest.fixture(scope="session")
def validation_subset_run(data_dir, ev_ml, allow, subset_pumps):
    """The real validation step on every tenth pump, data cut at the validation cut-off."""
    from fjordvik_service.ml import pipeline

    return pipeline.validation_step(data_dir, ev_ml, allow, pumps=subset_pumps, expected=False)


@pytest.fixture(scope="session")
def full_inputs(raw, ev):
    from fjordvik_service.forecast.backtest import build_inputs

    return build_inputs(raw["orders"], raw["parts"], raw["assets"], raw["telemetry"], ev)
