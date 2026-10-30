# How the Fjordvik portfolio was built

This guide walks through how the four Fjordvik projects were built, in the order they
were built, and why each main decision was made. The folder READMEs hold the full detail
and test evidence; this page shows how the parts fit together and the reasoning behind them.

> **Synthetic data only.** Fjordvik Manufacturing Oy is a fictional manufacturer. No real
> company, client or person is described. The emission factors are **illustrative**, not
> cited, and must not be used for real reporting.

## At a glance

| Part | Skill it shows | Built | Tests |
| --- | --- | --- | --- |
| [`data`](../data) | Reproducible synthetic data with a fixed schema and quality tests | 12 October 2026 | 24 |
| [`mcp`](../mcp) | A Model Context Protocol (MCP) server that gives Claude safe, read-only access to the data | 12 October 2026 | 48 |
| [`powerbi`](../powerbi) | A version-controlled Power BI semantic model whose every measure is reconciled against Python | 12 to 16 October 2026 | 100 |
| [`power-automate`](../power-automate) | Power Automate flows that take in, check and chase monthly site files, designed and tested offline | 12 October 2026 | 26 |

All 198 tests passed on 30 October 2026, including the 31 Power BI tests that run live
Data Analysis Expressions (DAX) queries against the open model. The raw output is saved
in each folder's `evidence/` folder.

## The order of the build

```
1. data             the contract: five tables, fixed names, checksums
      │
      ├──> 2. mcp             Claude asks questions of the data
      ├──> 3. powerbi         dashboards and governed measures
      └──> 4. power-automate  how the monthly data would arrive
```

The data came first because the other three parts depend on its table and column names.
Each consumer keeps its own copy of the data and checks every file against the SHA-256
checksums in `data/data/manifest.json`, so all three always show the same numbers and
each folder runs and tests on its own.

## 1. The dataset (`data`)

**What it is.** A Python generator that writes 36 months (January 2023 to December 2025)
of monthly emissions and site metrics for six sites in Finland, Sweden and Estonia, as a
five-table star schema: three dimensions (date, site, source) and two fact tables
(emissions, site metrics).

**Key decisions.**

| Choice | Picked | Over | Why |
| --- | --- | --- | --- |
| How the data is made | A generator script | A hand-made spreadsheet | Rebuildable, reviewable in git, and a change is one line of configuration |
| Randomness | A fixed seed, one random stream per site and source | One stream for everything | The same output on every run; adding a site never shifts other sites' numbers |
| Shape | Star schema | One wide table | What Power BI is designed for: simpler DAX, faster filters, no double counting |
| Zeros | A row with 0 | No row | A missing row could mean "nothing to report" or "forgot to report" |
| Proof the files match the code | Checksums in a manifest and a regenerate-and-compare test | Trust | Anyone can prove the data was not edited by hand |

**A story in the data,** so the dashboards and Claude have something to find: winter
heating peaks, a July slowdown, rooftop solar at Tampere Plant from July 2024, a new
Tartu Warehouse from July 2024 with no backfilled history, and a head office with no
revenue (so emissions per euro must be blank, not an error).

**How it is tested.** The tests check the schema, the data quality rules, that each story
event is visible in the data, and that regenerating gives byte-identical files.

## 2. The Claude connector (`mcp`)

**What it is.** An MCP server that lets Claude answer plain-language questions such as
"which site had the highest emissions per million euros of revenue in 2025?". Claude
calls five read-only tools; the server answers from an in-memory DuckDB database (a
file-based analytics database).

**Key decisions.**

| Choice | Picked | Over | Why |
| --- | --- | --- | --- |
| Database | DuckDB in memory | SQLite, pandas, a server database | Built for analytics, exact decimal sums, and a setting that locks off file and network access |
| Tools | Four purpose-built tools plus a guarded SQL tool | SQL only | Purpose-built tools carry tested logic; SQL alone lets the model get the grain wrong |
| Filter values | Bound parameters | Text pasted into SQL | Input can never change the query (no SQL injection) |
| Errors | Clear messages for input mistakes, a generic message for crashes | Show every error | Claude gets what it can fix; internal details stay on the server |
| Transport | Local stdio (standard input and output) | Remote HTTP | Simplest for one person on one machine; the remote version is the next step |

**Safety in layers.** The SQL tool accepts exactly one `SELECT`, the database's file and
network access is switched off and locked, and results are capped at 1,000 rows. Each
layer has its own tests, and the tests were checked by removing a guard on purpose and
watching them fail.

**Getting the grain right.** Emissions and revenue are flows, so they are summed over
months. Full-time equivalent employees (FTE) is a level, so it is summed across sites
within a month and then averaged over months. Summing FTE over a year would make
emissions per FTE twelve times too small.

## 3. The Power BI semantic model (`powerbi`)

**What it is.** A Power BI Project (PBIP): the model in Tabular Model Definition Language
(TMDL) and the report in the Power BI enhanced report format (PBIR), all as text files in
git. It has 14 measures, three row-level security (RLS) roles and a three-page report.

**Key decisions.**

| Choice | Picked | Over | Why |
| --- | --- | --- | --- |
| File format | Power BI Project (text files) | A single `.pbix` file | A `.pbix` is a binary file: git can store it but cannot show what changed |
| Report pages | Generated by a Python script | Hand-edited JSON (JavaScript Object Notation) | One definition, consistent names, and a test proves every visual's fields exist |
| Prior year | Shift the month key in DAX | `SAMEPERIODLASTYEAR` | A monthly date table cannot be marked as a date table, which those functions need |
| Year-on-year change | Like-for-like site-months | Total against total | A new site inflates the change: +136.5% against +10.7% for Tartu Warehouse in 2025 |
| Testing | DAX queries against Desktop's own engine | Checking visuals by eye | 31 exact comparisons in seconds, rerun after every change |
| Security | Three static country roles | Dynamic roles by email | Simple to test locally; dynamic security needs users in the Power BI Service |

**How the measures are proved.** Each measure is run as a DAX query against the model
open in Power BI Desktop, and the result is compared with an independent Python
calculation from the CSV files. The tests cover totals, intensities, prior year,
like-for-like change, blanks where a value must be blank, and each security role. Writing
the like-for-like test exposed a fault in the first version of the change measure: it
compared Tartu Warehouse's 12 months of 2025 with its 6 months of 2024.

**Governance.** Naming conventions, a generated data dictionary and a certification
checklist sit in [`powerbi/docs`](../powerbi/docs). Tests fail if the data dictionary or
the report files fall out of step with the model.

## 4. The Power Automate flows (`power-automate`)

**What it is.** Two cloud flows that replace a manual monthly routine. A site uploads its
Excel file to SharePoint; the intake flow checks it against ten written rules (R1 to R10)
and either loads it into a central list or rejects it with an email saying what to fix.
A reminder flow on day 5 chases sites with no accepted file.

**Key decisions.**

| Choice | Picked | Over | Why |
| --- | --- | --- | --- |
| Validation | Power Automate's own actions | An Office Script | Shows Power Automate skill directly |
| Storage | SharePoint lists | An Excel workbook, Dataverse | Lists take rows from several runs without locking; Dataverse is heavier to set up |
| Rules | Written once in Python, mirrored in the flow | Only in the flow | The Python version is testable offline and gives the expected result for every file |
| Test month | Replay December 2025 | Invent a new month | The clean files must rebuild the shared dataset exactly, which gives a reconciliation test |

**Whole file or nothing.** An accepted file adds all its rows; a rejected file adds none;
a technical failure removes any rows the run wrote. A month is never loaded twice.

**How it is tested.** Planted problems (electricity entered in MWh instead of kWh, a
missing source, a duplicated row, a missing file) each fail exactly the rules they
should. Loading the six clean December files on top of the seeded list rebuilds all 1,422
emission rows exactly.

**Status.** The design, rules, test files and offline tests are complete. The flows
themselves are not built yet; [`docs/tenant-setup.md`](../power-automate/docs/tenant-setup.md)
is the step-by-step guide for building them in a Microsoft 365 trial tenant.

## Practices used throughout

- **A second route to every number.** Power BI measures and MCP tools are each checked
  against an independent Python calculation from the raw files.
- **Tests that are tested.** Mistakes were planted on purpose (a typed-in factor in a
  measure, a misspelt field in a visual, a removed security guard) to confirm the tests
  catch them.
- **Evidence kept.** The raw output of every live test run is saved in the repository,
  not summarised.
- **No typed-in rates.** Measures contain no hard-coded factors; only unit conversions
  and the date-key shift are allowed, and a test enforces it.
- **Everything as code.** The data, model, report and rules are text files with readable
  git history.

## Limitations

- Illustrative emission factors, one per source for the whole period, and location-based
  scope 2 only.
- Monthly grain, with smooth seasonal and growth patterns.
- The Power BI model is not published, so scheduled refresh, endorsement and RLS
  membership in the Power BI Service are described rather than shown.
- The MCP server is local and single-user.
- The Power Automate flows are designed and tested offline but not yet built in a tenant.

## Next steps

- Publish the Power BI model to a workspace and run the live tests through the XML for
  Analysis (XMLA) endpoint.
- A remote MCP server with OAuth sign-in, and a tool that runs DAX against the published
  model, so Claude and the dashboards answer from the same measures.
- Build the Power Automate flows in a trial tenant and save their exports and screenshots.
- Market-based scope 2 and yearly factor versions in the dataset.
