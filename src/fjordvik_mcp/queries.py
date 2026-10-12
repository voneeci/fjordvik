"""The questions the MCP tools can answer, as plain Python over DuckDB.

Kept separate from the MCP layer (server.py) so each one can be tested directly.
Every filter value is passed as a bound parameter (?), never pasted into the SQL
text, so user input can't change the query. Grouping columns come from a fixed
list, never from free text.
"""

import re
from datetime import date
from decimal import Decimal
from typing import Any, Literal

import duckdb

GroupBy = Literal["year", "quarter", "month", "site", "country", "site_type",
                  "scope", "source", "category"]
IntensityGroupBy = Literal["year", "site", "country", "site_type"]

# group name -> list of (SQL expression, output column)
GROUPS: dict[str, list[tuple[str, str]]] = {
    "year": [("d.year", "year")],
    "quarter": [("d.year || '-Q' || d.quarter", "quarter")],
    "month": [("strftime(d.date, '%Y-%m')", "month")],
    "site": [("s.site_id", "site_id"), ("s.site_name", "site_name")],
    "country": [("s.country", "country")],
    "site_type": [("s.site_type", "site_type")],
    "scope": [("src.scope", "scope")],
    "source": [("src.source_id", "source_id"), ("src.source_name", "source_name")],
    "category": [("src.category", "category")],
}

MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
MAX_SQL_ROWS = 1000


def jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def rows_as_dicts(cur: duckdb.DuckDBPyConnection, limit: int | None = None) -> list[dict]:
    names = [c[0] for c in cur.description]
    rows = cur.fetchall() if limit is None else cur.fetchmany(limit)
    return [{n: jsonable(v) for n, v in zip(names, row)} for row in rows]


class Warehouse:
    def __init__(self, con: duckdb.DuckDBPyConnection):
        self.con = con
        cur = con.cursor()
        self.site_ids = {r[0] for r in cur.execute("SELECT site_id FROM dim_site").fetchall()}
        self.source_ids = {r[0] for r in cur.execute("SELECT source_id FROM dim_source").fetchall()}
        self.countries = {r[0] for r in cur.execute("SELECT DISTINCT country FROM dim_site").fetchall()}
        self.years = {r[0] for r in cur.execute("SELECT DISTINCT year FROM dim_date").fetchall()}

    def cursor(self) -> duckdb.DuckDBPyConnection:
        # A cursor is a separate handle on the same database, safe to use per call.
        return self.con.cursor()

    # ------------------------------------------------------------------
    # Filters shared by the tools
    # ------------------------------------------------------------------

    def _filters(self, year=None, site_id=None, country=None, scope=None,
                 source_id=None, start_month=None, end_month=None,
                 allow_source=True) -> tuple[str, list]:
        where, params = [], []
        if year is not None:
            self._check(year, self.years, "year")
            where.append("d.year = ?"); params.append(year)
        if site_id is not None:
            self._check(site_id, self.site_ids, "site_id")
            where.append("s.site_id = ?"); params.append(site_id)
        if country is not None:
            self._check(country, self.countries, "country")
            where.append("s.country = ?"); params.append(country)
        if allow_source and scope is not None:
            self._check(scope, {1, 2, 3}, "scope")
            where.append("src.scope = ?"); params.append(scope)
        if allow_source and source_id is not None:
            self._check(source_id, self.source_ids, "source_id")
            where.append("src.source_id = ?"); params.append(source_id)
        for value, op, name in ((start_month, ">=", "start_month"), (end_month, "<=", "end_month")):
            if value is not None:
                if not MONTH.match(value):
                    raise ValueError(f"{name} must look like 2024-07, got {value!r}")
                where.append(f"d.date_key {op} ?")
                params.append(int(value.replace("-", "")) * 100 + 1)
        return (" WHERE " + " AND ".join(where)) if where else "", params

    @staticmethod
    def _check(value, allowed, name):
        if value not in allowed:
            raise ValueError(f"Unknown {name} {value!r}. Valid values: {sorted(allowed)}")

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def describe(self) -> dict:
        cur = self.cursor()
        period = cur.execute("SELECT min(date), max(date) FROM dim_date").fetchone()
        sites = rows_as_dicts(cur.execute("""
            SELECT s.*, strftime(min(d.date), '%Y-%m') AS first_month
            FROM dim_site s
            JOIN fact_site_metrics m USING (site_id)
            JOIN dim_date d USING (date_key)
            GROUP BY ALL ORDER BY s.site_id"""))
        sources = rows_as_dicts(cur.execute("""
            SELECT src.*, any_value(f.unit) AS unit
            FROM dim_source src JOIN fact_emissions f USING (source_id)
            GROUP BY ALL ORDER BY src.source_id"""))
        counts = {t: cur.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                  for t in ("dim_date", "dim_site", "dim_source",
                            "fact_emissions", "fact_site_metrics")}
        return {
            "company": "Fjordvik Manufacturing Oy (fictional; all data is synthetic)",
            "period": {"first_month": period[0].isoformat()[:7],
                       "last_month": period[1].isoformat()[:7], "grain": "monthly"},
            "sites": sites,
            "sources": sources,
            "row_counts": counts,
            "units": {"tco2e": "tonnes of carbon dioxide equivalent",
                      "revenue_eur": "euros", "fte": "full-time equivalent employees"},
            "caveats": [
                "Emission factors are illustrative, not cited. Not for real reporting.",
                "Scope 2 is location-based only.",
                "Tartu Warehouse (EE02) opened in July 2024; it has no data before then.",
                "Helsinki Head Office (FI02) books no revenue, so emissions per euro "
                "is blank (null) for it.",
            ],
        }

    def emissions_total(self, group_by: list[GroupBy] | None = None, **filters) -> dict:
        group_by = list(dict.fromkeys(group_by or []))
        unknown = [g for g in group_by if g not in GROUPS]
        if unknown:
            raise ValueError(f"Unknown group_by {unknown}. Valid values: {list(GROUPS)}")
        cols = [pair for g in group_by for pair in GROUPS[g]]
        select = "".join(f"{expr} AS {alias}, " for expr, alias in cols)
        where, params = self._filters(**filters)
        sql = f"""
            SELECT {select}round(sum(f.tco2e), 3) AS tco2e, count(*) AS fact_rows
            FROM fact_emissions f
            JOIN dim_date d USING (date_key)
            JOIN dim_site s USING (site_id)
            JOIN dim_source src USING (source_id)
            {where}
            GROUP BY ALL ORDER BY ALL"""
        rows = rows_as_dicts(self.cursor().execute(sql, params))
        return {"unit": "tCO2e", "group_by": group_by,
                "filters": {k: v for k, v in filters.items() if v is not None},
                "rows": rows}

    def emissions_intensity(self, per: Literal["fte", "million_eur_revenue"],
                            group_by: list[IntensityGroupBy] | None = None,
                            year=None, site_id=None, country=None) -> dict:
        """Emissions divided by headcount or revenue, at a matching grain.

        Emissions and revenue are flows, so they add up over months. FTE is a
        level, so it is summed across sites within a month and then averaged
        over the months. Dividing by a sum of monthly FTE would be wrong."""
        if per not in ("fte", "million_eur_revenue"):
            raise ValueError("per must be 'fte' or 'million_eur_revenue'")
        group_by = list(dict.fromkeys(group_by or []))
        unknown = [g for g in group_by if g not in ("year", "site", "country", "site_type")]
        if unknown:
            raise ValueError(f"Unknown group_by {unknown}. Valid values: year, site, country, site_type")
        cols = [pair for g in group_by for pair in GROUPS[g]]
        inner = "".join(f"{expr} AS {alias}, " for expr, alias in cols)
        outer = "".join(f"{alias}, " for _expr, alias in cols)
        where, params = self._filters(year=year, site_id=site_id, country=country,
                                      allow_source=False)
        sql = f"""
            WITH site_month AS (
                SELECT m.date_key, m.site_id, m.revenue_eur, m.fte,
                       coalesce(sum(f.tco2e), 0) AS tco2e
                FROM fact_site_metrics m
                LEFT JOIN fact_emissions f USING (date_key, site_id)
                GROUP BY ALL
            ),
            group_month AS (
                SELECT {inner}d.date_key,
                       sum(sm.tco2e) AS tco2e, sum(sm.revenue_eur) AS revenue_eur,
                       sum(sm.fte) AS fte
                FROM site_month sm
                JOIN dim_date d USING (date_key)
                JOIN dim_site s USING (site_id)
                {where}
                GROUP BY ALL
            )
            SELECT {outer}
                   round(sum(tco2e), 3) AS tco2e,
                   round(sum(revenue_eur), 2) AS revenue_eur,
                   round(avg(fte), 1) AS average_fte,
                   count(*) AS months,
                   round(CAST(sum(tco2e) AS DOUBLE) / nullif(avg(fte), 0), 3) AS tco2e_per_fte,
                   round(CAST(sum(tco2e) AS DOUBLE) / nullif(sum(revenue_eur) / 1e6, 0), 3)
                       AS tco2e_per_million_eur
            FROM group_month
            GROUP BY ALL ORDER BY ALL"""
        rows = rows_as_dicts(self.cursor().execute(sql, params))
        key = "tco2e_per_fte" if per == "fte" else "tco2e_per_million_eur"
        for r in rows:
            r["intensity"] = r[key]
        return {
            "per": per,
            "unit": "tCO2e per FTE" if per == "fte" else "tCO2e per million EUR revenue",
            "method": ("FTE is averaged over the months in the period (it is a level); "
                       "emissions and revenue are summed (they are flows). "
                       "Intensity is null where the divisor is zero."),
            "group_by": group_by,
            "rows": rows,
        }

    def data_quality_report(self) -> dict:
        cur = self.cursor()
        checks = []

        def check(name, description, sql):
            failures = rows_as_dicts(cur.execute(sql), limit=10)
            checks.append({"check": name, "description": description,
                           "passed": not failures, "examples": failures})

        check("unique_emission_keys", "One row per month, site and source",
              """SELECT date_key, site_id, source_id, count(*) AS n FROM fact_emissions
                 GROUP BY ALL HAVING n > 1""")
        check("unique_metric_keys", "One row per month and site",
              """SELECT date_key, site_id, count(*) AS n FROM fact_site_metrics
                 GROUP BY ALL HAVING n > 1""")
        check("fact_rows_join_dimensions", "Every fact row matches a date, site and source",
              """SELECT f.date_key, f.site_id, f.source_id FROM fact_emissions f
                 LEFT JOIN dim_date d USING (date_key) LEFT JOIN dim_site s USING (site_id)
                 LEFT JOIN dim_source src USING (source_id)
                 WHERE d.date_key IS NULL OR s.site_id IS NULL OR src.source_id IS NULL""")
        check("tco2e_matches_formula", "tco2e = activity_amount * emission_factor / 1000",
              """SELECT date_key, site_id, source_id, tco2e,
                        activity_amount * emission_factor / 1000 AS expected
                 FROM fact_emissions
                 WHERE abs(tco2e - activity_amount * emission_factor / 1000) > 0.000001""")
        check("no_negative_values", "No negative activity, emissions, revenue or FTE",
              """SELECT 'emissions' AS tbl, date_key, site_id FROM fact_emissions
                   WHERE activity_amount < 0 OR tco2e < 0
                 UNION ALL
                 SELECT 'metrics', date_key, site_id FROM fact_site_metrics
                   WHERE revenue_eur < 0 OR fte <= 0""")
        check("one_unit_per_source", "Each source is always measured in the same unit",
              """SELECT source_id, count(DISTINCT unit) AS units FROM fact_emissions
                 GROUP BY ALL HAVING units > 1""")
        check("complete_monthly_grid",
              "Every site reports each of its sources every month from its first month",
              """WITH first AS (SELECT site_id, min(date_key) AS first_key
                                FROM fact_site_metrics GROUP BY ALL),
                      pairs AS (SELECT DISTINCT site_id, source_id FROM fact_emissions),
                      expected AS (SELECT d.date_key, p.site_id, p.source_id
                                   FROM pairs p JOIN first USING (site_id)
                                   JOIN dim_date d ON d.date_key >= first.first_key)
                 SELECT e.* FROM expected e
                 LEFT JOIN fact_emissions f USING (date_key, site_id, source_id)
                 WHERE f.date_key IS NULL ORDER BY ALL""")
        check("metrics_match_emissions",
              "Each site-month with emissions also has revenue and FTE, and the reverse",
              """SELECT coalesce(e.date_key, m.date_key) AS date_key,
                        coalesce(e.site_id, m.site_id) AS site_id,
                        CASE WHEN m.site_id IS NULL THEN 'no metrics row'
                             ELSE 'no emission rows' END AS problem
                 FROM (SELECT DISTINCT date_key, site_id FROM fact_emissions) e
                 FULL OUTER JOIN fact_site_metrics m USING (date_key, site_id)
                 WHERE e.site_id IS NULL OR m.site_id IS NULL""")

        passed = sum(c["passed"] for c in checks)
        return {"passed": passed, "failed": len(checks) - passed, "checks": checks}

    def run_sql(self, query: str, max_rows: int = 200) -> dict:
        """Run one read-only SELECT. Anything else is refused before it runs."""
        if not 1 <= max_rows <= MAX_SQL_ROWS:
            raise ValueError(f"max_rows must be between 1 and {MAX_SQL_ROWS}")
        try:
            statements = self.con.extract_statements(query)
        except duckdb.Error as e:
            raise ValueError(f"Could not parse the SQL: {e}") from e
        if len(statements) != 1:
            raise ValueError("Send exactly one SQL statement.")
        if statements[0].type != duckdb.StatementType.SELECT:
            raise ValueError(f"Only SELECT queries are allowed, not {statements[0].type.name}.")
        cur = self.cursor()
        try:
            cur.execute(query)
        except duckdb.Error as e:
            raise ValueError(f"The query failed: {e}") from e
        rows = rows_as_dicts(cur, limit=max_rows + 1)
        return {"columns": [c[0] for c in cur.description],
                "rows": rows[:max_rows],
                "truncated": len(rows) > max_rows}
