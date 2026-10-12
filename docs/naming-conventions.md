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

## Columns

| Rule | Example | Why |
| --- | --- | --- |
| Keep the source column names | `activity_amount`, `tco2e` | A column can be traced back to the CSV without a mapping table |
| Hide key columns on fact tables | `fact_emissions[site_id]` hidden | Report builders use the dimension's column instead, so filters always flow through the relationship |
| Columns are not summarised by default (`summarizeBy: none`) | `emission_factor` | Summing a factor or a key gives a meaningless number; totals come from measures |

## Measures

| Rule | Example | Why |
| --- | --- | --- |
| Plain English name, unit in brackets | `Total Emissions (tCO2e)`, `Revenue (EUR)` | The unit travels with the number into every visual |
| Ratios say what they divide by | `Emissions per FTE (tCO2e)`, `Emissions per Million EUR (tCO2e)` | "Intensity" alone is ambiguous |
| Percentages end in `(%)` and are stored as fractions with a percent format | `Emissions Change vs Prior Year (%)` | 0.075 displays as 7.5% |
| Every measure has a description and a format string | | The description appears as a tooltip in Power BI |
| Measures are grouped in display folders | `Emissions`, `Intensity`, `Time comparison`, `Data quality` | Finding a measure takes seconds, not scrolling |
| Divide with `DIVIDE()`, never `/` between measures | `DIVIDE([Total Emissions (tCO2e)], [Average FTE])` | `DIVIDE` returns blank instead of an error when the divisor is zero or blank |
| No typed-in rates or factors | | Every factor lives in the data. Only unit conversions (1,000 kg per tonne, 1,000,000 euros per million) appear in formulas, and each is named in its measure's description |

## Roles

| Rule | Example | Why |
| --- | --- | --- |
| One role per country, named after the country | `Finland` | Matches how access is granted: a country manager sees their country |
| Filter the dimension, not the facts | `dim_site[country] = "Finland"` | One filter on `dim_site` flows to both fact tables through the relationships |
