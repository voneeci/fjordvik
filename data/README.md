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

## Where the data comes from

| Data | Comes from | Owner | System | How often | Lands in |
| --- | --- | --- | --- | --- | --- |
| Activity: fuel, energy, refrigerant, flights, waste | Each site's invoices, meter readings, fuel card statements, service logs and travel and waste reports, entered in the site's monthly workbook | Site Energy Coordinator at each site | Excel workbook, uploaded to SharePoint and checked by the Power Automate intake flow | Monthly, early the next month | `fact_emissions` (`activity_amount`, `unit`) |
| Emission factors | A published factor set for each country (illustrative in this project) | Group Sustainability Manager | SharePoint list *EmissionFactors* | When a factor set is updated | `fact_emissions` (`emission_factor`), looked up by the intake flow, which works out `tco2e` |
| Sites and sources | The company's site register and its list of emission sources | Group Sustainability Manager | SharePoint lists *Sites* and *Sources* | When a site opens or a source changes | `dim_site`, `dim_source` |
| Revenue | The finance system, after each monthly close | Group Financial Controller | Monthly export (not designed yet) | Monthly | `fact_site_metrics` (`revenue_eur`) |
| Headcount | The HR system, as full-time equivalent employees (FTE) | HR Manager | Monthly export (not designed yet) | Monthly | `fact_site_metrics` (`fte`) |
| Calendar | The reporting months | Data and AI Specialist | Built with the dataset | Once per month added | `dim_date` |

The full monthly process, step by step with owners and checks, is in the
[process map](https://voneeci.github.io/fjordvik/docs/process-map.html).

## Approach

- **One governed dataset.** There is one copy, in `tables/`. The Power BI model, the
  Claude connector and the intake checks read it in place; nothing keeps its own copy.
- **A star schema.** Three dimension tables (date, site, source) and two fact tables
  (emissions, site metrics), the shape Power BI models work best with.
- **Names are a contract.** Every part depends on the table and column names below, so a
  test fails if anyone renames one.
- **A zero is a row, never a gap.** Every open site reports every source every month, so
  a missing row means a missing report, not zero emissions.
- **No backfilling.** A site's figures start in its first month; nothing is invented for
  months before it opened.
- **Provably unedited.** `tables/manifest.json` records each file's row count and SHA-256
  checksum, and every part's tests check the files against it before relying on them.
- **Tested.** 24 automated tests check the schema, the data quality rules, that the
  business events below show in the data, and that the files match their manifest.

### What happened in the period

The figures carry the business's own events, which the report and Claude should find:

- heating peaks in winter, and production and revenue grow about 4 to 5% a year;
- the plants slow down in July for the summer holidays;
- Tampere Plant installed rooftop solar panels in July 2024, which cut its bought
  electricity in spring and summer but barely in winter;
- Tartu Warehouse opened in July 2024 and ramped up over three months, so its figures
  start that month;
- the head office books no revenue, so its emissions per euro must be blank, not an error.

## Architecture

```
Site workbooks ──> Power Automate intake flow (ten rules) ──> central Emissions list ──┐
Reference lists: sites, sources, emission factors ───────────────────────────────────┤
Finance (revenue) and HR (headcount) ─────────────────────────────────────────────────┤
                                                                                      ▼
                          governed dataset: five tables + manifest.json (SHA-256 checksums)
                                                       │
                                  ┌────────────────────┼────────────────────┐
                                  ▼                    ▼                    ▼
                         Power BI report      Claude connector     intake checks (last
                           (powerbi/)              (mcp/)          month, last year)
```

In this repository, `tables/` holds the dataset as five CSV files and their manifest, with
synthetic figures in exactly the shape the central list and the finance and HR exports
would produce.

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

You need Python 3.10 or newer.

```bash
git clone https://github.com/voneeci/fjordvik.git
cd fjordvik/data
python -m pip install -e ".[dev]"
python -m pytest
```

To use the data elsewhere, take the CSV files from `tables/` at a known commit and check
them against the SHA-256 checksums in `tables/manifest.json`.

## Test evidence

```
python -m pytest -q
24 passed in 0.23s
```

(31 October 2026; raw output in `evidence/pytest-tables-2026-10-31.txt`.)

| Test file | What it proves |
| --- | --- |
| `test_schema.py` | Table and column names match the shared schema exactly; 36 months; dates and keys agree |
| `test_integrity.py` | Unique keys; every fact row joins to its dimensions; `tco2e` equals the formula; no negatives; one unit per source; factors match the reference values; every site reports every source every month from its opening (a zero is a row, never a gap) |
| `test_story.py` | The business events show in the data: the solar effect against a control site; Tartu starting in July 2024; winter heating peaks; revenue growth |
| `test_generator.py`, `test_reproducible.py` | The demonstration data is built as described below, and the files match their manifest's checksums and row counts |

## Limitations

- **Illustrative emission factors**, one per source and country for the whole period.
  Real reporting needs cited factors for each year and country.
- **Location-based scope 2 only.** The schema has one factor per row, so a market-based
  figure (which would show the effect of buying renewable electricity) is not included.
- **Monthly grain.** No daily or meter-level data.
- **Smooth synthetic patterns.** Seasonality, growth and noise follow simple patterns.
  Real data has billing lags, estimates, restatements and one-off events.
- The dataset has no data quality problems by design. Planted problems (a unit error, a
  missing month, a duplicate row) live only in the intake test files of `power-automate`.
- The finance and HR exports for revenue and headcount are not designed yet.

## Next steps

- Design the monthly revenue and headcount exports from the finance and HR systems.
- Add market-based scope 2 if the schema is ever extended.
- Add yearly factor versions to show how restating a factor changes past totals.

## For developers: the demonstration data

Fjordvik is fictional, so `tables/` cannot come from real sites. For this portfolio the
files are made by a small generator instead: `src/fjordvik_data/generate.py` builds every
table from the settings in `src/fjordvik_data/config.py` (sites, sources, illustrative
factors, and the business events above). It uses the Python standard library only, and a
fixed seed with a separate random stream for each site and source, so every run gives
byte-identical files and changing one site never changes the others.

```bash
python -m fjordvik_data --out tables
```

Without installing, from this folder in PowerShell:

```powershell
$env:PYTHONPATH = "src"; python -m fjordvik_data --out tables
```

Commit the code and the regenerated files together, then rerun every part's tests,
because they all read `tables/`. With real data, the generator, its settings and its two
tests (`test_generator.py`, `test_reproducible.py`) would be retired: the site workbooks,
the intake flow and the finance and HR exports would fill `tables/` instead, and the
schema, the quality tests and the manifest would stay as they are.

## Licence

Code: MIT ([LICENSE](LICENSE)). Data: Creative Commons Attribution 4.0 (CC BY 4.0)
([LICENSE-DATA.md](LICENSE-DATA.md)).
