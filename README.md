# Fjordvik: monthly emissions reporting with Power Automate, Power BI and Claude

Fjordvik Manufacturing Oy makes electric pumps and pump systems for water utilities,
industry and buildings, from six sites in Finland, Sweden and Estonia
([company profile](docs/company-profile.md)). Every month each site sends a spreadsheet
of the fuel, energy, refrigerant, flights and waste it used, and the sustainability team
turns those, with purchasing, freight and energy contract data, into the company's
greenhouse gas figures. Customers increasingly ask for the whole footprint: market-based
scope 2 and the scope 3 emissions of what Fjordvik buys and ships. Done by
hand, that is slow, error-prone and hard to trust: a unit slip makes a line 1,000 times
too big, copies of the central file drift, and country managers see all or nothing.

This project automates and governs that routine. Power Automate flows collect and check
each site's file against ten written rules, a Power BI model and report give management
and each country manager one tested set of figures, and a Claude connector answers
plain-language questions from the same data. It covers 36 months, January 2023 to
December 2025: scope 1, location-based and market-based scope 2, and scope 3 categories
1, 3, 4, 5, 6 and 9, with every category not yet calculated listed with its reason.

> **Synthetic data only.** Fjordvik Manufacturing Oy is a fictional company, and this is a
> portfolio project. No real company, client or person is described. The emission factors
> are **illustrative**, not cited, and must not be used for real reporting.

| Folder | What it shows | Tests |
| --- | --- | --- |
| [`data`](data) | The governed dataset: a twelve-table star schema with fixed names, checksums and quality tests | 38 |
| [`mcp`](mcp) | A Model Context Protocol (MCP) server that gives Claude six read-only tools over the data (Python, DuckDB) | 56 |
| [`powerbi`](powerbi) | A Power BI Project: semantic model in Tabular Model Definition Language (TMDL), 36 Data Analysis Expressions (DAX) measures, row-level security, a ten-page report | 225 (68 need Power BI Desktop open) |
| [`power-automate`](power-automate) | Power Automate intake and reminder flows with ten written rules, designed and tested offline | 26 |

Each folder has its own README with the problem, approach, architecture, test evidence
and limitations. [docs/learning-guide.md](docs/learning-guide.md) sets out the business
need and the data, then explains how each part was built and why each main decision was
made. The [process map](https://voneeci.github.io/fjordvik/docs/process-map.html) shows the
whole monthly process, from energy being used to the Power BI report, with the owner,
tool, data and checks for each step (source: [docs/process-map.html](docs/process-map.html)).

## How the parts fit

```
Site workbooks ──> Power Automate intake flow (power-automate/) ──> central Emissions list
Reference lists (sites, sources, factors), finance (revenue), HR (headcount) ──┐     │
ERP purchase ledger, transport system, energy contracts ───────────────────────┤     │
                                                                               ▼     ▼
                          governed dataset: twelve tables + manifest.json (data/tables/)
                                                    │
                              ┌─────────────────────┴─────────────────────┐
                              ▼                                           ▼
                  Power BI report (powerbi/)                Claude connector (mcp/)
```

Each month every site uploads a workbook of what it used. The intake flow checks it
against ten written rules and adds it to the central Emissions list, which joins the
reference lists, the finance and HR figures, and the purchase, freight and energy
contract exports in one governed dataset. The Power BI
report and the Claude connector both read that dataset, so they always show the same
numbers, and each part's tests check the files against the checksums in
`data/tables/manifest.json` before relying on them.

## How to run

You need Python 3.10 or newer. Each folder has its own virtual environment. In
PowerShell, from the folder:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"     # data and mcp
.venv\Scripts\python -m pip install pytest           # powerbi
.venv\Scripts\python -m pip install pytest openpyxl  # power-automate
.venv\Scripts\python -m pytest -q
```

Power BI Desktop (free) is needed to open `powerbi/FjordvikEmissions.pbip` and run the
live measure tests. Claude Desktop is needed to use the MCP server; see
[mcp/README.md](mcp/README.md).

## History

The four parts were built as separate repositories from 12 to 16 October 2026 and
combined here on 30 October 2026 with their full git history (`git subtree`), so every
original commit keeps its hash. The old repositories are archived on GitHub.

## Licence

Code: MIT (the `LICENSE` file in each folder). Data: Creative Commons Attribution 4.0
(CC BY 4.0) ([data/LICENSE-DATA.md](data/LICENSE-DATA.md)).
