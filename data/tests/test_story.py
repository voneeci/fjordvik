"""The planned story events are present, so the dashboards have something to find."""

from collections import defaultdict


def monthly(tables, site_id, source_id):
    return {r["date_key"]: float(r["activity_amount"])
            for r in tables["fact_emissions"]
            if r["site_id"] == site_id and r["source_id"] == source_id}


def window(series, year, months):
    return sum(series[f"{year}{m:02d}01"] for m in months)


def test_solar_cuts_tampere_summer_electricity_against_a_control_site(tables):
    """Compare Tampere (solar from July 2024) with Gothenburg (no solar).
    Both grow at the same rate, so growth and noise cancel out in the ratio of
    ratios. Solar should leave Tampere's April to August purchases clearly lower.
    Measured: 0.755 with solar, 0.897 with solar switched off (noise alone), so
    0.85 separates the two. The exact effect is tested in test_generator.py."""
    summer = [4, 5, 6, 7, 8]
    tampere = monthly(tables, "FI01", "S05")
    gothenburg = monthly(tables, "SE01", "S05")
    t_change = window(tampere, 2025, summer) / window(tampere, 2023, summer)
    g_change = window(gothenburg, 2025, summer) / window(gothenburg, 2023, summer)
    assert t_change / g_change < 0.85


def test_solar_does_little_in_winter(tables):
    winter = [1, 12]
    tampere = monthly(tables, "FI01", "S05")
    gothenburg = monthly(tables, "SE01", "S05")
    t_change = window(tampere, 2025, winter) / window(tampere, 2023, winter)
    g_change = window(gothenburg, 2025, winter) / window(gothenburg, 2023, winter)
    assert 0.9 < t_change / g_change < 1.1


def test_tartu_warehouse_starts_in_july_2024(tables):
    keys = sorted({r["date_key"] for r in tables["fact_emissions"] if r["site_id"] == "EE02"})
    assert keys[0] == "20240701"
    assert len(keys) == 18


def test_district_heating_peaks_in_winter(tables):
    for site_id in ["FI01", "FI02", "FI03", "SE01", "EE01"]:
        heat = monthly(tables, site_id, "S06")
        for year in (2023, 2024, 2025):
            assert heat[f"{year}0101"] > 2 * heat[f"{year}0701"], (site_id, year)


def test_revenue_grows_year_on_year_for_sites_open_all_period(tables):
    totals = defaultdict(float)
    for r in tables["fact_site_metrics"]:
        if r["site_id"] != "EE02":
            totals[r["date_key"][:4]] += float(r["revenue_eur"])
    assert totals["2023"] < totals["2024"] < totals["2025"]
