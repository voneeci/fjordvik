"""The Fjordvik MCP server: five read-only tools and one schema resource.

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
from fjordvik_mcp.queries import GroupBy, IntensityGroupBy, Warehouse

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False,
                            idempotent_hint=True, open_world_hint=False)

INSTRUCTIONS = """\
Answers questions about Fjordvik Manufacturing Oy, a FICTIONAL manufacturer with six
sites in Finland, Sweden and Estonia, using monthly synthetic data from January 2023 to
December 2025. Emission factors are illustrative, not cited: never present results as
real-world figures. Start with describe_dataset if unsure what exists. Prefer
emissions_total and emissions_intensity; use run_sql only for questions they can't answer.
Always state units (tCO2e = tonnes of carbon dioxide equivalent)."""

SCHEMA_DOC = """\
# Fjordvik schema (star schema, monthly grain)

dim_date(date_key INTEGER e.g. 20240701, date, year, quarter, month, month_name)
dim_site(site_id, site_name, country, site_type)
dim_source(source_id, source_name, scope 1|2|3, category)
fact_emissions(date_key, site_id, source_id, activity_amount, unit, emission_factor, tco2e)
  grain: one row per month, site and source; tco2e = activity_amount * emission_factor / 1000
fact_site_metrics(date_key, site_id, revenue_eur, fte)
  grain: one row per month and site; fte is a level (average it over months, never sum)

Joins: facts to dim_date on date_key, to dim_site on site_id, fact_emissions to
dim_source on source_id. fact_site_metrics has no source.
Emission factors are illustrative. Scope 2 is location-based only.
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
    ) -> dict[str, Any]:
        """Total emissions in tCO2e, optionally grouped and filtered.

        group_by: any of year, quarter, month, site, country, site_type, scope,
        source, category (empty = one company-wide total).
        Filters: year (2023 to 2025), site_id (e.g. FI01), country (Finland,
        Sweden, Estonia), scope (1, 2 or 3), source_id (e.g. S05), and
        start_month / end_month as YYYY-MM (inclusive).
        Example: monthly trend for one site = group_by ["month"], site_id "FI01"."""
        with user_errors():
            return wh.emissions_total(group_by, year=year, site_id=site_id, country=country,
                                      scope=scope, source_id=source_id,
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
    def data_quality_report() -> dict[str, Any]:
        """Run eight data quality checks (unique keys, joins to dimensions, the tco2e
        formula, no negatives, one unit per source, a complete monthly grid, and
        emissions and metrics covering the same site-months). Returns pass or fail
        for each, with up to ten example rows for any failure."""
        return wh.data_quality_report()

    @server.tool(annotations=READ_ONLY)
    def run_sql(query: str, max_rows: int = 200) -> dict[str, Any]:
        """Run one read-only DuckDB SELECT against the five tables (see the
        fjordvik://schema resource). Only a single SELECT statement is accepted;
        files and the network are blocked. max_rows: 1 to 1000."""
        with user_errors():
            return wh.run_sql(query, max_rows)

    @server.resource("fjordvik://schema", name="schema", mime_type="text/markdown",
                     description="Tables, columns, grain and joins of the Fjordvik dataset")
    def schema() -> str:
        return SCHEMA_DOC

    @server.resource("fjordvik://source", name="source", mime_type="application/json",
                     description="The manifest of the loaded data: generator version, "
                                 "seed, period, row counts and SHA-256 checksums")
    def source() -> str:
        path = db.data_dir() / "manifest.json"
        return path.read_text(encoding="utf-8") if path.exists() else json.dumps({})

    return server


def main() -> None:
    build_server().run("stdio")
