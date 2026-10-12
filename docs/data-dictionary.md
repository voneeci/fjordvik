# Data dictionary

Generated from the model by `scripts/build_data_dictionary.py`. Do not edit by hand.
Emission factors in this model are illustrative, not for real reporting.

## Measures

Every measure lives in the `_Measures` table, grouped by display folder.

### Emissions

**Total Emissions (tCO2e)**: Tonnes of CO2 equivalent across all scopes, from the stored tco2e column. Format: `#,0.0`.

```dax
SUM ( fact_emissions[tco2e] )
```

**Scope 1 Emissions (tCO2e)**: Scope 1. Direct emissions: fuels burned on site and refrigerant leaks. KEEPFILTERS means a slicer on another scope gives blank, not this scope's total. Format: `#,0.0`.

```dax
CALCULATE ( [Total Emissions (tCO2e)], KEEPFILTERS ( dim_source[scope] = 1 ) )
```

**Scope 2 Emissions (tCO2e)**: Scope 2. Purchased electricity and heat, location-based. KEEPFILTERS means a slicer on another scope gives blank, not this scope's total. Format: `#,0.0`.

```dax
CALCULATE ( [Total Emissions (tCO2e)], KEEPFILTERS ( dim_source[scope] = 2 ) )
```

**Scope 3 Emissions (tCO2e)**: Scope 3. Business flights and waste to landfill. KEEPFILTERS means a slicer on another scope gives blank, not this scope's total. Format: `#,0.0`.

```dax
CALCULATE ( [Total Emissions (tCO2e)], KEEPFILTERS ( dim_source[scope] = 3 ) )
```

### Intensity

**Revenue (EUR)**: Revenue in euros. A flow: it adds up over months. Format: `#,0`.

```dax
SUM ( fact_site_metrics[revenue_eur] )
```

**Average FTE**: Full-time equivalent employees. A level, not a flow: summed across sites within each month, then averaged over the months. Format: `#,0.0`.

```dax
AVERAGEX ( VALUES ( dim_date[date_key] ), CALCULATE ( SUM ( fact_site_metrics[fte] ) ) )
```

**Emissions per FTE (tCO2e)**: Total emissions divided by average FTE for the selected period. Format: `#,0.00`.

```dax
DIVIDE ( [Total Emissions (tCO2e)], [Average FTE] )
```

**Emissions per Million EUR (tCO2e)**: Total emissions per million euros of revenue (1,000,000 converts euros to millions). Blank where there is no revenue, such as the head office. Format: `#,0.0`.

```dax
DIVIDE ( [Total Emissions (tCO2e)], DIVIDE ( [Revenue (EUR)], 1000000 ) )
```

### Time comparison

**Emissions Prior Year (tCO2e)**: Emissions for the same months one year earlier. dim_date has one row per month, so it can't be marked as a date table and SAMEPERIODLASTYEAR doesn't apply; this shifts each month key back a year instead (20250301 to 20240301). Format: `#,0.0`.

```dax
VAR PriorKeys =
	SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
RETURN
	CALCULATE ( [Total Emissions (tCO2e)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
```

**Emissions Change vs Prior Year (%)**: Like-for-like change against the same months a year earlier: only site-months with emissions in both years count, so a site that opened partway through (Tartu, July 2024) or months with no prior year (2023) don't inflate the change. Shown as a percentage; blank when nothing is comparable. Format: `0.0%`.

```dax
VAR Comparable =
	FILTER (
		CROSSJOIN ( VALUES ( dim_site[site_id] ), VALUES ( dim_date[date_key] ) ),
		NOT ISBLANK ( CALCULATE ( [Total Emissions (tCO2e)] ) )
			&& NOT ISBLANK ( CALCULATE ( [Emissions Prior Year (tCO2e)] ) )
	)
VAR CurrentYear = SUMX ( Comparable, CALCULATE ( [Total Emissions (tCO2e)] ) )
VAR PriorYear = SUMX ( Comparable, CALCULATE ( [Emissions Prior Year (tCO2e)] ) )
RETURN
	DIVIDE ( CurrentYear - PriorYear, PriorYear )
```

### Data quality

**Recalculated Emissions (tCO2e)**: Emissions worked out again row by row: activity times factor, divided by 1,000 to turn kilograms into tonnes. Format: `#,0.0`.

```dax
SUMX ( fact_emissions, fact_emissions[activity_amount] * fact_emissions[emission_factor] / 1000 )
```

**Reconciliation Difference (tCO2e)**: Stored minus recalculated emissions, rounded to 0.001 t (1 kg): the stored values carry 6 decimals, so adding 1,422 of them leaves a few grams of rounding. Anything that survives the rounding means a row's tco2e doesn't match its activity and factor. Format: `#,0.000`.

```dax
ROUND ( [Total Emissions (tCO2e)] - [Recalculated Emissions (tCO2e)], 3 )
```

**Emission Rows**: Number of emission rows in the current filter. Format: `#,0`.

```dax
COUNTROWS ( fact_emissions )
```

**Sites Reporting**: Number of sites with at least one emission row in the current filter. Format: `#,0`.

```dax
DISTINCTCOUNT ( fact_emissions[site_id] )
```

## Tables

### dim_date

One row per month, January 2023 to December 2025. Monthly grain, so it is not marked as a date table (that needs every day).

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| date_key | int64 | 0 |  | First day of the month as a number, for example 20240701. |
| date | dateTime | mmm yyyy |  | First day of the month. |
| year | int64 | 0 |  |  |
| quarter | int64 | 0 |  |  |
| month | int64 | 0 |  |  |
| month_name | string |  |  |  |

### dim_site

The six sites. Row-level security filters this table by country.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| site_id | string |  |  |  |
| site_name | string |  |  |  |
| country | string |  |  |  |
| site_type | string |  |  |  |

### dim_source

The eight emission sources, with their Greenhouse Gas Protocol scope.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| source_id | string |  |  |  |
| source_name | string |  |  |  |
| scope | int64 | 0 |  |  |
| category | string |  |  |  |

### fact_emissions

One row per month, site and source. tco2e = activity_amount * emission_factor / 1000. Factors are illustrative.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| date_key | int64 | 0 | yes |  |
| site_id | string |  | yes |  |
| source_id | string |  | yes |  |
| activity_amount | double | #,0.00 |  | Amount of activity in the row's unit (kWh, litre, kg, passenger-km or tonne). |
| unit | string |  |  |  |
| emission_factor | double | #,0.000 |  | Illustrative factor in kilograms of CO2 equivalent per unit. Not for real reporting. |
| tco2e | double | #,0.000000 |  | Tonnes of CO2 equivalent, as stored in the source data. |

### fact_site_metrics

One row per month and site: revenue and full-time equivalent employees (FTE). FTE is a level: average it over months, never sum it.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| date_key | int64 | 0 | yes |  |
| site_id | string |  | yes |  |
| revenue_eur | double | #,0.00 |  |  |
| fte | double | #,0.0 |  |  |

## Relationships

All many-to-one, filtering from the dimension to the fact.

| From (many) | To (one) |
| --- | --- |
| fact_emissions.date_key | dim_date.date_key |
| fact_emissions.site_id | dim_site.site_id |
| fact_emissions.source_id | dim_source.source_id |
| fact_site_metrics.date_key | dim_date.date_key |
| fact_site_metrics.site_id | dim_site.site_id |

## Row-level security roles

| Role | Filter |
| --- | --- |
| Estonia | `dim_site = dim_site[country] = "Estonia"` |
| Finland | `dim_site = dim_site[country] = "Finland"` |
| Sweden | `dim_site = dim_site[country] = "Sweden"` |
