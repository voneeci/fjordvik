"""Unit tests of the generator's logic, independent of the random noise."""

from fjordvik_data import config as c
from fjordvik_data import generate as g


def electricity(rows, site_id):
    return {r["date_key"]: r["activity_amount"] for r in rows
            if r["site_id"] == site_id and r["source_id"] == "S05"}


def test_solar_reduces_purchases_by_exactly_the_solar_share(monkeypatch):
    """Each (site, source) has its own random stream, and solar draws no random
    numbers, so with and without solar the noise is identical. The ratio of the
    two runs is therefore exactly 1 minus the month's solar share."""
    shares = dict(c.SOLAR_SHARE_BY_MONTH)  # keep a copy before switching solar off
    with_solar = electricity(g.build_fact_emissions(), "FI01")
    monkeypatch.setattr(c, "SOLAR_SHARE_BY_MONTH", {m: 0.0 for m in range(1, 13)})
    without = electricity(g.build_fact_emissions(), "FI01")

    for key, amount in with_solar.items():
        month = key // 100 % 100  # date_key is a number here, e.g. 20240701
        expected = 1 - shares[month] if key >= 20240701 else 1.0
        if without[key] > 0:
            assert abs(amount / without[key] - expected) < 1e-4, key


def test_other_sites_are_untouched_by_the_solar_setting(monkeypatch):
    before = electricity(g.build_fact_emissions(), "SE01")
    monkeypatch.setattr(c, "SOLAR_SHARE_BY_MONTH", {m: 0.0 for m in range(1, 13)})
    assert electricity(g.build_fact_emissions(), "SE01") == before


def test_ramp_applies_only_to_sites_opening_mid_period():
    from datetime import date
    assert g.ramp(date(2023, 1, 1), date(2023, 1, 1)) == 1.0
    assert g.ramp(date(2024, 7, 1), date(2024, 7, 1)) == c.RAMP_UP[0]
    assert g.ramp(date(2024, 7, 1), date(2024, 10, 1)) == 1.0


def test_tco2e_formula():
    rows = g.build_fact_emissions()
    r = rows[0]
    assert r["tco2e"] == round(r["activity_amount"] * r["emission_factor"] / 1000, 6)
