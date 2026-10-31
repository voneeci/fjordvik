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
USE_PHASE = read("fact_use_phase")
EM = SITE_EM + read("fact_energy_upstream") + read("fact_purchases") + read("fact_freight") + USE_PHASE
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
    "family": ("dim_product_group", "product_family", str),
    "region": ("dim_region", "region_id", str),
    "group": ("dim_product_group", "product_group", str),
    "quarter": ("dim_date", "quarter", int),
    "step": ("dim_bridge_step", "step", str),
    "contract": ("dim_contract", "contract_id", str),
}


def case(case_id, measure, expected, role=None, tolerance=0.001, prefix=False, **filters):
    return {"id": case_id, "measure": measure, "expected": expected, "role": role,
            "tolerance": tolerance, "prefix": prefix, "filters": filters}


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
    out += portfolio_cases()
    out += redesign_cases()
    return out


# ---------------------------------------------------------------------------
# Phase 2: sales, the price/volume/mix bridge, balance, scorecard, category 11
# ---------------------------------------------------------------------------

SALES = read("fact_sales")
PRODUCT = {r["product_id"]: r for r in read("dim_product")}
ISSUES = read("fact_data_issue")
RATINGS = read("fact_product_rating")
WEIGHT = {r["criterion_id"]: int(r["weight"]) for r in read("dim_score_criterion")}
GROUP_FAMILY = {r["product_group"]: r["product_family"] for r in read("dim_product_group")}


def sales_rows(year=None, family=None, region=None, site=None, month_key=None, product=None):
    for r in SALES:
        if year and not r["date_key"].startswith(str(year)):
            continue
        if month_key and r["date_key"] != str(month_key):
            continue
        if family and PRODUCT[r["product_id"]]["product_family"] != family:
            continue
        if region and r["region_id"] != region:
            continue
        if site and r["site_id"] != site:
            continue
        if product and r["product_id"] != product:
            continue
        yield r


def sales(column, **f):
    picked = [float(r[column]) for r in sales_rows(**f)]
    return sum(picked) if picked else None


def by_product(**f):
    out = defaultdict(lambda: [0.0, 0.0, 0.0])
    for r in sales_rows(**f):
        a = out[r["product_id"]]
        a[0] += float(r["units"]); a[1] += float(r["net_sales_eur"]); a[2] += float(r["cost_of_sales_eur"])
    return out


def bridge(cur, prev):
    """ACCA F5 sales variances with the prior year as standard, product by product.
    cur and prev are sales_rows filters for this period and the same months a year earlier."""
    cy, py = by_product(**cur), by_product(**prev)
    comp = [p for p in cy if p in py]
    ta, tp = sum(cy[p][0] for p in comp), sum(py[p][0] for p in comp)
    pm = {p: (py[p][1] - py[p][2]) / py[p][0] for p in comp}
    margin = lambda d, p: d[p][1] - d[p][2] if p in d else 0.0
    others = (set(cy) | set(py)) - set(comp)
    return {"price": sum(cy[p][1] - py[p][1] / py[p][0] * cy[p][0] for p in comp),
            "mix": sum((cy[p][0] - ta * py[p][0] / tp) * pm[p] for p in comp),
            "quantity": sum((ta * py[p][0] / tp - py[p][0]) * pm[p] for p in comp),
            "cost": sum(py[p][2] / py[p][0] * cy[p][0] - cy[p][2] for p in comp),
            "other": sum(margin(cy, p) - margin(py, p) for p in others) if others else None,
            "change": sum(margin(cy, p) for p in cy) - sum(margin(py, p) for p in py)}


def weighted_score(year=None, group=None, family=None):
    num = den = 0.0
    for r in RATINGS:
        if year and not r["date_key"].startswith(str(year)):
            continue
        if group and r["product_group"] != group:
            continue
        if family and GROUP_FAMILY[r["product_group"]] != family:
            continue
        num += int(r["rating"]) * WEIGHT[r["criterion_id"]]
        den += WEIGHT[r["criterion_id"]]
    return num / den


def use_phase(column="tco2e", **f):
    picked = [float(r[column]) for r in USE_PHASE
              if (not f.get("year") or r["date_key"].startswith(str(f["year"])))
              and (not f.get("region") or r["region_id"] == f["region"])
              and (not f.get("family") or PRODUCT[r["product_id"]]["product_family"] == f["family"])]
    return sum(picked) if picked else None


def portfolio_cases():
    pumps = "Industrial process pumps"
    b25 = bridge({"year": 2025}, {"year": 2024})
    b25f = bridge({"year": 2025, "family": pumps}, {"year": 2024, "family": pumps})
    packages = "Pump packages and controls"
    june = bridge({"month_key": 20250601, "region": "BAL", "family": packages},
                  {"month_key": 20240601, "region": "BAL", "family": packages})
    quarantined = sum(float(r["amount_eur"]) for r in ISSUES if r["status"] == "Quarantined")
    total_2025 = sales("net_sales_eur", year=2025)
    return [
        case("units_2025", "Units Sold", sales("units", year=2025), year=2025),
        case("net_sales_2025", "Net Sales (EUR)", total_2025, year=2025, tolerance=0.01),
        case("net_sales_baltics_2024", "Net Sales (EUR)", sales("net_sales_eur", year=2024, region="BAL"),
             year=2024, region="BAL", tolerance=0.01),
        case("cost_2025", "Cost of Sales (EUR)", sales("cost_of_sales_eur", year=2025), year=2025, tolerance=0.01),
        case("margin_2025", "Margin (EUR)", sales("margin_eur", year=2025), year=2025, tolerance=0.01),
        case("margin_pct_pumps_2025", "Margin (%)",
             sales("margin_eur", year=2025, family=pumps) / sales("net_sales_eur", year=2025, family=pumps),
             year=2025, family=pumps, tolerance=0.00001),
        case("average_price_pumps_2025", "Average Price (EUR)",
             sales("net_sales_eur", year=2025, family=pumps) / sales("units", year=2025, family=pumps),
             year=2025, family=pumps, tolerance=0.01),
        case("margin_prior_year_of_2025", "Margin Prior Year (EUR)", sales("margin_eur", year=2024),
             year=2025, tolerance=0.01),
        case("margin_prior_year_of_2023_is_blank", "Margin Prior Year (EUR)", None, year=2023),
        case("margin_change_2025", "Margin Change vs Prior Year (EUR)", b25["change"], year=2025, tolerance=0.01),
        case("price_effect_2025", "Price Effect (EUR)", b25["price"], year=2025, tolerance=0.01),
        case("mix_effect_2025", "Mix Effect (EUR)", b25["mix"], year=2025, tolerance=0.01),
        case("quantity_effect_2025", "Quantity Effect (EUR)", b25["quantity"], year=2025, tolerance=0.01),
        case("volume_effect_2025", "Volume Effect (EUR)", b25["mix"] + b25["quantity"], year=2025, tolerance=0.01),
        case("cost_effect_2025", "Cost Effect (EUR)", b25["cost"], year=2025, tolerance=0.01),
        # Every product sold in both years, so nothing is left out of the comparison.
        case("not_comparable_2025_is_blank", "Not Comparable Change (EUR)", None, year=2025),
        # June 2025: one Baltic booster set line was quarantined, so that product has no
        # sales that month and its prior-year margin is not comparable.
        case("not_comparable_baltics_june_2025", "Not Comparable Change (EUR)", june["other"],
             month_key=20250601, region="BAL", family=packages, tolerance=0.01),
        case("margin_change_baltics_june_2025", "Margin Change vs Prior Year (EUR)", june["change"],
             month_key=20250601, region="BAL", family=packages, tolerance=0.01),
        case("price_effect_pumps_2024", "Price Effect (EUR)",
             bridge({"year": 2024, "family": pumps}, {"year": 2023, "family": pumps})["price"],
             year=2024, family=pumps, tolerance=0.01),
        case("mix_effect_pumps_2025", "Mix Effect (EUR)", b25f["mix"], year=2025, family=pumps, tolerance=0.01),
        case("quantity_effect_pumps_2025", "Quantity Effect (EUR)", b25f["quantity"], year=2025, family=pumps,
             tolerance=0.01),
        case("price_effect_2023_is_blank", "Price Effect (EUR)", None, year=2023),
        case("share_pumps_2025", "Share of Net Sales (%)",
             sales("net_sales_eur", year=2025, family=pumps) / total_2025, year=2025, family=pumps,
             tolerance=0.00001),
        case("share_margin_western_europe_2025", "Share of Margin (%)",
             sales("margin_eur", year=2025, region="WEU") / sales("margin_eur", year=2025),
             year=2025, region="WEU", tolerance=0.00001),
        case("use_phase_2025", "Use-phase Emissions (tCO2e)", use_phase(year=2025), year=2025, tolerance=0.01),
        case("use_phase_rest_of_world_is_blank", "Use-phase Emissions (tCO2e)", None, region="ROW"),
        case("use_phase_per_unit_pumps_2025", "Use-phase Emissions per Unit (tCO2e)",
             use_phase(year=2025, family=pumps) / use_phase("units", year=2025, family=pumps),
             year=2025, family=pumps, tolerance=0.0001),
        case("use_phase_per_thousand_eur_2025", "Use-phase Emissions per Thousand EUR (tCO2e)",
             use_phase(year=2025) / (use_phase("net_sales_eur", year=2025) / 1000), year=2025,
             tolerance=0.0001),
        case("total_under_category_11_2025", "Total Emissions (tCO2e)", use_phase(year=2025),
             year=2025, scope3_category=11, tolerance=0.01),
        case("weighted_score_2025", "Weighted Score", weighted_score(year=2025), year=2025, tolerance=0.00001),
        case("weighted_score_multistage_2024", "Weighted Score", weighted_score(year=2024, group="Multistage pumps"),
             year=2024, group="Multistage pumps", tolerance=0.00001),
        case("quarantined_2025", "Quarantined Sales (EUR)", quarantined, year=2025, tolerance=0.01),
        case("sales_reconciliation_all", "Sales Reconciliation Difference (EUR)", 0.0, tolerance=0.001),
        case("data_issues_all", "Data Issues", float(len(ISSUES))),
        # Region roles see their region's sales, and blank site figures.
        case("rls_nordics_sales_2025", "Net Sales (EUR)", sales("net_sales_eur", year=2025, region="NOR"),
             role="Nordics", year=2025, tolerance=0.01),
        case("rls_nordics_cannot_see_baltics", "Net Sales (EUR)", None, role="Nordics", region="BAL"),
        case("rls_baltics_site_emissions_blank", "Scope 1 Emissions (tCO2e)", None, role="Baltics"),
        case("rls_western_europe_use_phase", "Use-phase Emissions (tCO2e)", use_phase(region="WEU"),
             role="Western Europe", tolerance=0.01),
        case("rls_rest_of_world_revenue_blank", "Revenue (EUR)", None, role="Rest of world"),
        case("rls_finland_sales_2025", "Net Sales (EUR)",
             sum(float(r["net_sales_eur"]) for r in sales_rows(year=2025)
                 if SITE[r["site_id"]]["country"] == "Finland"), role="Finland", year=2025, tolerance=0.01),
    ]


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
        # Was blank until phase 2 calculated category 11 from units sold (31 October 2026).
        case("total_under_category_11", "Total Emissions (tCO2e)", total(EM, scope3_category=11),
             scope3_category=11, tolerance=0.01),
        case("total_under_category_2_is_blank", "Total Emissions (tCO2e)", None,
             scope3_category=2),
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


# ---------------------------------------------------------------------------
# Report redesign (31 October 2026): comparisons, budget, the bridge waterfall,
# the scorecard's prior quarter, and the text the pages show.
# ---------------------------------------------------------------------------

BUDGET = read("fact_budget")
CONTRACTS = {r["contract_id"]: r for r in read("dim_contract")}


def budget(column, year=None, family=None, region=None):
    picked = [float(r[column]) for r in BUDGET
              if (not year or r["date_key"].startswith(str(year)))
              and (not family or GROUP_FAMILY[r["product_group"]] == family)
              and (not region or r["region_id"] == region)]
    return sum(picked) if picked else None


def thousands(x):
    return f"{x / 1000:,.1f}K"


def millions(x):
    return f"{x / 1_000_000:,.1f}M"


def score_in_quarter(first_month_key, group=None):
    num = den = 0.0
    for r in RATINGS:
        if r["date_key"] == str(first_month_key) and (not group or r["product_group"] == group):
            num += int(r["rating"]) * WEIGHT[r["criterion_id"]]
            den += WEIGHT[r["criterion_id"]]
    return num / den


def by_group_bridge(year, effect):
    """An effect worked out within each product group, then added over the groups."""
    out = 0.0
    for group in GROUP_FAMILY:
        cur = {p: v for p, v in by_product(year=year).items() if PRODUCT[p]["product_group"] == group}
        prev = {p: v for p, v in by_product(year=year - 1).items() if PRODUCT[p]["product_group"] == group}
        comp = [p for p in cur if p in prev]
        if not comp:
            continue
        ta, tp = sum(cur[p][0] for p in comp), sum(prev[p][0] for p in comp)
        pm = {p: (prev[p][1] - prev[p][2]) / prev[p][0] for p in comp}
        if effect == "mix":
            out += sum((cur[p][0] - ta * prev[p][0] / tp) * pm[p] for p in comp)
        else:
            out += sum((ta * prev[p][0] / tp - prev[p][0]) * pm[p] for p in comp)
    return out


def redesign_cases():
    e25, e24 = emissions(year=2025), emissions(year=2024)
    s25, s24 = sales("net_sales_eur", year=2025), sales("net_sales_eur", year=2024)
    m25, m24 = sales("margin_eur", year=2025), sales("margin_eur", year=2024)
    b25 = bridge({"year": 2025}, {"year": 2024})
    operational = emissions(year=2025, scope=1) + emissions(year=2025, scope=2)
    plan_sales, plan_margin = budget("budget_net_sales_eur", year=2025), budget("budget_margin_eur", year=2025)
    pumps = "Industrial process pumps"
    steps = [("Prior-year margin", m24), ("Sales prices", b25["price"]), ("Mix", b25["mix"]),
             ("Delivery volumes", b25["quantity"]), ("Variable costs", b25["cost"]),
             ("Not comparable", None), ("This year's margin", m25)]
    before_mix = m24 + b25["price"]
    drivers = {"sales prices": b25["price"], "mix": b25["mix"], "delivery volumes": b25["quantity"],
               "variable costs": b25["cost"]}
    biggest = max(drivers, key=lambda k: abs(drivers[k]))
    change = (e25 - e24) / e24
    margin_pct = (m25 / s25, m24 / s24)
    contract = sorted(CONTRACTS)[0]
    start = CONTRACTS[contract]["start_date_key"]
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    out = [
        case("operational_2025", "Operational Emissions (tCO2e)", operational, year=2025),
        case("operational_per_fte_2025", "Operational Emissions per FTE (tCO2e)",
             operational / average_fte(year=2025), year=2025, tolerance=0.0001),
        case("market_minus_location_2025", "Scope 2 Market minus Location (tCO2e)",
             total(MARKET, year=2025) - emissions(year=2025, scope=2), year=2025),
        case("sales_growth_2025", "Sales Growth vs Prior Year (%)", s25 / s24 - 1, year=2025,
             tolerance=0.00001),
        case("sales_growth_2023_is_blank", "Sales Growth vs Prior Year (%)", None, year=2023),
        case("budget_sales_2025", "Budget Net Sales (EUR)", plan_sales, year=2025, tolerance=0.5),
        case("budget_margin_2025", "Budget Margin (EUR)", plan_margin, year=2025, tolerance=0.5),
        case("budget_units_pumps_2025", "Budget Units", budget("budget_units", year=2025, family=pumps),
             year=2025, family=pumps),
        case("sales_vs_budget_2025", "Net Sales vs Budget (EUR)", s25 - plan_sales, year=2025, tolerance=0.5),
        case("sales_vs_budget_pct_2025", "Net Sales vs Budget (%)", s25 / plan_sales - 1, year=2025,
             tolerance=0.00001),
        case("margin_vs_budget_2025", "Margin vs Budget (EUR)", m25 - plan_margin, year=2025, tolerance=0.5),
        case("rls_nordics_budget_2025", "Budget Net Sales (EUR)", budget("budget_net_sales_eur", year=2025, region="NOR"),
             role="Nordics", year=2025, tolerance=0.5),
        case("rls_nordics_cannot_see_baltics_budget", "Budget Net Sales (EUR)", None, role="Nordics", region="BAL"),
        case("mix_by_group_2025", "Mix Effect by Group (EUR)", by_group_bridge(2025, "mix"), year=2025, tolerance=0.01),
        case("quantity_by_group_2025", "Quantity Effect by Group (EUR)", by_group_bridge(2025, "quantity"),
             year=2025, tolerance=0.01),
        case("mix_between_groups_2025", "Mix Between Groups (EUR)",
             b25["mix"] - by_group_bridge(2025, "mix"), year=2025, tolerance=0.01),
        # Within groups, mix plus quantity add to the company's volume effect: volume is additive.
        case("volume_adds_over_groups_2025", "Volume Effect (EUR)",
             by_group_bridge(2025, "mix") + by_group_bridge(2025, "quantity"), year=2025, tolerance=0.01),
        case("bridge_mix_base_2025", "Bridge Base (EUR)", min(before_mix, before_mix + b25["mix"]),
             year=2025, step="Mix", tolerance=0.01),
        case("bridge_prior_total_2025", "Bridge Prior Year Total (EUR)", m24, year=2025,
             step="Prior-year margin", tolerance=0.01),
        case("bridge_this_year_total_2025", "Bridge This Year Total (EUR)", m25, year=2025,
             step="This year's margin", tolerance=0.01),
        case("bridge_not_comparable_2025_is_blank", "Bridge Value (EUR)", None, year=2025, step="Not comparable"),
        case("bridge_this_year_base_is_blank", "Bridge Base (EUR)", None, year=2025, step="This year's margin"),
        case("score_prior_quarter_2025_q1", "Weighted Score Prior Quarter", score_in_quarter(20241001),
             year=2025, quarter=1, tolerance=0.00001),
        case("score_change_booster_2025_q2", "Weighted Score Change vs Prior Quarter",
             score_in_quarter(20250401, "Booster sets") - score_in_quarter(20250101, "Booster sets"),
             year=2025, quarter=2, group="Booster sets", tolerance=0.00001),
        case("open_issues_all", "Open Data Issues",
             float(sum(1 for r in ISSUES if r["status"] == "Quarantined"))),
        # Text measures: the exact words a page shows.
        case("total_context_2025", "Total Emissions Context",
             f"2024: {thousands(e24)}, {change:+.1%}", year=2025),
        case("total_context_2023", "Total Emissions Context", "No prior year to compare", year=2023),
        case("margin_percent_context_2025", "Margin Percent Context",
             f"2024: {margin_pct[1]:.1%}, " + f"{margin_pct[0] - margin_pct[1]:+.1%}".replace("%", " pts"),
             year=2025),
        case("net_sales_budget_context_2025", "Net Sales Budget Context",
             f"Budget: {millions(plan_sales)}, {s25 / plan_sales - 1:+.1%}", year=2025),
        case("overview_message_2025", "Overview Message",
             f"Emissions {'fell' if change < 0 else 'rose'} {abs(change):.1%} in 2025; use of sold products is "
             f"{use_phase(year=2025) / e25:.0%} of the total", year=2025),
        case("price_volume_mix_message_2025", "Price Volume Mix Message",
             f"Margin {'fell' if b25['change'] < 0 else 'rose'} EUR {abs(b25['change']) / 1e6:,.1f} million in 2025; "
             f"the biggest driver was {biggest} ({drivers[biggest] / 1e6:+,.1f} million)", year=2025),
        case("contract_start", "Contract Start",
             f"{month_names[int(start[4:6]) - 1]} {start[:4]}", contract=contract),
        case("report_footer", "Report Footer", "Data Jan 2023 to Dec 2025, monthly. Refreshed ", prefix=True),
    ]
    pumps_sales = (sales("net_sales_eur", year=2025), sales("net_sales_eur", year=2024))
    out += [
        # The label of each step sits on top of its bar: after the step if it rose, before if it fell.
        case("bridge_label_sales_prices_2025", "Bridge Label Position (EUR)", m24 + b25["price"],
             year=2025, step="Sales prices", tolerance=0.01),
        case("bridge_label_mix_2025", "Bridge Label Position (EUR)", m24 + b25["price"],
             year=2025, step="Mix", tolerance=0.01),
        case("bridge_label_total_is_blank", "Bridge Label Position (EUR)", None, year=2025,
             step="This year's margin"),
        # Company averages ignore the product group a visual shows.
        case("company_margin_under_a_group_2025", "Company Margin (%)", m25 / s25, year=2025,
             group="Booster sets", tolerance=0.00001),
        case("company_growth_under_a_group_2025", "Company Sales Growth (%)",
             pumps_sales[0] / pumps_sales[1] - 1, year=2025, group="Booster sets", tolerance=0.00001),
        case("company_score_under_a_group_2025", "Company Weighted Score", weighted_score(year=2025),
             year=2025, group="Booster sets", tolerance=0.00001),
    ]
    # Each step of the waterfall equals its measure, and the steps add from one total to the other.
    for name, value in steps:
        if value is not None:
            out.append(case(f"bridge_value_{name.split()[0].lower()}_2025", "Bridge Value (EUR)", value,
                            year=2025, step=name, tolerance=0.01))
    assert abs(m24 + b25["price"] + b25["mix"] + b25["quantity"] + b25["cost"] - m25) < 0.01
    return out
