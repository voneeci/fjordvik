"""Expected values for the DAX measures, worked out independently in plain Python.

Each case names a measure, a filter context and (optionally) a security role.
The live test turns it into a DAX query, runs it against the model open in
Power BI Desktop, and compares. Two independent routes to the same number is
how a measure is reconciled.
"""

import csv
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "data"


def read(name):
    with (DATA / f"{name}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


EM = read("fact_emissions")
SM = read("fact_site_metrics")
SITE = {r["site_id"]: r for r in read("dim_site")}
SCOPE = {r["source_id"]: int(r["scope"]) for r in read("dim_source")}


def emissions(year=None, site=None, country=None, scope=None, month_key=None):
    total = 0.0
    for r in EM:
        if year and not r["date_key"].startswith(str(year)):
            continue
        if month_key and r["date_key"] != str(month_key):
            continue
        if site and r["site_id"] != site:
            continue
        if country and SITE[r["site_id"]]["country"] != country:
            continue
        if scope and SCOPE[r["source_id"]] != scope:
            continue
        total += float(r["tco2e"])
    return total


def metric_rows(year=None, site=None, country=None):
    for r in SM:
        if year and not r["date_key"].startswith(str(year)):
            continue
        if site and r["site_id"] != site:
            continue
        if country and SITE[r["site_id"]]["country"] != country:
            continue
        yield r


def revenue(**f):
    return sum(float(r["revenue_eur"]) for r in metric_rows(**f))


def average_fte(**f):
    """FTE is a level: sum across sites within each month, then average the months."""
    by_month = defaultdict(float)
    for r in metric_rows(**f):
        by_month[r["date_key"]] += float(r["fte"])
    return sum(by_month.values()) / len(by_month)


def like_for_like_change(year=None, site=None):
    """Change against the same month a year earlier, counting only site-months
    with emissions in both years (a new site's first year and 2023 drop out)."""
    by_site_month = defaultdict(float)
    for r in EM:
        by_site_month[(r["site_id"], int(r["date_key"]))] += float(r["tco2e"])
    current = prior = 0.0
    for (s, key), value in by_site_month.items():
        if year and key // 10000 != year:
            continue
        if site and s != site:
            continue
        before = by_site_month.get((s, key - 10000))
        if before is None:
            continue
        current += value
        prior += before
    return None if prior == 0 else current / prior - 1


MONTHS = {int(r["date_key"]) for r in read("dim_date")}


def activity(source=None, unit=None, year=None, site=None, country=None):
    """Activity in the sites' own units, for one source or every source in one unit."""
    return sum(float(r["activity_amount"]) for r in EM
               if (source is None or r["source_id"] == source)
               and (unit is None or r["unit"] == unit)
               and (year is None or r["date_key"].startswith(str(year)))
               and (site is None or r["site_id"] == site)
               and (country is None or SITE[r["site_id"]]["country"] == country))


def change_including_new_sites(year=None, site=None):
    """Plain change against the same month a year earlier, every site counted, over the
    months whose prior-year month is in the data (none in 2023, so None)."""
    months = [m for m in MONTHS if (year is None or m // 10000 == year) and m - 10000 in MONTHS]
    if not months:
        return None
    return sum(emissions(site=site, month_key=m) - emissions(site=site, month_key=m - 10000)
               for m in months)


def per_million_eur(**f):
    rev = revenue(**f)
    return None if rev == 0 else emissions(**f) / (rev / 1e6)


FILTERS = {
    "year": ("dim_date", "year", int),
    "site": ("dim_site", "site_id", str),
    "country": ("dim_site", "country", str),
    "scope": ("dim_source", "scope", int),
    "month_key": ("dim_date", "date_key", int),
}


def case(case_id, measure, expected, role=None, tolerance=0.001, **filters):
    return {"id": case_id, "measure": measure, "expected": expected, "role": role,
            "tolerance": tolerance, "filters": filters}


def cases():
    total = "Total Emissions (tCO2e)"
    out = [
        case("total_all", total, emissions()),
        case("total_2023", total, emissions(year=2023), year=2023),
        case("total_2024", total, emissions(year=2024), year=2024),
        case("total_2025", total, emissions(year=2025), year=2025),
        case("scope1_2025", "Scope 1 Emissions (tCO2e)", emissions(year=2025, scope=1), year=2025),
        case("scope2_2025", "Scope 2 Emissions (tCO2e)", emissions(year=2025, scope=2), year=2025),
        case("scope3_2025", "Scope 3 Emissions (tCO2e)", emissions(year=2025, scope=3), year=2025),
        # A scope measure under a different scope filter is blank, not the scope total.
        case("scope1_under_scope2_filter", "Scope 1 Emissions (tCO2e)", None, scope=2),
        case("total_fi01_2024", total, emissions(year=2024, site="FI01"), year=2024, site="FI01"),
        case("total_estonia", total, emissions(country="Estonia"), country="Estonia"),
        case("recalculated_all", "Recalculated Emissions (tCO2e)", emissions(), tolerance=0.01),
        case("reconciliation_difference_all", "Reconciliation Difference (tCO2e)", 0.0,
             tolerance=0.01),
        case("revenue_2025", "Revenue (EUR)", revenue(year=2025), year=2025, tolerance=0.01),
        case("average_fte_2024", "Average FTE", average_fte(year=2024), year=2024),
        case("per_fte_2024", "Emissions per FTE (tCO2e)",
             emissions(year=2024) / average_fte(year=2024), year=2024),
        case("per_meur_ee01_2025", "Emissions per Million EUR (tCO2e)",
             per_million_eur(year=2025, site="EE01"), year=2025, site="EE01"),
        case("per_meur_head_office_is_blank", "Emissions per Million EUR (tCO2e)", None,
             site="FI02"),
        case("prior_year_of_2025", "Emissions Prior Year (tCO2e)", emissions(year=2024), year=2025),
        case("prior_year_of_2023_is_blank", "Emissions Prior Year (tCO2e)", None, year=2023),
        case("prior_year_se01_march_2025", "Emissions Prior Year (tCO2e)",
             emissions(site="SE01", month_key=20240301), site="SE01", month_key=20250301),
        # Like-for-like: only site-months with emissions in both years count.
        case("yoy_change_2025", "Emissions Change vs Prior Year (%)",
             like_for_like_change(year=2025), year=2025, tolerance=0.00001),
        case("yoy_change_tartu_2025", "Emissions Change vs Prior Year (%)",
             like_for_like_change(year=2025, site="EE02"), year=2025, site="EE02",
             tolerance=0.00001),
        case("yoy_change_all_years", "Emissions Change vs Prior Year (%)",
             like_for_like_change(), tolerance=0.00001),
        case("yoy_change_2023_is_blank", "Emissions Change vs Prior Year (%)", None, year=2023),
        # Activity in the sites' own units (added 31 October 2026).
        case("energy_used_2025", "Energy Used (kWh)", activity(unit="kWh", year=2025),
             year=2025, tolerance=0.01),
        case("natural_gas_2024", "Natural Gas Used (kWh)", activity(source="S01", year=2024),
             year=2024, tolerance=0.01),
        case("electricity_fi01_2025", "Electricity Purchased (kWh)",
             activity(source="S05", year=2025, site="FI01"), year=2025, site="FI01",
             tolerance=0.01),
        case("district_heating_2025", "District Heating Purchased (kWh)",
             activity(source="S06", year=2025), year=2025, tolerance=0.01),
        case("vehicle_fuel_2025", "Vehicle Fuel Used (litres)", activity(unit="litre", year=2025),
             year=2025, tolerance=0.01),
        case("refrigerant_all", "Refrigerant Leakage (kg)", activity(source="S04"),
             tolerance=0.01),
        case("flights_2025", "Business Flights (passenger-km)", activity(source="S07", year=2025),
             year=2025, tolerance=0.01),
        case("waste_estonia", "Waste to Landfill (tonnes)", activity(source="S08", country="Estonia"),
             country="Estonia", tolerance=0.01),
        # A source measure under a filter on another scope is blank, not that source's total.
        case("electricity_under_scope1_is_blank", "Electricity Purchased (kWh)", None, scope=1),
        # Change including new sites: Tartu's whole first year counts as an increase.
        case("change_incl_new_2025", "Emissions Change Including New Sites (tCO2e)",
             change_including_new_sites(year=2025), year=2025, tolerance=0.01),
        case("change_incl_new_tartu_2024", "Emissions Change Including New Sites (tCO2e)",
             change_including_new_sites(year=2024, site="EE02"), year=2024, site="EE02",
             tolerance=0.01),
        case("change_incl_new_2023_is_blank", "Emissions Change Including New Sites (tCO2e)",
             None, year=2023),
        case("change_incl_new_pct_2025", "Emissions Change Including New Sites (%)",
             change_including_new_sites(year=2025) / emissions(year=2024), year=2025,
             tolerance=0.00001),
        case("emission_rows_all", "Emission Rows", float(len(EM))),
        case("sites_reporting_2023", "Sites Reporting", 5.0, year=2023),
        case("sites_reporting_2025", "Sites Reporting", 6.0, year=2025),
        # Row-level security: the Finland role sees only Finnish sites.
        case("rls_finland_total", total, emissions(country="Finland"), role="Finland"),
        case("rls_finland_sites", "Sites Reporting", 3.0, role="Finland"),
        case("rls_estonia_sites_2023", "Sites Reporting", 1.0, role="Estonia", year=2023),
        case("rls_sweden_cannot_see_finland", total, None, role="Sweden", country="Finland"),
    ]
    return out


def dax_query(c) -> str:
    """EVALUATE a one-row table holding the measure under the case's filters."""
    filters = []
    for key, value in c["filters"].items():
        table, column, kind = FILTERS[key]
        literal = f'"{value}"' if kind is str else str(value)
        filters.append(f"{table}[{column}] = {literal}")
    inner = f"[{c['measure']}]"
    if filters:
        inner = f"CALCULATE({inner}, {', '.join(filters)})"
    return f'EVALUATE ROW("value", {inner})'
