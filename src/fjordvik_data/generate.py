"""Build the five Fjordvik tables and write them as CSV files.

Run with:  python -m fjordvik_data --out data

The output is deterministic: the same code and seed always give byte-identical
files. Each (site, source) pair gets its own random stream, seeded from its
names, so adding a site or source never changes the numbers of the others.
"""

import argparse
import calendar
import csv
import hashlib
import json
import math
import random
from datetime import date
from pathlib import Path

from fjordvik_data import config as c

GENERATOR_VERSION = "1.0.0"

COLUMNS = {
    "dim_date": ["date_key", "date", "year", "quarter", "month", "month_name"],
    "dim_site": ["site_id", "site_name", "country", "site_type"],
    "dim_source": ["source_id", "source_name", "scope", "category"],
    "fact_emissions": ["date_key", "site_id", "source_id", "activity_amount",
                       "unit", "emission_factor", "tco2e"],
    "fact_site_metrics": ["date_key", "site_id", "revenue_eur", "fte"],
}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def months() -> list[date]:
    """First day of every month in the reporting period."""
    out = []
    for i in range(c.MONTH_COUNT):
        y, m = divmod(c.FIRST_MONTH.month - 1 + i, 12)
        out.append(date(c.FIRST_MONTH.year + y, m + 1, 1))
    return out


def months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)


def date_key(d: date) -> int:
    """20230101 for January 2023: a whole number that sorts like the date."""
    return d.year * 10000 + d.month * 100 + d.day


def rng_for(*parts: str) -> random.Random:
    """A random stream of its own for each named thing, stable across runs."""
    return random.Random("-".join([str(c.SEED), *parts]))


def noise(rng: random.Random) -> float:
    return max(0.5, rng.gauss(1.0, c.NOISE))


def seasonal(source_id: str, month: int) -> float:
    swing = c.SEASONAL_SWING.get(source_id, 0.0)
    # cos peaks at month 1 (January) and bottoms at month 7 (July)
    return 1.0 + swing * math.cos(2 * math.pi * (month - 1) / 12)


def ramp(site_first: date, d: date) -> float:
    """Share of full activity for a site that opened during the period."""
    if site_first <= c.FIRST_MONTH:
        return 1.0  # already running when reporting began
    j = months_between(site_first, d)
    return c.RAMP_UP[j] if j < len(c.RAMP_UP) else 1.0


def emission_factor(source_id: str, country: str) -> float:
    if source_id in c.FACTORS_BY_COUNTRY:
        return c.FACTORS_BY_COUNTRY[source_id][country]
    return c.FACTORS_ALL_COUNTRIES[source_id]


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def build_dim_date() -> list[dict]:
    return [
        {
            "date_key": date_key(d),
            "date": d.isoformat(),
            "year": d.year,
            "quarter": (d.month - 1) // 3 + 1,
            "month": d.month,
            "month_name": calendar.month_name[d.month],
        }
        for d in months()
    ]


def build_dim_site() -> list[dict]:
    return [
        {"site_id": s, "site_name": n, "country": co, "site_type": t}
        for s, n, co, t, _first in c.SITES
    ]


def build_dim_source() -> list[dict]:
    return [
        {"source_id": s, "source_name": n, "scope": sc, "category": cat}
        for s, n, sc, cat, _unit in c.SOURCES
    ]


def activity(site_id: str, source_id: str, site_first: date, d: date,
             rng: random.Random) -> float:
    base = c.BASE_ACTIVITY[site_id][source_id]
    i = months_between(c.FIRST_MONTH, d)

    if source_id == "S04":
        # Refrigerant: zero in most months, a top-up in some. Draw both numbers
        # every month so the stream stays aligned whatever the outcome.
        topped_up = rng.random() < c.REFRIGERANT_TOPUP_CHANCE
        size = rng.uniform(0.5, 1.5)
        return base / c.REFRIGERANT_TOPUP_CHANCE * size if topped_up else 0.0

    amount = base * seasonal(source_id, d.month) * noise(rng)
    if source_id in c.PRODUCTION_LINKED:
        amount *= (1 + c.ANNUAL_OUTPUT_GROWTH) ** (i / 12)
        amount *= c.SUMMER_SHUTDOWN_FACTOR.get(d.month, 1.0)
    if source_id == "S07":
        amount *= c.FLIGHT_MONTH_FACTOR.get(d.month, 1.0)
    if site_id == c.SOLAR_SITE and source_id == "S05" and d >= c.SOLAR_FIRST_MONTH:
        amount *= 1 - c.SOLAR_SHARE_BY_MONTH[d.month]
    return amount * ramp(site_first, d)


def build_fact_emissions() -> list[dict]:
    units = {s: u for s, _n, _sc, _cat, u in c.SOURCES}
    rows = []
    for site_id, _name, country, _type, site_first in c.SITES:
        for source_id, *_rest in c.SOURCES:
            if source_id not in c.BASE_ACTIVITY[site_id]:
                continue
            rng = rng_for(site_id, source_id)
            for d in months():
                if d < site_first:
                    continue  # no backfill before the site opened
                amount = round(activity(site_id, source_id, site_first, d, rng), 2)
                factor = emission_factor(source_id, country)
                rows.append({
                    "date_key": date_key(d),
                    "site_id": site_id,
                    "source_id": source_id,
                    "activity_amount": amount,
                    "unit": units[source_id],
                    "emission_factor": factor,
                    "tco2e": round(amount * factor / 1000, 6),
                })
    rows.sort(key=lambda r: (r["date_key"], r["site_id"], r["source_id"]))
    return rows


def build_fact_site_metrics() -> list[dict]:
    rows = []
    for site_id, _name, _country, site_type, site_first in c.SITES:
        rng = rng_for(site_id, "metrics")
        for d in months():
            if d < site_first:
                continue
            i = months_between(c.FIRST_MONTH, d)
            r = ramp(site_first, d)
            revenue = c.BASE_REVENUE_EUR[site_id] * (1 + c.ANNUAL_REVENUE_GROWTH) ** (i / 12)
            revenue *= noise(rng) * r
            if site_type == "Manufacturing plant":
                revenue *= c.SUMMER_SHUTDOWN_FACTOR.get(d.month, 1.0)
            fte = c.BASE_FTE[site_id] * (1 + c.ANNUAL_FTE_GROWTH) ** (i / 12) * r
            fte *= 1 + rng.gauss(0, 0.01)
            rows.append({
                "date_key": date_key(d),
                "site_id": site_id,
                "revenue_eur": round(revenue, 2),
                "fte": round(fte, 1),
            })
    rows.sort(key=lambda r: (r["date_key"], r["site_id"]))
    return rows


def build_all() -> dict[str, list[dict]]:
    return {
        "dim_date": build_dim_date(),
        "dim_site": build_dim_site(),
        "dim_source": build_dim_source(),
        "fact_emissions": build_fact_emissions(),
        "fact_site_metrics": build_fact_site_metrics(),
    }


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

FORMATS = {
    "activity_amount": "{:.2f}",
    "emission_factor": "{:.3f}",
    "tco2e": "{:.6f}",
    "revenue_eur": "{:.2f}",
    "fte": "{:.1f}",
}


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(columns)
        for row in rows:
            w.writerow([FORMATS.get(col, "{}").format(row[col]) for col in columns])


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_all(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    tables = build_all()
    manifest = {
        "dataset": "Fjordvik Manufacturing Oy (synthetic)",
        "generator_version": GENERATOR_VERSION,
        "seed": c.SEED,
        "period": f"{months()[0].isoformat()} to {months()[-1].isoformat()}",
        "emission_factors": "illustrative, not for real reporting",
        "tables": {},
    }
    for name, rows in tables.items():
        path = out_dir / f"{name}.csv"
        write_csv(path, COLUMNS[name], rows)
        manifest["tables"][name] = {"file": path.name, "rows": len(rows),
                                    "sha256": sha256(path)}
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the Fjordvik dataset.")
    parser.add_argument("--out", default="data", type=Path,
                        help="folder to write the CSV files to (default: data)")
    args = parser.parse_args()
    manifest = write_all(args.out)
    for name, info in manifest["tables"].items():
        print(f"{name:<18} {info['rows']:>5} rows")
    print(f"Written to {args.out.resolve()}")
