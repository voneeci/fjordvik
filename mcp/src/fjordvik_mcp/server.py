"""The Fjordvik MCP server: seven read-only tools and two resources.

Claude Desktop starts this as a subprocess and talks to it over standard input
and output (the stdio transport): one person on one laptop, full access. With
--http it runs as a company connector would: over Streamable HTTP, behind an
OAuth sign-in, and each tool checks the signed-in role (auth.py).

Each tool is a thin wrapper over a method in queries.py; the descriptions here
are what Claude reads when deciding which tool to call, so they say what each
tool is for, not how it works.
"""

import argparse
import json
from contextlib import contextmanager
from typing import Any, Literal

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

from fjordvik_mcp import db
from fjordvik_mcp.auth import ROLES, SCOPE, DemoOAuthProvider, Role, sign_in_routes
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


DEFAULT_PORT = 8765


def permitted(tool: str) -> Role | None:
    """The signed-in role, if it may use this tool. Over stdio there is no sign-in
    and no token: one person on their own laptop, so every tool is open (None)."""
    token = get_access_token()
    if token is None:
        return None
    role = ROLES.get(token.subject or "")
    if role is None or tool not in role.tools:
        allowed = ", ".join(r.name for r in ROLES.values() if tool in r.tools)
        who = role.name if role else "an unknown role"
        raise ToolError(f"Signed in as {who}: {tool} is not available to this role. "
                        f"Roles that can use it: {allowed}.")
    return role


def build_server(warehouse: Warehouse | None = None, http_url: str | None = None) -> MCPServer:
    """The server. http_url (for example http://127.0.0.1:8765) turns on the OAuth
    sign-in for the HTTP transport; without it the server is for stdio."""
    wh = warehouse or Warehouse(db.connect())
    sign_in: dict[str, Any] = {}
    if http_url:
        provider = DemoOAuthProvider(http_url, f"{http_url}/mcp")
        sign_in = dict(
            auth_server_provider=provider,
            auth=AuthSettings(
                issuer_url=http_url, resource_server_url=f"{http_url}/mcp",
                validate_token_resource=True, required_scopes=[SCOPE],
                client_registration_options=ClientRegistrationOptions(
                    enabled=True, valid_scopes=[SCOPE], default_scopes=[SCOPE]),
                revocation_options=RevocationOptions(enabled=True)))
    server = MCPServer(name="fjordvik", title="Fjordvik emissions data",
                       instructions=INSTRUCTIONS, version="1.0.0", **sign_in)
    if http_url:
        show, finish = sign_in_routes(provider)
        server.custom_route("/login", methods=["GET"])(show)
        server.custom_route("/login", methods=["POST"])(finish)

    @server.tool(annotations=READ_ONLY)
    def describe_dataset() -> dict[str, Any]:
        """List the sites, emission sources, period, row counts, units and caveats.
        Use this first to learn valid site_id and source_id values."""
        permitted("describe_dataset")
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
        permitted("emissions_total")
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
        permitted("emissions_intensity")
        with user_errors():
            return wh.emissions_intensity(per, group_by, year=year, site_id=site_id,
                                          country=country)

    @server.tool(annotations=READ_ONLY)
    def scope3_inventory(year: int | None = None) -> dict[str, Any]:
        """The 15 Greenhouse Gas (GHG) Protocol scope 3 categories: whether Fjordvik
        calculates each, the reason for any it doesn't, and tCO2e for the year (or
        the whole period). Use it for questions about scope 3 coverage or exclusions."""
        permitted("scope3_inventory")
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
        Filters: year, region_id (NOR, BAL, WEU, ROW), product_family.
        A sales region role sees its own region only."""
        role = permitted("sales_summary")
        if role and role.region_id:
            if region_id and region_id != role.region_id:
                raise ToolError(f"Signed in as {role.name}: only region {role.region_id} "
                                f"is available, not {region_id}.")
            region_id = role.region_id
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
        permitted("data_quality_report")
        return wh.data_quality_report()

    @server.tool(annotations=READ_ONLY)
    def run_sql(query: str, max_rows: int = 200) -> dict[str, Any]:
        """Run one read-only DuckDB SELECT against the 21 tables and the
        all_emissions view (see the
        fjordvik://schema resource). Only a single SELECT statement is accepted;
        files and the network are blocked. max_rows: 1 to 1000."""
        permitted("run_sql")
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


def http_security(port: int) -> TransportSecuritySettings:
    """Only Host and Origin headers naming this computer: a web page elsewhere can't use it."""
    return TransportSecuritySettings(
        allowed_hosts=[f"127.0.0.1:{port}", f"localhost:{port}"],
        allowed_origins=[f"http://127.0.0.1:{port}", f"http://localhost:{port}"])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="fjordvik-mcp", description=__doc__.splitlines()[0])
    parser.add_argument("--http", action="store_true",
                        help="run over Streamable HTTP with sign-in, on this computer only")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    if not args.http:
        build_server().run("stdio")
        return
    url = f"http://127.0.0.1:{args.port}"
    print(f"Fjordvik connector with sign-in at {url}/mcp (this computer only; Ctrl+C stops it)",
          flush=True)
    # Bound to 127.0.0.1, so no other machine can reach it.
    build_server(http_url=url).run("streamable-http", host="127.0.0.1", port=args.port,
                                   transport_security=http_security(args.port))
