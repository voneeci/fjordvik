# Emission factors (illustrative)

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

## Simplifications

- One factor per source for the whole period. Real factors are updated each year.
- Only location-based scope 2. A market-based figure (which reflects renewable contracts)
  would need a second factor per row, and the shared schema has one.
- Refrigerant uses one factor for all leaks, as if every site used the same refrigerant.

The values live in `src/fjordvik_data/config.py`, and `tests/test_integrity.py` checks
every row of the data against them.
