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

# ===========================================================================
# Value chain: market-based scope 2 and scope 3 categories 1, 3, 4 and 9.
# Same rule as above: every factor here is ILLUSTRATIVE. Each block names the
# published source a company would cite instead (see docs/emission-factors.md).
# ===========================================================================

# Sources that come from company systems, not from the site workbooks.
# Same shape as SOURCES. S09 and S10 carry their parent source's unit.
VALUE_CHAIN_SOURCES = [
    ("S09", "Upstream emissions of purchased fuels", 3,
     "Fuel- and energy-related activities", "kWh or litre"),
    ("S10", "Transmission and distribution losses", 3,
     "Fuel- and energy-related activities", "kWh"),
    ("S11", "Purchased goods and services", 3, "Purchased goods and services", "EUR"),
    ("S12", "Freight paid by Fjordvik", 3,
     "Upstream transportation and distribution", "tonne-km"),
    ("S13", "Outbound freight paid by customers", 3,
     "Downstream transportation and distribution", "tonne-km"),
    ("S14", "Use of sold products", 3, "Use of sold products", "kWh"),
]

# GHG Protocol scope 3 category (None for scopes 1 and 2) and calculation
# method of each source. Method names follow the GHG Protocol Technical
# Guidance for Calculating Scope 3 Emissions (2013).
SOURCE_METHOD = {
    "S01": (None, "Fuel quantity times factor"),
    "S02": (None, "Fuel quantity times factor"),
    "S03": (None, "Fuel quantity times factor"),
    "S04": (None, "Refrigerant mass times factor"),
    "S05": (None, "Location-based: grid average factor"),
    "S06": (None, "Location-based: network average factor"),
    "S07": (6, "Distance-based"),
    "S08": (5, "Waste-type-specific"),
    "S09": (3, "Average-data: well-to-tank factors"),
    "S10": (3, "Average-data: transmission and distribution loss factors"),
    "S11": (1, "Spend-based"),
    "S12": (4, "Distance-based"),
    "S13": (9, "Distance-based"),
    "S14": (11, "Direct use-phase: lifetime electricity"),
}

# The 15 scope 3 categories with Fjordvik's status for each. The GHG Protocol
# Scope 3 Standard requires every excluded category to be listed with a reason.
SCOPE3_CATEGORIES = [
    (1, "Purchased goods and services", "Calculated",
     "Spend-based, from the purchase ledger. Supplier-specific data should replace the "
     "spend-based rows of the largest suppliers over time."),
    (2, "Capital goods", "Not yet calculated",
     "Relevant: needs capital spend by asset type from the fixed asset register, counted "
     "in full in the year bought. Planned after categories 1, 3, 4 and 9."),
    (3, "Fuel- and energy-related activities", "Calculated in part",
     "Parts (a), upstream of purchased fuels, and (c), transmission and distribution "
     "losses, are calculated from the fuel and kWh already reported. Part (b), upstream "
     "of the fuels burnt to generate bought electricity and heat, is not calculated: no "
     "source of these factors for Finland, Sweden or Estonia has been found. Part (d) "
     "applies only to companies that resell energy."),
    (4, "Upstream transportation and distribution", "Calculated",
     "Distance-based (tonne-km) for all inbound freight and the outbound freight Fjordvik "
     "pays for. No third-party warehouses: Fjordvik's own warehouses are in scopes 1 and 2."),
    (5, "Waste generated in operations", "Calculated in part",
     "Waste to landfill only. Recycling, incineration and hazardous waste need rows by "
     "waste type and treatment from the waste contractors' reports."),
    (6, "Business travel", "Calculated in part",
     "Flights only. Rail, hire cars, private cars and hotel nights need the travel "
     "agency's report and expense claims."),
    (7, "Employee commuting", "Not yet calculated",
     "Relevant but likely small: needs a yearly staff survey of distance, mode and days."),
    (8, "Upstream leased assets", "Not relevant",
     "Fjordvik leases no assets beyond its six sites, which are already in scopes 1 and 2."),
    (9, "Downstream transportation and distribution", "Calculated",
     "Distance-based (tonne-km) for outbound freight that customers pay for, identified "
     "from the Incoterms on sales orders."),
    (10, "Processing of sold products", "Not relevant",
     "Fjordvik sells finished pumps and pump systems, which customers install rather "
     "than process further."),
    (11, "Use of sold products", "Calculated in part",
     "The largest category: units sold times each model's lifetime and yearly electricity, "
     "at the grid factor of the region of use. Sales to Rest of world are not calculated: no "
     "grid factor source for that region has been identified."),
    (12, "End-of-life treatment of sold products", "Not yet calculated",
     "Relevant but usually small: needs the mass and materials of products and packaging "
     "sold, from the bill of materials."),
    (13, "Downstream leased assets", "Not relevant", "Fjordvik does not lease out assets."),
    (14, "Franchises", "Not relevant", "Fjordvik has no franchises."),
    (15, "Investments", "Not relevant",
     "Fjordvik holds no equity stakes, debt investments or project finance."),
]

# ---------------------------------------------------------------------------
# Market-based scope 2. Named sources: AIB European Residual Mixes 2025 (FI, SE,
# EE); Energimarknadsinspektionen residual mix 2025 (Sweden); Elering (Estonia);
# for heat, each network's declared value (Energiföretagen local values 2025 in
# Sweden). A guarantee of origin (GO) for renewable electricity carries a zero
# generation factor under the GHG Protocol Scope 2 Guidance (2015).
# ---------------------------------------------------------------------------
# (contract_id, site_id, source_id, supplier_name, instrument, start, end, covered_share)
CONTRACTS = [
    ("C01", "SE01", "S05", "Electricity supplier SE-1 (synthetic)",
     "Guarantee of origin (hydro)", date(2023, 1, 1), date(2027, 12, 1), 1.00),
    ("C02", "FI01", "S05", "Electricity supplier FI-1 (synthetic)",
     "Guarantee of origin (wind)", date(2025, 1, 1), date(2027, 12, 1), 0.60),
]
GO_FACTOR = 0.0  # per kWh covered by a renewable GO
RESIDUAL_MIX_FACTOR = {"Finland": 0.350, "Sweden": 0.300, "Estonia": 0.650}  # per kWh
HEAT_NETWORK_FACTOR = {"Finland": 0.140, "Sweden": 0.045, "Estonia": 0.240}  # per kWh

# ---------------------------------------------------------------------------
# Category 3. Named sources: UK Department for Energy Security and Net Zero
# (DESNZ) conversion factors 2026, well-to-tank and transmission and
# distribution (T&D); Joint Research Centre (JRC) 2019 fuel supply factors.
# DESNZ T&D factors are for the UK grid; a company would need national loss
# data for Finland, Sweden and Estonia.
# ---------------------------------------------------------------------------
WTT_FACTOR = {"S01": 0.030, "S02": 0.610, "S03": 0.190}  # per kWh or litre
TD_FACTOR = {  # per kWh bought
    "S05": {"Finland": 0.005, "Sweden": 0.001, "Estonia": 0.040},
    "S06": {"Finland": 0.010, "Sweden": 0.003, "Estonia": 0.020},
}

# ---------------------------------------------------------------------------
# Category 1, spend-based, from the purchase ledger. Named source: EXIOBASE 3
# release 3.11.2 (check its licence); alternative US Supply Chain GHG Emission
# Factors v1.4.0 (in US dollars). Factors in kg CO2e per euro spent.
# ---------------------------------------------------------------------------
SPEND_FACTOR = {
    "Castings and steel": 1.20,
    "Machined parts": 0.70,
    "Motors and electronics": 0.45,
    "Packaging": 0.60,
    "Maintenance and facility services": 0.25,
    "Professional services": 0.12,
}
# (supplier_id, supplier_name, country, spend_category). Names are synthetic.
SUPPLIERS = [
    ("SUP01", "Castings supplier FI-1", "Finland", "Castings and steel"),
    ("SUP02", "Castings supplier SE-1", "Sweden", "Castings and steel"),
    ("SUP03", "Castings supplier EE-1", "Estonia", "Castings and steel"),
    ("SUP04", "Machining supplier FI-1", "Finland", "Machined parts"),
    ("SUP05", "Machining supplier SE-1", "Sweden", "Machined parts"),
    ("SUP06", "Motor supplier DE-1", "Germany", "Motors and electronics"),
    ("SUP07", "Electronics supplier EE-1", "Estonia", "Motors and electronics"),
    ("SUP08", "Packaging supplier FI-1", "Finland", "Packaging"),
    ("SUP09", "Packaging supplier SE-1", "Sweden", "Packaging"),
    ("SUP10", "Packaging supplier EE-1", "Estonia", "Packaging"),
    ("SUP11", "Facility services supplier FI-1", "Finland", "Maintenance and facility services"),
    ("SUP12", "Facility services supplier SE-1", "Sweden", "Maintenance and facility services"),
    ("SUP13", "Facility services supplier EE-1", "Estonia", "Maintenance and facility services"),
    ("SUP14", "Professional services supplier FI-1", "Finland", "Professional services"),
]
# Typical monthly spend in euros by site and supplier, before growth and noise.
# Goods follow production (growth, July slowdown); services do not.
BASE_SPEND_EUR = {
    "FI01": {"SUP01": 690_000, "SUP04": 460_000, "SUP06": 690_000, "SUP08": 115_000,
             "SUP11": 185_000, "SUP14": 160_000},
    "FI02": {"SUP11": 40_000, "SUP14": 300_000},
    "FI03": {"SUP08": 15_000, "SUP11": 20_000},
    "SE01": {"SUP02": 560_000, "SUP05": 375_000, "SUP06": 560_000, "SUP09": 95_000,
             "SUP12": 150_000, "SUP14": 130_000},
    "EE01": {"SUP03": 460_000, "SUP04": 310_000, "SUP06": 230_000, "SUP07": 230_000,
             "SUP10": 75_000, "SUP13": 125_000, "SUP14": 105_000},
    "EE02": {"SUP10": 12_000, "SUP13": 15_000},
}
SERVICE_CATEGORIES = {"Maintenance and facility services", "Professional services"}

# ---------------------------------------------------------------------------
# Categories 4 and 9, distance-based, from freight invoices and the transport
# management system. Named sources: Global Logistics Emissions Council (GLEC)
# Framework v3.3; DESNZ 2026 freight factors. kg CO2e per tonne-km.
# Inbound freight is category 4 whoever pays. Outbound freight is category 4
# when Fjordvik pays and category 9 when the customer pays (Incoterms).
# ---------------------------------------------------------------------------
FREIGHT_FACTOR = {"Road": 0.100, "Rail": 0.025, "Sea": 0.015}
# (direction, mode, paid_by, typical tonnes per month, average distance in km)
FREIGHT_LANES = {
    "FI01": [("Inbound", "Road", "Fjordvik", 900, 450), ("Inbound", "Sea", "Supplier", 300, 1600),
             ("Outbound", "Road", "Fjordvik", 500, 600), ("Outbound", "Sea", "Customer", 250, 2500),
             ("Outbound", "Road", "Customer", 150, 900)],
    "FI03": [("Inbound", "Road", "Fjordvik", 80, 500), ("Outbound", "Road", "Fjordvik", 70, 450),
             ("Outbound", "Road", "Customer", 20, 700)],
    "SE01": [("Inbound", "Road", "Fjordvik", 700, 400), ("Inbound", "Sea", "Supplier", 250, 1200),
             ("Outbound", "Road", "Fjordvik", 350, 550), ("Outbound", "Rail", "Fjordvik", 200, 800),
             ("Outbound", "Road", "Customer", 180, 1000)],
    "EE01": [("Inbound", "Road", "Fjordvik", 650, 500), ("Inbound", "Sea", "Supplier", 200, 1100),
             ("Outbound", "Road", "Fjordvik", 300, 700), ("Outbound", "Sea", "Customer", 220, 1800)],
    "EE02": [("Inbound", "Road", "Fjordvik", 60, 200), ("Outbound", "Road", "Fjordvik", 55, 400),
             ("Outbound", "Road", "Customer", 15, 600)],
}

# ===========================================================================
# Product portfolio and sales (phase 2). All synthetic. Sales split each
# site-month's revenue_eur exactly, so sales and finance agree to the cent.
# Product specifications (rated kW, yearly kWh, lifetime) are Fjordvik's own
# engineering data: client input, not published figures.
# ===========================================================================

# (product_group, product_family)
PRODUCT_GROUPS = [
    ("End-suction pumps", "Industrial process pumps"),
    ("Split-case pumps", "Industrial process pumps"),
    ("Multistage pumps", "Industrial process pumps"),
    ("Submersible pumps", "Water and wastewater pumps"),
    ("Dry-installed pumps", "Water and wastewater pumps"),
    ("Booster sets", "Pump packages and controls"),
    ("Control panels", "Pump packages and controls"),
    ("Drive packages", "Pump packages and controls"),
    ("Spare parts", "Spare parts and service"),
    ("Service kits", "Spare parts and service"),
]

# (product_id, product_name, product_group, made_at, rated_kw, kwh_per_year,
#  lifetime_years, list_price_eur, standard_cost_eur, mix_weight, mix_trend)
# kwh_per_year is the expected yearly use in service, below rated power times
# running hours because pumps run part-loaded (lowered by 40% on 31 October 2026,
# Reece's decision, so category 11 sits nearer the planned scale).
# mix_weight: share of the shipping site's sales value; mix_trend: change in
# that weight per year, which gives the price/volume/mix bridge a mix to find.
PRODUCTS = [
    ("IPP-ES-015", "End-suction pump 15 kW", "End-suction pumps", "FI01", 15, 32_400, 15, 6_800, 4_350, 0.16, 0.00),
    ("IPP-ES-030", "End-suction pump 30 kW", "End-suction pumps", "FI01", 30, 64_800, 15, 9_400, 6_000, 0.14, 0.00),
    ("IPP-ES-055", "End-suction pump 55 kW", "End-suction pumps", "FI01", 55, 118_800, 15, 13_900, 8_800, 0.10, -0.01),
    ("IPP-SC-075", "Split-case pump 75 kW", "Split-case pumps", "FI01", 75, 180_000, 20, 21_500, 13_100, 0.12, 0.00),
    ("IPP-SC-160", "Split-case pump 160 kW", "Split-case pumps", "FI01", 160, 384_000, 20, 38_000, 22_400, 0.08, 0.00),
    ("IPP-MS-011", "Multistage pump 11 kW", "Multistage pumps", "FI01", 11, 23_800, 15, 5_200, 3_050, 0.14, 0.02),
    ("IPP-MS-022", "Multistage pump 22 kW", "Multistage pumps", "FI01", 22, 47_500, 15, 7_900, 4_600, 0.16, 0.02),
    ("IPP-MS-045", "Multistage pump 45 kW", "Multistage pumps", "FI01", 45, 97_200, 15, 12_600, 7_250, 0.10, -0.03),
    ("WWP-SB-004", "Submersible pump 4 kW", "Submersible pumps", "SE01", 4, 6_000, 12, 2_300, 1_480, 0.14, 0.00),
    ("WWP-SB-011", "Submersible pump 11 kW", "Submersible pumps", "SE01", 11, 16_500, 12, 4_600, 2_900, 0.18, 0.02),
    ("WWP-SB-022", "Submersible pump 22 kW", "Submersible pumps", "SE01", 22, 33_000, 12, 7_800, 4_850, 0.16, 0.01),
    ("WWP-SB-045", "Submersible pump 45 kW", "Submersible pumps", "SE01", 45, 67_500, 12, 13_200, 8_100, 0.12, 0.00),
    ("WWP-DI-015", "Dry-installed pump 15 kW", "Dry-installed pumps", "SE01", 15, 31_500, 20, 6_400, 4_050, 0.14, -0.01),
    ("WWP-DI-037", "Dry-installed pump 37 kW", "Dry-installed pumps", "SE01", 37, 77_700, 20, 11_800, 7_300, 0.14, -0.01),
    ("WWP-DI-075", "Dry-installed pump 75 kW", "Dry-installed pumps", "SE01", 75, 157_500, 20, 19_900, 12_100, 0.12, -0.01),
    ("PPC-BS-022", "Booster set 2 x 11 kW", "Booster sets", "EE01", 22, 26_400, 15, 9_800, 6_500, 0.20, 0.02),
    ("PPC-BS-045", "Booster set 3 x 15 kW", "Booster sets", "EE01", 45, 54_000, 15, 16_500, 10_800, 0.16, 0.01),
    ("PPC-BS-090", "Booster set 3 x 30 kW", "Booster sets", "EE01", 90, 108_000, 15, 27_000, 17_400, 0.10, 0.00),
    ("PPC-CP-001", "Pump control panel, single", "Control panels", "EE01", 0, 0, 15, 1_900, 1_150, 0.14, -0.01),
    ("PPC-CP-002", "Pump control panel, duty and standby", "Control panels", "EE01", 0, 0, 15, 3_400, 2_050, 0.12, -0.01),
    ("PPC-VD-030", "Variable-speed drive package 30 kW", "Drive packages", "EE01", 0, 0, 15, 5_600, 3_700, 0.16, 0.00),
    ("PPC-VD-075", "Variable-speed drive package 75 kW", "Drive packages", "EE01", 0, 0, 15, 9_900, 6_400, 0.12, -0.01),
    ("SPS-SP-100", "Spare parts (mixed)", "Spare parts", "FI01", 0, 0, 0, 140, 70, 0.70, 0.00),
    ("SPS-SK-200", "Service kit", "Service kits", "FI01", 0, 0, 0, 620, 330, 0.30, 0.00),
]
# The family each site ships: plants ship what they make; the warehouses ship
# spare parts and service kits.
SITE_FAMILY = {"FI01": "Industrial process pumps", "SE01": "Water and wastewater pumps",
               "EE01": "Pump packages and controls", "FI03": "Spare parts and service",
               "EE02": "Spare parts and service"}
ANNUAL_PRICE_CHANGE = {"Industrial process pumps": 0.035, "Water and wastewater pumps": 0.02,
                       "Pump packages and controls": 0.045, "Spare parts and service": 0.03}
ANNUAL_COST_CHANGE = 0.025
PRICE_NOISE = 0.02

# (region_id, region_name, customer region code in the ERP)
REGIONS = [("NOR", "Nordics", "NORDIC"), ("BAL", "Baltics", "BALTIC"),
           ("WEU", "Western Europe", "WEST-EU"), ("ROW", "Rest of world", "OTHER")]
REGION_SPLIT = {
    "FI01": {"NOR": 0.40, "BAL": 0.10, "WEU": 0.35, "ROW": 0.15},
    "SE01": {"NOR": 0.50, "BAL": 0.05, "WEU": 0.30, "ROW": 0.15},
    "EE01": {"NOR": 0.30, "BAL": 0.30, "WEU": 0.30, "ROW": 0.10},
    "FI03": {"NOR": 0.90, "BAL": 0.10},
    "EE02": {"NOR": 0.20, "BAL": 0.80},
}

# ---------------------------------------------------------------------------
# The simulated Oracle Fusion Cloud ERP extract: business units, their ledger
# currency, and the local item numbers each uses. Gothenburg's business unit
# still uses its legacy item numbers, mapped to the global classification.
# ---------------------------------------------------------------------------
# (business_unit, site_id, ledger_currency)
BUSINESS_UNITS = [("FJV FI Tampere", "FI01", "EUR"), ("FJV SE Gothenburg", "SE01", "SEK"),
                  ("FJV EE Tallinn", "EE01", "EUR"), ("FJV FI Oulu", "FI03", "EUR"),
                  ("FJV EE Tartu", "EE02", "EUR")]
LEGACY_ITEM_NUMBERS = {  # SE01 local item numbers
    "WWP-SB-004": "GBG-40411", "WWP-SB-011": "GBG-41111", "WWP-SB-022": "GBG-42211",
    "WWP-SB-045": "GBG-44511", "WWP-DI-015": "GBG-51522", "WWP-DI-037": "GBG-53722",
    "WWP-DI-075": "GBG-57522",
}
# Planted extract problems, realistic artefacts the SQL must catch and log:
# new local codes not yet in the map (month, business unit, code, the product it
# is, the region whose lines carry it); one extract re-sent (arrives in, business
# unit, period it repeats); one month with no currency code.
UNMAPPED_CODES = [(date(2025, 6, 1), "FJV EE Tallinn", "EE-BS-NEW1", "PPC-BS-045", "BAL"),
                  (date(2025, 11, 1), "FJV EE Tallinn", "EE-VD-NEW2", "PPC-VD-030", "BAL")]
RESENT_EXTRACT = (date(2024, 9, 1), "FJV FI Tampere", date(2024, 8, 1))
MISSING_CURRENCY = (date(2025, 3, 1), "FJV SE Gothenburg")

# ---------------------------------------------------------------------------
# Category 11, use of sold products: units x lifetime years x yearly kWh x the
# grid factor of the region of use (GHG Protocol direct use-phase method).
# ILLUSTRATIVE factors, kg CO2e per kWh. Source a company would cite: the
# European Environment Agency (EEA) greenhouse gas emission intensity of
# electricity indicator (published 10 July 2026). Rest of world has no factor
# source identified, so it is not calculated: no row, never an estimate.
# ---------------------------------------------------------------------------
USE_PHASE_GRID_FACTOR = {"NOR": 0.060, "BAL": 0.400, "WEU": 0.250}

# ---------------------------------------------------------------------------
# Sales plan (budget), Fjordvik's own input (synthetic). Each family's plan for a
# year, as how far the actuals ended up from it: +0.04 means actual net sales were
# 4% above plan. Margin has its own variance, because price and cost move apart
# from volume. Monthly timing differences between plan and actual are seeded noise
# of PLAN_MONTHLY_NOISE (standard deviation, as a share). The budget table is the
# plan; actuals stay as they are.
# ---------------------------------------------------------------------------
PLAN_SALES_VARIANCE = {
    "Industrial process pumps": {2023: 0.02, 2024: -0.03, 2025: 0.04},
    "Water and wastewater pumps": {2023: -0.01, 2024: 0.02, 2025: -0.02},
    "Pump packages and controls": {2023: 0.03, 2024: 0.01, 2025: -0.05},
    "Spare parts and service": {2023: -0.02, 2024: -0.01, 2025: 0.03},
}
PLAN_MARGIN_VARIANCE = {
    "Industrial process pumps": {2023: 0.01, 2024: -0.05, 2025: 0.06},
    "Water and wastewater pumps": {2023: -0.03, 2024: 0.01, 2025: -0.04},
    "Pump packages and controls": {2023: 0.02, 2024: -0.01, 2025: -0.07},
    "Spare parts and service": {2023: 0.00, 2024: 0.02, 2025: 0.05},
}
PLAN_MONTHLY_NOISE = 0.03

# ---------------------------------------------------------------------------
# Quarterly portfolio scorecard. Criteria from Cooper and Edgett (Stage-Gate
# International, 2022). No source publishes weights, so these are Fjordvik's
# own stated choice (client input). Ratings 1 to 10 come from each quarter's
# portfolio review (synthetic).
# ---------------------------------------------------------------------------
SCORE_CRITERIA = [("C1", "Strategic alignment", 25), ("C2", "Product advantage", 20),
                  ("C3", "Market attractiveness", 20),
                  ("C4", "Ability to leverage core competencies", 10),
                  ("C5", "Technical feasibility", 10), ("C6", "Reward against risk", 15)]
# Typical rating of each product group before quarter-to-quarter movement.
BASE_RATING = {"End-suction pumps": 6, "Split-case pumps": 7, "Multistage pumps": 8,
               "Submersible pumps": 7, "Dry-installed pumps": 5, "Booster sets": 8,
               "Control panels": 5, "Drive packages": 6, "Spare parts": 7, "Service kits": 6}
