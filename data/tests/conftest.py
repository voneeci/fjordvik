import csv
from pathlib import Path

import pytest

from fjordvik_data.generate import COLUMNS

DATA = Path(__file__).resolve().parents[1] / "tables"


def read(name: str) -> list[dict]:
    with (DATA / f"{name}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="session")
def data_dir() -> Path:
    return DATA


@pytest.fixture(scope="session")
def tables() -> dict[str, list[dict]]:
    """The committed CSV files, read as text exactly as a consumer sees them."""
    names = list(COLUMNS)
    return {n: read(n) for n in names}
