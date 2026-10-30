# Fjordvik: emissions data, Power BI, Power Automate and a Claude connector

Four portfolio projects built on one synthetic dataset for Fjordvik Manufacturing Oy, a
**fictional** manufacturer with six sites in Finland, Sweden and Estonia and 36 months of
monthly data (January 2023 to December 2025).

> **Synthetic data only.** No real company, client or person is described. The emission
> factors are **illustrative**, not cited, and must not be used for real reporting.

| Folder | What it shows | Tests |
| --- | --- | --- |
| [`data`](data) | The dataset: a seeded Python generator, a five-table star schema and its quality tests | 24 |
| [`mcp`](mcp) | A Model Context Protocol (MCP) server that gives Claude five read-only tools over the data (Python, DuckDB) | 48 |
| [`powerbi`](powerbi) | A Power BI Project: semantic model in Tabular Model Definition Language (TMDL), 14 Data Analysis Expressions (DAX) measures, row-level security, a three-page report | 100 (31 need Power BI Desktop open) |
| [`power-automate`](power-automate) | Power Automate intake and reminder flows with ten written rules, designed and tested offline | 26 |

Each folder has its own README with the problem, approach, architecture, test evidence
and limitations.

## How the parts fit

```
data/ ──generator──> data/data/*.csv + manifest.json (SHA-256 checksums)
                          │
          scripts/sync_data.py in each folder (refuses files that fail their checksum)
                          │
        ┌─────────────────┼──────────────────┐
        ▼                 ▼                  ▼
  mcp/data/         powerbi/data/     power-automate/data/
```

The three consumers each keep a checked copy of the dataset, so each folder runs and
tests on its own. To refresh a copy after a data change, run
`python scripts\sync_data.py` from that folder; it reads `..\data` by default.

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

Code: MIT. Data: Creative Commons Attribution 4.0 (CC BY 4.0). See the `LICENSE` and
`LICENSE-DATA.md` files in each folder.
