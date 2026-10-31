"""run_sql can read the five tables and do nothing else."""

import pytest


def test_select_and_cte_are_allowed(wh):
    r = wh.run_sql("SELECT count(*) AS n FROM fact_emissions")
    assert r["rows"] == [{"n": 1422}]
    r = wh.run_sql("WITH s AS (SELECT * FROM dim_site) SELECT count(*) AS n FROM s")
    assert r["rows"] == [{"n": 6}]


def test_results_are_capped(wh):
    r = wh.run_sql("SELECT * FROM fact_emissions", max_rows=5)
    assert len(r["rows"]) == 5 and r["truncated"] is True
    r = wh.run_sql("SELECT * FROM dim_site", max_rows=10)
    assert len(r["rows"]) == 6 and r["truncated"] is False


@pytest.mark.parametrize("max_rows", [0, 1001])
def test_max_rows_bounds(wh, max_rows):
    with pytest.raises(ValueError, match="max_rows"):
        wh.run_sql("SELECT 1", max_rows=max_rows)


@pytest.mark.parametrize("query", [
    "DROP TABLE dim_site",
    "DELETE FROM fact_emissions",
    "INSERT INTO dim_site VALUES ('X', 'X', 'X', 'X')",
    "UPDATE fact_emissions SET tco2e = 0",
    "CREATE TABLE x AS SELECT 1",
    "SET enable_external_access = true",
    "ATTACH 'other.db'",
    "COPY dim_site TO 'leak.csv'",
    "INSTALL httpfs",
    "SELECT 1; DROP TABLE dim_site",
])
def test_anything_but_one_select_is_refused(wh, query):
    with pytest.raises(ValueError):
        wh.run_sql(query)
    assert wh.run_sql("SELECT count(*) AS n FROM dim_site")["rows"] == [{"n": 6}]


@pytest.mark.parametrize("query", [
    "SELECT * FROM read_csv('../data/data/dim_site.csv')",
    "SELECT * FROM '../data/data/dim_site.csv'",
    "SELECT * FROM read_text('README.md')",
    "SELECT * FROM read_csv('https://example.com/x.csv')",
])
def test_a_select_cannot_reach_files_or_the_network(wh, query):
    with pytest.raises(ValueError, match="Permission Error|failed"):
        wh.run_sql(query)
