# Fjordvik data: the governed emissions dataset

Fjordvik Manufacturing Oy makes electric pumps and pump systems for water utilities,
industry and buildings, from six sites in Finland, Sweden and Estonia
([company profile](../docs/company-profile.md)). It reports its greenhouse gas emissions
every month. This folder holds the one dataset behind those figures: 36 months (January
2023 to December 2025) of emissions by site and source, each site's revenue and
headcount, the value chain (market-based scope 2 from energy contracts, and scope 3 from
purchases, freight, the upstream emissions of the energy used and the lifetime electricity
of the pumps sold), and the product portfolio: sales by product and region from the
enterprise resource planning (ERP) system, cleaned and reconciled to finance by SQL. The Power BI report, the Claude connector and the
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
| Energy contracts and guarantees of origin (GOs) | Electricity supplier contracts and GO cancellation statements | Group Sustainability Manager | Contract register, from the suppliers' statements | Yearly, and when a contract starts or ends | `dim_contract`; `fact_scope2_market`, worked out from the site kWh and the residual mix of each country |
| Purchases | The purchase ledger: supplier, spend category, euros, by site and month | Procurement Manager | Enterprise resource planning (ERP) system, monthly export | Monthly, after the close | `dim_supplier`, `fact_purchases` (spend-based scope 3 category 1) |
| Freight | Freight invoices and shipments (tonnes, origin, destination, mode), with the Incoterms on each order saying who pays | Logistics Manager | Transport management system and the carriers' invoices | Monthly | `fact_freight` (scope 3 categories 4 and 9) |
| Upstream fuel and grid losses | Nothing new: the fuel and kWh the sites already report | Group Sustainability Manager | Worked out from `fact_emissions` | Monthly, with the site data | `fact_energy_upstream` (scope 3 category 3) |
| Scope 3 category list | The 15 Greenhouse Gas (GHG) Protocol categories, with a status and reason for each | Group Sustainability Manager | Reference list, reviewed with the yearly inventory | Yearly | `dim_scope3_category` |
| Sales order lines | Every invoiced line: business unit, local item number, customer region, quantity, amount, cost, currency | Regional controllers | Oracle Fusion Cloud ERP, Data Extraction tool: ZIP files of CSV with a SHA-256 manifest, landed in storage and loaded by the SQL in `sql/` | Monthly, after the close | `fact_sales`, `fact_data_issue` |
| Product classification | Each business unit's local item number for each global product, and the hierarchy (family, group, model) | Portfolio governance | Mapping table kept with the ERP master data | When a product or code is added | `dim_product_code`, `dim_product`, `dim_product_group` |
| Product specification | Rated power, yearly electricity use and lifetime of each model | Product Managers, from engineering | Product data sheets | When a model changes | `dim_product` |
| Exchange rates | ECB monthly average EUR/SEK reference rates | Group Financial Controller | ECB Data Portal (published) | Monthly | `reference/ecb_eur_sek_monthly.csv`, used by the SQL |
| Scorecard ratings and weights | Each quarter's 1 to 10 rating per product group and criterion; the weight of each criterion | Portfolio governance, with Product Managers | Quarterly review record | Quarterly; weights yearly | `fact_product_rating`, `dim_score_criterion` |

**The ERP extract in `erp-extract/` is simulated.** It follows the shape of Oracle's Data
Extraction tool, which Oracle's documentation calls the long-term replacement for its BI
Cloud Connector: monthly ZIP files of CSV with a manifest of SHA-256 checksums. It carries
the problems real extracts have: legacy item numbers, codes not yet mapped, a re-sent
file and a month with no currency code. The SQL in `sql/` checks the manifest, stages the
lines, removes duplicates, converts kronor at the ECB rate, maps to the global
classification, validates, publishes, and reconciles to finance revenue to the cent.
What it cannot resolve (unmapped codes) it quarantines and lists in `fact_data_issue`.
| Calendar | The reporting months | Data and AI Specialist | Built with the dataset | Once per month added | `dim_date` |

The full monthly process, step by step with owners and checks, is in the
[process map](https://voneeci.github.io/fjordvik/docs/process-map.html).

## Approach

- **One governed dataset.** There is one copy, in `tables/`. The Power BI model, the
  Claude connector and the intake checks read it in place; nothing keeps its own copy.
- **A star schema.** Dimension tables (date, site, source, scope 3 category, supplier,
  contract) and fact tables (site emissions, site metrics, and one table per value-chain
  data source), the shape Power BI models work best with.
- **One table per data source.** What the sites report (`fact_emissions`) stays apart
  from what comes from the ERP system, the transport system and the energy contracts, so
  each table has one owner and one collection routine.
- **Location-based totals.** Totals add scope 1, location-based scope 2 and the scope 3
  rows. Market-based scope 2 covers the same kWh with contract factors and is reported
  beside the total, never added to it.
- **Every scope 3 category accounted for.** `dim_scope3_category` lists all 15 with a
  status and a reason, as the GHG Protocol Scope 3 Standard requires for any category
  left out.
- **Names are a contract.** Every part depends on the table and column names below, so a
  test fails if anyone renames one.
- **A zero is a row, never a gap.** Every open site reports every source every month, so
  a missing row means a missing report, not zero emissions.
- **No backfilling.** A site's figures start in its first month; nothing is invented for
  months before it opened.
- **Provably unedited.** `tables/manifest.json` records each file's row count and SHA-256
  checksum, and every part's tests check the files against it before relying on them.
- **Tested.** 58 automated tests check the schema, the data quality rules, the
  value-chain and portfolio rules, that each planted extract problem is caught, that the
  business events below show in the data, and that the files match their manifest.

### What happened in the period

The figures carry the business's own events, which the report and Claude should find:

- heating peaks in winter, and production and revenue grow about 4 to 5% a year;
- the plants slow down in July for the summer holidays;
- Tampere Plant installed rooftop solar panels in July 2024, which cut its bought
  electricity in spring and summer but barely in winter;
- Tartu Warehouse opened in July 2024 and ramped up over three months, so its figures
  start that month;
- the head office books no revenue, so its emissions per euro must be blank, not an error;
- Gothenburg Plant buys hydro guarantees of origin for all its electricity, so its
  market-based electricity is zero; Tampere Plant covers 60% of its electricity with wind
  guarantees of origin from January 2025, which halves its market-based figure.

## Architecture

```
Site workbooks ──> Power Automate intake flow (ten rules) ──> central Emissions list ──┐
Reference lists: sites, sources, emission factors, scope 3 categories ────────────────┤
Finance (revenue) and HR (headcount) ─────────────────────────────────────────────────┤
ERP purchase ledger, transport system, energy contracts ─────────────────────────────┤
                                                                                      ▼
                          governed dataset: twelve tables + manifest.json (SHA-256 checksums)
                                                       │
                                  ┌────────────────────┼────────────────────┐
                                  ▼                    ▼                    ▼
                         Power BI report      Claude connector     intake checks (last
                           (powerbi/)              (mcp/)          month, last year)
```

In this repository, `tables/` holds the dataset as twelve CSV files and their manifest,
with synthetic figures in exactly the shape the central list and the finance, HR, ERP,
transport and contract exports would produce.

Shared schema (names are a contract; the other three parts depend on them):

| Table | Columns | Grain |
| --- | --- | --- |
| `dim_date` | date_key, date, year, quarter, month, month_name | One row per month |
| `dim_site` | site_id, site_name, country, site_type | One row per site |
| `dim_source` | source_id, source_name, scope, category, scope3_category, method | One row per emission source |
| `fact_emissions` | date_key, site_id, source_id, activity_amount, unit, emission_factor, tco2e | One row per month, site and source reported by the sites |
| `fact_site_metrics` | date_key, site_id, revenue_eur, fte | One row per month and site |
| `dim_scope3_category` | scope3_category, category_name, status, reason | One row per GHG Protocol scope 3 category (15) |
| `dim_contract` | contract_id, site_id, source_id, supplier_name, instrument, start_date_key, end_date_key, covered_share | One row per energy contract |
| `fact_scope2_market` | date_key, site_id, source_id, contract_id, instrument, activity_amount, unit, emission_factor, tco2e | One row per month, site, source and instrument |
| `fact_energy_upstream` | date_key, site_id, source_id, based_on_source_id, activity_amount, unit, emission_factor, tco2e | One row per month, site and the source it is worked out from |
| `dim_supplier` | supplier_id, supplier_name, country, spend_category | One row per supplier |
| `fact_purchases` | date_key, site_id, source_id, supplier_id, spend_category, method, activity_amount, unit, emission_factor, tco2e | One row per month, site and supplier |
| `fact_freight` | date_key, site_id, source_id, direction, mode, paid_by, tonnes, distance_km, activity_amount, unit, emission_factor, tco2e | One row per month, site, direction, mode and payer |

`tco2e` is tonnes of carbon dioxide equivalent: `activity_amount × emission_factor / 1000`,
with the factor in kilograms per unit, in every table that has it. New units:
euros (`EUR`) for purchases and tonne-kilometres (`tonne-km`, tonnes moved times
kilometres) for freight. `fte` is full-time equivalent employees.
`date_key` is the first day of the month as a number, for example `20230101`.

**Sites:** Tampere Plant, Helsinki Head Office and Oulu Warehouse (Finland); Gothenburg
Plant (Sweden); Tallinn Plant and Tartu Warehouse (Estonia).

**Sources reported by the sites:** natural gas, diesel, liquefied petroleum gas (LPG)
and refrigerant leakage (scope 1); purchased electricity and district heating (scope 2);
business flights (scope 3 category 6) and waste to landfill (category 5).

**Value-chain sources:** upstream emissions of purchased fuels and transmission and
distribution losses (category 3, parts a and c); purchased goods and services (category
1, spend-based); freight paid by Fjordvik (category 4); outbound freight paid by
customers (category 9).

**Scope 3 categories not calculated, with the reason in `dim_scope3_category`:** 2, 7,
11 and 12 are relevant but not yet calculated (11, use of sold products, is likely the
largest for a pump maker and needs product and sales data); 8, 10, 13, 14 and 15 are
not relevant to Fjordvik; 3(b), 5 and 6 are counted only in part.

### The SQL checks

| Check | Fails when | What happens |
| --- | --- | --- |
| Manifest | A ZIP is missing, extra or changed | Nothing is loaded |
| Duplicates are exact copies | One line id carries two different lines | Nothing is loaded |
| Business units, exchange rates, regions, products known | A code has no reference row | Nothing is loaded |
| Currency matches the ledger | A line is in another currency than its business unit's ledger | Nothing is loaded |
| Quantities positive, amounts not negative | A line has zero or negative units, or a negative amount | Nothing is loaded |
| Reconciles to finance | Sales plus quarantined lines differ from revenue in any site-month | Nothing is loaded |

Problems the rules can fix are fixed and logged: exact duplicates are removed, a missing
currency code takes the business unit's ledger currency. Unmapped item numbers are
quarantined for portfolio governance. All four planted issues appear in `fact_data_issue`.

### Dataset at a glance

| Table | Rows |
| --- | --- |
| dim_date | 36 |
| dim_site | 6 |
| dim_source | 13 |
| fact_emissions | 1,422 |
| fact_site_metrics | 198 |
| dim_scope3_category | 15 |
| dim_contract | 2 |
| fact_scope2_market | 444 |
| fact_energy_upstream | 828 |
| dim_supplier | 14 |
| fact_purchases | 864 |
| fact_freight | 666 |
| dim_product_group | 10 |
| dim_product | 24 |
| dim_region | 4 |
| dim_product_code | 26 |
| fact_sales | 3,379 |
| fact_data_issue | 4 |
| fact_use_phase | 1,940 |
| dim_score_criterion | 6 |
| fact_product_rating | 720 |

Total emissions (illustrative, location-based):

| Year | Scope 1 | Scope 2 location-based | Scope 3 | Total | Scope 2 market-based |
| --- | --- | --- | --- | --- | --- |
| 2023 | 3,482.8 | 5,294.0 | 2,364,017.1 | 2,372,794.0 | 8,003.2 |
| 2024 | 3,745.2 | 5,718.1 | 2,375,528.8 | 2,384,992.1 | 8,437.6 |
| 2025 | 3,948.6 | 6,243.6 | 2,318,494.4 | 2,328,686.6 | 7,383.5 |

Use of sold products (category 11), the lifetime electricity of the pumps sold, is 97% of
the 2025 total; purchased goods and services comes next. Sales: EUR 137.4 million in
2023, 146.2 million in 2024 and 154.7 million in 2025, at a margin of 39.0%, 39.7% and
40.2%. Market-based scope 2 is higher
than location-based because each country's residual mix is higher than its grid
average; it falls in 2025 when Tampere's wind guarantees of origin start. Tampere Plant
is the largest emitter overall (its large process pumps carry the most use-phase
emissions), and Tallinn Plant has the largest scope 2, because Estonia's illustrative grid
factor is the highest.

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
58 passed in 4.23s
```

(31 October 2026; raw output in `evidence/pytest-portfolio-2026-10-31.txt`.)

| Test file | What it proves |
| --- | --- |
| `test_schema.py` | Table and column names match the shared schema exactly; 36 months; dates and keys agree |
| `test_integrity.py` | Unique keys; every fact row joins to its dimensions; `tco2e` equals the formula; no negatives; one unit per source; factors match the reference values; every site reports every source every month from its opening (a zero is a row, never a gap) |
| `test_value_chain.py` | Unique keys and joins in the value-chain tables; `tco2e` equals the formula; market-based scope 2 covers exactly the location-based kWh, with contract or residual-mix factors; category 3 rows are worked out from the reported fuel and kWh; purchases are spend-based in euros; freight is tonnes times distance, and customer-paid outbound freight is category 9; all 15 scope 3 categories have a status and a reason |
| `test_portfolio.py` | Sales plus quarantined lines equal finance revenue to the cent; margin is sales minus cost; every product sells every month; the four planted issues are listed; kronor convert at the ECB rate (recomputed from the raw extract); category 11 follows its method and leaves out Rest of world; ratings are 1 to 10, one per quarter; and nine planted problems (changed checksum, file not in the manifest, exact and conflicting duplicates, unmapped code, missing currency, kronor labelled as euros, unknown region, missing line) each hit their own check |
| `test_story.py` | The business events show in the data: the solar effect against a control site; Tartu starting in July 2024; winter heating peaks; revenue growth; Gothenburg's guarantees of origin covering all its electricity; Tampere's from 2025; purchased goods as the largest category |
| `test_generator.py`, `test_reproducible.py` | The demonstration data is built as described below, the files match their manifest's checksums and row counts, and the four original tables kept their checksums when the value chain was added |

## Limitations

- **Illustrative emission factors**, one per source and country for the whole period.
  Real reporting needs cited factors for each year and country.
- **Scope 3 is incomplete.** Categories 2, 7 and 12 are not yet calculated, category 11
  leaves out Rest of world, and category 1 is spend-based, the least precise method.
- **The ERP extract is simulated**, and the sales split finance revenue by settings, not
  from real orders.
- **Freight uses one average distance per lane**, and category 3(b) is not calculated
  because no factor source for Finland, Sweden or Estonia has been found.
- **Monthly grain.** No daily or meter-level data.
- **Smooth synthetic patterns.** Seasonality, growth and noise follow simple patterns.
  Real data has billing lags, estimates, restatements and one-off events.
- The dataset has no data quality problems by design. Planted problems (a unit error, a
  missing month, a duplicate row) live only in the intake test files of `power-automate`.
- The finance and HR exports for revenue and headcount are not designed yet.

## Next steps

- Design the monthly revenue and headcount exports from the finance and HR systems.
- Find a grid factor source for Rest of world, then categories 2, 7 and 12.
- Replace spend-based rows with supplier-specific data for the largest suppliers.
- Add yearly factor versions to show how restating a factor changes past totals.

## For developers: the demonstration data

Fjordvik is fictional, so `tables/` cannot come from real sites. For this portfolio the
files are made by a small generator instead: `src/fjordvik_data/generate.py` builds every
table from the settings in `src/fjordvik_data/config.py` (sites, sources, suppliers,
freight lanes, energy contracts, products, regions, illustrative factors, and the business
events above). `src/fjordvik_data/portfolio.py` turns each site-month's revenue into sales
order lines, writes them as the simulated extract in `erp-extract/` with its planted
problems, and runs the SQL in `sql/` to publish `fact_sales`, so the tables come out of the
same pipeline a company would run. It uses the Python standard library only, and a
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
the intake flow and the finance, HR, ERP, transport and contract exports would fill
`tables/` instead, and the
schema, the quality tests and the manifest would stay as they are.

## Licence

Code: MIT ([LICENSE](LICENSE)). Data: Creative Commons Attribution 4.0 (CC BY 4.0)
([LICENSE-DATA.md](LICENSE-DATA.md)).
