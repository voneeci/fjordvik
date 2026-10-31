# Fjordvik data: the governed emissions dataset

Fjordvik Manufacturing Oy reports the greenhouse gas emissions of its six sites in
Finland, Sweden and Estonia every month. This folder holds the one dataset behind those
figures: 36 months (January 2023 to December 2025) of emissions by site and source, with
each site's revenue and headcount. The Power BI report, the Claude connector and the
intake checks all read it, so every answer comes from the same numbers. All four parts are
folders of the [fjordvik](https://github.com/voneeci/fjordvik) repository:

| Folder | What it does for the business |
| --- | --- |
| `data` (this one) | The governed dataset, with fixed names, checksums and quality tests |
| [`mcp`](../mcp) | A Model Context Protocol (MCP) connector that lets Claude answer questions from the data |
| [`powerbi`](../powerbi) | The Power BI model and report, with Data Analysis Expressions (DAX) measures |
| [`power-automate`](../power-automate) | Power Automate flows that take in and check each site's monthly file |

> **Synthetic data only.** Fjordvik Manufacturing Oy is a fictional company, and this is a
> portfolio project. No real company, client or person is described. The emission factors
> are **illustrative**, not cited, and must not be used for real reporting. See
> [docs/emission-factors.md](docs/emission-factors.md).

## Problem

Fjordvik's figures used to live in copies of a central spreadsheet. Copies drift, so two
charts built a week apart could disagree, and nobody could prove which version a report
used. The business needs one dataset that every report reads: fixed table and column
names that tools can rely on, checks that catch impossible values, and a way to prove the
files have not been edited by hand.

In this portfolio version the dataset is generated, so it is safe to publish. The
generator exists only because there is no real data: it invents plausible figures for
six fictional sites. It does not combine the sites' files; in the real process the
Power Automate intake flow does that, adding each accepted site file to the central
Emissions list. The generated `tables/` folder stands in for that list, and for the
revenue and headcount that finance and HR would supply.

## Approach

- **Generated, not hand-typed.** A Python script builds every table from a short
  configuration file (`src/fjordvik_data/config.py`). It uses the Python standard library
  only, so it needs no installs.
- **Deterministic.** A fixed seed, and a separate random stream for each site and source,
  give byte-identical files on every run. Changing one site never changes the others.
- **A star schema.** Three dimension tables (date, site, source) and two fact tables
  (emissions, site metrics), the shape Power BI models work best with.
- **A story in the data**, so the dashboards and Claude have something to find:
  - heating peaks in winter, and production and revenue grow about 4 to 5% a year;
  - factories slow down in July for the summer holidays;
  - Tampere Plant installs rooftop solar in July 2024, which cuts its purchased
    electricity in spring and summer but barely in winter;
  - Tartu Warehouse opens in July 2024 and ramps up over three months. Its data starts in
    its first month, with nothing backfilled before it;
  - the head office books no revenue, so emissions per euro must be blank for it, not an
    error.
- **Tested.** 24 automated tests check the schema, data quality rules, the story events and
  that the committed files match the code.

## Architecture

```
config.py ──> generate.py ──> tables/*.csv + manifest.json ──> read directly by
 (sites,       (builds the       (five tables, row counts,      │
  sources,      five tables)      SHA-256 checksums)            ├─> mcp/
  factors,                                                      ├─> powerbi/
  story)                                                        └─> power-automate/
```

This `data/tables` folder is the project's one copy of the dataset: the other three parts
read it in place and check it against `manifest.json` in their own tests.

Shared schema (names are a contract; the other three parts depend on them):

| Table | Columns | Grain |
| --- | --- | --- |
| `dim_date` | date_key, date, year, quarter, month, month_name | One row per month |
| `dim_site` | site_id, site_name, country, site_type | One row per site |
| `dim_source` | source_id, source_name, scope, category | One row per emission source |
| `fact_emissions` | date_key, site_id, source_id, activity_amount, unit, emission_factor, tco2e | One row per month, site and source |
| `fact_site_metrics` | date_key, site_id, revenue_eur, fte | One row per month and site |

`tco2e` is tonnes of carbon dioxide equivalent: `activity_amount × emission_factor / 1000`,
with the factor in kilograms per unit. `fte` is full-time equivalent employees.
`date_key` is the first day of the month as a number, for example `20230101`.

**Sites:** Tampere Plant, Helsinki Head Office and Oulu Warehouse (Finland); Gothenburg
Plant (Sweden); Tallinn Plant and Tartu Warehouse (Estonia).

**Sources:** natural gas, diesel, liquefied petroleum gas (LPG) and refrigerant leakage
(scope 1); purchased electricity and district heating (scope 2, location-based);
business flights and waste to landfill (scope 3).

### Dataset at a glance

| Table | Rows |
| --- | --- |
| dim_date | 36 |
| dim_site | 6 |
| dim_source | 8 |
| fact_emissions | 1,422 |
| fact_site_metrics | 198 |

Total emissions (illustrative): 9,454.0 tCO2e in 2023, 10,158.2 in 2024 and 10,921.8
in 2025. Tallinn Plant is the largest emitter because Estonia's illustrative grid factor
is the highest.

## How to run

You need Python 3.10 or newer. No other installs are needed to generate the data.

```bash
git clone https://github.com/voneeci/fjordvik.git
cd fjordvik/data
python -m pip install -e ".[dev]"
python -m fjordvik_data --out tables
python -m pytest
```

Without installing, from the repository folder in PowerShell:

```powershell
$env:PYTHONPATH = "src"; python -m fjordvik_data --out tables
```

To use the data elsewhere, take the CSV files from `tables/` at a known commit and check
them against the SHA-256 checksums in `tables/manifest.json`. After any change, rerun the
tests of every part, because they all read this folder.

## Test evidence

```
python -m pytest -q
........................                                                 [100%]
24 passed in 0.38s
```

| Test file | What it proves |
| --- | --- |
| `test_schema.py` | Table and column names match the shared schema exactly; 36 months; dates and keys agree |
| `test_integrity.py` | Unique keys; every fact row joins to its dimensions; `tco2e` equals the formula; no negatives; one unit per source; factors match the configuration; every site reports every source every month from its opening (a zero is a row, never a gap) |
| `test_story.py` | The solar effect is visible against a control site; Tartu starts in July 2024; heating peaks in winter; revenue grows |
| `test_generator.py` | The solar logic cuts purchases by exactly the configured share; other sites are untouched; the ramp-up only applies to new sites |
| `test_reproducible.py` | Regenerating gives byte-identical files; the manifest's checksums and row counts match |

## Limitations

- **Illustrative emission factors**, one per source for the whole period. Real reporting
  needs cited factors for each year and country.
- **Location-based scope 2 only.** The schema has one factor per row, so a market-based
  figure (which would show the effect of buying renewable electricity) is not included.
- **Monthly grain.** No daily or meter-level data.
- **Simple patterns.** Seasonality, growth and noise are smooth formulas. Real data has
  billing lags, estimates, restatements and one-off events.
- The clean dataset has no data quality problems by design. Planted problems (a unit
  error, a missing month, a duplicate row) live only in the intake files of
  `power-automate`.

## Next steps

- Add market-based scope 2 if the schema is ever extended.
- Add yearly factor versions to show how restating a factor changes past totals.

## Licence

Code: MIT ([LICENSE](LICENSE)). Data: Creative Commons Attribution 4.0 (CC BY 4.0)
([LICENSE-DATA.md](LICENSE-DATA.md)).
