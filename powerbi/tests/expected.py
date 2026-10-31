"""Expected values for the DAX measures, worked out independently in plain Python.

Each case names a measure, a filter context and (optionally) a security role.
The live test turns it into a DAX query, runs it against the model open in
Power BI Desktop, and compares. Two independent routes to the same number is
how a measure is reconciled.
"""

import csv
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "tables"


def read(name):
    with (DATA / f"{name}.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# Since 31 October 2026 the location-based inventory is four tables: what the sites
# report, plus the value-chain tables (category 3, purchases, freight).
SITE_EM = read("fact_emissions")
EM = SITE_EM + read("fact_energy_upstream") + read("fact_purchases") + read("fact_freight")
MARKET = read("fact_scope2_market")
PURCHASES = read("fact_purchases")
FREIGHT = read("fact_freight")
SM = read("fact_site_metrics")
SITE = {r["site_id"]: r for r in read("dim_site")}
SCOPE = {r["source_id"]: int(r["scope"]) for r in read("dim_source")}
CATEGORY = {r["source_id"]: r["scope3_category"] for r in read("dim_source")}


def keep(r, year=None, site=None, country=None, scope=None, month_key=None, source=None,
         scope3_category=None):
    return ((not year or r["date_key"].startswith(str(year)))
            and (not month_key or r["date_key"] == str(month_key))
            and (not site or r["site_id"] == site)
            and (not country or SITE[r["site_id"]]["country"] == country)
            and (not scope or SCOPE[r["source_id"]] == scope)
            and (not source or r["source_id"] == source)
            and (not scope3_category or CATEGORY[r["source_id"]] == str(scope3_category)))


def total(rows, column="tco2e", **f):
    """Sum a column over the rows that pass the filters; None (blank) if no rows do."""
    picked = [float(r[column]) for r in rows if keep(r, **f)]
    return sum(picked) if picked else None


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
    return sum(float(r["activity_amount"]) for r in SITE_EM
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
    "source": ("dim_source", "source_id", str),
    "scope3_category": ("dim_scope3_category", "scope3_category", int),
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
        case("emission_rows_all", "Emission Rows", float(len(SITE_EM))),
        case("sites_reporting_2023", "Sites Reporting", 5.0, year=2023),
        case("sites_reporting_2025", "Sites Reporting", 6.0, year=2025),
        # Row-level security: the Finland role sees only Finnish sites.
        case("rls_finland_total", total, emissions(country="Finland"), role="Finland"),
        case("rls_finland_sites", "Sites Reporting", 3.0, role="Finland"),
        case("rls_estonia_sites_2023", "Sites Reporting", 1.0, role="Estonia", year=2023),
        case("rls_sweden_cannot_see_finland", total, None, role="Sweden", country="Finland"),
    ]
    out += value_chain_cases()
    return out


def value_chain_cases():
    """Market-based scope 2 and scope 3 categories 1, 3, 4 and 9 (added 31 October 2026)."""
    market = "Scope 2 Market-based Emissions (tCO2e)"
    go_kwh = "Electricity with Guarantees of Origin (kWh)"

    def go(**f):
        return total([r for r in MARKET if r["contract_id"]], "activity_amount", **f)

    def market_total(**f):
        return emissions(**f) - emissions(scope=2, **f) + total(MARKET, **f)

    def per_thousand(**f):
        return total(PURCHASES, **f) / (total(PURCHASES, "activity_amount", **f) / 1000)

    return [
        case("market_scope2_2025", market, total(MARKET, year=2025), year=2025),
        case("market_scope2_fi01_2025", market, total(MARKET, year=2025, site="FI01"),
             year=2025, site="FI01"),
        # Gothenburg's hydro guarantees cover every kWh: zero, not blank.
        case("market_electricity_se01_is_zero", market, 0.0, site="SE01", source="S05"),
        case("market_scope2_under_scope1_is_blank", market, None, scope=1),
        case("market_total_2025", "Total Emissions Market-based (tCO2e)",
             market_total(year=2025), year=2025),
        case("market_total_estonia_2024", "Total Emissions Market-based (tCO2e)",
             market_total(year=2024, country="Estonia"), year=2024, country="Estonia"),
        case("go_kwh_2025", go_kwh, go(year=2025), year=2025, tolerance=0.01),
        case("go_share_fi01_2025", "Electricity with Guarantees of Origin (%)",
             go(year=2025, site="FI01") / activity(source="S05", year=2025, site="FI01"),
             year=2025, site="FI01", tolerance=0.00001),
        case("go_share_estonia_is_blank", "Electricity with Guarantees of Origin (%)", None,
             country="Estonia"),
        case("purchased_goods_2025", "Purchased Goods and Services Emissions (tCO2e)",
             total(PURCHASES, year=2025), year=2025),
        case("purchased_goods_ee01_2024", "Purchased Goods and Services Emissions (tCO2e)",
             total(PURCHASES, year=2024, site="EE01"), year=2024, site="EE01"),
        case("fuel_energy_2025", "Fuel and Energy Related Emissions (tCO2e)",
             total(EM, year=2025, scope3_category=3), year=2025),
        case("upstream_transport_2025", "Upstream Transport Emissions (tCO2e)",
             total(FREIGHT, year=2025, source="S12"), year=2025),
        case("downstream_transport_2025", "Downstream Transport Emissions (tCO2e)",
             total(FREIGHT, year=2025, source="S13"), year=2025),
        case("downstream_under_scope1_is_blank", "Downstream Transport Emissions (tCO2e)",
             None, scope=1),
        case("spend_2025", "Purchased Spend (EUR)", total(PURCHASES, "activity_amount", year=2025),
             year=2025, tolerance=0.01),
        case("freight_tkm_2025", "Freight Transport (tonne-km)",
             total(FREIGHT, "activity_amount", year=2025), year=2025, tolerance=0.01),
        case("per_thousand_eur_2025", "Purchased Goods Emissions per Thousand EUR (tCO2e)",
             per_thousand(year=2025), year=2025, tolerance=0.00001),
        case("market_reconciliation_all", "Market-based Reconciliation Difference (tCO2e)", 0.0,
             tolerance=0.01),
        # The category table filters through dim_source to every emission table.
        case("total_under_category_1_2025", "Total Emissions (tCO2e)",
             total(PURCHASES, year=2025), year=2025, scope3_category=1),
        case("total_under_category_9", "Total Emissions (tCO2e)", total(FREIGHT, source="S13"),
             scope3_category=9),
        case("total_under_category_11_is_blank", "Total Emissions (tCO2e)", None,
             scope3_category=11),
        # Row-level security reaches the new tables through dim_site.
        case("rls_finland_market", market, total(MARKET, country="Finland"), role="Finland"),
        case("rls_estonia_purchases_2025", "Purchased Goods and Services Emissions (tCO2e)",
             total(PURCHASES, year=2025, country="Estonia"), role="Estonia", year=2025),
    ]


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
