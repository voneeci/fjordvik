# Fjordvik emissions reporting: how it was built

Fjordvik Manufacturing Oy needs one set of monthly greenhouse gas figures that it can
trust, explain and show to the right people, and its customers now ask for the whole
footprint, including what it buys and ships. This project delivers that in four parts:
Power Automate flows that collect and check each site's monthly file, a governed dataset,
a Power BI model and report for management and country managers, and a Claude connector
that answers plain-language questions from the same data. This guide sets out the business
need, what the data is, and how and why each part was built.

> **Synthetic data only.** Fjordvik Manufacturing Oy is a fictional company, and this is a
> portfolio project. No real company, client or person is described. The emission factors
> are **illustrative**, not cited, and must not be used for real reporting.

## The business

Fjordvik Manufacturing Oy makes electric pumps and pump systems for water utilities,
industry and buildings ([company profile](company-profile.md)): industrial process pumps
in Tampere, water and wastewater pumps in Gothenburg, and pump packages and controls in
Tallinn. It has six sites in three countries:

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
landfill. Beyond its own sites, Fjordvik buys castings, machined parts, motors and
services, and pays carriers to move materials and pumps. Each of these produces
greenhouse gas emissions, which the company reports every month and in its annual
sustainability report.

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
data). Finance supplies each site's monthly revenue, and HR its headcount as full-time
equivalent employees (FTE).

| Scope | What it covers | Sources at Fjordvik |
| --- | --- | --- |
| 1 | Direct emissions from fuel the company burns or gas it releases | Natural gas, diesel, liquefied petroleum gas (LPG), refrigerant leakage |
| 2, location-based | Emissions from the energy it buys, at the average factor of the grid or heat network in each site's country | Purchased electricity, district heating |
| 2, market-based | The same kWh at the factor of the contract each site buys under: zero where guarantees of origin cover it, the country's residual mix for the rest | Gothenburg's hydro contract, Tampere's wind contract from 2025 |
| 3 | Other emissions in its value chain, in the Greenhouse Gas (GHG) Protocol's 15 categories | Purchased goods and services (1), upstream fuels and grid losses (3), freight (4 and 9), waste to landfill (5), business flights (6) |

Every scope 3 category not calculated is listed with its reason, as the GHG Protocol
Scope 3 Standard requires. Use of sold products (category 11) is likely the largest for
a pump maker and needs product and sales data, so it is "not yet calculated".

Emissions in tonnes of carbon dioxide equivalent (tCO2e) are worked out as activity
amount × emission factor ÷ 1,000, with the factor in kilograms per unit. Revenue and FTE
turn totals into intensities, emissions per million euros and per employee, so a growing
business can see whether it is getting cleaner as well as bigger.

The dataset covers 36 months, January 2023 to December 2025: 1,422 monthly rows the
sites report, 198 rows of revenue and FTE, and 2,802 value-chain rows. Illustrative
location-based totals are 61,421.3 tCO2e in 2023, 63,780.3 in 2024 and 66,622.5 in 2025,
of which purchased goods and services is 77% in 2025. Market-based scope 2 is 7,383.5
tCO2e in 2025 against 6,243.6 location-based: residual mixes are higher than grid
averages, so only the guarantees of origin bring it down.

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
  For 2025 that gives +3.5% for the company instead of a misleading +4.5%.
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
Microsoft 365 tenant, and the governed dataset in `data/tables` holds synthetic figures in
the shape the central Emissions list and the finance and HR exports would have. The intake
tests prove the link: loading the six clean December files onto the earlier months
rebuilds that dataset exactly.

The [process map](https://voneeci.github.io/fjordvik/docs/process-map.html) shows all 27
steps, from energy being used at a site to the figures on the Power BI report,
with the owner, tool, data and checks for each, and which steps are built, designed or
outside the project.

## At a glance

| Part | What it does for the business | Built | Tests |
| --- | --- | --- | --- |
| [`data`](../data) | The governed dataset: twelve tables with fixed names, checksums and quality tests | 12 to 31 October 2026 | 38 |
| [`mcp`](../mcp) | A Model Context Protocol (MCP) server that lets Claude answer questions from the data, read-only | 12 to 31 October 2026 | 56 |
| [`powerbi`](../powerbi) | The Power BI model and report, with every measure reconciled against an independent calculation | 12 to 31 October 2026 | 225 |
| [`power-automate`](../power-automate) | The flows that take in, check and chase the monthly site files, designed and tested offline | 12 October 2026 | 26 |

All 345 tests passed on 31 October 2026, including the 68 Power BI tests that run live
Data Analysis Expressions (DAX) queries against the open model. The raw output is saved
in each folder's `evidence/` folder.

## The order of the build

```
1. data             the contract: twelve tables, fixed names, checksums
      │
      ├──> 2. mcp             Claude asks questions of the data
      ├──> 3. powerbi         dashboards and governed measures
      └──> 4. power-automate  how the monthly data would arrive
```

The data came first because the other three parts depend on its table and column names.
The other three parts read the one shared dataset in `data/tables/` directly, so they
always show the same numbers. Each part's tests check every file against the SHA-256
checksums in `data/tables/manifest.json` before relying on it.

## 1. The governed dataset (`data`)

**What it is.** The one dataset every report reads: 36 months (January 2023 to December
2025) of emissions by site and source, with each site's revenue and headcount and the
value chain, as a twelve-table star schema. Each month it is filled from the site
workbooks, through the intake flow into the central Emissions list; the reference lists
of sites, sources, emission factors and scope 3 categories; monthly exports of revenue
from finance and headcount from HR; the purchase ledger from the enterprise resource
planning (ERP) system; freight from the transport management system; and, yearly, the
energy contracts and their guarantees of origin. The [data README](../data/README.md) sets out each source, its owner and system.

**Key decisions.**

| Choice | Picked | Over | Why |
| --- | --- | --- | --- |
| Shape | Star schema | One wide table | What Power BI is designed for: simpler DAX, faster filters, no double counting |
| Copies | One shared dataset, read in place by every part | A copy per part | One place to change, nothing to keep in step |
| Zeros | A row with 0 | No row | A missing row could mean "nothing to report" or "forgot to report" |
| History | A site's figures start in its first month | Backfilled estimates | No figure is invented for months before a site opened |
| Proof the files are unedited | Checksums in a manifest, checked by every part's tests | Trust | Anyone can prove the data was not edited by hand |
| Market-based scope 2 | Its own table, same kWh, contract or residual-mix factor | A method column with two rows per source | Every existing total, the intake flow and the connector stay as they were; nothing can double count |
| Scope 3 data | One table per data source (purchases, freight, upstream energy) | One wide value-chain table | Each table has one owner and one collection routine, and no half-empty columns |
| Scope 3 coverage | All 15 categories listed, each with a status and reason | Only the categories counted | The GHG Protocol requires every exclusion to be listed and justified |

**What happened in the period,** which the dashboards and Claude should find: winter
heating peaks, a July slowdown at the plants, rooftop solar at Tampere Plant from July
2024, Tartu Warehouse opening in July 2024, and a head office with no revenue (so its
emissions per euro must be blank, not an error).

**How it is tested.** The tests check the schema, the data quality rules, that each
business event shows in the data, and that the files match their manifest.

## 2. The Claude connector (`mcp`)

**What it is.** An MCP server that lets Claude answer plain-language questions such as
"which site had the highest emissions per million euros of revenue in 2025?". Claude
calls six read-only tools; the server answers from an in-memory DuckDB database (a
file-based analytics database).

**Key decisions.**

| Choice | Picked | Over | Why |
| --- | --- | --- | --- |
| Database | DuckDB in memory | SQLite, pandas, a server database | Built for analytics, exact decimal sums, and a setting that locks off file and network access |
| Tools | Five purpose-built tools plus a guarded SQL tool | SQL only | Purpose-built tools carry tested logic; SQL alone lets the model get the grain wrong |
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
git. It has 36 measures, three row-level security (RLS) roles and a ten-page report,
opening on an Introduction page that explains the company and what each page answers.

**Key decisions.**

| Choice | Picked | Over | Why |
| --- | --- | --- | --- |
| File format | Power BI Project (text files) | A single `.pbix` file | A `.pbix` is a binary file: git can store it but cannot show what changed |
| Report pages | Generated by a Python script | Hand-edited JSON (JavaScript Object Notation) | One definition, consistent names, and a test proves every visual's fields exist |
| Prior year | Shift the month key in DAX | `SAMEPERIODLASTYEAR` | A monthly date table cannot be marked as a date table, which those functions need |
| Year-on-year change | Like-for-like site-months | Total against total | A new site inflates the change: +138.3% against +13.2% for Tartu Warehouse in 2025 |
| Testing | DAX queries against Desktop's own engine | Checking visuals by eye | 68 exact comparisons in seconds, rerun after every change |
| Market-based total | Total minus location-based scope 2 plus market-based scope 2 | A second copy of every measure | One extra measure; scopes 1 and 3 are the same in both totals by construction |
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

- Illustrative emission factors, one per source for the whole period.
- Scope 3 is incomplete: categories 2, 7, 11 and 12 are not yet calculated, category 1 is
  spend-based, and category 3(b) waits for a Nordic and Baltic factor source.
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
- Product and sales data, then category 11 (use of sold products) from units sold.
- Yearly factor versions in the dataset.
