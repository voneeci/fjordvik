import csv
from collections import defaultdict
from pathlib import Path

import pytest

from fjordvik_data.generate import COLUMNS

DATA = Path(__file__).resolve().parents[1] / "tables"
TELEMETRY = "fact_asset_telemetry"


def read(name: str) -> list[dict]:
    with (DATA / f"{name}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class Tables(dict):
    """The committed CSV files, read as text exactly as a consumer sees them, each
    on first use. The daily telemetry is too big to hold as dicts: use the
    `telemetry` fixture for it."""

    def __missing__(self, name: str) -> list[dict]:
        if name not in COLUMNS or name == TELEMETRY:
            raise KeyError(name)
        self[name] = read(name)
        return self[name]


@pytest.fixture(scope="session")
def data_dir() -> Path:
    return DATA


@pytest.fixture(scope="session")
def tables() -> Tables:
    return Tables()


class Telemetry:
    """One pass over the telemetry file: each asset's readings by day, as numbers
    (None for a blank), the row count, and whether every (day, asset) key came
    in strictly increasing order (so none repeats)."""

    def __init__(self, path: Path):
        self.by_asset = defaultdict(dict)
        self.rows, self.strictly_ordered, last = 0, True, None
        with path.open(encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            self.header = next(reader)
            for day, asset, hours, vibration, temperature, power in reader:
                key = (int(day), asset)
                self.strictly_ordered &= last is None or key > last
                last = key
                self.rows += 1
                self.by_asset[asset][int(day)] = (
                    float(hours), float(vibration) if vibration else None,
                    float(temperature) if temperature else None, float(power))


@pytest.fixture(scope="session")
def telemetry() -> Telemetry:
    return Telemetry(DATA / f"{TELEMETRY}.csv")


@pytest.fixture(scope="session")
def scenario_files(tmp_path_factory) -> tuple[Path, Path]:
    """The phase 3 scenario files, built once outside data/: the folder of CSV
    files, and the folder with the manifest and planning inputs written beside them."""
    from fjordvik_data import scenarios
    root = tmp_path_factory.mktemp("scenarios")
    manifest = scenarios.write_scenarios(root / "out")
    scenarios.record(root / "record", manifest)
    return root / "out", root / "record"
