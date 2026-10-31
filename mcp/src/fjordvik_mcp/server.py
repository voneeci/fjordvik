"""The Fjordvik MCP server: seven read-only tools and two resources.

Claude Desktop starts this as a subprocess and talks to it over standard input
and output (the stdio transport). Each tool is a thin wrapper over a method in
queries.py; the descriptions here are what Claude reads when deciding which
tool to call, so they say what each tool is for, not how it works.
"""

import json
from contextlib import contextmanager
from typing import Any, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from fjordvik_mcp import db
from fjordvik_mcp.queries import (GroupBy, IntensityGroupBy, SalesGroupBy, Scope2Method,
                                  Warehouse)

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False,
                            idempotent_hint=True, open_world_hint=False)

INSTRUCTIONS = """\
Answers questions about Fjordvik Manufacturing Oy, a FICTIONAL maker of electric pumps
and pump systems with six sites in Finland, Sweden and Estonia, using monthly synthetic
data from January 2023 to December 2025. Emission factors are illustrative, not cited:
never present results as real-world figures. Start with describe_dataset if unsure what
exists. Prefer emissions_total, emissions_intensity, scope3_inventory and sales_summary; use run_sql only
for questions they can't answer. Totals are location-based unless scope2_method is
'market'. Always state units (tCO2e = tonnes of carbon dioxide equivalent) and which
scope 3 categories a total holds."""

SCHEMA_DOC = """\
# Fjordvik schema (star schema, monthly grain)

dim_date(date_key INTEGER e.g. 20240701, date, year, quarter, month, month_name)
dim_site(site_id, site_name, country, site_type)
dim_source(source_id, source_name, scope 1|2|3, category, scope3_category 1-15 or null, method)
dim_scope3_category(scope3_category, category_name, status, reason): all 15 categories
dim_supplier(supplier_id, supplier_name, country, spend_category)
dim_contract(contract_id, site_id, source_id, supplier_name, instrument, start_date_key,
             end_date_key, covered_share)
fact_emissions(date_key, site_id, source_id, activity_amount, unit, emission_factor, tco2e)
  grain: one row per month, site and source reported by the sites (S01 to S08)
fact_energy_upstream(date_key, site_id, source_id, based_on_source_id, activity_amount,
                     unit, emission_factor, tco2e)
  scope 3 category 3 (S09, S10), derived from the fuel and kWh in fact_emissions
fact_purchases(date_key, site_id, source_id, supplier_id, spend_category, method,
               activity_amount (EUR), unit, emission_factor, tco2e)
  scope 3 category 1 (S11), spend-based; grain: month, site, supplier
fact_freight(date_key, site_id, source_id, direction, mode, paid_by, tonnes, distance_km,
             activity_amount (tonne-km), unit, emission_factor, tco2e)
  scope 3 categories 4 (S12) and 9 (S13); grain: month, site, direction, mode, payer
fact_scope2_market(date_key, site_id, source_id, contract_id, instrument, activity_amount,
                   unit, emission_factor, tco2e)
  market-based scope 2: the same kWh as location-based; never add it to the totals
fact_site_metrics(date_key, site_id, revenue_eur, fte)
  grain: one row per month and site; fte is a level (average it over months, never sum)
dim_product_group(product_group, product_family)
dim_product(product_id, product_name, product_group, product_family, made_at_site_id,
            rated_kw, kwh_per_year, lifetime_years, list_price_eur, standard_cost_eur)
dim_region(region_id NOR|BAL|WEU|ROW, region_name)
dim_product_code(business_unit, local_item_number, product_id): the global classification
fact_sales(date_key, site_id, product_id, region_id, units, net_sales_eur,
           cost_of_sales_eur, margin_eur)
  grain: month, shipping site, product, region; cleaned by SQL from a simulated Oracle extract
fact_data_issue(issue_id, date_key, site_id, business_unit, issue_type, detail, line_count,
                amount_eur, status, action): problems found in the extract, for the data owner
fact_use_phase(date_key, site_id, source_id, product_id, region_id, units, net_sales_eur,
               activity_amount (lifetime kWh), unit, emission_factor, tco2e)
  scope 3 category 11 (S14): units x lifetime x yearly kWh x grid factor; no Rest of world rows
dim_score_criterion(criterion_id, criterion_name, weight, source)
fact_product_rating(date_key (first month of the quarter), product_group, criterion_id, rating 1-10)
all_emissions (view): fact_emissions, fact_energy_upstream, fact_purchases,
  fact_freight and fact_use_phase stacked (from_table, date_key, site_id, source_id, activity_amount, unit,
  emission_factor, tco2e): the location-based inventory

In every table tco2e = activity_amount * emission_factor / 1000.
Joins: facts to dim_date on date_key, to dim_site on site_id, to dim_source on
source_id; dim_source to dim_scope3_category on scope3_category; fact_purchases to
dim_supplier on supplier_id; fact_scope2_market to dim_contract on contract_id.
Emission factors are illustrative.
"""


@contextmanager
def user_errors():
    """Bad input (an unknown site, a non-SELECT query) is the caller's mistake,
    so its message goes back to Claude to correct. The SDK only passes the text
    of a ToolError through; any other exception reaches Claude as a generic
    "Error executing tool", so internal details of a real crash stay private."""
    try:
        yield
    except ValueError as e:
        raise ToolError(str(e)) from e


def build_server(warehouse: Warehouse | None = None) -> MCPServer:
    wh = warehouse or Warehouse(db.connect())
    server = MCPServer(name="fjordvik", title="Fjordvik emissions data",
                       instructions=INSTRUCTIONS, version="1.0.0")

    @server.tool(annotations=READ_ONLY)
    def describe_dataset() -> dict[str, Any]:
        """List the sites, emission sources, period, row counts, units and caveats.
        Use this first to learn valid site_id and source_id values."""
        return wh.describe()

    @server.tool(annotations=READ_ONLY)
    def emissions_total(
        group_by: list[GroupBy] | None = None,
        year: int | None = None,
        site_id: str | None = None,
        country: str | None = None,
        scope: int | None = None,
        source_id: str | None = None,
        start_month: str | None = None,
        end_month: str | None = None,
        scope2_method: Scope2Method = "location",
    ) -> dict[str, Any]:
        """Total emissions in tCO2e, optionally grouped and filtered.

        group_by: any of year, quarter, month, site, country, site_type, scope,
        source, category, scope3_category (empty = one company-wide total).
        scope2_method: "location" (default) or "market" (scope 2 from guarantees of
        origin and residual mixes; scopes 1 and 3 unchanged).
        Filters: year (2023 to 2025), site_id (e.g. FI01), country (Finland,
        Sweden, Estonia), scope (1, 2 or 3), source_id (e.g. S05), and
        start_month / end_month as YYYY-MM (inclusive).
        Example: monthly trend for one site = group_by ["month"], site_id "FI01"."""
        with user_errors():
            return wh.emissions_total(group_by, scope2_method, year=year, site_id=site_id,
                                      country=country, scope=scope, source_id=source_id,
                                      start_month=start_month, end_month=end_month)

    @server.tool(annotations=READ_ONLY)
    def emissions_intensity(
        per: Literal["fte", "million_eur_revenue"],
        group_by: list[IntensityGroupBy] | None = None,
        year: int | None = None,
        site_id: str | None = None,
        country: str | None = None,
    ) -> dict[str, Any]:
        """Emissions per full-time equivalent employee (FTE) or per million euros of
        revenue, grouped by any of year, site, country, site_type. Covers all scopes.
        Intensity is null where the divisor is zero (the head office has no revenue)."""
        with user_errors():
            return wh.emissions_intensity(per, group_by, year=year, site_id=site_id,
                                          country=country)

    @server.tool(annotations=READ_ONLY)
    def scope3_inventory(year: int | None = None) -> dict[str, Any]:
        """The 15 Greenhouse Gas (GHG) Protocol scope 3 categories: whether Fjordvik
        calculates each, the reason for any it doesn't, and tCO2e for the year (or
        the whole period). Use it for questions about scope 3 coverage or exclusions."""
        with user_errors():
            return wh.scope3_inventory(year)

    @server.tool(annotations=READ_ONLY)
    def sales_summary(
        group_by: list[SalesGroupBy] | None = None,
        year: int | None = None,
        region_id: str | None = None,
        product_family: str | None = None,
    ) -> dict[str, Any]:
        """Units sold, net sales (EUR), margin (EUR) and margin % from the cleaned sales,
        grouped by any of year, quarter, site, family, group, product, region.
        Filters: year, region_id (NOR, BAL, WEU, ROW), product_family."""
        with user_errors():
            return wh.sales_summary(group_by, year=year, region_id=region_id,
                                    product_family=product_family)

    @server.tool(annotations=READ_ONLY)
    def data_quality_report() -> dict[str, Any]:
        """Run fifteen data quality checks (unique keys, joins to dimensions, the tco2e
        formula, no negatives, one unit per source, a complete monthly grid, emissions
        and metrics covering the same site-months, and for the value-chain tables:
        keys, joins, formula, market-based kWh matching location-based kWh, the freight
        payer split, a reason for every scope 3 category, and sales reconciling to finance
        revenue). Returns pass or fail for
        each, with up to ten example rows for any failure."""
        return wh.data_quality_report()

    @server.tool(annotations=READ_ONLY)
    def run_sql(query: str, max_rows: int = 200) -> dict[str, Any]:
        """Run one read-only DuckDB SELECT against the 21 tables and the
        all_emissions view (see the
        fjordvik://schema resource). Only a single SELECT statement is accepted;
        files and the network are blocked. max_rows: 1 to 1000."""
        with user_errors():
            return wh.run_sql(query, max_rows)

    @server.resource("fjordvik://schema", name="schema", mime_type="text/markdown",
                     description="Tables, columns, grain and joins of the Fjordvik dataset")
    def schema() -> str:
        return SCHEMA_DOC

    @server.resource("fjordvik://source", name="source", mime_type="application/json",
                     description="The manifest of the loaded data: dataset version, "
                                 "period, row counts and SHA-256 checksums")
    def source() -> str:
        path = db.data_dir() / "manifest.json"
        return path.read_text(encoding="utf-8") if path.exists() else json.dumps({})

    return server


def main() -> None:
    build_server().run("stdio")
