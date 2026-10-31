# Data dictionary

Generated from the model by `scripts/build_data_dictionary.py`. Do not edit by hand.
Emission factors in this model are illustrative, not for real reporting.

## Measures

Every measure lives in the `_Measures` table, grouped by display folder.

### Emissions

**Total Emissions (tCO2e)**: Tonnes of CO2 equivalent, location-based: scope 1, scope 2 location-based and the scope 3 categories held (1; 3 parts a and c; 4; 5 landfill only; 6 flights only; 9), from the stored tco2e columns of the four emission tables. Market-based scope 2 is a separate measure and is never added in. Format: `#,0.0`.

```dax
SUM ( fact_emissions[tco2e] ) + SUM ( fact_energy_upstream[tco2e] ) + SUM ( fact_purchases[tco2e] ) + SUM ( fact_freight[tco2e] )
```

**Scope 1 Emissions (tCO2e)**: Scope 1. Direct emissions: fuels burned on site and refrigerant leaks. KEEPFILTERS means a slicer on another scope gives blank, not this scope's total. Format: `#,0.0`.

```dax
CALCULATE ( [Total Emissions (tCO2e)], KEEPFILTERS ( dim_source[scope] = 1 ) )
```

**Scope 2 Emissions (tCO2e)**: Scope 2, location-based: purchased electricity and heat at each country's grid or network average factor. KEEPFILTERS means a slicer on another scope gives blank, not this scope's total. Format: `#,0.0`.

```dax
CALCULATE ( [Total Emissions (tCO2e)], KEEPFILTERS ( dim_source[scope] = 2 ) )
```

**Scope 3 Emissions (tCO2e)**: Scope 3: the categories held (purchased goods and services, upstream fuels and transmission losses, freight, waste to landfill, business flights). Category 11, use of sold products, is not yet calculated. KEEPFILTERS means a slicer on another scope gives blank, not this scope's total. Format: `#,0.0`.

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

**Emissions Change Including New Sites (tCO2e)**: Plain change against the same months a year earlier, counting every site, so a new site's whole first year counts as an increase (Tartu, July 2024). Only months whose prior year is in the data count, so 2023 is blank. Sums across sites to the company change; set it beside the like-for-like Emissions Change vs Prior Year (%). Format: `#,0.0`.

```dax
VAR AllKeys = ALL ( dim_date[date_key] )
VAR Months =
	FILTER ( VALUES ( dim_date[date_key] ), ( dim_date[date_key] - 10000 ) IN AllKeys )
RETURN
	IF (
		NOT ISEMPTY ( Months ),
		SUMX ( Months, CALCULATE ( [Total Emissions (tCO2e)] ) - CALCULATE ( [Emissions Prior Year (tCO2e)] ) )
	)
```

**Emissions Change Including New Sites (%)**: Emissions Change Including New Sites (tCO2e) as a share of the prior year's emissions. Blank when nothing is comparable. Format: `0.0%`.

```dax
DIVIDE ( [Emissions Change Including New Sites (tCO2e)], [Emissions Prior Year (tCO2e)] )
```

### Data quality

**Recalculated Emissions (tCO2e)**: Emissions worked out again row by row in all four emission tables: activity times factor, divided by 1,000 to turn kilograms into tonnes. Format: `#,0.0`.

```dax
SUMX ( fact_emissions, fact_emissions[activity_amount] * fact_emissions[emission_factor] / 1000 ) + SUMX ( fact_energy_upstream, fact_energy_upstream[activity_amount] * fact_energy_upstream[emission_factor] / 1000 ) + SUMX ( fact_purchases, fact_purchases[activity_amount] * fact_purchases[emission_factor] / 1000 ) + SUMX ( fact_freight, fact_freight[activity_amount] * fact_freight[emission_factor] / 1000 )
```

**Reconciliation Difference (tCO2e)**: Stored minus recalculated emissions, rounded to 0.001 t (1 kg): the stored values carry 6 decimals, so adding thousands of them leaves a few grams of rounding. Anything that survives the rounding means a row's tco2e doesn't match its activity and factor. Format: `#,0.000`.

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

**Market-based Reconciliation Difference (tCO2e)**: Stored minus recalculated market-based scope 2, rounded to 0.001 t (1 kg). Anything that survives the rounding means a row's tco2e doesn't match its activity and factor. Format: `#,0.000`.

```dax
ROUND ( [Scope 2 Market-based Emissions (tCO2e)] - SUMX ( fact_scope2_market, fact_scope2_market[activity_amount] * fact_scope2_market[emission_factor] / 1000 ), 3 )
```

### Activity

**Energy Used (kWh)**: Natural gas, purchased electricity and district heating, the three sources reported in kWh, added together. Format: `#,0`.

```dax
CALCULATE ( SUM ( fact_emissions[activity_amount] ), KEEPFILTERS ( fact_emissions[unit] = "kWh" ) )
```

**Natural Gas Used (kWh)**: Natural gas burned on site (source S01). KEEPFILTERS means a filter on another source gives blank. Format: `#,0`.

```dax
CALCULATE ( SUM ( fact_emissions[activity_amount] ), KEEPFILTERS ( dim_source[source_id] = "S01" ) )
```

**Electricity Purchased (kWh)**: Electricity bought from the grid (source S05). Tampere's rooftop solar from July 2024 shows as lower purchases. KEEPFILTERS means a filter on another source gives blank. Format: `#,0`.

```dax
CALCULATE ( SUM ( fact_emissions[activity_amount] ), KEEPFILTERS ( dim_source[source_id] = "S05" ) )
```

**District Heating Purchased (kWh)**: Heat bought from a district heating network (source S06). KEEPFILTERS means a filter on another source gives blank. Format: `#,0`.

```dax
CALCULATE ( SUM ( fact_emissions[activity_amount] ), KEEPFILTERS ( dim_source[source_id] = "S06" ) )
```

**Vehicle Fuel Used (litres)**: Diesel and liquefied petroleum gas (sources S02 and S03), both reported in litres, added together. Format: `#,0`.

```dax
CALCULATE ( SUM ( fact_emissions[activity_amount] ), KEEPFILTERS ( fact_emissions[unit] = "litre" ) )
```

**Refrigerant Leakage (kg)**: Refrigerant lost from cooling equipment (source S04). KEEPFILTERS means a filter on another source gives blank. Format: `#,0.0`.

```dax
CALCULATE ( SUM ( fact_emissions[activity_amount] ), KEEPFILTERS ( dim_source[source_id] = "S04" ) )
```

**Business Flights (passenger-km)**: Distance flown on business, in passenger-kilometres (source S07). KEEPFILTERS means a filter on another source gives blank. Format: `#,0`.

```dax
CALCULATE ( SUM ( fact_emissions[activity_amount] ), KEEPFILTERS ( dim_source[source_id] = "S07" ) )
```

**Waste to Landfill (tonnes)**: Waste sent to landfill (source S08). KEEPFILTERS means a filter on another source gives blank. Format: `#,0.0`.

```dax
CALCULATE ( SUM ( fact_emissions[activity_amount] ), KEEPFILTERS ( dim_source[source_id] = "S08" ) )
```

### Market-based scope 2

**Scope 2 Market-based Emissions (tCO2e)**: Scope 2, market-based (GHG Protocol Scope 2 Guidance): kWh covered by guarantees of origin carry the certificate's factor, the rest the country's residual mix; heat uses the network's declared value. The same kWh as location-based. Factors are illustrative. Format: `#,0.0`.

```dax
SUM ( fact_scope2_market[tco2e] )
```

**Total Emissions Market-based (tCO2e)**: Total Emissions with market-based scope 2 in place of location-based scope 2. Scopes 1 and 3 are the same in both totals. Format: `#,0.0`.

```dax
[Total Emissions (tCO2e)] - [Scope 2 Emissions (tCO2e)] + [Scope 2 Market-based Emissions (tCO2e)]
```

**Electricity with Guarantees of Origin (kWh)**: Purchased electricity covered by guarantees of origin under a supplier contract (rows with a contract). KEEPFILTERS means another filter on contract_id gives blank. Format: `#,0`.

```dax
CALCULATE ( SUM ( fact_scope2_market[activity_amount] ), KEEPFILTERS ( NOT ISBLANK ( fact_scope2_market[contract_id] ) ) )
```

**Electricity with Guarantees of Origin (%)**: Share of purchased electricity covered by guarantees of origin. Blank where no contract covers any kWh. Format: `0.0%`.

```dax
DIVIDE ( [Electricity with Guarantees of Origin (kWh)], [Electricity Purchased (kWh)] )
```

### Value chain

**Purchased Goods and Services Emissions (tCO2e)**: Scope 3 category 1, spend-based: each month's purchase ledger spend times an illustrative factor per euro for its spend category. Format: `#,0.0`.

```dax
SUM ( fact_purchases[tco2e] )
```

**Fuel and Energy Related Emissions (tCO2e)**: Scope 3 category 3, parts (a) upstream of purchased fuels and (c) transmission and distribution losses, worked out from the fuel and kWh the sites report. Format: `#,0.0`.

```dax
SUM ( fact_energy_upstream[tco2e] )
```

**Upstream Transport Emissions (tCO2e)**: Scope 3 category 4: inbound freight and the outbound freight Fjordvik pays for (source S12), distance-based. KEEPFILTERS means a filter on another source gives blank. Format: `#,0.0`.

```dax
CALCULATE ( SUM ( fact_freight[tco2e] ), KEEPFILTERS ( dim_source[source_id] = "S12" ) )
```

**Downstream Transport Emissions (tCO2e)**: Scope 3 category 9: outbound freight that customers pay for (source S13), distance-based. KEEPFILTERS means a filter on another source gives blank. Format: `#,0.0`.

```dax
CALCULATE ( SUM ( fact_freight[tco2e] ), KEEPFILTERS ( dim_source[source_id] = "S13" ) )
```

**Purchased Spend (EUR)**: Spend in the purchase ledger, in euros. A flow: it adds up over months. Format: `#,0`.

```dax
SUM ( fact_purchases[activity_amount] )
```

**Freight Transport (tonne-km)**: Freight moved, in tonne-kilometres: tonnes times distance for each lane. Format: `#,0`.

```dax
SUM ( fact_freight[activity_amount] )
```

**Purchased Goods Emissions per Thousand EUR (tCO2e)**: Category 1 emissions per thousand euros spent. Dividing spend by 1,000 turns euros into thousands of euros; the result equals kilograms of CO2 equivalent per euro. Format: `#,0.000`.

```dax
DIVIDE ( [Purchased Goods and Services Emissions (tCO2e)], DIVIDE ( [Purchased Spend (EUR)], 1000 ) )
```

## Tables

### dim_contract

Electricity contracts backed by guarantees of origin, from the supplier contracts and cancellation statements. Supplier names are synthetic.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| contract_id | string |  |  |  |
| site_id | string |  |  |  |
| source_id | string |  |  |  |
| supplier_name | string |  |  |  |
| instrument | string |  |  |  |
| start_date_key | int64 | 0 |  |  |
| end_date_key | int64 | 0 |  |  |
| covered_share | double | 0% |  | Share of the site's monthly kWh covered by the contract's guarantees of origin. |

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

### dim_scope3_category

The 15 Greenhouse Gas Protocol scope 3 categories, with Fjordvik's status for each and the reason for any not calculated.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| scope3_category | int64 | 0 |  |  |
| category_name | string |  |  |  |
| status | string |  |  | Calculated, Calculated in part, Not yet calculated or Not relevant. |
| reason | string |  |  | What the figure covers, or why the category is not calculated (the Scope 3 Standard requires a reason for every exclusion). |

### dim_site

The six sites. Row-level security filters this table by country.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| site_id | string |  |  |  |
| site_name | string |  |  |  |
| country | string |  |  |  |
| site_type | string |  |  |  |

### dim_source

The 13 emission sources, with their Greenhouse Gas Protocol scope, scope 3 category and calculation method.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| source_id | string |  |  |  |
| source_name | string |  |  |  |
| scope | int64 | 0 |  |  |
| category | string |  |  |  |
| scope3_category | int64 | 0 |  | Greenhouse Gas Protocol scope 3 category, 1 to 15. Blank for scopes 1 and 2. |
| method | string |  |  |  |

### dim_supplier

Suppliers in the purchase ledger, each with its spend category. Names are synthetic.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| supplier_id | string |  |  |  |
| supplier_name | string |  |  |  |
| country | string |  |  |  |
| spend_category | string |  |  |  |

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

### fact_energy_upstream

Scope 3 category 3, parts (a) and (c): upstream emissions of purchased fuels and transmission and distribution losses, derived from the fuel and kWh in fact_emissions. Factors are illustrative.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| date_key | int64 | 0 | yes |  |
| site_id | string |  | yes |  |
| source_id | string |  | yes |  |
| based_on_source_id | string |  |  | The fact_emissions source this row is worked out from. |
| activity_amount | double | #,0.00 |  |  |
| unit | string |  |  |  |
| emission_factor | double | #,0.000 |  | Illustrative factor in kilograms of CO2 equivalent per unit. Not for real reporting. |
| tco2e | double | #,0.000000 |  | Tonnes of CO2 equivalent, as stored in the source data. |

### fact_freight

Scope 3 categories 4 and 9, distance-based: one row per month, site, direction, mode and payer, in tonne-kilometres. Outbound freight paid by customers is category 9. Factors are illustrative.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| date_key | int64 | 0 | yes |  |
| site_id | string |  | yes |  |
| source_id | string |  | yes |  |
| direction | string |  |  |  |
| mode | string |  |  |  |
| paid_by | string |  |  |  |
| tonnes | double | #,0.00 |  |  |
| distance_km | int64 | #,0 |  |  |
| activity_amount | double | #,0.00 |  |  |
| unit | string |  |  |  |
| emission_factor | double | #,0.000 |  | Illustrative factor in kilograms of CO2 equivalent per unit. Not for real reporting. |
| tco2e | double | #,0.000000 |  | Tonnes of CO2 equivalent, as stored in the source data. |

### fact_purchases

Scope 3 category 1, spend-based: one row per month, site and supplier from the purchase ledger, in euros. Factors (kg CO2e per euro) are illustrative.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| date_key | int64 | 0 | yes |  |
| site_id | string |  | yes |  |
| source_id | string |  | yes |  |
| supplier_id | string |  | yes |  |
| spend_category | string |  |  |  |
| method | string |  |  |  |
| activity_amount | double | #,0.00 |  |  |
| unit | string |  |  |  |
| emission_factor | double | #,0.000 |  | Illustrative factor in kilograms of CO2 equivalent per unit. Not for real reporting. |
| tco2e | double | #,0.000000 |  | Tonnes of CO2 equivalent, as stored in the source data. |

### fact_scope2_market

Market-based scope 2: the same kWh as location-based, split by instrument (guarantee of origin, residual mix, network declared value). Never added to Total Emissions. Factors are illustrative.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| date_key | int64 | 0 | yes |  |
| site_id | string |  | yes |  |
| source_id | string |  | yes |  |
| contract_id | string |  | yes | Blank for residual mix and heat network rows. |
| instrument | string |  |  |  |
| activity_amount | double | #,0.00 |  |  |
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
| fact_scope2_market.date_key | dim_date.date_key |
| fact_scope2_market.site_id | dim_site.site_id |
| fact_scope2_market.source_id | dim_source.source_id |
| fact_energy_upstream.date_key | dim_date.date_key |
| fact_energy_upstream.site_id | dim_site.site_id |
| fact_energy_upstream.source_id | dim_source.source_id |
| fact_purchases.date_key | dim_date.date_key |
| fact_purchases.site_id | dim_site.site_id |
| fact_purchases.source_id | dim_source.source_id |
| fact_freight.date_key | dim_date.date_key |
| fact_freight.site_id | dim_site.site_id |
| fact_freight.source_id | dim_source.source_id |
| fact_purchases.supplier_id | dim_supplier.supplier_id |
| fact_scope2_market.contract_id | dim_contract.contract_id |
| dim_source.scope3_category | dim_scope3_category.scope3_category |

## Row-level security roles

| Role | Filter |
| --- | --- |
| Estonia | `dim_site = dim_site[country] = "Estonia"` |
| Finland | `dim_site = dim_site[country] = "Finland"` |
| Sweden | `dim_site = dim_site[country] = "Sweden"` |
