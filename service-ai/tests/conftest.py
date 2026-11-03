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
def full_inputs(raw, ev):
    from fjordvik_service.forecast.backtest import build_inputs

    return build_inputs(raw["orders"], raw["parts"], raw["assets"], raw["telemetry"], ev)
