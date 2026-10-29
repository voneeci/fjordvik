"""Everything that shapes the Fjordvik dataset, in one place.

All numbers here are synthetic. The emission factors are ILLUSTRATIVE: chosen by
hand to be a plausible order of magnitude, not taken from any publication, and not
for real reporting. See docs/emission-factors.md.
"""

from datetime import date

SEED = 20230101

FIRST_MONTH = date(2023, 1, 1)
MONTH_COUNT = 36  # January 2023 to December 2025

# ---------------------------------------------------------------------------
# Sites: (site_id, site_name, country, site_type, first_month)
# A site reports from its first month only. Nothing is backfilled before it.
# ---------------------------------------------------------------------------
SITES = [
    ("FI01", "Tampere Plant", "Finland", "Manufacturing plant", date(2023, 1, 1)),
    ("FI02", "Helsinki Head Office", "Finland", "Office", date(2023, 1, 1)),
    ("FI03", "Oulu Warehouse", "Finland", "Warehouse", date(2023, 1, 1)),
    ("SE01", "Gothenburg Plant", "Sweden", "Manufacturing plant", date(2023, 1, 1)),
    ("EE01", "Tallinn Plant", "Estonia", "Manufacturing plant", date(2023, 1, 1)),
    ("EE02", "Tartu Warehouse", "Estonia", "Warehouse", date(2024, 7, 1)),
]

# ---------------------------------------------------------------------------
# Sources: (source_id, source_name, scope, category, unit)
# ---------------------------------------------------------------------------
SOURCES = [
    ("S01", "Natural gas", 1, "Stationary combustion", "kWh"),
    ("S02", "Diesel", 1, "Mobile combustion", "litre"),
    ("S03", "Liquefied petroleum gas (LPG)", 1, "Mobile combustion", "litre"),
    ("S04", "Refrigerant leakage", 1, "Fugitive emissions", "kg"),
    ("S05", "Purchased electricity", 2, "Purchased electricity", "kWh"),
    ("S06", "District heating", 2, "Purchased heat", "kWh"),
    ("S07", "Business flights", 3, "Business travel", "passenger-km"),
    ("S08", "Waste to landfill", 3, "Waste generated in operations", "tonne"),
]

# ---------------------------------------------------------------------------
# ILLUSTRATIVE emission factors, in kilograms of CO2 equivalent per unit.
# tco2e = activity_amount * emission_factor / 1000
# Grid electricity and district heating vary by country (location-based).
# The same factor is used in every year: a simplification, see the README.
# ---------------------------------------------------------------------------
FACTORS_ALL_COUNTRIES = {
    "S01": 0.20,    # per kWh
    "S02": 2.70,    # per litre
    "S03": 1.60,    # per litre
    "S04": 2000.0,  # per kg
    "S07": 0.15,    # per passenger-km
    "S08": 500.0,   # per tonne
}
FACTORS_BY_COUNTRY = {
    "S05": {"Finland": 0.080, "Sweden": 0.020, "Estonia": 0.600},  # per kWh
    "S06": {"Finland": 0.150, "Sweden": 0.050, "Estonia": 0.250},  # per kWh
}

# ---------------------------------------------------------------------------
# Typical monthly activity per site, before seasonality, growth and noise.
# A source missing from a site's dict is not used at that site (no rows).
# ---------------------------------------------------------------------------
BASE_ACTIVITY = {
    "FI01": {"S01": 420_000, "S02": 3_000, "S03": 1_200, "S04": 4.0,
             "S05": 650_000, "S06": 180_000, "S07": 45_000, "S08": 14.0},
    "FI02": {"S04": 1.5, "S05": 60_000, "S06": 70_000, "S07": 120_000, "S08": 1.5},
    "FI03": {"S02": 6_000, "S03": 900, "S04": 1.0,
             "S05": 90_000, "S06": 60_000, "S07": 8_000, "S08": 4.0},
    "SE01": {"S01": 300_000, "S02": 2_500, "S03": 1_000, "S04": 3.0,
             "S05": 520_000, "S06": 150_000, "S07": 40_000, "S08": 11.0},
    "EE01": {"S01": 360_000, "S02": 3_500, "S03": 1_100, "S04": 3.5,
             "S05": 480_000, "S06": 120_000, "S07": 30_000, "S08": 16.0},
    "EE02": {"S02": 5_000, "S03": 700, "S04": 0.8,
             "S05": 70_000, "S06": 40_000, "S07": 5_000, "S08": 3.0},
}

# Sources whose activity follows production volume, so they grow with output.
PRODUCTION_LINKED = {"S01", "S02", "S03", "S05", "S08"}

# Heating sources peak in January and dip in July. Value = swing either side of 1.
SEASONAL_SWING = {"S01": 0.35, "S06": 0.55, "S05": 0.08}

# Finnish, Swedish and Estonian factories often slow down for summer holidays.
# Production-linked activity and plant revenue fall in July by this factor.
SUMMER_SHUTDOWN_FACTOR = {7: 0.7}

# Business flights dip in July (holidays) and December.
FLIGHT_MONTH_FACTOR = {7: 0.35, 12: 0.6}

# Refrigerant: leaks are found and topped up only some months.
# Probability that a site records a top-up in a given month.
REFRIGERANT_TOPUP_CHANCE = 0.25

ANNUAL_OUTPUT_GROWTH = 0.04   # production volume, per year
ANNUAL_REVENUE_GROWTH = 0.05  # revenue, per year, before noise
NOISE = 0.05                  # standard deviation of month-to-month noise

# A new site ramps up over its first months (share of full activity).
RAMP_UP = [0.4, 0.7, 0.9]

# ---------------------------------------------------------------------------
# Story event: rooftop solar at Tampere Plant from July 2024.
# Share of the site's electricity demand met by its own panels, by calendar
# month. Finnish winters give almost nothing; June gives the most.
# Purchased electricity = demand * (1 - share).
# ---------------------------------------------------------------------------
SOLAR_SITE = "FI01"
SOLAR_FIRST_MONTH = date(2024, 7, 1)
SOLAR_SHARE_BY_MONTH = {
    1: 0.00, 2: 0.02, 3: 0.06, 4: 0.12, 5: 0.17, 6: 0.19,
    7: 0.18, 8: 0.14, 9: 0.08, 10: 0.03, 11: 0.01, 12: 0.00,
}

# ---------------------------------------------------------------------------
# Site metrics: typical monthly revenue (EUR) and full-time equivalents (FTE).
# The head office books no revenue of its own (revenue is booked at the sites
# that make and ship goods), so its revenue is 0. Intensity per euro is blank
# for it, which the Power BI model must handle (DIVIDE, not "/").
# ---------------------------------------------------------------------------
BASE_REVENUE_EUR = {
    "FI01": 4_200_000, "FI02": 0, "FI03": 900_000,
    "SE01": 3_400_000, "EE01": 2_800_000, "EE02": 600_000,
}
BASE_FTE = {
    "FI01": 210.0, "FI02": 85.0, "FI03": 40.0,
    "SE01": 165.0, "EE01": 190.0, "EE02": 28.0,
}
ANNUAL_FTE_GROWTH = 0.02
