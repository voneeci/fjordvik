# Solution architecture

Fjordvik needs one platform that takes in its sites', ERP and service data, checks it,
holds it once, and serves the same figures to its reports, a Claude connector and its
service AI. This page shows the shape of that platform in the C4 model: the system in its
context (level 1), its containers (level 2) and the service AI's components (level 3).
It then sets out the interfaces between parts, the environments, operations, and where the
project stands against the data product delivery map. It is station 02 of that map.

Why the platform exists is in the [business case](business-case.md); what it must do is in
[requirements.md](requirements.md); the choices behind it are in the
[decision log](decision-log.md); the threats it faces are in the
[threat model](threat-model.md); the data it holds is in [data-model.md](data-model.md).

> **Synthetic data only.** Fjordvik Manufacturing Oy is a fictional company, and this is a
> portfolio project. No real company, client or person is described; roles are job titles,
> not people. The emission factors are **illustrative**, not cited.

**How to read the diagrams.** Solid boxes are built and tested in this repository. Dashed
boxes are designed (a written design, tests offline) but not running anywhere. Grey dotted
boxes are planned service AI phases with a pass mark but no code.

## Level 1: system context

Who uses the platform, and which systems it depends on.

```mermaid
flowchart TB
    classDef person fill:#08427b,color:#ffffff,stroke:#052e56
    classDef system fill:#1168bd,color:#ffffff,stroke:#0b4884
    classDef external fill:#999999,color:#ffffff,stroke:#6b6b6b

    SEC["Site Energy Coordinators<br/>[Person]<br/>upload the monthly site workbook"]:::person
    OFFICE["Sustainability, finance and<br/>portfolio staff [Person]<br/>read and sign off the figures"]:::person
    MGR["Country and sales region<br/>managers [Person]<br/>see their own sites or region"]:::person
    SVC["Service Manager and service desk<br/>[Person]<br/>plan visits, approve drafts"]:::person
    TECH["Technicians [Person]<br/>visit pumps, ask the manuals"]:::person
    CUST["Customers [Person]<br/>order parts on the portal"]:::person

    P["Fjordvik data and AI platform<br/>[Software system]<br/>checks, holds and serves one set of figures;<br/>forecasts, risk scores, plans and drafts"]:::system

    M365["Microsoft 365<br/>[External]<br/>SharePoint, Excel Online, Outlook"]:::external
    ERP["Oracle Fusion Cloud ERP<br/>[External]<br/>sales, purchases, parts orders"]:::external
    FINHR["Finance, HR and transport systems<br/>[External]<br/>revenue, headcount, freight"]:::external
    MON["Pump monitoring service<br/>[External]<br/>daily readings from each drive"]:::external
    CRM["CRM and installed base register<br/>[External]<br/>customers, pumps, contracts"]:::external
    PBI["Power BI Service<br/>[External]<br/>publishes the reports"]:::external
    CLAUDE["Claude<br/>[External]<br/>Claude Desktop; the Claude API<br/>for phases 6 and 7"]:::external
    PUB["Publishers<br/>[External]<br/>ECB exchange rates, GeoNames towns"]:::external
    PORTAL["Parts portal<br/>[External]<br/>shows suggestions, logs clicks"]:::external

    SEC -->|"uploads workbook"| M365
    M365 -->|"site rows, factors"| P
    ERP -->|"monthly extract files"| P
    FINHR -->|"monthly exports"| P
    MON -->|"daily readings"| P
    CRM -->|"master data"| P
    PUB -->|"cited reference files"| P
    P -->|"semantic model"| PBI
    PBI -->|"reports"| OFFICE
    PBI -->|"row-level security"| MGR
    P <-->|"read-only tools"| CLAUDE
    P -->|"risk list, plans, forecasts, drafts"| SVC
    P -->|"schedule, cited answers"| TECH
    P -->|"suggestions"| PORTAL
    PORTAL --> CUST
    P -->|"rejection email"| SEC
```

In this repository every external system is simulated: the data generator in `data`
writes what each one would send, in its shape.

## Level 2: containers

The applications and data stores inside the platform, the technology of each, and how
they connect.

```mermaid
flowchart LR
    classDef built fill:#1168bd,color:#ffffff,stroke:#0b4884
    classDef designed fill:#ffffff,color:#1168bd,stroke:#1168bd,stroke-dasharray:6 4
    classDef planned fill:#eeeeee,color:#555555,stroke:#999999,stroke-dasharray:2 3
    classDef external fill:#999999,color:#ffffff,stroke:#6b6b6b

    subgraph SRC["Sources (simulated here)"]
        WB["Site workbooks"]:::external
        X["ERP extract<br/>ZIP of CSV + SHA-256 manifest"]:::external
        EXP["Finance, HR, transport,<br/>CRM, monitoring exports"]:::external
    end

    subgraph INTAKE["Intake"]
        FLOW["Intake and reminder flows<br/>[Power Automate]<br/>rules R1 to R10"]:::designed
        LISTS[("SharePoint lists<br/>[Sites, Sources, EmissionFactors,<br/>Emissions, IntakeLog]")]:::designed
        SQL["SQL pipeline<br/>[DuckDB SQL, data/sql]<br/>check, clean, map, reconcile"]:::built
        STG[("Staging database<br/>[production design]")]:::designed
        LOAD["Load to the governed dataset<br/>[not designed]"]:::planned
    end

    GEN["Data generator<br/>[Python, demo only]<br/>writes every source's shape"]:::built
    DS[("Governed dataset<br/>[31 CSV files + manifest.json,<br/>data/tables]")]:::built

    subgraph READ["Readers"]
        SM["Semantic model<br/>[Power BI, TMDL]<br/>134 measures, 7 RLS roles"]:::built
        REP["Emissions and portfolio reports<br/>[Power BI, PBIR]<br/>17 pages"]:::built
        MCP["Claude connector<br/>[MCP server, Python,<br/>DuckDB in memory]<br/>7 read-only tools"]:::built
        SAI["Service AI jobs<br/>[Python]<br/>forecast, failure risk"]:::built
        RES[("Service AI results<br/>[CSV and JSON + manifest]")]:::built
        LATER["Scheduler, recommender,<br/>assistant, agent<br/>[phases 4 to 7]"]:::planned
    end

    WB --> FLOW --> LISTS
    X --> SQL --> STG
    LISTS -.-> LOAD
    STG -.-> LOAD
    EXP -.-> LOAD
    LOAD -.-> DS
    GEN -->|"demo: writes tables,<br/>extract, corpus"| DS
    DS -->|"DataFolder parameter"| SM --> REP
    DS -->|"read in place,<br/>checksums checked"| MCP
    DS -->|"read in place"| SAI --> RES
    RES -.->|"planned read-only tools"| MCP
    RES -.-> LATER
```

| Container | Technology | Status | Part | Notes |
| --- | --- | --- | --- | --- |
| Intake and reminder flows | Power Automate cloud flows | Designed; rules tested offline in Python | power-automate | [Flow design](../power-automate/docs/flow-design.md); building them needs a Microsoft 365 tenant |
| SharePoint lists | SharePoint Online | Designed; seed workbooks built | power-automate | [Lists](../power-automate/docs/sharepoint-lists.md) |
| SQL pipeline | DuckDB SQL | Built | data | Stops the load on any failed check |
| Staging database | Not chosen | Designed | data, powerbi | [Refresh design](../powerbi/docs/refresh-design.md#the-route) |
| Load to the governed dataset | Not designed | **Gap** | none | No route yet from the SharePoint list, the staging database and the monthly exports into the dataset in production |
| Data generator | Python | Built | data | Demo only: it stands in for every source |
| Governed dataset | CSV files with a SHA-256 manifest | Built | data | The contract every reader depends on |
| Semantic model and reports | Power BI Project (TMDL and PBIR) | Built; not published | powerbi | Desktop reads the CSV files |
| Claude connector | Python, MCP SDK 2.x, DuckDB | Built; local only | mcp | Stdio, or Streamable HTTP on 127.0.0.1 with OAuth 2.1 sign-in |
| Service AI jobs and results | Python (pandas, statsmodels, scikit-learn) | Phases 2 and 3 built | service-ai | Each result stamped with data checksum, commit and model version |
| Scheduler, recommender, assistant, agent | Google OR-Tools; Python; retrieval-augmented generation (RAG) with Claude; an agent with an outbox | Planned | service-ai | Phases 4 to 7 |

## Level 3: service AI components

The service AI is where most of the remaining build sits, so it gets its own view. Each
capability reads the governed dataset in place and never writes under `data/` (rule A5).

```mermaid
flowchart LR
    classDef built fill:#1168bd,color:#ffffff,stroke:#0b4884
    classDef planned fill:#eeeeee,color:#555555,stroke:#999999,stroke-dasharray:2 3
    classDef store fill:#ffffff,color:#1168bd,stroke:#1168bd
    classDef person fill:#08427b,color:#ffffff,stroke:#052e56

    subgraph IN["Governed dataset (read only)"]
        TEL[("fact_asset_telemetry")]:::store
        EVT[("fact_service_event")]:::store
        ORD[("fact_parts_order")]:::store
        POR[("fact_portal_event")]:::store
        MAS[("dim_asset, dim_part,<br/>dim_technician, dim_customer")]:::store
        COR[("data/corpus<br/>manuals, terms, warranty")]:::store
    end

    DEM["Demand and drivers<br/>forecast/demand.py, drivers.py"]:::built
    FC["Parts forecast<br/>Poisson driver model + 80% ranges<br/>(phase 2)"]:::built
    FEAT["Features<br/>ml/features.py, 31 allowlisted columns"]:::built
    ANO["Anomaly score<br/>isolation forest (phase 3)"]:::built
    CLF["Failure risk<br/>gradient-boosted trees (phase 3)"]:::built
    ALR["Alerts and drift<br/>cost-based alert level,<br/>seasonal drift monitor"]:::built
    SCH["Technician schedule<br/>OR-Tools + independent<br/>constraint checker (phase 4)"]:::planned
    REC["Parts recommendations<br/>fit checked in code (phase 5)"]:::planned
    IDX["Manual search index<br/>version and date per chunk"]:::planned
    AST["Service assistant<br/>RAG with Claude, cites sections (phase 6)"]:::planned
    AGT["Service desk agent<br/>read tools + create draft only (phase 7)"]:::planned
    OUT[("outbox/<br/>drafts with a UUID request ID")]:::store
    APP["Approve command<br/>human only, applies once"]:::planned
    REV["Service Manager"]:::person

    ORD --> DEM
    TEL --> DEM
    MAS --> DEM
    DEM --> FC
    TEL --> FEAT
    MAS --> FEAT
    EVT -->|"labels only"| CLF
    FEAT --> ANO --> CLF --> ALR
    ALR --> SCH
    MAS --> SCH
    ORD --> REC
    POR --> REC
    COR --> IDX --> AST
    ALR --> AGT
    FC --> AGT
    REC --> AGT
    IDX --> AGT
    SCH --> AGT
    AGT --> OUT --> REV --> APP
```

The answer key in `data/generator-truth/` is read only by the evaluation step, after the
model is fixed, and never by a model, the connector or an agent (rule D10). The planned
connector tools (asset health, parts forecast, part recommendations, manual search) read
the committed results and stay read-only (rule A1).

## Interfaces and contracts

| # | From | To | Form | Contract and check |
| --- | --- | --- | --- | --- |
| I1 | Site workbook | Intake flow | Excel table "Submission" | Rules R1 to R10, [intake-rules.md](../power-automate/docs/intake-rules.md); the Python reference is tested |
| I2 | Intake flow | SharePoint Emissions list | List rows with factor and tCO2e | [sharepoint-lists.md](../power-automate/docs/sharepoint-lists.md); whole file or nothing |
| I3 | Oracle ERP | SQL pipeline | Monthly ZIP of CSV with a SHA-256 manifest | Manifest check stops the load; [refresh design](../powerbi/docs/refresh-design.md) |
| I4 | SQL pipeline | Governed dataset | `fact_sales`, `fact_data_issue` | Sales plus quarantine equal finance revenue to the cent |
| I5 | Governed dataset | Every reader | Table and column names; row counts and checksums | `data/tests/test_schema.py` (names never renamed, rule D4); each part's `tests/test_data.py` |
| I6 | Governed dataset | Semantic model | CSV through the `DataFolder` parameter | `powerbi/tests/test_data.py` |
| I7 | Claude connector | Claude | MCP tools over stdio or Streamable HTTP | Read-only annotations; OAuth 2.1 and a role check per tool over HTTP (rules A1, A2) |
| I8 | Service AI results | Claude connector (planned tools) | Committed CSV and JSON with a manifest | The layout map names `service-ai/results/` as what mcp reads |
| I9 | Agent | Approve command | Draft in `outbox/` with a version 4 UUID | Applied once, only by a person (rules A3, A4) |
| I10 | Corpus | Search index | Manual chunks with version and date | A changed manual rebuilds its chunks (rule D17) |
| I11 | Finance and HR | Governed dataset | Monthly export | **Not designed** ([data README](../data/README.md#where-the-data-comes-from)) |

## Environments

Today there is one environment: a Windows laptop with synthetic data. Power BI Desktop
reads the CSV files, the connector listens on 127.0.0.1 only, and every part's tests run
without keys or network. Nothing is published.

Proposed target (decision [ADR-026](decision-log.md#adr-026-four-environments-with-separate-credentials), awaiting Reece):

| Environment | Where | Data | Credentials | Purpose |
| --- | --- | --- | --- | --- |
| Development | The laptop | Synthetic | None needed; keys from environment variables for live model runs | Build and test |
| Continuous integration | GitHub Actions on every push | Synthetic | None: tests are keyless | Run every part's tests and the guardrail checks |
| Test | A Microsoft 365 trial tenant and a Power BI test workspace | Synthetic | Separate test accounts | Build the flows, publish the model, run the live tests, user acceptance |
| Production | Fjordvik's own tenant and staging database | Fjordvik's own | Separate; never in this repository | Live use; out of scope for a portfolio project |

ISO/IEC 27001:2022 control 8.31 asks for development, test and production to be kept
apart; the delivery map adds continuous integration as the fourth.

## Security design

Summarised from the [threat model](threat-model.md): synthetic data only; no secrets in
git (keys from environment variables); row-level security in Power BI mirrored by role
checks in the connector; a read-only connector with three guards on its SQL tool; agents
that draft and never act; text from documents treated as data, never instructions; and a
Claude Code hook with guardrail tests that catch common mistakes before they land.

## Non-functional targets

In [requirements.md](requirements.md#non-functional-requirements): correctness against
independent calculations, refresh and visual times, reliability of failed loads,
reproducible models, security, safety, accessibility and maintainability.

## Operations and support

Designed today: a failed SQL check keeps last month's figures; a failed Power BI refresh
emails the owner and four in a row turn the schedule off; every intake run is logged in
IntakeLog with Accepted, Rejected or Failed; open data issues sit in `fact_data_issue`
with an owner and an action; the drift monitor flags a sensor that changes against the
same month in earlier years.

Not designed yet: who supports the platform after handover, at what hours, and how a
technician reports a false alert; when a model is retrained and who approves the new
version; a backup and a tested restore. These belong to stations 06 and 09.

## Where Fjordvik stands on the delivery map

The map has eleven stations, from the business case (00) to continuous improvement (10).
Status on 19 November 2026, at commit `790589d`:

| Station | Status | Evidence or gap |
| --- | --- | --- |
| 00 Business case | First edition, not signed | [business-case.md](business-case.md); licence prices missing |
| 01 Discovery and requirements | First edition, G1 not taken | [requirements.md](requirements.md); no workshops; transition requirements new |
| 02 Solution architecture | This page, not reviewed | Environment strategy proposed; production load route not designed |
| 03 Data modelling | Model built; G2 partly met | [data-model.md](data-model.md); history handling proposed |
| 04 Build in slices | Strong, two gaps | Locked pass marks, independent review, saved evidence; no continuous integration, no user demos |
| 05 Migration and cutover | Not started | Reconciliation strong; no runbook, rehearsal, rollback or communication plan |
| 06 Testing stages | Component and system tests only | No user or operational acceptance; nothing published to test |
| 07 Go-live | Not started | Release package and go/no-go not written |
| 08 Hypercare | Not started | |
| 09 Handover | Partial | Handover notes per phase; no runbook with a measured restore time |
| 10 Continuous improvement | Designed for the scorecard only | Quarterly scorecard cycle; no benefits review |

### Follow-up tasks for stations 04 and 05

Recorded here, to start once this architecture is agreed (Reece, 19 November 2026):

1. **Continuous integration.** A GitHub Actions workflow that runs every part's tests and
   `guardrails/check.py` on every push, keyless (the 154 live Power BI tests stay manual).
   A new `.github/` folder needs a layout map entry from Attena first (rule L1).
2. **Demos.** Hold the open portfolio milestone M5: each page reviewed with two Product
   Managers, recorded as acceptance evidence.
3. **Cutover runbook.** One runbook for the move from the central spreadsheet and the
   service planning spreadsheet: steps, owners, timings against the monthly close, and
   go/no-go criteria (transition requirements TR1 to TR6).
4. **Rehearsal.** A clean-room rebuild from a tagged release in an empty folder, which
   the delivery map accepts as the lean cutover rehearsal, with reconciliation to the
   finance totals.
5. **Rollback plan and communication plan.** What happens if the first live close fails,
   and who tells the sites, controllers and technicians, when.

## Change history

- 19 November 2026: first edition, during the architecture pause (Reece asked).
