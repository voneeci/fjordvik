# Decision log

The architecture decisions behind Fjordvik's data and AI platform, one numbered record
each: the context, the decision, what it was chosen over, and what follows from it. A
reviewer, or a new chat, can see why the platform is shaped as it is without reading every
handover. These are the architecture decision records (ADRs) of station 02 of the delivery
map.

Records 001 to 025 were taken during the build and are written up here from the
[project guide](learning-guide.md), the [learning notes](learning/service-ai.md), the
handovers and the repository's `CLAUDE.md` files. Records 026 to 029 are proposals from
the architecture pause and wait for Reece's decision. A decision is never edited after it
is accepted: a later record supersedes it and says so.

> **Synthetic data only.** Fjordvik Manufacturing Oy is a fictional company, and this is a
> portfolio project. No real company, client or person is described. The emission factors
> are **illustrative**, not cited.

| # | Decision | Status | Date |
| --- | --- | --- | --- |
| 001 | Synthetic data with illustrative emission factors | Accepted | 12 October 2026 |
| 002 | A star schema | Accepted | By 16 October 2026 |
| 003 | Table and column names are a contract | Accepted | By 16 October 2026 |
| 004 | A zero is a row; no backfilling | Accepted | By 16 October 2026 |
| 005 | One repository, five parts | Accepted | 30 October 2026 |
| 006 | One shared copy of the data, read in place | Accepted | 31 October 2026 |
| 007 | Checksums prove the data unedited | Accepted | 31 October 2026 |
| 008 | Planted errors only in intake files | Accepted | 31 October 2026 |
| 009 | Market-based scope 2 in its own table | Accepted | 31 October 2026 |
| 010 | One table per scope 3 data source | Accepted | 31 October 2026 |
| 011 | ERP sales through extract files and SQL | Accepted | 31 October 2026 |
| 012 | Quarantine unmapped item numbers | Accepted | 31 October 2026 |
| 013 | Connector on DuckDB in memory | Accepted | By 16 October 2026 |
| 014 | Purpose-built tools plus one guarded SQL tool | Accepted | By 16 October 2026 |
| 015 | Stdio, plus HTTP with OAuth sign-in on 127.0.0.1 | Accepted | 31 October 2026 |
| 016 | Power BI Project text files, generated pages | Accepted | By 16 October 2026 |
| 017 | Two reports on one model | Accepted | 31 October 2026 |
| 018 | Static row-level security roles | Accepted | By 16 October 2026 |
| 019 | Prior year by shifting the month key | Accepted | By 16 October 2026 |
| 020 | Intake rules in Python, mirrored in Power Automate | Accepted | By 16 October 2026 |
| 021 | Master guardrails with a hook and tests | Accepted | 2 November 2026 |
| 022 | Pass marks and time splits fixed before code | Accepted | 2 November 2026 |
| 023 | Parts forecast: a driver model that must beat simple rules | Accepted | 3 November 2026 |
| 024 | Failure risk: fleet-adjusted z-scores, boosted trees, cost-based alerts | Accepted | 12 November 2026 |
| 025 | Agents draft, never act | Accepted | 2 November 2026 |
| 026 | Four environments with separate credentials | Proposed | 19 November 2026 |
| 027 | History handling for dimensions | Proposed | 19 November 2026 |
| 028 | Continuous integration on every push | Proposed | 19 November 2026 |
| 029 | A daily date table for the service data | Proposed | 19 November 2026 |

"By 16 October 2026" means the decision was built into one of the four original
repositories, which were built from 12 to 16 October 2026 ([README](../README.md#history)).

## Accepted

### ADR-001: Synthetic data with illustrative emission factors

- **Status:** Accepted, 12 October 2026 (Reece); confirmed 2 November 2026.
- **Context:** Fjordvik is a learning and portfolio project that will never be sold. The
  permanent rules ask for cited factors in any data model.
- **Decision:** Every figure is synthetic. Emission factors are illustrative, a one-off
  exception for this project; every other rate (exchange rates, town coordinates, planning
  costs) is fetched from its publisher and cited.
- **Over:** Cited factors throughout.
- **Consequences:** Every README and doc says so (rule W6); no result may be read as
  real-world performance (rule W8).
- **Source:** [GUARDRAILS.md](../GUARDRAILS.md) D1, D6, D7.

### ADR-002: A star schema

- **Status:** Accepted, by 16 October 2026.
- **Context:** Power BI, the connector and the service AI all query the same data.
- **Decision:** Dimension tables and fact tables, each fact at a declared grain.
- **Over:** One wide table.
- **Consequences:** Simpler Data Analysis Expressions (DAX), faster filters, no double
  counting; each new subject adds facts that reuse the existing dimensions
  ([bus matrix](data-model.md#bus-matrix)).
- **Source:** [Project guide](learning-guide.md#1-the-governed-dataset-data).

### ADR-003: Table and column names are a contract

- **Status:** Accepted, by 16 October 2026.
- **Context:** Four parts read the data by name.
- **Decision:** Never rename a table or column; add new ones instead. A unit change needs a
  new column.
- **Over:** Renaming as the model evolves.
- **Consequences:** Some names age (for example `fact_emissions` holds only site-reported
  rows); `data/tests/test_schema.py` enforces the rule (D4).
- **Source:** [data README](../data/README.md#architecture).

### ADR-004: A zero is a row; no backfilling

- **Status:** Accepted, by 16 October 2026.
- **Decision:** Every open site reports every source every month, with 0 where nothing was
  used; a site's series starts in its first month.
- **Over:** No row for nothing used; estimates for months before a site opened.
- **Consequences:** A missing row means a missing report, which the intake gap rule can
  catch; Tartu Warehouse's year-on-year change uses like-for-like site-months.
- **Source:** [Project guide](learning-guide.md#1-the-governed-dataset-data).

### ADR-005: One repository, five parts

- **Status:** Accepted, 30 October 2026 (Reece); service-ai added 2 November 2026.
- **Context:** Four separate repositories drifted apart and each kept a copy of the data.
- **Decision:** Combine them with `git subtree`, keeping every original commit hash; one
  project in five parts, never "projects".
- **Consequences:** Shared guardrails and one data folder; the old repositories were
  retired on 2 November 2026.
- **Source:** Root [CLAUDE.md](../CLAUDE.md).

### ADR-006: One shared copy of the data, read in place

- **Status:** Accepted, 31 October 2026 (Reece), superseding the per-folder copies of
  30 October.
- **Decision:** mcp, powerbi, power-automate and service-ai read `data/tables/` directly.
- **Over:** A copy per part.
- **Consequences:** One place to change; a data change means rerunning every part's tests.
- **Source:** Root [CLAUDE.md](../CLAUDE.md).

### ADR-007: Checksums prove the data unedited

- **Status:** Accepted, 31 October 2026.
- **Decision:** `data/tables/manifest.json` holds each file's row count and SHA-256
  checksum; every part's tests check the files before relying on them; the tables change
  only through the generator.
- **Over:** Trust.
- **Consequences:** Anyone can prove the data was not edited by hand (rules D3, D5).
- **Source:** [data README](../data/README.md#approach).

### ADR-008: Planted errors only in intake files

- **Status:** Accepted, 31 October 2026 (Reece, approving the phase 2 plan).
- **Decision:** The clean dataset has no planted errors. They live in the power-automate
  intake files and the simulated ERP extract, where the rules and SQL must catch them.
- **Consequences:** Every reader can trust the dataset; every check has a planted problem
  that proves it works.
- **Source:** [data/CLAUDE.md](../data/CLAUDE.md).

### ADR-009: Market-based scope 2 in its own table

- **Status:** Accepted, 31 October 2026.
- **Decision:** `fact_scope2_market` holds the same kWh with contract or residual-mix
  factors, reported beside the location-based total, never added to it.
- **Over:** A method column with two rows per source.
- **Consequences:** Existing totals, the intake flow and the connector were unchanged;
  nothing can double count.
- **Source:** [Project guide](learning-guide.md#1-the-governed-dataset-data).

### ADR-010: One table per scope 3 data source

- **Status:** Accepted, 31 October 2026.
- **Decision:** Purchases, freight and upstream energy each get a fact table; all 15
  scope 3 categories are listed with a status and reason.
- **Over:** One wide value-chain table.
- **Consequences:** One owner and one collection routine per table; exclusions justified
  as the Greenhouse Gas (GHG) Protocol requires.
- **Source:** [Project guide](learning-guide.md#1-the-governed-dataset-data).

### ADR-011: ERP sales through extract files and SQL

- **Status:** Accepted, 31 October 2026.
- **Context:** Microsoft lists no Power BI connector for Oracle's extraction routes, and
  Oracle advises against bulk extraction through its reporting tools.
- **Decision:** A monthly extract of ZIP files with a SHA-256 manifest lands in storage, is
  loaded and checked by SQL into a staging database, and Power BI refreshes from there.
- **Over:** Connecting Power BI to Oracle directly.
- **Consequences:** The extract's problems are caught in tested SQL; a staging database is
  needed in production.
- **Source:** [Refresh design](../powerbi/docs/refresh-design.md#the-route).

### ADR-012: Quarantine unmapped item numbers

- **Status:** Accepted, 31 October 2026.
- **Decision:** Sales lines with an unmapped local item number are held back and listed in
  `fact_data_issue` for portfolio governance; kronor are converted at the ECB's published
  monthly rate.
- **Over:** Guessing from similar codes; a typed-in rate.
- **Consequences:** No figure is invented; the reconciliation shows exactly what is held
  back.
- **Source:** [Project guide](learning-guide.md#1-the-governed-dataset-data).

### ADR-013: Connector on DuckDB in memory

- **Status:** Accepted, by 16 October 2026.
- **Decision:** The connector loads the CSV files into DuckDB in memory, then locks off file
  and network access.
- **Over:** SQLite, pandas, a server database.
- **Consequences:** Exact decimal sums and a lockable sandbox for `run_sql`.
- **Source:** [Project guide](learning-guide.md#2-the-claude-connector-mcp).

### ADR-014: Purpose-built tools plus one guarded SQL tool

- **Status:** Accepted, by 16 October 2026.
- **Decision:** Six tools with tested logic answer the common questions; `run_sql` handles
  the rest as one read-only `SELECT`, capped at 1,000 rows, with bound parameters.
- **Over:** SQL only.
- **Consequences:** The model cannot get the grain wrong on common questions (for example
  FTE is a level, not a flow).
- **Source:** [mcp README](../mcp/README.md#approach).

### ADR-015: Stdio, plus HTTP with OAuth sign-in on 127.0.0.1

- **Status:** Accepted, 31 October 2026.
- **Decision:** Stdio for one person in Claude Desktop; Streamable HTTP with OAuth 2.1 and a
  role per tool check to show how a company would share it, bound to 127.0.0.1 only.
- **Consequences:** The sign-in page is a demo with no password; opening the server further
  needs Reece's yes (rule A2) and a production identity provider ([threat model](threat-model.md#b5-the-claude-connector)).
- **Source:** [mcp README](../mcp/README.md#approach).

### ADR-016: Power BI Project text files, generated pages

- **Status:** Accepted, by 16 October 2026.
- **Decision:** The model in TMDL and the report in PBIR as text in git; report pages
  generated by a Python script; the data dictionary generated from the model.
- **Over:** A binary `.pbix`; hand-edited JSON.
- **Consequences:** Readable diffs; tests fail if the pages or dictionary fall out of step.
- **Source:** [Project guide](learning-guide.md#3-the-power-bi-semantic-model-powerbi).

### ADR-017: Two reports on one model

- **Status:** Accepted, 31 October 2026 (Reece).
- **Decision:** `FjordvikEmissions.pbip` and `FjordvikPortfolio.pbip` both read one
  semantic model.
- **Consequences:** One set of measures and security roles; open one report at a time.
- **Source:** [powerbi/CLAUDE.md](../powerbi/CLAUDE.md).

### ADR-018: Static row-level security roles

- **Status:** Accepted, by 16 October 2026; region roles added 31 October 2026.
- **Decision:** Three country roles and four sales region roles; region roles also deny
  site figures.
- **Over:** Dynamic roles by email address.
- **Consequences:** Testable locally; dynamic security would need users in the Power BI
  Service. Members are assigned once published.
- **Source:** [Project guide](learning-guide.md#3-the-power-bi-semantic-model-powerbi).

### ADR-019: Prior year by shifting the month key

- **Status:** Accepted, by 16 October 2026.
- **Context:** The date table is monthly, so it cannot be marked as a date table.
- **Decision:** Shift the month key in DAX; compare like-for-like site-months.
- **Over:** `SAMEPERIODLASTYEAR`; total against total.
- **Consequences:** A new site no longer inflates year-on-year change (Tartu Warehouse,
  2025: +13.2% like for like against +138.3%).
- **Source:** [Project guide](learning-guide.md#3-the-power-bi-semantic-model-powerbi).

### ADR-020: Intake rules in Python, mirrored in Power Automate

- **Status:** Accepted, by 16 October 2026.
- **Decision:** Ten rules written once in Python as the testable reference, then built as
  Power Automate actions; storage in SharePoint lists; whole file or nothing.
- **Over:** Rules only in the flow; an Office Script; Dataverse.
- **Consequences:** Every file's expected result is known before the flow exists; the
  flows still need building in a tenant.
- **Source:** [Project guide](learning-guide.md#4-the-power-automate-flows-power-automate).

### ADR-021: Master guardrails with a hook and tests

- **Status:** Accepted, 2 November 2026 (Reece); slimmed 3 November 2026.
- **Decision:** One master rule set, `GUARDRAILS.md`, maintained only by Attena, enforced
  by `check.py`, every part's guardrail tests, a Claude Code hook and a pre-commit check.
- **Consequences:** Rules stay the same across chats; a new folder or kind of file needs a
  layout map entry first (rule L1).
- **Source:** [GUARDRAILS.md](../GUARDRAILS.md).

### ADR-022: Pass marks and time splits fixed before code

- **Status:** Accepted, 2 November 2026.
- **Decision:** Each service AI phase commits its evaluation set and pass mark before any
  code, written by a different chat; train, validation and test periods are fixed by date
  with a 30-day gap; settings are chosen on validation only; the test period is scored
  once, behind a split lock.
- **Consequences:** Results cannot be tuned to the test; a missed control is reported as
  it fell (phase 3).
- **Source:** [GUARDRAILS.md](../GUARDRAILS.md) A9, E1.

### ADR-023: Parts forecast: a driver model that must beat simple rules

- **Status:** Accepted, 3 November 2026.
- **Decision:** A Poisson regression per warehouse and part family on fleet running hours
  and age, each driver used only as known at the forecast date, with 80% ranges from past
  errors; judged against naive, seasonal naive and moving average forecasts on rolling
  origins.
- **Consequences:** Met the pass marks at Oulu with a small margin; Tartu is reported apart
  until it has enough history.
- **Source:** [Learning notes, phase 2](learning/service-ai.md#phase-2-forecasting-spare-parts-demand).

### ADR-024: Failure risk: fleet-adjusted z-scores, boosted trees, cost-based alerts

- **Status:** Accepted, 12 November 2026.
- **Decision:** Readings compared with the same application's fleet and then with the
  pump's own normal (robust z-scores); an isolation forest score; gradient-boosted trees
  for the 30-day failure chance; the alert level set from the cost of a wasted visit
  against a missed failure, on validation only; a drift monitor against the same month in
  earlier years.
- **Over:** Accuracy or area under the curve as headline metrics.
- **Consequences:** Met the three main pass marks; three control checks missed and are
  reported; acting on alerts will change future training data (rule E3, phase 4).
- **Source:** [Learning notes, phase 3](learning/service-ai.md#phase-3-predicting-pump-failures).

### ADR-025: Agents draft, never act

- **Status:** Accepted, 2 November 2026.
- **Decision:** Agents have read-only tools plus "create draft"; drafts go to
  `service-ai/outbox/` with a unique request ID; only a human-run approve command applies
  one, once; every tool call is logged.
- **Consequences:** A planted instruction can at worst produce a draft a person rejects.
- **Source:** [GUARDRAILS.md](../GUARDRAILS.md) A3, A4, A11, A12.

## Proposed

Each waits for Reece's decision. Accepting one changes its status here and starts its
follow-up task in [architecture.md](architecture.md#follow-up-tasks-for-stations-04-and-05).

### ADR-026: Four environments with separate credentials

- **Status:** Proposed, 19 November 2026.
- **Context:** Everything runs on one laptop. The delivery map asks for environments chosen
  at architecture, and ISO/IEC 27001:2022 control 8.31 asks for development, test and
  production to be kept apart.
- **Proposal:** Development (the laptop), continuous integration (keyless), test (a
  Microsoft 365 trial tenant and a Power BI test workspace, synthetic data) and production
  (Fjordvik's own, out of scope here), each with its own credentials.
- **Consequences:** Publishing the model and building the flows happen in test, never
  against a live system; credentials never cross environments.
- **Detail:** [architecture.md](architecture.md#environments).

### ADR-027: History handling for dimensions

- **Status:** Proposed, 19 November 2026.
- **Context:** Every dimension today is overwritten in place (slowly changing dimension
  type 1). Some attributes change and matter to past figures: a customer's service
  contract, a technician's skills and weekly hours (phase 4 needs them "as at" a date, rule
  D16), a pump's location, and emission factors (one per source for the whole period).
- **Proposal:** Type 2 history (a row per version with valid-from and valid-to dates) for
  `dim_customer.service_contract`, the technician's skills and hours, and yearly factor
  versions; type 1 elsewhere. New columns or tables only, so no name changes (ADR-003).
- **Consequences:** Phase 4 can build plans from data as it stood; a factor change no
  longer rewrites past emissions. Needs generator changes in `data` and Reece's yes for
  any checksum change (rule D5).
- **Detail:** [data-model.md](data-model.md#history-handling).

### ADR-028: Continuous integration on every push

- **Status:** Proposed, 19 November 2026.
- **Context:** Tests run only by hand; the delivery map's build station expects automated
  tests on every push.
- **Proposal:** A GitHub Actions workflow running every part's tests and the guardrail
  checks on every push and pull request, without keys or network; the live Power BI tests
  stay manual.
- **Consequences:** Needs a layout map entry for `.github/` from Attena (rule L1).

### ADR-029: A daily date table for the service data

- **Status:** Proposed, 19 November 2026.
- **Context:** `fact_asset_telemetry.date_key` is a day (1,096 values), but `dim_date` holds
  months (36 values), so telemetry cannot join the calendar. `fact_service_event` and
  `fact_portal_event` carry dates with no date key at all.
- **Proposal:** Add a new `dim_day` table (one row per day, with its month's `date_key`)
  rather than changing `dim_date` (ADR-003).
- **Consequences:** Service data can be sliced by month and year with the rest; Power BI
  could mark it as a date table.
- **Detail:** [data-model.md](data-model.md#findings).

## Change history

- 19 November 2026: first edition: 25 records from the build, 4 proposals (Reece asked,
  during the architecture pause).
