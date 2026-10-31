"""Build the Fjordvik tables and write them as CSV files.

Run with:  python -m fjordvik_data --out tables

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
from fjordvik_data import portfolio

GENERATOR_VERSION = "1.2.0"

COLUMNS = {
    "dim_date": ["date_key", "date", "year", "quarter", "month", "month_name"],
    "dim_site": ["site_id", "site_name", "country", "site_type"],
    "dim_source": ["source_id", "source_name", "scope", "category",
                   "scope3_category", "method"],
    "fact_emissions": ["date_key", "site_id", "source_id", "activity_amount",
                       "unit", "emission_factor", "tco2e"],
    "fact_site_metrics": ["date_key", "site_id", "revenue_eur", "fte"],
    "dim_scope3_category": ["scope3_category", "category_name", "status", "reason"],
    "dim_contract": ["contract_id", "site_id", "source_id", "supplier_name", "instrument",
                     "start_date_key", "end_date_key", "covered_share"],
    "fact_scope2_market": ["date_key", "site_id", "source_id", "contract_id", "instrument",
                           "activity_amount", "unit", "emission_factor", "tco2e"],
    "fact_energy_upstream": ["date_key", "site_id", "source_id", "based_on_source_id",
                             "activity_amount", "unit", "emission_factor", "tco2e"],
    "dim_supplier": ["supplier_id", "supplier_name", "country", "spend_category"],
    "fact_purchases": ["date_key", "site_id", "source_id", "supplier_id", "spend_category",
                       "method", "activity_amount", "unit", "emission_factor", "tco2e"],
    "fact_freight": ["date_key", "site_id", "source_id", "direction", "mode", "paid_by",
                     "tonnes", "distance_km", "activity_amount", "unit", "emission_factor",
                     "tco2e"],
    "dim_product_group": ["product_group", "product_family"],
    "dim_product": ["product_id", "product_name", "product_group", "product_family",
                    "made_at_site_id", "rated_kw", "kwh_per_year", "lifetime_years",
                    "list_price_eur", "standard_cost_eur"],
    "dim_region": ["region_id", "region_name"],
    "dim_score_criterion": ["criterion_id", "criterion_name", "weight", "source"],
    "fact_product_rating": ["date_key", "product_group", "criterion_id", "rating"],
    "dim_product_code": ["business_unit", "local_item_number", "product_id"],
    "fact_sales": ["date_key", "site_id", "product_id", "region_id", "units", "net_sales_eur",
                   "cost_of_sales_eur", "margin_eur"],
    "fact_data_issue": ["issue_id", "date_key", "site_id", "business_unit", "issue_type",
                        "detail", "line_count", "amount_eur", "status", "action"],
    "fact_use_phase": ["date_key", "site_id", "source_id", "product_id", "region_id", "units",
                       "net_sales_eur", "activity_amount", "unit", "emission_factor", "tco2e"],
}

# Reference lists the pipeline reads (data/reference). The ECB rates there are
# fetched from the ECB, never generated.
REFERENCE_COLUMNS = {
    "product_code_map": ["business_unit", "local_item_number", "product_id"],
    "region_codes": ["erp_region_code", "region_id"],
    "business_units": ["business_unit", "site_id", "ledger_currency"],
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
        {"source_id": s, "source_name": n, "scope": sc, "category": cat,
         "scope3_category": c.SOURCE_METHOD[s][0], "method": c.SOURCE_METHOD[s][1]}
        for s, n, sc, cat, _unit in c.SOURCES + c.VALUE_CHAIN_SOURCES
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


def build_dim_scope3_category() -> list[dict]:
    return [{"scope3_category": n, "category_name": name, "status": st, "reason": why}
            for n, name, st, why in c.SCOPE3_CATEGORIES]


def build_dim_contract() -> list[dict]:
    return [
        {"contract_id": cid, "site_id": site, "source_id": src, "supplier_name": who,
         "instrument": inst, "start_date_key": date_key(start), "end_date_key": date_key(end),
         "covered_share": share}
        for cid, site, src, who, inst, start, end, share in c.CONTRACTS
    ]


def emission_row(row: dict, amount: float, unit: str, factor: float) -> dict:
    """Fill the activity, unit, factor and tco2e columns the same way everywhere."""
    amount = round(amount, 2)
    return {**row, "activity_amount": amount, "unit": unit, "emission_factor": factor,
            "tco2e": round(amount * factor / 1000, 6)}


def build_fact_scope2_market(fact_emissions: list[dict]) -> list[dict]:
    """Market-based scope 2 from the same kWh as location-based (Scope 2 Guidance):
    kWh covered by a contract's guarantees of origin get the GO factor, the rest
    the country's residual mix. Heat uses the network's declared value."""
    country = {s: co for s, _n, co, _t, _f in c.SITES}
    rows = []
    for r in fact_emissions:
        site, src, key = r["site_id"], r["source_id"], r["date_key"]
        base = {"date_key": key, "site_id": site, "source_id": src}
        if src == "S06":
            rows.append(emission_row({**base, "contract_id": None,
                                      "instrument": "Network declared value"},
                                     r["activity_amount"], "kWh",
                                     c.HEAT_NETWORK_FACTOR[country[site]]))
        if src != "S05":
            continue
        covered = 0.0
        for cid, c_site, c_src, _who, inst, start, end, share in c.CONTRACTS:
            if c_site == site and c_src == src and date_key(start) <= key <= date_key(end):
                covered = round(r["activity_amount"] * share, 2)
                rows.append(emission_row({**base, "contract_id": cid, "instrument": inst},
                                         covered, "kWh", c.GO_FACTOR))
        rows.append(emission_row({**base, "contract_id": None, "instrument": "Residual mix"},
                                 r["activity_amount"] - covered, "kWh",
                                 c.RESIDUAL_MIX_FACTOR[country[site]]))
    rows.sort(key=lambda r: (r["date_key"], r["site_id"], r["source_id"], r["instrument"]))
    return rows


def build_fact_energy_upstream(fact_emissions: list[dict]) -> list[dict]:
    """Category 3 (a) and (c), worked out from the fuel and kWh already reported."""
    country = {s: co for s, _n, co, _t, _f in c.SITES}
    rows = []
    for r in fact_emissions:
        parent, site = r["source_id"], r["site_id"]
        if parent in c.WTT_FACTOR:
            source, factor = "S09", c.WTT_FACTOR[parent]
        elif parent in c.TD_FACTOR:
            source, factor = "S10", c.TD_FACTOR[parent][country[site]]
        else:
            continue
        rows.append(emission_row({"date_key": r["date_key"], "site_id": site,
                                  "source_id": source, "based_on_source_id": parent},
                                 r["activity_amount"], r["unit"], factor))
    rows.sort(key=lambda r: (r["date_key"], r["site_id"], r["source_id"],
                             r["based_on_source_id"]))
    return rows


def build_dim_supplier() -> list[dict]:
    return [{"supplier_id": s, "supplier_name": n, "country": co, "spend_category": cat}
            for s, n, co, cat in c.SUPPLIERS]


def build_fact_purchases() -> list[dict]:
    category = {s: cat for s, _n, _co, cat in c.SUPPLIERS}
    rows = []
    for site_id, _name, _country, site_type, site_first in c.SITES:
        for supplier_id, base in c.BASE_SPEND_EUR[site_id].items():
            rng = rng_for(site_id, supplier_id, "spend")
            cat = category[supplier_id]
            for d in months():
                if d < site_first:
                    continue
                i = months_between(c.FIRST_MONTH, d)
                spend = base * noise(rng) * ramp(site_first, d)
                if cat not in c.SERVICE_CATEGORIES:
                    spend *= (1 + c.ANNUAL_OUTPUT_GROWTH) ** (i / 12)
                    if site_type == "Manufacturing plant":
                        spend *= c.SUMMER_SHUTDOWN_FACTOR.get(d.month, 1.0)
                rows.append(emission_row(
                    {"date_key": date_key(d), "site_id": site_id, "source_id": "S11",
                     "supplier_id": supplier_id, "spend_category": cat,
                     "method": c.SOURCE_METHOD["S11"][1]},
                    spend, "EUR", c.SPEND_FACTOR[cat]))
    rows.sort(key=lambda r: (r["date_key"], r["site_id"], r["supplier_id"]))
    return rows


def build_fact_freight() -> list[dict]:
    rows = []
    for site_id, _name, _country, site_type, site_first in c.SITES:
        for direction, mode, paid_by, base, km in c.FREIGHT_LANES.get(site_id, []):
            rng = rng_for(site_id, direction, mode, paid_by, "freight")
            source = "S13" if (direction, paid_by) == ("Outbound", "Customer") else "S12"
            for d in months():
                if d < site_first:
                    continue
                i = months_between(c.FIRST_MONTH, d)
                tonnes = base * noise(rng) * ramp(site_first, d)
                tonnes *= (1 + c.ANNUAL_OUTPUT_GROWTH) ** (i / 12)
                if site_type == "Manufacturing plant":
                    tonnes *= c.SUMMER_SHUTDOWN_FACTOR.get(d.month, 1.0)
                tonnes = round(tonnes, 2)
                rows.append(emission_row(
                    {"date_key": date_key(d), "site_id": site_id, "source_id": source,
                     "direction": direction, "mode": mode, "paid_by": paid_by,
                     "tonnes": tonnes, "distance_km": km},
                    tonnes * km, "tonne-km", c.FREIGHT_FACTOR[mode]))
    rows.sort(key=lambda r: (r["date_key"], r["site_id"], r["direction"], r["mode"],
                             r["paid_by"]))
    return rows


def build_all() -> dict[str, list[dict]]:
    emissions = build_fact_emissions()
    return {
        "dim_date": build_dim_date(),
        "dim_site": build_dim_site(),
        "dim_source": build_dim_source(),
        "fact_emissions": emissions,
        "fact_site_metrics": build_fact_site_metrics(),
        "dim_scope3_category": build_dim_scope3_category(),
        "dim_contract": build_dim_contract(),
        "fact_scope2_market": build_fact_scope2_market(emissions),
        "fact_energy_upstream": build_fact_energy_upstream(emissions),
        "dim_supplier": build_dim_supplier(),
        "fact_purchases": build_fact_purchases(),
        "fact_freight": build_fact_freight(),
        "dim_product_group": portfolio.build_dim_product_group(),
        "dim_product": portfolio.build_dim_product(),
        "dim_region": portfolio.build_dim_region(),
        "dim_score_criterion": portfolio.build_dim_score_criterion(),
        "fact_product_rating": portfolio.build_fact_product_rating(months, rng_for),
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
    "tonnes": "{:.2f}",
    "covered_share": "{:.2f}",
    "net_sales_eur": "{:.2f}",
    "cost_of_sales_eur": "{:.2f}",
    "margin_eur": "{:.2f}",
    "amount_eur": "{:.2f}",
}


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(columns)
        for row in rows:
            # None is written as an empty field: a blank, not the text "None"
            w.writerow(["" if row[col] is None else FORMATS.get(col, "{}").format(row[col])
                        for col in columns])


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_all(out_dir: Path) -> dict:
    """Write the tables to out_dir, and the simulated ERP extract and the reference
    lists beside it (out_dir/../erp-extract, out_dir/../reference). The sales
    tables come out of the SQL pipeline run on that extract."""
    out_dir.mkdir(parents=True, exist_ok=True)
    root = out_dir.parent
    tables = build_all()
    for name, rows in tables.items():
        write_csv(out_dir / f"{name}.csv", COLUMNS[name], rows)

    reference = root / "reference"
    reference.mkdir(exist_ok=True)
    for name, rows in (("product_code_map", portfolio.build_product_code_map()),
                       ("region_codes", portfolio.build_region_codes()),
                       ("business_units", portfolio.build_business_units())):
        write_csv(reference / f"{name}.csv", REFERENCE_COLUMNS[name], rows)
    lines = portfolio.build_sales_lines(tables["fact_site_metrics"], months, months_between, rng_for)
    extract = root / "erp-extract"
    portfolio.write_extract(extract, portfolio.extract_rows(lines, portfolio.read_rates()))
    published = portfolio.run_sql(extract, reference, out_dir)
    for name in ("dim_product_code", "fact_sales", "fact_data_issue"):
        tables[name] = published[name]
    tables["fact_use_phase"] = portfolio.build_fact_use_phase(published["fact_sales"])
    manifest = {
        "dataset": "Fjordvik Manufacturing Oy (synthetic)",
        "generator_version": GENERATOR_VERSION,
        "seed": c.SEED,
        "period": f"{months()[0].isoformat()} to {months()[-1].isoformat()}",
        "emission_factors": "illustrative, not for real reporting",
        "tables": {},
    }
    for name in COLUMNS:
        path = out_dir / f"{name}.csv"
        write_csv(path, COLUMNS[name], tables[name])
        manifest["tables"][name] = {"file": path.name, "rows": len(tables[name]),
                                    "sha256": sha256(path)}
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the Fjordvik dataset.")
    parser.add_argument("--out", default="tables", type=Path,
                        help="folder to write the CSV files to (default: tables)")
    args = parser.parse_args()
    manifest = write_all(args.out)
    for name, info in manifest["tables"].items():
        print(f"{name:<21} {info['rows']:>5} rows")
    print(f"Written to {args.out.resolve()}")
