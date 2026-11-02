"""Copy the towns Fjordvik serves out of the GeoNames cities file into reference/.

Town coordinates are cited reference data, never typed by hand. Download
cities15000.zip from https://download.geonames.org/export/dump/ (GeoNames,
CC BY 4.0) into a folder of its own, then run:

    python -m fjordvik_data.geonames <path to cities15000.zip> <date read, YYYY-MM-DD>

It keeps only the towns in config.SERVICE_TOWNS and writes
reference/geonames_towns.csv with the source, the date read and the zip's SHA-256
on every row. The generator reads that file; it never downloads anything.
"""

import csv
import hashlib
import io
import sys
import zipfile
from pathlib import Path

from fjordvik_data import config as c

REFERENCE = Path(__file__).resolve().parents[2] / "reference" / "geonames_towns.csv"
COLUMNS = ["geonameid", "name", "country_code", "latitude", "longitude", "population",
           "modification_date", "source"]


def wanted_ids() -> set[int]:
    return {town for towns in c.SERVICE_TOWNS.values() for town in towns}


def extract(zip_path: Path, read_on: str, out: Path = REFERENCE) -> int:
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    source = (f"GeoNames cities15000.zip (CC BY 4.0), download.geonames.org/export/dump, "
              f"read {read_on}, sha256 {digest}")
    wanted = wanted_ids()
    rows = []
    with zipfile.ZipFile(zip_path) as z, z.open("cities15000.txt") as f:
        for line in io.TextIOWrapper(f, encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if int(p[0]) in wanted:
                rows.append({"geonameid": p[0], "name": p[1], "country_code": p[8],
                             "latitude": p[4], "longitude": p[5], "population": p[14],
                             "modification_date": p[18], "source": source})
    missing = wanted - {int(r["geonameid"]) for r in rows}
    if missing:
        raise SystemExit(f"not in the GeoNames file: {sorted(missing)}")
    rows.sort(key=lambda r: int(r["geonameid"]))
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def read_towns(path: Path = REFERENCE) -> dict[int, dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return {int(r["geonameid"]): r for r in csv.DictReader(f)}


if __name__ == "__main__":
    n = extract(Path(sys.argv[1]), sys.argv[2])
    print(f"{n} towns written to {REFERENCE}")
