# Emission factors (illustrative)

Fjordvik Manufacturing Oy is a fictional maker of electric pumps and pump systems
([company profile](../../docs/company-profile.md)).

**These factors are illustrative. They were chosen by hand to be a plausible order of
magnitude for a demonstration. They were not taken from any publication, have not been
checked against one, and must not be used for real reporting.**

For real reporting you would replace each one with a cited factor for the right year and
country, for example from a national inventory, a government conversion-factor set or a
residual mix publication, and record the source, year and version beside it.

The factor in each row of `fact_emissions` is in kilograms of carbon dioxide equivalent
(kg CO2e) per unit of activity, so:

```
tco2e = activity_amount × emission_factor / 1000
```

## Same factor in every country

| source_id | Source | Scope | Unit | kg CO2e per unit |
| --- | --- | --- | --- | --- |
| S01 | Natural gas | 1 | kWh | 0.200 |
| S02 | Diesel | 1 | litre | 2.700 |
| S03 | Liquefied petroleum gas (LPG) | 1 | litre | 1.600 |
| S04 | Refrigerant leakage | 1 | kg | 2000.000 |
| S07 | Business flights | 3 | passenger-km | 0.150 |
| S08 | Waste to landfill | 3 | tonne | 500.000 |

## Factor by country (location-based scope 2)

Location-based scope 2 uses the average emissions of the grid or heat network where the
site is, whatever contract the site buys. So the factor depends on the site's country.

| source_id | Source | Finland | Sweden | Estonia |
| --- | --- | --- | --- | --- |
| S05 | Purchased electricity (per kWh) | 0.080 | 0.020 | 0.600 |
| S06 | District heating (per kWh) | 0.150 | 0.050 | 0.250 |

## Value chain (added 31 October 2026)

The factors below are illustrative too. Each table names the published source a company
would cite for that factor, as identified in the project's research of 31 October 2026.
No value here was taken from those sources.

### Market-based scope 2 (`fact_scope2_market`)

Under the Greenhouse Gas (GHG) Protocol Scope 2 Guidance (2015), market-based scope 2
uses the factor of the contract a site buys under. Electricity covered by a renewable
guarantee of origin (GO) carries a zero generation factor; the rest uses the country's
residual mix, the grid mix left once GO-backed electricity is taken out.

| Instrument | Finland | Sweden | Estonia | Source a company would cite |
| --- | --- | --- | --- | --- |
| Guarantee of origin (renewable) | 0.000 | 0.000 | 0.000 | GHG Protocol Scope 2 Guidance (2015) |
| Residual mix (per kWh) | 0.350 | 0.300 | 0.650 | Association of Issuing Bodies (AIB) European Residual Mixes 2025; Energimarknadsinspektionen residual mix 2025 (Sweden); Elering (Estonia, published to 2023) |
| District heat, network declared value (per kWh) | 0.140 | 0.045 | 0.240 | Each network's declared value; Energiföretagen local values 2025 in Sweden |

Contracts: Gothenburg Plant buys hydro GOs for all its electricity from January 2023;
Tampere Plant buys wind GOs for 60% of its electricity from January 2025.

### Category 3, fuel- and energy-related activities (`fact_energy_upstream`)

| Part | Applies to | Finland | Sweden | Estonia | Source a company would cite |
| --- | --- | --- | --- | --- | --- |
| (a) Upstream of purchased fuels, well-to-tank | Natural gas (per kWh) | 0.030 | 0.030 | 0.030 | UK Department for Energy Security and Net Zero (DESNZ) conversion factors 2026; Joint Research Centre (JRC) 2019 fuel supply factors |
| (a) | Diesel (per litre) | 0.610 | 0.610 | 0.610 | As above |
| (a) | Liquefied petroleum gas (LPG) (per litre) | 0.190 | 0.190 | 0.190 | As above |
| (c) Transmission and distribution (T&D) losses | Electricity (per kWh) | 0.005 | 0.001 | 0.040 | DESNZ 2026 T&D factors (UK grid only: a company would need national loss data) |
| (c) | District heat (per kWh) | 0.010 | 0.003 | 0.020 | DESNZ 2026 heat distribution losses (UK only) |

Part (b), upstream of the fuels burnt to generate bought electricity and heat, is not
calculated: no source of these factors for Finland, Sweden or Estonia has been found.

### Category 1, purchased goods and services (`fact_purchases`, spend-based)

| Spend category | kg CO2e per euro | Source a company would cite |
| --- | --- | --- |
| Castings and steel | 1.20 | EXIOBASE 3, release 3.11.2 (check its dual licence before commercial use); alternative US Supply Chain GHG Emission Factors v1.4.0 (in US dollars) |
| Machined parts | 0.70 | As above |
| Motors and electronics | 0.45 | As above |
| Packaging | 0.60 | As above |
| Maintenance and facility services | 0.25 | As above |
| Professional services | 0.12 | As above |

A spend-based factor comes from an environmentally extended input-output model: it
counts the whole supply chain behind a euro spent, not one industry's direct emissions.

### Categories 4 and 9, freight (`fact_freight`, distance-based)

| Mode | kg CO2e per tonne-km | Source a company would cite |
| --- | --- | --- |
| Road | 0.100 | Global Logistics Emissions Council (GLEC) Framework v3.3; DESNZ 2026 freight factors |
| Rail | 0.025 | As above |
| Sea | 0.015 | As above |

## Simplifications

- One factor per source for the whole period. Real factors are updated each year.
- Refrigerant uses one factor for all leaks, as if every site used the same refrigerant.
- Spend-based category 1 is the least precise method; supplier-specific data should
  replace it for the largest suppliers.
- Freight uses one average distance per lane.

The values live in `src/fjordvik_data/config.py`; `tests/test_integrity.py` and
`tests/test_value_chain.py` check every row of the data against them.
