"""Data quality rules the clean dataset must always meet."""

from collections import Counter, defaultdict

from fjordvik_data import config as c


def test_fact_keys_are_unique(tables):
    em = Counter((r["date_key"], r["site_id"], r["source_id"]) for r in tables["fact_emissions"])
    assert max(em.values()) == 1
    sm = Counter((r["date_key"], r["site_id"]) for r in tables["fact_site_metrics"])
    assert max(sm.values()) == 1


def test_every_fact_row_joins_to_its_dimensions(tables):
    dates = {r["date_key"] for r in tables["dim_date"]}
    sites = {r["site_id"] for r in tables["dim_site"]}
    sources = {r["source_id"] for r in tables["dim_source"]}
    for r in tables["fact_emissions"]:
        assert r["date_key"] in dates and r["site_id"] in sites and r["source_id"] in sources
    for r in tables["fact_site_metrics"]:
        assert r["date_key"] in dates and r["site_id"] in sites


def test_tco2e_equals_activity_times_factor_over_1000(tables):
    for r in tables["fact_emissions"]:
        expected = float(r["activity_amount"]) * float(r["emission_factor"]) / 1000
        assert abs(float(r["tco2e"]) - expected) < 1e-6, r


def test_no_negative_values(tables):
    for r in tables["fact_emissions"]:
        assert float(r["activity_amount"]) >= 0 and float(r["tco2e"]) >= 0
    for r in tables["fact_site_metrics"]:
        assert float(r["revenue_eur"]) >= 0 and float(r["fte"]) > 0


def test_each_source_has_one_unit(tables):
    units = defaultdict(set)
    for r in tables["fact_emissions"]:
        units[r["source_id"]].add(r["unit"])
    assert all(len(u) == 1 for u in units.values())


def test_factors_match_config_for_the_site_country(tables):
    country = {r["site_id"]: r["country"] for r in tables["dim_site"]}
    for r in tables["fact_emissions"]:
        s = r["source_id"]
        if s in c.FACTORS_BY_COUNTRY:
            expected = c.FACTORS_BY_COUNTRY[s][country[r["site_id"]]]
        else:
            expected = c.FACTORS_ALL_COUNTRIES[s]
        assert float(r["emission_factor"]) == expected


def test_grid_is_complete_from_each_site_opening(tables):
    """Every site reports every one of its sources every month from opening:
    a zero is written as 0, never left as a missing row."""
    months = [r["date_key"] for r in tables["dim_date"]]
    have = {(r["date_key"], r["site_id"], r["source_id"]) for r in tables["fact_emissions"]}
    have_metrics = {(r["date_key"], r["site_id"]) for r in tables["fact_site_metrics"]}
    for site_id, _n, _co, _t, first in c.SITES:
        first_key = first.strftime("%Y%m%d")
        for m in months:
            for source_id in c.BASE_ACTIVITY[site_id]:
                assert ((m, site_id, source_id) in have) == (m >= first_key)
            assert ((m, site_id) in have_metrics) == (m >= first_key)


def test_only_head_office_books_zero_revenue(tables):
    zero = {r["site_id"] for r in tables["fact_site_metrics"] if float(r["revenue_eur"]) == 0}
    assert zero == {"FI02"}
