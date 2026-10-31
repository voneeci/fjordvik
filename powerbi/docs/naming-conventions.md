# Naming conventions

These rules keep the model readable for report builders and predictable for anyone
writing Data Analysis Expressions (DAX) against it. `tests/test_model_files.py` checks
the ones a machine can check.

## Tables

| Rule | Example | Why |
| --- | --- | --- |
| Keep the shared schema's names exactly | `fact_emissions`, `dim_site` | The MCP connector and the Power Automate flows use the same names; one name per thing across all tools |
| `fact_` for tables of measured events, `dim_` for tables you slice by | `fact_site_metrics`, `dim_date` | The role of a table is clear from its name |
| A `_Measures` table holds every measure, and no data | `_Measures` | Report builders find all measures in one place; the underscore sorts it to the top |
| Small calculated tables that hold no figures are `dim_` too, and say what they hold | `dim_bridge_step` (waterfall steps), `dim_refresh` (last refresh time) | They are sliced by or read for labels, never summed (added 31 October 2026) |

## Columns

| Rule | Example | Why |
| --- | --- | --- |
| Keep the source column names | `activity_amount`, `tco2e` | A column can be traced back to the CSV without a mapping table |
| Hide key columns on fact tables | `fact_emissions[site_id]` hidden | Report builders use the dimension's column instead, so filters always flow through the relationship |
| Columns are not summarised by default (`summarizeBy: none`) | `emission_factor` | Summing a factor or a key gives a meaningless number; totals come from measures |

## Measures

| Rule | Example | Why |
| --- | --- | --- |
| Plain English name, unit in brackets | `Total Emissions (tCO2e)`, `Revenue (EUR)`, `Freight Transport (tonne-km)` | The unit travels with the number into every visual |
| Ratios say what they divide by | `Emissions per FTE (tCO2e)`, `Emissions per Million EUR (tCO2e)` | "Intensity" alone is ambiguous |
| Percentages end in `(%)` and are stored as fractions with a percent format | `Emissions Change vs Prior Year (%)` | 0.075 displays as 7.5% |
| Every measure has a description and a format string | | The description appears as a tooltip in Power BI |
| Measures are grouped in display folders | `Emissions`, `Market-based scope 2`, `Value chain`, `Sales`, `Price, volume and mix`, `Portfolio balance`, `Product sustainability`, `Scorecard`, `Intensity`, `Activity`, `Time comparison`, `Data quality`, `Budget`, `Bridge`, `Text` | Finding a measure takes seconds, not scrolling |
| A method's source is named in its description | `Price Effect (EUR)`: ACCA F5, prior year as standard | Anyone can check the formula against its source |
| Counts and scores carry no unit | `Units Sold`, `Data Issues`, `Weighted Score` | There is no unit to bracket |
| Text measures live in the `Text` folder, named for what they say, with no unit or format string | `Overview Message`, `Net Sales Context`, `Report Footer` | They build the words on the pages (titles, card context lines, the footer) from the data, so the words never go stale (31 October 2026) |
| Market-based figures say so in the name; location-based is the default | `Scope 2 Market-based Emissions (tCO2e)` beside `Scope 2 Emissions (tCO2e)` | Nobody adds the two methods together by mistake |
| Divide with `DIVIDE()`, never `/` between measures | `DIVIDE([Total Emissions (tCO2e)], [Average FTE])` | `DIVIDE` returns blank instead of an error when the divisor is zero or blank |
| No typed-in rates or factors | | Every factor lives in the data. Only unit conversions (1,000 kg per tonne, 1,000,000 euros per million) appear in formulas, and each is named in its measure's description |

## Roles

| Rule | Example | Why |
| --- | --- | --- |
| One role per country, named after the country | `Finland` | Matches how access is granted: a country manager sees their country |
| Filter the dimension, not the facts | `dim_site[country] = "Finland"` | One filter on `dim_site` flows to every fact table through the relationships |
| Sales region roles are named after the region | `Nordics`, `'Western Europe'` | Matches how access is granted: a region manager sees their region |
| Exception: region roles also deny the site tables | `fact_emissions = FALSE()` | Site emissions and finance revenue have no region, so a region filter cannot reach them; denying them keeps a region manager to their own sales (decided 31 October 2026) |
