# Data dictionary

Generated from the model by `scripts/build_data_dictionary.py`. Do not edit by hand.
Emission factors in this model are illustrative, not for real reporting.

## Measures

Every measure lives in the `_Measures` table, grouped by display folder.

### Emissions

**Total Emissions (tCO2e)**: Tonnes of CO2 equivalent, location-based: scope 1, scope 2 location-based and the scope 3 categories held (1; 3 parts a and c; 4; 5 landfill only; 6 flights only; 9; 11 outside Rest of world), from the stored tco2e columns of the five emission tables. Market-based scope 2 is a separate measure and is never added in. Format: `#,0.0`.

```dax
SUM ( fact_emissions[tco2e] ) + SUM ( fact_energy_upstream[tco2e] ) + SUM ( fact_purchases[tco2e] ) + SUM ( fact_freight[tco2e] ) + SUM ( fact_use_phase[tco2e] )
```

**Scope 1 Emissions (tCO2e)**: Scope 1. Direct emissions: fuels burned on site and refrigerant leaks. KEEPFILTERS means a slicer on another scope gives blank, not this scope's total. Format: `#,0.0`.

```dax
CALCULATE ( [Total Emissions (tCO2e)], KEEPFILTERS ( dim_source[scope] = 1 ) )
```

**Scope 2 Emissions (tCO2e)**: Scope 2, location-based: purchased electricity and heat at each country's grid or network average factor. KEEPFILTERS means a slicer on another scope gives blank, not this scope's total. Format: `#,0.0`.

```dax
CALCULATE ( [Total Emissions (tCO2e)], KEEPFILTERS ( dim_source[scope] = 2 ) )
```

**Scope 3 Emissions (tCO2e)**: Scope 3: the categories held (purchased goods and services, upstream fuels and transmission losses, freight, waste to landfill, business flights, use of sold products). KEEPFILTERS means a slicer on another scope gives blank, not this scope's total. Format: `#,0.0`.

```dax
CALCULATE ( [Total Emissions (tCO2e)], KEEPFILTERS ( dim_source[scope] = 3 ) )
```

**Operational Emissions (tCO2e)**: Scopes 1 and 2 only (location-based): the emissions a site controls, without the value chain or the use of products it made. Format: `#,0.0`.

```dax
[Scope 1 Emissions (tCO2e)] + [Scope 2 Emissions (tCO2e)]
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

**Operational Emissions per FTE (tCO2e)**: Scopes 1 and 2 per average full-time equivalent employee: the site measure a site manager can act on. Emissions per FTE (tCO2e) includes the use-phase emissions of products made at a plant. Format: `#,0.00`.

```dax
DIVIDE ( [Operational Emissions (tCO2e)], [Average FTE] )
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

**Recalculated Emissions (tCO2e)**: Emissions worked out again row by row in all five emission tables: activity times factor, divided by 1,000 to turn kilograms into tonnes. Format: `#,0.0`.

```dax
SUMX ( fact_emissions, fact_emissions[activity_amount] * fact_emissions[emission_factor] / 1000 ) + SUMX ( fact_energy_upstream, fact_energy_upstream[activity_amount] * fact_energy_upstream[emission_factor] / 1000 ) + SUMX ( fact_purchases, fact_purchases[activity_amount] * fact_purchases[emission_factor] / 1000 ) + SUMX ( fact_freight, fact_freight[activity_amount] * fact_freight[emission_factor] / 1000 ) + SUMX ( fact_use_phase, fact_use_phase[activity_amount] * fact_use_phase[emission_factor] / 1000 )
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

**Quarantined Sales (EUR)**: Value of extract lines held back because their item number is not in the global classification. KEEPFILTERS means a filter on another status gives blank. Format: `#,0.00`.

```dax
CALCULATE ( SUM ( fact_data_issue[amount_eur] ), KEEPFILTERS ( fact_data_issue[status] = "Quarantined" ) )
```

**Sales Reconciliation Difference (EUR)**: Finance revenue minus clean sales minus quarantined sales, rounded to the cent. Should be zero; read it without a product or region filter, since revenue has neither. Format: `#,0.00`.

```dax
ROUND ( [Revenue (EUR)] - [Net Sales (EUR)] - [Quarantined Sales (EUR)], 2 )
```

**Data Issues**: Number of issues the SQL logged in the ERP extract. Format: `#,0`.

```dax
COUNTROWS ( fact_data_issue )
```

**Open Data Issues**: Issues still waiting for their owner: quarantined lines stay out of sales until portfolio governance maps the item number. Removed and corrected issues are closed by rule. Format: `#,0`.

```dax
CALCULATE ( COUNTROWS ( fact_data_issue ), KEEPFILTERS ( fact_data_issue[status] = "Quarantined" ) )
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

**Scope 2 Market minus Location (tCO2e)**: Market-based scope 2 minus location-based scope 2. Positive means the guarantees of origin and residual mixes give a higher figure than grid averages. A comparison only; never added to a total. Format: `#,0.0`.

```dax
[Scope 2 Market-based Emissions (tCO2e)] - [Scope 2 Emissions (tCO2e)]
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

### Sales

**Units Sold**: Units sold, from the cleaned sales. A flow: it adds up over months. Format: `#,0`.

```dax
SUM ( fact_sales[units] )
```

**Net Sales (EUR)**: Net sales in euros from the cleaned ERP extract. Swedish kronor are converted at the ECB monthly average rate in the SQL. Format: `#,0`.

```dax
SUM ( fact_sales[net_sales_eur] )
```

**Cost of Sales (EUR)**: Standard cost of the units sold, in euros. Format: `#,0`.

```dax
SUM ( fact_sales[cost_of_sales_eur] )
```

**Margin (EUR)**: Net sales minus cost of sales. Format: `#,0`.

```dax
SUM ( fact_sales[margin_eur] )
```

**Margin (%)**: Margin as a share of net sales. Format: `0.0%`.

```dax
DIVIDE ( [Margin (EUR)], [Net Sales (EUR)] )
```

**Average Price (EUR)**: Net sales per unit. Mixes products of very different prices, so read it within one product group. Format: `#,0`.

```dax
DIVIDE ( [Net Sales (EUR)], [Units Sold] )
```

**Units Sold Prior Year**: Units sold in the same months a year earlier (the month key shifted back one year). Blank where there is no prior year. Format: `#,0`.

```dax
VAR PriorKeys =
	SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
RETURN
	CALCULATE ( [Units Sold], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
```

**Net Sales Prior Year (EUR)**: Net sales in the same months a year earlier. Format: `#,0`.

```dax
VAR PriorKeys =
	SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
RETURN
	CALCULATE ( [Net Sales (EUR)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
```

**Cost of Sales Prior Year (EUR)**: Cost of sales in the same months a year earlier. Format: `#,0`.

```dax
VAR PriorKeys =
	SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
RETURN
	CALCULATE ( [Cost of Sales (EUR)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
```

**Margin Prior Year (EUR)**: Margin in the same months a year earlier. Format: `#,0`.

```dax
VAR PriorKeys =
	SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
RETURN
	CALCULATE ( [Margin (EUR)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
```

**Sales Growth vs Prior Year (%)**: Net sales against the same months a year earlier. Blank with no prior year. Format: `0.0%`.

```dax
DIVIDE ( [Net Sales (EUR)] - [Net Sales Prior Year (EUR)], [Net Sales Prior Year (EUR)] )
```

### Price, volume and mix

**Margin Change vs Prior Year (EUR)**: This period's margin minus the same months a year earlier. Equals the sum of the price, volume, cost and not-comparable effects. Blank with no prior year. Format: `#,0`.

```dax
IF ( NOT ISBLANK ( [Margin Prior Year (EUR)] ), [Margin (EUR)] - [Margin Prior Year (EUR)] )
```

**Price Effect (EUR)**: ACCA F5 sales variances with the prior year as standard: actual = this period, standard = the same months a year earlier, compared product by product over products sold in both. Price effect = (actual price - prior-year price) x actual units. The joint price-times-volume piece sits here, as most textbooks place it (Sorochuk, Vinroot and Leemis, 2023). Format: `#,0`.

```dax
VAR Products =
	ADDCOLUMNS (
		VALUES ( dim_product[product_id] ),
		"@AU", [Units Sold], "@PU", [Units Sold Prior Year],
		"@S", [Net Sales (EUR)], "@PS", [Net Sales Prior Year (EUR)],
		"@C", [Cost of Sales (EUR)], "@PC", [Cost of Sales Prior Year (EUR)]
	)
VAR Comparable = FILTER ( Products, NOT ISBLANK ( [@AU] ) && NOT ISBLANK ( [@PU] ) )
RETURN
	SUMX ( Comparable, [@S] - DIVIDE ( [@PS], [@PU] ) * [@AU] )
```

**Mix Effect (EUR)**: ACCA F5 sales variances with the prior year as standard: actual = this period, standard = the same months a year earlier, compared product by product over products sold in both. Mix effect = (actual units - actual total units in the prior-year mix) x prior-year margin per unit, measured on units (ACCA examiner's report, June 2020). Across very different products (pumps and spare parts) it is large and offset by quantity: read it within one family. Format: `#,0`.

```dax
VAR Products =
	ADDCOLUMNS (
		VALUES ( dim_product[product_id] ),
		"@AU", [Units Sold], "@PU", [Units Sold Prior Year],
		"@S", [Net Sales (EUR)], "@PS", [Net Sales Prior Year (EUR)],
		"@C", [Cost of Sales (EUR)], "@PC", [Cost of Sales Prior Year (EUR)]
	)
VAR Comparable = FILTER ( Products, NOT ISBLANK ( [@AU] ) && NOT ISBLANK ( [@PU] ) )
VAR TotalAU = SUMX ( Comparable, [@AU] )
VAR TotalPU = SUMX ( Comparable, [@PU] )
RETURN
	SUMX ( Comparable, ( [@AU] - TotalAU * DIVIDE ( [@PU], TotalPU ) ) * DIVIDE ( [@PS] - [@PC], [@PU] ) )
```

**Quantity Effect (EUR)**: ACCA F5 sales variances with the prior year as standard: actual = this period, standard = the same months a year earlier, compared product by product over products sold in both. Quantity effect = (actual total units in the prior-year mix - prior-year units) x prior-year margin per unit. Format: `#,0`.

```dax
VAR Products =
	ADDCOLUMNS (
		VALUES ( dim_product[product_id] ),
		"@AU", [Units Sold], "@PU", [Units Sold Prior Year],
		"@S", [Net Sales (EUR)], "@PS", [Net Sales Prior Year (EUR)],
		"@C", [Cost of Sales (EUR)], "@PC", [Cost of Sales Prior Year (EUR)]
	)
VAR Comparable = FILTER ( Products, NOT ISBLANK ( [@AU] ) && NOT ISBLANK ( [@PU] ) )
VAR TotalAU = SUMX ( Comparable, [@AU] )
VAR TotalPU = SUMX ( Comparable, [@PU] )
RETURN
	SUMX ( Comparable, ( TotalAU * DIVIDE ( [@PU], TotalPU ) - [@PU] ) * DIVIDE ( [@PS] - [@PC], [@PU] ) )
```

**Volume Effect (EUR)**: ACCA F5 sales variances with the prior year as standard: actual = this period, standard = the same months a year earlier, compared product by product over products sold in both. Volume effect = mix effect + quantity effect = (actual units - prior-year units) x prior-year margin per unit. Format: `#,0`.

```dax
[Mix Effect (EUR)] + [Quantity Effect (EUR)]
```

**Cost Effect (EUR)**: Change in unit cost against the prior year: (prior-year cost per unit - actual cost per unit) x actual units, over products sold in both periods. Completes the margin bridge. Format: `#,0`.

```dax
VAR Products =
	ADDCOLUMNS (
		VALUES ( dim_product[product_id] ),
		"@AU", [Units Sold], "@PU", [Units Sold Prior Year],
		"@S", [Net Sales (EUR)], "@PS", [Net Sales Prior Year (EUR)],
		"@C", [Cost of Sales (EUR)], "@PC", [Cost of Sales Prior Year (EUR)]
	)
VAR Comparable = FILTER ( Products, NOT ISBLANK ( [@AU] ) && NOT ISBLANK ( [@PU] ) )
RETURN
	SUMX ( Comparable, DIVIDE ( [@PC], [@PU] ) * [@AU] - [@C] )
```

**Not Comparable Change (EUR)**: Margin change from products sold in only one of the two periods, kept apart so the ACCA effects compare like with like. Blank with no prior year. Format: `#,0`.

```dax
VAR Products =
	ADDCOLUMNS (
		VALUES ( dim_product[product_id] ),
		"@AU", [Units Sold], "@PU", [Units Sold Prior Year],
		"@S", [Net Sales (EUR)], "@PS", [Net Sales Prior Year (EUR)],
		"@C", [Cost of Sales (EUR)], "@PC", [Cost of Sales Prior Year (EUR)]
	)
VAR Comparable = FILTER ( Products, NOT ISBLANK ( [@AU] ) && NOT ISBLANK ( [@PU] ) )
RETURN
	IF (
		NOT ISBLANK ( [Margin Prior Year (EUR)] ),
		SUMX ( FILTER ( Products, ISBLANK ( [@AU] ) || ISBLANK ( [@PU] ) ), ( [@S] - [@C] ) - ( [@PS] - [@PC] ) )
	)
```

**Mix Effect by Group (EUR)**: Mix effect within each product group, added up over the groups shown, so a table's total row adds down its column. The mix between groups is in Mix Between Groups (EUR). Format: `#,0`.

```dax
SUMX ( VALUES ( dim_product_group[product_group] ), [Mix Effect (EUR)] )
```

**Quantity Effect by Group (EUR)**: Quantity effect within each product group, added up over the groups shown, so a table's total row adds down its column. Format: `#,0`.

```dax
SUMX ( VALUES ( dim_product_group[product_group] ), [Quantity Effect (EUR)] )
```

**Mix Between Groups (EUR)**: Mix from the shift in sales between product groups: the company-level mix effect minus the mix within each group. The quantity effect moves by the same amount the other way, so the volume effect (mix plus quantity) is the same either way. Format: `#,0`.

```dax
[Mix Effect (EUR)] - [Mix Effect by Group (EUR)]
```

### Portfolio balance

**Share of Net Sales (%)**: Share of all net sales in the same months and sites, across every product and region: portfolio balance. Format: `0.0%`.

```dax
DIVIDE ( [Net Sales (EUR)], CALCULATE ( [Net Sales (EUR)], REMOVEFILTERS ( dim_product ), REMOVEFILTERS ( dim_product_group ), REMOVEFILTERS ( dim_region ) ) )
```

**Share of Margin (%)**: Share of all margin in the same months and sites, across every product and region. Format: `0.0%`.

```dax
DIVIDE ( [Margin (EUR)], CALCULATE ( [Margin (EUR)], REMOVEFILTERS ( dim_product ), REMOVEFILTERS ( dim_product_group ), REMOVEFILTERS ( dim_region ) ) )
```

**Company Margin (%)**: Margin % for all product groups together, whatever group or product a visual shows: the company average line on the scatter charts. Format: `0.0%`.

```dax
CALCULATE ( [Margin (%)], REMOVEFILTERS ( dim_product_group ), REMOVEFILTERS ( dim_product ) )
```

**Company Sales Growth (%)**: Sales growth on the prior year for all product groups together: the company average line. Format: `0.0%`.

```dax
CALCULATE ( [Sales Growth vs Prior Year (%)], REMOVEFILTERS ( dim_product_group ), REMOVEFILTERS ( dim_product ) )
```

### Product sustainability

**Use-phase Emissions (tCO2e)**: Scope 3 category 11: the lifetime electricity of the pumps sold, at the grid factor of the region of use (GHG Protocol direct use-phase method). Rest of world is not calculated. Factors are illustrative. Format: `#,0.0`.

```dax
SUM ( fact_use_phase[tco2e] )
```

**Use-phase Emissions per Unit (tCO2e)**: Category 11 per unit sold, over the units it covers (energy-using products outside Rest of world). Format: `#,0.0`.

```dax
DIVIDE ( [Use-phase Emissions (tCO2e)], SUM ( fact_use_phase[units] ) )
```

**Use-phase Emissions per Thousand EUR (tCO2e)**: Category 11 per thousand euros of the sales it covers. Dividing sales by 1,000 turns euros into thousands of euros. Format: `#,0.00`.

```dax
DIVIDE ( [Use-phase Emissions (tCO2e)], DIVIDE ( SUM ( fact_use_phase[net_sales_eur] ), 1000 ) )
```

**Company Use-phase Emissions per Thousand EUR (tCO2e)**: Use-phase emissions per thousand euros of sales for all product groups together: the company average line. Format: `#,0.00`.

```dax
CALCULATE ( [Use-phase Emissions per Thousand EUR (tCO2e)], REMOVEFILTERS ( dim_product_group ), REMOVEFILTERS ( dim_product ) )
```

### Scorecard

**Weighted Score**: Scorecard score: ratings (1 to 10) times each criterion's weight, divided by the sum of the weights (Cooper and Edgett's scoring model). Weights are Fjordvik's own choice, held in dim_score_criterion. Format: `0.0`.

```dax
DIVIDE ( SUMX ( fact_product_rating, fact_product_rating[rating] * RELATED ( dim_score_criterion[weight] ) ), SUMX ( fact_product_rating, RELATED ( dim_score_criterion[weight] ) ) )
```

**Weighted Score Prior Quarter**: The weighted score of the quarter before (each month moved back three months). Format: `0.0`.

```dax
VAR PriorDates = SELECTCOLUMNS ( VALUES ( dim_date[date] ), "date", EDATE ( dim_date[date], -3 ) )
RETURN
	CALCULATE ( [Weighted Score], REMOVEFILTERS ( dim_date ), TREATAS ( PriorDates, dim_date[date] ) )
```

**Weighted Score Change vs Prior Quarter**: Change in weighted score on the quarter before, in score points. Format: `+0.0;-0.0;0.0`.

```dax
IF ( NOT ISBLANK ( [Weighted Score Prior Quarter] ), [Weighted Score] - [Weighted Score Prior Quarter] )
```

**Company Weighted Score**: Weighted score of all product groups together: the average line on the score against margin chart. Format: `0.0`.

```dax
CALCULATE ( [Weighted Score], REMOVEFILTERS ( dim_product_group ) )
```

### Budget

**Budget Net Sales (EUR)**: Fjordvik's planned net sales (fact_budget, client input, synthetic). The plan is by product group, so read it at product group, family, region or site level, not by single product. Format: `#,0`.

```dax
SUM ( fact_budget[budget_net_sales_eur] )
```

**Budget Margin (EUR)**: Fjordvik's planned margin (fact_budget). By product group, region, site and month. Format: `#,0`.

```dax
SUM ( fact_budget[budget_margin_eur] )
```

**Budget Units**: Fjordvik's planned units sold (fact_budget). By product group, region, site and month. Format: `#,0`.

```dax
SUM ( fact_budget[budget_units] )
```

**Net Sales vs Budget (EUR)**: Net sales minus budget. Positive means ahead of plan. Format: `#,0`.

```dax
IF ( NOT ISBLANK ( [Budget Net Sales (EUR)] ), [Net Sales (EUR)] - [Budget Net Sales (EUR)] )
```

**Net Sales vs Budget (%)**: Net sales against budget, as a share of budget. Format: `0.0%`.

```dax
DIVIDE ( [Net Sales (EUR)] - [Budget Net Sales (EUR)], [Budget Net Sales (EUR)] )
```

**Margin vs Budget (EUR)**: Margin minus budgeted margin. Positive means ahead of plan. Format: `#,0`.

```dax
IF ( NOT ISBLANK ( [Budget Margin (EUR)] ), [Margin (EUR)] - [Budget Margin (EUR)] )
```

### Bridge

**Bridge Value (EUR)**: The value of each bridge step (dim_bridge_step): prior-year margin, the ACCA effects named as segment reports name them (price as sales prices, quantity as delivery volumes, cost as variable costs), not comparable, and this year's margin. Format: `#,0`.

```dax
SWITCH ( SELECTEDVALUE ( dim_bridge_step[step] ),
	"Prior-year margin", [Margin Prior Year (EUR)],
	"Sales prices", [Price Effect (EUR)],
	"Mix", [Mix Effect (EUR)],
	"Delivery volumes", [Quantity Effect (EUR)],
	"Variable costs", [Cost Effect (EUR)],
	"Not comparable", [Not Comparable Change (EUR)],
	"This year's margin", [Margin (EUR)]
)
```

**Bridge Base (EUR)**: The invisible base of each step in the waterfall: where the bar starts, so steps float between the prior-year and this year's margin. Format: `#,0`.

```dax
VAR ThisStep = SELECTEDVALUE ( dim_bridge_step[step_order] )
VAR StepStart = SUMX ( FILTER ( ALL ( dim_bridge_step ), dim_bridge_step[step_order] < ThisStep ), CALCULATE ( [Bridge Value (EUR)] ) )
VAR StepValue = [Bridge Value (EUR)]
VAR IsTotal = SELECTEDVALUE ( dim_bridge_step[step] ) IN { "Prior-year margin", "This year's margin" }
RETURN
	IF ( NOT IsTotal && NOT ISBLANK ( StepValue ), MIN ( StepStart, StepStart + StepValue ) )
```

**Bridge Increase (EUR)**: A step that raised margin (green in the waterfall). Format: `+#,0;-#,0`.

```dax
VAR ThisStep = SELECTEDVALUE ( dim_bridge_step[step_order] )
VAR StepStart = SUMX ( FILTER ( ALL ( dim_bridge_step ), dim_bridge_step[step_order] < ThisStep ), CALCULATE ( [Bridge Value (EUR)] ) )
VAR StepValue = [Bridge Value (EUR)]
VAR IsTotal = SELECTEDVALUE ( dim_bridge_step[step] ) IN { "Prior-year margin", "This year's margin" }
RETURN
	IF ( NOT IsTotal && StepValue > 0, StepValue )
```

**Bridge Decrease (EUR)**: A step that lowered margin, as a positive bar height (red in the waterfall); its label shows the minus sign. Format: `-#,0;-#,0`.

```dax
VAR ThisStep = SELECTEDVALUE ( dim_bridge_step[step_order] )
VAR StepStart = SUMX ( FILTER ( ALL ( dim_bridge_step ), dim_bridge_step[step_order] < ThisStep ), CALCULATE ( [Bridge Value (EUR)] ) )
VAR StepValue = [Bridge Value (EUR)]
VAR IsTotal = SELECTEDVALUE ( dim_bridge_step[step] ) IN { "Prior-year margin", "This year's margin" }
RETURN
	IF ( NOT IsTotal && StepValue < 0, - StepValue )
```

**Bridge Prior Year Total (EUR)**: The waterfall's first bar: the same months a year earlier. Format: `#,0`.

```dax
IF ( SELECTEDVALUE ( dim_bridge_step[step] ) = "Prior-year margin", [Bridge Value (EUR)] )
```

**Bridge This Year Total (EUR)**: The waterfall's last bar: this period's margin. Equals the first bar plus every step. Format: `#,0`.

```dax
IF ( SELECTEDVALUE ( dim_bridge_step[step] ) = "This year's margin", [Bridge Value (EUR)] )
```

**Bridge Label Position (EUR)**: Where each waterfall step's label sits: the top of the step's bar. Its format string turns the label into the step's own value (for example +4.4M), so even a step too short to hold a label inside its bar is labelled above it. Format: ``.

```dax
VAR ThisStep = SELECTEDVALUE ( dim_bridge_step[step_order] )
VAR StepStart = SUMX ( FILTER ( ALL ( dim_bridge_step ), dim_bridge_step[step_order] < ThisStep ), CALCULATE ( [Bridge Value (EUR)] ) )
VAR StepValue = [Bridge Value (EUR)]
VAR IsTotal = SELECTEDVALUE ( dim_bridge_step[step] ) IN { "Prior-year margin", "This year's margin" }
RETURN
	IF ( NOT IsTotal && NOT ISBLANK ( StepValue ), MAX ( StepStart, StepStart + StepValue ) )
```

### Text

**Total Emissions Context**: Card context for Total Emissions (tCO2e): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Total Emissions (tCO2e)]
VAR Prior = CALCULATE ( [Total Emissions (tCO2e)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( DIVIDE ( Prior, 1000 ), "#,0.0" ) & "K" & ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) )
```

**Scope 1 Emissions Context**: Card context for Scope 1 Emissions (tCO2e): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Scope 1 Emissions (tCO2e)]
VAR Prior = CALCULATE ( [Scope 1 Emissions (tCO2e)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( DIVIDE ( Prior, 1000 ), "#,0.0" ) & "K" & ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) )
```

**Scope 2 Emissions Context**: Card context for Scope 2 Emissions (tCO2e): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Scope 2 Emissions (tCO2e)]
VAR Prior = CALCULATE ( [Scope 2 Emissions (tCO2e)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( DIVIDE ( Prior, 1000 ), "#,0.0" ) & "K" & ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) )
```

**Scope 3 Emissions Context**: Card context for Scope 3 Emissions (tCO2e): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Scope 3 Emissions (tCO2e)]
VAR Prior = CALCULATE ( [Scope 3 Emissions (tCO2e)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( DIVIDE ( Prior, 1000 ), "#,0.0" ) & "K" & ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) )
```

**Emissions per FTE Context**: Card context for Emissions per FTE (tCO2e): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Emissions per FTE (tCO2e)]
VAR Prior = CALCULATE ( [Emissions per FTE (tCO2e)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( Prior, "#,0" ) & ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) )
```

**Emissions per Million EUR Context**: Card context for Emissions per Million EUR (tCO2e): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Emissions per Million EUR (tCO2e)]
VAR Prior = CALCULATE ( [Emissions per Million EUR (tCO2e)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( Prior, "#,0" ) & ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) )
```

**Operational Emissions per FTE Context**: Card context for Operational Emissions per FTE (tCO2e): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Operational Emissions per FTE (tCO2e)]
VAR Prior = CALCULATE ( [Operational Emissions per FTE (tCO2e)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( Prior, "#,0.0" ) & ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) )
```

**Purchased Goods Context**: Card context for Purchased Goods and Services Emissions (tCO2e): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Purchased Goods and Services Emissions (tCO2e)]
VAR Prior = CALCULATE ( [Purchased Goods and Services Emissions (tCO2e)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( DIVIDE ( Prior, 1000 ), "#,0.0" ) & "K" & ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) )
```

**Fuel and Energy Context**: Card context for Fuel and Energy Related Emissions (tCO2e): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Fuel and Energy Related Emissions (tCO2e)]
VAR Prior = CALCULATE ( [Fuel and Energy Related Emissions (tCO2e)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( DIVIDE ( Prior, 1000 ), "#,0.0" ) & "K" & ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) )
```

**Upstream Transport Context**: Card context for Upstream Transport Emissions (tCO2e): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Upstream Transport Emissions (tCO2e)]
VAR Prior = CALCULATE ( [Upstream Transport Emissions (tCO2e)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( DIVIDE ( Prior, 1000 ), "#,0.0" ) & "K" & ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) )
```

**Downstream Transport Context**: Card context for Downstream Transport Emissions (tCO2e): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Downstream Transport Emissions (tCO2e)]
VAR Prior = CALCULATE ( [Downstream Transport Emissions (tCO2e)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( DIVIDE ( Prior, 1000 ), "#,0.0" ) & "K" & ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) )
```

**Scope 2 Market-based Context**: Card context for Scope 2 Market-based Emissions (tCO2e): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Scope 2 Market-based Emissions (tCO2e)]
VAR Prior = CALCULATE ( [Scope 2 Market-based Emissions (tCO2e)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( DIVIDE ( Prior, 1000 ), "#,0.0" ) & "K" & ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) )
```

**Guarantees of Origin Context**: Card context for Electricity with Guarantees of Origin (%): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Electricity with Guarantees of Origin (%)]
VAR Prior = CALCULATE ( [Electricity with Guarantees of Origin (%)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( Prior, "0.0%" ) & ", " & SUBSTITUTE ( FORMAT ( Now - Prior, "+0.0%;-0.0%;0.0%" ), "%", " pts" ) )
```

**Energy Used Context**: Card context for Energy Used (kWh): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Energy Used (kWh)]
VAR Prior = CALCULATE ( [Energy Used (kWh)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( DIVIDE ( Prior, 1000000 ), "#,0.0" ) & "M" & ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) )
```

**Vehicle Fuel Context**: Card context for Vehicle Fuel Used (litres): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Vehicle Fuel Used (litres)]
VAR Prior = CALCULATE ( [Vehicle Fuel Used (litres)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( DIVIDE ( Prior, 1000 ), "#,0.0" ) & "K" & ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) )
```

**Refrigerant Context**: Card context for Refrigerant Leakage (kg): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Refrigerant Leakage (kg)]
VAR Prior = CALCULATE ( [Refrigerant Leakage (kg)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( Prior, "#,0.0" ) & ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) )
```

**Business Flights Context**: Card context for Business Flights (passenger-km): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Business Flights (passenger-km)]
VAR Prior = CALCULATE ( [Business Flights (passenger-km)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( DIVIDE ( Prior, 1000000 ), "#,0.0" ) & "M" & ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) )
```

**Waste Context**: Card context for Waste to Landfill (tonnes): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Waste to Landfill (tonnes)]
VAR Prior = CALCULATE ( [Waste to Landfill (tonnes)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( Prior, "#,0.0" ) & ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) )
```

**Net Sales Context**: Card context for Net Sales (EUR): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Net Sales (EUR)]
VAR Prior = CALCULATE ( [Net Sales (EUR)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( DIVIDE ( Prior, 1000000 ), "#,0.0" ) & "M" & ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) )
```

**Margin Context**: Card context for Margin (EUR): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Margin (EUR)]
VAR Prior = CALCULATE ( [Margin (EUR)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( DIVIDE ( Prior, 1000000 ), "#,0.0" ) & "M" & ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) )
```

**Margin Percent Context**: Card context for Margin (%): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Margin (%)]
VAR Prior = CALCULATE ( [Margin (%)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( Prior, "0.0%" ) & ", " & SUBSTITUTE ( FORMAT ( Now - Prior, "+0.0%;-0.0%;0.0%" ), "%", " pts" ) )
```

**Units Sold Context**: Card context for Units Sold: the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Units Sold]
VAR Prior = CALCULATE ( [Units Sold], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( DIVIDE ( Prior, 1000 ), "#,0.0" ) & "K" & ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) )
```

**Use-phase Emissions Context**: Card context for Use-phase Emissions (tCO2e): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Use-phase Emissions (tCO2e)]
VAR Prior = CALCULATE ( [Use-phase Emissions (tCO2e)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( DIVIDE ( Prior, 1000 ), "#,0.0" ) & "K" & ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) )
```

**Use-phase per Unit Context**: Card context for Use-phase Emissions per Unit (tCO2e): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Use-phase Emissions per Unit (tCO2e)]
VAR Prior = CALCULATE ( [Use-phase Emissions per Unit (tCO2e)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( Prior, "#,0.0" ) & ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) )
```

**Use-phase per Thousand EUR Context**: Card context for Use-phase Emissions per Thousand EUR (tCO2e): the same months a year earlier and the change on them (percentage points for a rate). Text, for the line under the card. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Use-phase Emissions per Thousand EUR (tCO2e)]
VAR Prior = CALCULATE ( [Use-phase Emissions per Thousand EUR (tCO2e)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) & ": " & FORMAT ( Prior, "#,0.00" ) & ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) )
```

**Net Sales Budget Context**: Card context for Net Sales (EUR) against Fjordvik's budget (fact_budget): the plan and the variance on it. Text, for the line under the card. Format: ``.

```dax
VAR Now = [Net Sales (EUR)]
VAR Plan = [Budget Net Sales (EUR)]
RETURN
	IF ( ISBLANK ( Plan ), "No budget", "Budget: " & FORMAT ( DIVIDE ( Plan, 1000000 ), "#,0.0" ) & "M" & ", " & FORMAT ( DIVIDE ( Now - Plan, Plan ), "+0.0%;-0.0%;0.0%" ) )
```

**Margin Budget Context**: Card context for Margin (EUR) against Fjordvik's budget (fact_budget): the plan and the variance on it. Text, for the line under the card. Format: ``.

```dax
VAR Now = [Margin (EUR)]
VAR Plan = [Budget Margin (EUR)]
RETURN
	IF ( ISBLANK ( Plan ), "No budget", "Budget: " & FORMAT ( DIVIDE ( Plan, 1000000 ), "#,0.0" ) & "M" & ", " & FORMAT ( DIVIDE ( Now - Plan, Plan ), "+0.0%;-0.0%;0.0%" ) )
```

**Margin Percent Budget Context**: Card context for Margin (%) against Fjordvik's budget (fact_budget): the plan and the variance on it. Text, for the line under the card. Format: ``.

```dax
VAR Now = [Margin (%)]
VAR Plan = DIVIDE ( [Budget Margin (EUR)], [Budget Net Sales (EUR)] )
RETURN
	IF ( ISBLANK ( Plan ), "No budget", "Budget: " & FORMAT ( Plan, "0.0%" ) & ", " & SUBSTITUTE ( FORMAT ( Now - Plan, "+0.0%;-0.0%;0.0%" ), "%", " pts" ) )
```

**Units Sold Budget Context**: Card context for Units Sold against Fjordvik's budget (fact_budget): the plan and the variance on it. Text, for the line under the card. Format: ``.

```dax
VAR Now = [Units Sold]
VAR Plan = [Budget Units]
RETURN
	IF ( ISBLANK ( Plan ), "No budget", "Budget: " & FORMAT ( DIVIDE ( Plan, 1000 ), "#,0.0" ) & "K" & ", " & FORMAT ( DIVIDE ( Now - Plan, Plan ), "+0.0%;-0.0%;0.0%" ) )
```

**Margin Change Context**: Card context for the margin change: the change as a share of the prior-year margin. Format: ``.

```dax
VAR Prior = [Margin Prior Year (EUR)]
RETURN
	IF ( ISBLANK ( Prior ), "No prior year to compare", FORMAT ( DIVIDE ( [Margin (EUR)] - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) & " on " & FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) )
```

**Open Issues Context**: Card context for open issues: how many were logged in all. Format: ``.

```dax
"of " & FORMAT ( [Data Issues], "0" ) & " logged"
```

**Overview Message**: Overview page title: the change on the prior year (all sites) and the share of use of sold products. Format: ``.

```dax
VAR Change = [Emissions Change Including New Sites (%)]
VAR Share = DIVIDE ( [Use-phase Emissions (tCO2e)], [Total Emissions (tCO2e)] )
RETURN
	IF ( ISBLANK ( Change ), "Emissions in " & FORMAT ( MAX ( dim_date[year] ), "0" ) & ": " & FORMAT ( DIVIDE ( [Total Emissions (tCO2e)], 1000 ), "#,0.0" ) & "K tCO2e",
		"Emissions " & IF ( Change < 0, "fell ", "rose " ) & FORMAT ( ABS ( Change ), "0.0%" ) & " in " & FORMAT ( MAX ( dim_date[year] ), "0" ) )
	& "; use of sold products is " & FORMAT ( Share, "0%" ) & " of the total"
```

**Breakdown Message**: Emissions breakdown page title. Ignores the Scope slicer, so it always describes the whole. Format: ``.

```dax
VAR Total = CALCULATE ( [Total Emissions (tCO2e)], REMOVEFILTERS ( dim_source ) )
VAR Scope3 = CALCULATE ( [Scope 3 Emissions (tCO2e)], REMOVEFILTERS ( dim_source ) )
VAR Operational = CALCULATE ( [Operational Emissions (tCO2e)], REMOVEFILTERS ( dim_source ) )
RETURN
	"Scope 3 is " & FORMAT ( DIVIDE ( Scope3, Total ), "0.0%" ) & " of emissions in " & FORMAT ( MAX ( dim_date[year] ), "0" ) & "; scopes 1 and 2 together are " & FORMAT ( DIVIDE ( Operational, 1000 ), "#,0.0" ) & "K tCO2e"
```

**Value Chain Message**: Value chain page title: how many of the 15 categories are calculated, and the share of category 11. Format: ``.

```dax
VAR Counted = CALCULATE ( COUNTROWS ( dim_scope3_category ), REMOVEFILTERS ( dim_scope3_category ), dim_scope3_category[status] IN { "Calculated", "Calculated in part" } )
VAR InPart = CALCULATE ( COUNTROWS ( dim_scope3_category ), REMOVEFILTERS ( dim_scope3_category ), dim_scope3_category[status] = "Calculated in part" )
VAR Categories = CALCULATE ( COUNTROWS ( dim_scope3_category ), REMOVEFILTERS ( dim_scope3_category ) )
VAR Share = DIVIDE ( [Use-phase Emissions (tCO2e)], [Scope 3 Emissions (tCO2e)] )
RETURN
	FORMAT ( Counted, "0" ) & " of " & FORMAT ( Categories, "0" ) & " scope 3 categories calculated (" & FORMAT ( InPart, "0" ) & " in part); use of sold products is " & FORMAT ( Share, "0%" ) & " of scope 3 in " & FORMAT ( MAX ( dim_date[year] ), "0" )
```

**Scope 2 Message**: Scope 2 methods page title. Format: ``.

```dax
VAR Location = [Scope 2 Emissions (tCO2e)]
VAR Gap = DIVIDE ( [Scope 2 Market-based Emissions (tCO2e)] - Location, Location )
RETURN
	"Market-based scope 2 is " & FORMAT ( ABS ( Gap ), "0%" ) & IF ( Gap >= 0, " above", " below" ) & " location-based in " & FORMAT ( MAX ( dim_date[year] ), "0" ) & "; guarantees of origin cover " & FORMAT ( [Electricity with Guarantees of Origin (%)], "0.0%" ) & " of electricity bought"
```

**Intensity Message**: Intensity and growth page title. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Emissions per Million EUR (tCO2e)]
VAR Prior = CALCULATE ( [Emissions per Million EUR (tCO2e)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	"Emissions per million euros of revenue were " & FORMAT ( Now, "#,0" ) & " tCO2e in " & FORMAT ( MAX ( dim_date[year] ), "0" )
	& IF ( ISBLANK ( Prior ), "", ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) & " on " & FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) )
```

**Energy Message**: Energy and activity page title. Format: ``.

```dax
VAR PriorKeys = SELECTCOLUMNS ( VALUES ( dim_date[date_key] ), "date_key", dim_date[date_key] - 10000 )
VAR Now = [Energy Used (kWh)]
VAR Prior = CALCULATE ( [Energy Used (kWh)], REMOVEFILTERS ( dim_date ), TREATAS ( PriorKeys, dim_date[date_key] ) )
RETURN
	"Sites used " & FORMAT ( DIVIDE ( Now, 1000000 ), "#,0.0" ) & " million kWh of energy in " & FORMAT ( MAX ( dim_date[year] ), "0" )
	& IF ( ISBLANK ( Prior ), "", ", " & FORMAT ( DIVIDE ( Now - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) & " on " & FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) )
```

**What Changed Message**: What changed page title: the like-for-like change and the site that moved most. Format: ``.

```dax
VAR Sites = ADDCOLUMNS ( VALUES ( dim_site[site_name] ), "@change", [Emissions Change Including New Sites (tCO2e)] )
VAR Biggest = TOPN ( 1, Sites, ABS ( [@change] ), DESC )
VAR LikeForLike = [Emissions Change vs Prior Year (%)]
RETURN
	IF ( ISBLANK ( LikeForLike ), "No prior year to compare in " & FORMAT ( MAX ( dim_date[year] ), "0" ),
		"Emissions " & IF ( LikeForLike < 0, "fell ", "rose " ) & FORMAT ( ABS ( LikeForLike ), "0.0%" ) & " like for like in " & FORMAT ( MAX ( dim_date[year] ), "0" )
		& "; the biggest change was at " & MAXX ( Biggest, dim_site[site_name] ) & " (" & FORMAT ( DIVIDE ( MAXX ( Biggest, [@change] ), 1000 ), "+#,0.0;-#,0.0" ) & "K tCO2e)" )
```

**Sites Message**: Sites page title. Format: ``.

```dax
VAR Ranked = ADDCOLUMNS ( VALUES ( dim_site[site_name] ), "@value", [Operational Emissions per FTE (tCO2e)] )
VAR Highest = TOPN ( 1, Ranked, [@value], DESC )
RETURN
	MAXX ( Highest, dim_site[site_name] ) & " has the highest operational (scope 1 and 2) emissions per FTE in " & FORMAT ( MAX ( dim_date[year] ), "0" ) & ": " & FORMAT ( MAXX ( Highest, [@value] ), "#,0.0" ) & " tCO2e"
```

**Data Quality Message**: Data quality page title. Format: ``.

```dax
VAR Difference = [Reconciliation Difference (tCO2e)]
RETURN
	"Stored emissions " & IF ( Difference = 0, "match", "do not match" ) & " activity times factor for all " & FORMAT ( [Emission Rows], "#,0" ) & " site rows in " & FORMAT ( MAX ( dim_date[year] ), "0" ) & " (difference " & FORMAT ( Difference, "0.000" ) & " tCO2e)"
```

**Portfolio Overview Message**: Portfolio overview page title. Format: ``.

```dax
VAR Sales = [Net Sales (EUR)]
VAR Prior = [Net Sales Prior Year (EUR)]
VAR Plan = [Budget Net Sales (EUR)]
RETURN
	"Net sales were EUR " & FORMAT ( DIVIDE ( Sales, 1000000 ), "#,0.0" ) & " million in " & FORMAT ( MAX ( dim_date[year] ), "0" )
	& IF ( ISBLANK ( Prior ), "", ", " & FORMAT ( DIVIDE ( Sales - Prior, Prior ), "+0.0%;-0.0%;0.0%" ) & " on " & FORMAT ( MAX ( dim_date[year] ) - 1, "0" ) )
	& IF ( ISBLANK ( Plan ), "", " and " & FORMAT ( DIVIDE ( Sales - Plan, Plan ), "+0.0%;-0.0%;0.0%" ) & " against budget" )
	& "; margin " & FORMAT ( [Margin (%)], "0.0%" )
```

**Price Volume Mix Message**: Price, volume and mix page title: the margin change and its biggest driver. Format: ``.

```dax
VAR Change = [Margin Change vs Prior Year (EUR)]
VAR Drivers = { ( "sales prices", [Price Effect (EUR)] ), ( "mix", [Mix Effect (EUR)] ), ( "delivery volumes", [Quantity Effect (EUR)] ), ( "variable costs", [Cost Effect (EUR)] ) }
VAR Biggest = TOPN ( 1, Drivers, ABS ( [Value2] ), DESC )
RETURN
	IF ( ISBLANK ( Change ), "No prior year to compare in " & FORMAT ( MAX ( dim_date[year] ), "0" ),
		"Margin " & IF ( Change < 0, "fell", "rose" ) & " EUR " & FORMAT ( DIVIDE ( ABS ( Change ), 1000000 ), "#,0.0" ) & " million in " & FORMAT ( MAX ( dim_date[year] ), "0" )
		& "; the biggest driver was " & MAXX ( Biggest, [Value1] ) & " (" & FORMAT ( DIVIDE ( MAXX ( Biggest, [Value2] ), 1000000 ), "+#,0.0;-#,0.0" ) & " million)" )
```

**Portfolio Balance Message**: Portfolio balance page title. Format: ``.

```dax
VAR Regions = TOPN ( 1, ADDCOLUMNS ( VALUES ( dim_region[region_name] ), "@share", [Share of Net Sales (%)] ), [@share], DESC )
VAR Groups = TOPN ( 1, ADDCOLUMNS ( VALUES ( dim_product_group[product_group] ), "@share", [Share of Margin (%)] ), [@share], DESC )
RETURN
	MAXX ( Regions, dim_region[region_name] ) & " bring " & FORMAT ( MAXX ( Regions, [@share] ), "0%" ) & " of net sales in " & FORMAT ( MAX ( dim_date[year] ), "0" ) & "; " & MAXX ( Groups, dim_product_group[product_group] ) & " earn the largest share of margin (" & FORMAT ( MAXX ( Groups, [@share] ), "0.0%" ) & ")"
```

**Scorecard Message**: Quarterly scorecard page title. Format: ``.

```dax
VAR Scores = FILTER ( ADDCOLUMNS ( VALUES ( dim_product_group[product_group] ), "@score", [Weighted Score], "@change", [Weighted Score Change vs Prior Quarter] ), NOT ISBLANK ( [@score] ) )
VAR Highest = TOPN ( 1, Scores, [@score], DESC )
VAR Lowest = TOPN ( 1, Scores, [@score], ASC )
VAR Fell = COUNTROWS ( FILTER ( Scores, [@change] < 0 ) ) + 0
VAR Period = IF ( HASONEVALUE ( dim_date[quarter] ), FORMAT ( MAX ( dim_date[year] ), "0" ) & " Q" & FORMAT ( MAX ( dim_date[quarter] ), "0" ), FORMAT ( MAX ( dim_date[year] ), "0" ) )
RETURN
	MAXX ( Highest, dim_product_group[product_group] ) & " score highest (" & FORMAT ( MAXX ( Highest, [@score] ), "0.0" ) & ") and " & MAXX ( Lowest, dim_product_group[product_group] ) & " lowest (" & FORMAT ( MAXX ( Lowest, [@score] ), "0.0" ) & ") in " & Period & "; " & FORMAT ( Fell, "0" ) & " of " & FORMAT ( COUNTROWS ( Scores ), "0" ) & " fell"
```

**Product Sustainability Message**: Product sustainability page title. Format: ``.

```dax
VAR Groups = TOPN ( 1, FILTER ( ADDCOLUMNS ( VALUES ( dim_product_group[product_group] ), "@perUnit", [Use-phase Emissions per Unit (tCO2e)] ), NOT ISBLANK ( [@perUnit] ) ), [@perUnit], DESC )
RETURN
	"Pumps sold in " & FORMAT ( MAX ( dim_date[year] ), "0" ) & " will cause " & FORMAT ( DIVIDE ( [Use-phase Emissions (tCO2e)], 1000 ), "#,0.0" ) & "K tCO2e over their lives; " & MAXX ( Groups, dim_product_group[product_group] ) & " are highest per unit (" & FORMAT ( MAXX ( Groups, [@perUnit] ), "#,0" ) & " t)"
```

**Classification Message**: Classification and data quality page title. Format: ``.

```dax
VAR Difference = [Sales Reconciliation Difference (EUR)]
RETURN
	FORMAT ( [Open Data Issues], "0" ) & " of " & FORMAT ( [Data Issues], "0" ) & " issues open; EUR " & FORMAT ( [Quarantined Sales (EUR)], "#,0" ) & " of sales held back until mapped; "
	& IF ( Difference = 0, "sales reconcile to finance to the cent", "sales differ from finance revenue by EUR " & FORMAT ( Difference, "#,0.00" ) )
```

**Mix Between Groups Note**: Note under the bridge table, so a reader knows why its mix and quantity columns differ from the waterfall. Format: ``.

```dax
"Rows show mix within each group. The waterfall's Mix also holds the shift between groups (EUR " & FORMAT ( DIVIDE ( [Mix Between Groups (EUR)], 1000000 ), "+#,0.0;-#,0.0" ) & " million), which its Delivery volumes step offsets, so both add to the same change."
```

**Report Footer**: Page footer: the period the data covers and when the model last refreshed. Format: ``.

```dax
VAR FirstMonth = CALCULATE ( MIN ( dim_date[date] ), REMOVEFILTERS ( dim_date ) )
VAR LastMonth = CALCULATE ( MAX ( dim_date[date] ), REMOVEFILTERS ( dim_date ) )
RETURN
	"Data " & FORMAT ( FirstMonth, "mmm yyyy" ) & " to " & FORMAT ( LastMonth, "mmm yyyy" ) & ", monthly. Refreshed " & FORMAT ( MAX ( dim_refresh[refreshed_at] ), "d mmm yyyy hh:nn" ) & "."
```

**Contract Start**: A contract's first month, as a month name, from its yyyymmdd key. Format: ``.

```dax
VAR DateKey = SELECTEDVALUE ( dim_contract[start_date_key] )
RETURN
	IF ( NOT ISBLANK ( DateKey ), FORMAT ( DATE ( QUOTIENT ( DateKey, 10000 ), MOD ( QUOTIENT ( DateKey, 100 ), 100 ), 1 ), "mmm yyyy" ) )
```

**Contract End**: A contract's last month, as a month name, from its yyyymmdd key. Format: ``.

```dax
VAR DateKey = SELECTEDVALUE ( dim_contract[end_date_key] )
RETURN
	IF ( NOT ISBLANK ( DateKey ), FORMAT ( DATE ( QUOTIENT ( DateKey, 10000 ), MOD ( QUOTIENT ( DateKey, 100 ), 100 ), 1 ), "mmm yyyy" ) )
```

## Tables

### dim_bridge_step

The steps of the margin bridge, in order, for the waterfall on Price, volume and mix. Names only; the values come from the Bridge measures. Step names follow how segment reports describe margin drivers; the measures keep their ACCA names.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| step | string |  |  |  |
| step_order | int64 | 0 | yes |  |

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

### dim_product

One row per product model. Rated kW, yearly kWh and lifetime are Fjordvik's own engineering specification.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| product_id | string |  |  | Global product code. |
| product_name | string |  |  |  |
| product_group | string |  | yes |  |
| product_family | string |  |  |  |
| made_at_site_id | string |  |  |  |
| rated_kw | int64 | 0 |  |  |
| kwh_per_year | int64 | #,0 |  | Expected electricity use per year in service. |
| lifetime_years | int64 | 0 |  |  |
| list_price_eur | double | #,0 |  |  |
| standard_cost_eur | double | #,0 |  |  |

### dim_product_code

The global classification: each business unit's local item number for each product.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| business_unit | string |  |  |  |
| local_item_number | string |  |  |  |
| product_id | string |  | yes |  |

### dim_product_group

Product groups and the family each belongs to: the top two levels of the global product classification.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| product_group | string |  |  |  |
| product_family | string |  |  |  |

### dim_refresh

When the model last refreshed: NOW() is worked out at each refresh, so this is the time the data was loaded. Shown in each page's footer.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| refreshed_at | dateTime | d mmm yyyy hh:nn |  |  |

### dim_region

The four sales regions.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| region_id | string |  |  |  |
| region_name | string |  |  |  |

### dim_scope3_category

The 15 Greenhouse Gas Protocol scope 3 categories, with Fjordvik's status for each and the reason for any not calculated.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| scope3_category | int64 | 0 |  |  |
| category_name | string |  |  |  |
| status | string |  |  | Calculated, Calculated in part, Not yet calculated or Not relevant. |
| reason | string |  |  | What the figure covers, or why the category is not calculated (the Scope 3 Standard requires a reason for every exclusion). |

### dim_score_criterion

The six scorecard criteria (Cooper and Edgett) and the weight Fjordvik gives each: its own stated choice.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| criterion_id | string |  |  |  |
| criterion_name | string |  |  |  |
| weight | int64 | 0 |  | Fjordvik's own weight; no source publishes weights. |
| source | string |  |  |  |

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

### fact_budget

Fjordvik's sales plan (synthetic client input): one row per month, shipping site, product group and region. Product group is the finest level, so a filter on a single product does not narrow the budget.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| date_key | int64 | 0 | yes |  |
| site_id | string |  | yes |  |
| product_group | string |  | yes |  |
| region_id | string |  | yes |  |
| budget_units | int64 | #,0 |  |  |
| budget_net_sales_eur | double | #,0 |  |  |
| budget_margin_eur | double | #,0 |  |  |

### fact_data_issue

Problems the SQL found in the ERP extract, one row each, with the action for the data owner.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| issue_id | int64 | 0 |  |  |
| date_key | int64 | 0 | yes |  |
| site_id | string |  | yes |  |
| business_unit | string |  |  |  |
| issue_type | string |  |  |  |
| detail | string |  |  |  |
| line_count | int64 | #,0 |  |  |
| amount_eur | double | #,0.00 |  |  |
| status | string |  |  | Removed by rule, Corrected by rule or Quarantined. |
| action | string |  |  |  |

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

### fact_product_rating

Each quarter's portfolio review: a 1 to 10 rating per product group and criterion, keyed to the quarter's first month.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| date_key | int64 | 0 | yes |  |
| product_group | string |  | yes |  |
| criterion_id | string |  | yes |  |
| rating | int64 | 0 |  |  |

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

### fact_sales

One row per month, shipping site, product and region, cleaned by SQL from the simulated Oracle extract. Reconciles to finance revenue.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| date_key | int64 | 0 | yes |  |
| site_id | string |  | yes |  |
| product_id | string |  | yes |  |
| region_id | string |  | yes |  |
| units | int64 | #,0 |  |  |
| net_sales_eur | double | #,0.00 |  |  |
| cost_of_sales_eur | double | #,0.00 |  |  |
| margin_eur | double | #,0.00 |  |  |

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

### fact_use_phase

Scope 3 category 11, use of sold products: units x lifetime years x yearly kWh x the grid factor of the region of use. No Rest of world rows: no factor source identified. Factors are illustrative.

| Column | Type | Format | Hidden | Description |
| --- | --- | --- | --- | --- |
| date_key | int64 | 0 | yes |  |
| site_id | string |  | yes |  |
| source_id | string |  | yes |  |
| product_id | string |  | yes |  |
| region_id | string |  | yes |  |
| units | int64 | #,0 |  |  |
| net_sales_eur | double | #,0.00 |  |  |
| activity_amount | double | #,0 |  | Lifetime electricity of the units sold, kWh. |
| unit | string |  |  |  |
| emission_factor | double | #,0.000 |  | Illustrative grid factor in kilograms of CO2 equivalent per kWh. Not for real reporting. |
| tco2e | double | #,0.000000 |  | Tonnes of CO2 equivalent, as stored in the source data. |

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
| fact_sales.date_key | dim_date.date_key |
| fact_sales.site_id | dim_site.site_id |
| fact_sales.product_id | dim_product.product_id |
| fact_sales.region_id | dim_region.region_id |
| fact_use_phase.date_key | dim_date.date_key |
| fact_use_phase.site_id | dim_site.site_id |
| fact_use_phase.source_id | dim_source.source_id |
| fact_use_phase.product_id | dim_product.product_id |
| fact_use_phase.region_id | dim_region.region_id |
| fact_data_issue.date_key | dim_date.date_key |
| fact_data_issue.site_id | dim_site.site_id |
| fact_product_rating.date_key | dim_date.date_key |
| fact_product_rating.product_group | dim_product_group.product_group |
| fact_product_rating.criterion_id | dim_score_criterion.criterion_id |
| dim_product.product_group | dim_product_group.product_group |
| dim_product_code.product_id | dim_product.product_id |
| fact_budget.date_key | dim_date.date_key |
| fact_budget.site_id | dim_site.site_id |
| fact_budget.product_group | dim_product_group.product_group |
| fact_budget.region_id | dim_region.region_id |

## Row-level security roles

| Role | Filter |
| --- | --- |
| Baltics | `dim_region = dim_region[region_id] = "BAL"` |
| Estonia | `dim_site = dim_site[country] = "Estonia"` |
| Finland | `dim_site = dim_site[country] = "Finland"` |
| Nordics | `dim_region = dim_region[region_id] = "NOR"` |
| Rest of world | `dim_region = dim_region[region_id] = "ROW"` |
| Sweden | `dim_site = dim_site[country] = "Sweden"` |
| Western Europe | `dim_region = dim_region[region_id] = "WEU"` |
