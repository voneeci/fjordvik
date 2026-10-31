# Fjordvik emissions reporting: how it was built

Fjordvik Manufacturing Oy needs one set of monthly greenhouse gas figures that it can
trust, explain and show to the right people. This project delivers that in four parts:
Power Automate flows that collect and check each site's monthly file, a governed dataset,
a Power BI model and report for management and country managers, and a Claude connector
that answers plain-language questions from the same data. This guide sets out the business
need, what the data is, and how and why each part was built.

> **Synthetic data only.** Fjordvik Manufacturing Oy is a fictional company, and this is a
> portfolio project. No real company, client or person is described. The emission factors
> are **illustrative**, not cited, and must not be used for real reporting.

## The business

Fjordvik Manufacturing Oy is a manufacturer with six sites in three countries:

| Site | Country | Type |
| --- | --- | --- |
| Tampere Plant | Finland | Manufacturing plant |
| Helsinki Head Office | Finland | Office |
| Oulu Warehouse | Finland | Warehouse |
| Gothenburg Plant | Sweden | Manufacturing plant |
| Tallinn Plant | Estonia | Manufacturing plant |
| Tartu Warehouse | Estonia | Warehouse |

The sites burn gas and fuel, buy electricity and district heating, and lose some
refrigerant from cooling equipment. Staff fly on business, and the sites send waste to
landfill. Each of these produces greenhouse gas emissions, which the company reports
every month and in its annual sustainability report.

The Group Sustainability Manager owns the figures. Country managers in Finland, Sweden and
Estonia are responsible for their own sites and should see only those. Over the three
years covered, the business also changed: Tampere Plant installed rooftop solar panels in
July 2024, and Tartu Warehouse opened the same month.

## The problem

Each month, every site sends the sustainability team a spreadsheet of what it used. The
team opens each file, checks the numbers by eye, copies them into a central file, works
out the emissions, and emails sites whose files are late or wrong. That routine has
predictable failures:

- **It is slow, and the checks depend on who does them.**
- **Small slips become large errors.** Electricity entered in megawatt hours (MWh)
  instead of kilowatt hours (kWh) makes that line 1,000 times too big. A duplicated row
  counts emissions twice, and a missing row looks like zero emissions.
- **Nobody can say which numbers are current.** Copies of the central file drift, so two
  charts built a week apart can disagree.
- **Comparisons mislead.** A site that opened mid-year makes the company's year-on-year
  growth look larger than it is.
- **Access is all or nothing.** A country manager either sees every country or nothing.
- **Every new question means a new spreadsheet.** "Which site emits most per euro of
  revenue?" waits until someone has time to build it.

## What the data is

Each month, each site reports how much of each emission source it used (its activity
data), plus its revenue and its headcount as full-time equivalent employees (FTE).

| Scope | What it covers | Sources at Fjordvik |
| --- | --- | --- |
| 1 | Direct emissions from fuel the company burns or gas it releases | Natural gas, diesel, liquefied petroleum gas (LPG), refrigerant leakage |
| 2 | Emissions from the energy it buys, using the average factor of the grid or heat network in each site's country (location-based) | Purchased electricity, district heating |
| 3 | Other emissions in its value chain | Business flights, waste to landfill |

Emissions in tonnes of carbon dioxide equivalent (tCO2e) are worked out as activity
amount × emission factor ÷ 1,000, with the factor in kilograms per unit. Revenue and FTE
turn totals into intensities, emissions per million euros and per employee, so a growing
business can see whether it is getting cleaner as well as bigger.

The dataset covers 36 months, January 2023 to December 2025: 1,422 monthly emission rows
and 198 rows of revenue and FTE. Illustrative totals are 9,454.0 tCO2e in 2023, 10,158.2
in 2024 and 10,921.8 in 2025. Tallinn Plant is the largest emitter, because Estonia's
illustrative grid factor is the highest.

## Why automate the intake, and why Power BI

**Power Automate takes over the monthly collection.** A site uploads its file to
SharePoint and the intake flow starts on its own. Every file is checked against the same
ten written rules every month, whoever is on duty. A file that passes is loaded whole, with
the emission factor looked up and tCO2e worked out. A file that fails loads nothing, and
the site gets an email listing what to fix. A month can never be loaded twice, every run
is logged, and a second flow chases sites with no accepted file on day 5.

**Power BI gives one trusted view of the figures.**

- One set of tested measures (totals, emissions per FTE and per million euros, change on
  the year) means every page and every user sees the same answer.
- Year-on-year change compares like for like: only site-months reported in both years.
  For 2025 that gives +2.9% for the company instead of a misleading +7.5%.
- Row-level security (RLS) gives each country manager their own sites only.
- The model is saved as text in git, so every change can be reviewed, and a certification
  checklist sets out what is checked before the report is endorsed.

**The Claude connector answers new questions without a new spreadsheet.** A manager asks
in plain language and Claude answers from the same data, read-only, using tested logic for
the calculations that are easy to get wrong.

## How it fits together

```
Site spreadsheet ──upload──> SharePoint ──> Power Automate intake flow (ten rules)
                                               │ accepted              │ rejected
                                               ▼                       ▼
                                      central Emissions list   email to the site
                                               │
                             ┌─────────────────┴─────────────────┐
                             ▼                                   ▼
                  Power BI model and report         Claude connector (MCP)
```

In this portfolio version, the flows are designed and tested offline, ready to build in a
Microsoft 365 tenant. The dataset in `data/data` stands in for the central Emissions list,
so Power BI and the connector read it directly. The intake tests prove the link: loading
the six clean December files onto the earlier months rebuilds that dataset exactly.

The [process map](process-map.html) ([published page](https://claude.ai/artifact/N4pKe8vgcofYXPDwhB9mom))
shows all 23 steps, from energy being used at a site to the figures on the Power BI report,
with the owner, tool, data and checks for each, and which steps are built, designed or
outside the project.

## At a glance

| Part | What it does for the business | Built | Tests |
| --- | --- | --- | --- |
| [`data`](../data) | The governed dataset: five tables with fixed names, checksums and quality tests | 12 October 2026 | 24 |
| [`mcp`](../mcp) | A Model Context Protocol (MCP) server that lets Claude answer questions from the data, read-only | 12 October 2026 | 48 |
| [`powerbi`](../powerbi) | The Power BI model and report, with every measure reconciled against an independent calculation | 12 to 16 October 2026 | 100 |
| [`power-automate`](../power-automate) | The flows that take in, check and chase the monthly site files, designed and tested offline | 12 October 2026 | 26 |

All 198 tests passed on 31 October 2026, including the 31 Power BI tests that run live
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
The other three parts read the one shared dataset in `data/data/` directly, so they
always show the same numbers. Each part's tests check every file against the SHA-256
checksums in `data/data/manifest.json` before relying on it.

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
