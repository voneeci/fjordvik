# Fjordvik Power BI: one trusted view of the emissions figures

Fjordvik Manufacturing Oy's Group Sustainability Manager and its country managers need one
trusted view of the company's monthly greenhouse gas figures: totals by scope, site and
country, emissions per employee and per euro of revenue, and honest year-on-year change.
This Power BI semantic model and three-page report provide it. Country managers see only
their own sites, and every Data Analysis Expressions (DAX) measure is reconciled against
an independent Python calculation by automated tests. The model is saved as a Power BI
Project (PBIP): plain text files in git, written in Tabular Model Definition Language
(TMDL) and the Power BI enhanced report format (PBIR), so every change can be reviewed.

> **Synthetic data only.** Fjordvik Manufacturing Oy is a fictional company, and this is a
> portfolio project. No real company, client or person is described. The emission factors
> are **illustrative**, not cited, and must not be used for real reporting.

![Overview page](docs/images/overview.jpg)

## Problem

Fjordvik's charts used to be built by hand from copies of a central spreadsheet. Each
report redid the calculations, so two reports could disagree, and nobody could say which
version a chart used. When Tartu Warehouse opened in July 2024, a plain comparison of
totals made the company's growth look larger than it was. A country manager saw every
country or nothing. Management needs a model it can certify: under version control, with
measures that reconcile, clear rules for who sees what, and documentation a reviewer can
check.

## Approach

- **Model as code.** The whole model (tables, relationships, measures, security roles)
  and the report pages are text files, so every change shows up as a readable git diff.
- **A star schema** on the shared Fjordvik dataset: three dimensions (date, site, source)
  and two fact tables (emissions, site metrics), with single-direction relationships.
- **Twenty-four measures** in one `_Measures` table, grouped in five display folders
  (Emissions, Intensity, Activity, Time comparison, Data quality), each with a description
  and a format string. The Activity measures give each source in the unit the sites report
  it in (kWh, litres, kg, passenger-km, tonnes).
- **Grain handled explicitly.** Full-time equivalent employees (FTE) is a level, so
  `Average FTE` sums sites within each month and averages the months; summing FTE over a
  year would make emissions per FTE twelve times too small.
- **Like-for-like year-on-year change.** Only site-months with emissions in both years
  count. Without this, Tartu Warehouse (opened July 2024) shows +136.5% for 2025 instead of
  +10.7%, and the company shows +7.5% instead of +2.9%. The What changed page shows both
  views side by side, with `Emissions Change Including New Sites` beside the like-for-like
  measure.
- **No date-table shortcut.** The date table has one row per month, which Power BI will
  not mark as a date table (it needs every day). The prior-year measure shifts month keys
  in plain DAX instead of using `SAMEPERIODLASTYEAR`.
- **Row-level security (RLS).** Three roles (Finland, Sweden, Estonia) each filter
  `dim_site` by country; the filter flows to both fact tables.
- **In-model reconciliation.** `Reconciliation Difference (tCO2e)` compares stored tCO2e
  with activity times factor, row by row, on the Data quality page.
- **Governance documents:** [naming conventions](docs/naming-conventions.md), a generated
  [data dictionary](docs/data-dictionary.md), and a
  [certification checklist](docs/certification-checklist.md).

## Architecture

```
checksums checked by tests/test_data.py ──> ../data/tables/*.csv  (the shared dataset)
                                                    │  Power Query, en-US locale
                                                    ▼
FjordvikEmissions.SemanticModel/definition/   TMDL: tables, relationships, measures, roles
FjordvikEmissions.Report/definition/          PBIR: 8 pages, 58 visuals (from build_report.py)
                                                    │
               Power BI Desktop (local engine) <────┘
                       ▲
  tests/test_measures_live.py ──run_dax.ps1──┘  44 DAX queries, compared with tests/expected.py
```

| Page | Question it answers | Shows |
| --- | --- | --- |
| Introduction | What is this report? | The company and its six sites, who owns the figures, what each page answers, how to read the figures; a button for every page |
| Overview | How much does Fjordvik emit, and where? | Total and scope 1, 2 and 3 emissions, emissions per FTE, monthly trend, emissions by site |
| Emissions breakdown | What are the emissions made of? | Scope 1, 2 and 3 stacked by month, each scope's share, emissions by source, by country |
| Intensity and growth | Is Fjordvik getting cleaner as it grows? | Emissions per FTE and per million euros by month, revenue and headcount trends, like-for-like change by site |
| Energy and activity | What did the sites use? | Energy, fuel, refrigerant, flights and waste in their own units; energy by month; electricity by site (Tampere's solar panels from July 2024); an activity table by site |
| What changed | Why did emissions move on the prior year? | Like-for-like change against change including new sites, a 2025 waterfall of change by site, change by site and year |
| Sites | How do the six sites compare? | Per site: emissions, per FTE, per million euros, like-for-like change; scope 2 by month and site |
| Data quality | Do the figures reconcile? | Reconciliation difference, row count and sites reporting, by year |

Every chart has a title that says what it shows. Scopes, countries and sites keep one
colour on every page; each colour set was checked for colour-blind separation and contrast
on white, and the charts whose site colours are below 3:1 contrast share their page with a
site table.

## How to run

You need Power BI Desktop (free, Microsoft Store) and Python 3.10 or newer with pytest.

1. Clone the repository. If it is not at `C:\Users\reece\Projects\fjordvik` (this folder is `powerbi`),
   change the `DataFolder` value in
   `FjordvikEmissions.SemanticModel/definition/expressions.tmdl` (or in Desktop:
   **Transform data > Edit parameters**) to your clone's shared `data\tables` folder.
2. Open `FjordvikEmissions.pbip` in Power BI Desktop. It opens without data; select
   **Refresh now** on the yellow bar.
3. Run the tests:

```bash
python -m pytest
```

The offline tests always run. The 44 live measure tests run when Power BI Desktop has the
model open and refreshed; otherwise they are skipped.

To change the report, edit `scripts/build_report.py` and run it; to refresh the data
dictionary after a model change, run `scripts/build_data_dictionary.py`. Close Desktop
**without saving** before regenerating files it has open.

## Test evidence

```
python -m pytest -q
153 passed in 4.06s
```

(31 October 2026, Power BI Desktop open and refreshed; raw output in
`evidence/pytest-dashboard-2026-10-31.txt`.)

| Test file | What it proves |
| --- | --- |
| `test_measures_live.py` (44) | Every measure, run as DAX against the open model, matches an independent Python calculation from the CSVs: totals by year, scope, site and country; the scope and source measures under a conflicting filter (blank); reconciliation; revenue, average FTE and both intensities; blank per-euro intensity for the head office; prior year (blank for 2023); like-for-like change for the company, for Tartu and across all years; change including new sites (Tartu's first year counts in full; blank for 2023); each activity measure in its own unit; row and site counts; and each security role, including that the Sweden role sees nothing when filtered to Finland |
| `test_model_files.py` (106) | Table and column names match the shared schema; every measure has a description, format string and display folder, carries its unit in its name, divides with `DIVIDE()`, and contains no typed-in rates (only unit conversions and the date-key shift); three country roles; every field used by a visual exists in the model; page and visual names follow the PBIR rules; the report files are exactly what `build_report.py` writes |
| `test_docs.py`, `test_data.py` (3) | The data dictionary matches the model; the shared data matches its manifest's checksums, and `DataFolder` points at it |

The tests were checked by planting mistakes: a typed-in factor (`* 0.95`) in a measure and
a misspelt measure name in a visual were both caught. Writing the like-for-like test
exposed a fault in the first version of the change measure, which compared Tartu's
12 months of 2025 with its 6 months of 2024.

![Data quality page](docs/images/data-quality.jpg)

## Ownership

| Role | Who (fictional) |
| --- | --- |
| Business owner | Fjordvik Group Sustainability Manager |
| Technical owner | Data and AI Specialist |

## Limitations

- **Not published.** Endorsement, certification, scheduled refresh and RLS membership
  live in the Power BI Service; the [certification checklist](docs/certification-checklist.md)
  shows what would be reviewed.
- **Local file source.** The data comes from CSV files through a folder parameter. A
  production model would read a database or lakehouse, with a gateway for refresh.
- **Monthly grain** and illustrative emission factors (see the
  [data README](../data/README.md)).
- **Live tests need Desktop open.** In a team, the same DAX queries would run in CI
  (continuous integration) against a published model through the XMLA endpoint.
- **Screenshots are from the first version.** The two images on this page show the
  original Overview and Data quality pages, before the 31 October 2026 redesign.

## Next steps

- Publish to a Power BI workspace, assign RLS members, and run the live tests against the
  XMLA endpoint.
- Add a Power Automate flow that refreshes the model after each monthly data load
  (the `power-automate` folder).

## Licence

Code: MIT ([LICENSE](LICENSE)). Data: Creative Commons Attribution 4.0 (CC BY 4.0)
([data/LICENSE-DATA.md](../data/LICENSE-DATA.md)).
