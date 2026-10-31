# Fjordvik: monthly emissions reporting with Power Automate, Power BI and Claude

Fjordvik Manufacturing Oy has six sites in Finland, Sweden and Estonia. Every month each
site sends a spreadsheet of the fuel, energy, refrigerant, flights and waste it used, and
the sustainability team turns those into the company's greenhouse gas figures. Done by
hand, that is slow, error-prone and hard to trust: a unit slip makes a line 1,000 times
too big, copies of the central file drift, and country managers see all or nothing.

This project automates and governs that routine. Power Automate flows collect and check
each site's file against ten written rules, a Power BI model and report give management
and each country manager one tested set of figures, and a Claude connector answers
plain-language questions from the same data. It covers 36 months, January 2023 to
December 2025.

> **Synthetic data only.** Fjordvik Manufacturing Oy is a fictional company, and this is a
> portfolio project. No real company, client or person is described. The emission factors
> are **illustrative**, not cited, and must not be used for real reporting.

| Folder | What it shows | Tests |
| --- | --- | --- |
| [`data`](data) | The dataset: a seeded Python generator, a five-table star schema and its quality tests | 24 |
| [`mcp`](mcp) | A Model Context Protocol (MCP) server that gives Claude five read-only tools over the data (Python, DuckDB) | 48 |
| [`powerbi`](powerbi) | A Power BI Project: semantic model in Tabular Model Definition Language (TMDL), 14 Data Analysis Expressions (DAX) measures, row-level security, a three-page report | 100 (31 need Power BI Desktop open) |
| [`power-automate`](power-automate) | Power Automate intake and reminder flows with ten written rules, designed and tested offline | 26 |

Each folder has its own README with the problem, approach, architecture, test evidence
and limitations. [docs/learning-guide.md](docs/learning-guide.md) sets out the business
need and the data, then explains how each part was built and why each main decision was
made. [docs/process-map.html](docs/process-map.html) maps the whole monthly process, from
energy being used to the Power BI report, with the owner, tool, data and checks for each
step (download it and open it in a browser).

## How the parts fit

```
data/ ──generator──> data/data/*.csv + manifest.json (SHA-256 checksums)
                          │
        ┌─────────────────┼──────────────────┐
        ▼                 ▼                  ▼
       mcp/            powerbi/        power-automate/
```

The other three parts all read the one shared dataset in `data/data/`, so they always
show the same numbers. Each part's tests check the files against the checksums in
`data/data/manifest.json` before relying on them. After a data change, regenerate in
`data` and rerun every part's tests.

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
