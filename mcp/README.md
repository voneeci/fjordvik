# Fjordvik MCP: a Claude connector for emissions data

A Model Context Protocol (MCP) server that lets Claude answer questions about the
emissions of Fjordvik Manufacturing Oy, a **fictional** manufacturer with six sites in
Finland, Sweden and Estonia. Claude calls five read-only tools; the server answers from
a locked-down DuckDB database (a file-based analytics database) built from the shared
[fjordvik-data](https://github.com/voneeci/fjordvik-data) dataset.

> **Synthetic data only.** No real company, client or person is described. The emission
> factors are **illustrative**, not cited, and must not be used for real reporting.

## Problem

People ask data questions in plain language ("which site is our worst emitter per euro
of revenue?"), but the answers live in tables. An AI assistant can bridge that gap, but
only if it can reach the data safely: it must not change anything, must not read files
it was not given, and must get the arithmetic right (for example, averaging headcount
over months instead of adding it up).

## Approach

- **Purpose-built tools first, SQL as a fallback.** Four tools answer the common
  questions with tested logic: `describe_dataset`, `emissions_total`,
  `emissions_intensity` and `data_quality_report`. A fifth, `run_sql`, handles anything
  else, but only as a single read-only `SELECT`.
- **Defence in depth for `run_sql`.** Three layers, each tested on its own:
  1. DuckDB parses the SQL and anything that is not exactly one `SELECT` is refused
     before it runs.
  2. After loading, the database's access to files and the network is switched off,
     and that setting is locked so SQL cannot turn it back on.
  3. Results are capped at 1,000 rows.
- **No SQL injection.** Filter values are passed as bound parameters, and grouping
  columns come from a fixed list, never from free text.
- **Correct grain for intensity.** Emissions and revenue are flows (summed over
  months); full-time equivalent employees (FTE) is a level (summed across sites within
  a month, then averaged over months). The head office has no revenue, so its
  emissions per euro is `null`, not an error.
- **Helpful errors.** A wrong `site_id` returns the list of valid ones, so Claude can
  correct itself. Unexpected crashes return a generic message, so internal details stay
  on the server.
- **Read-only hints.** Every tool is annotated `readOnlyHint: true` and
  `destructiveHint: false`, so MCP clients can treat them as safe to call.

## Architecture

```
Claude Desktop ──stdio──> fjordvik-mcp server (Python, MCP SDK 2.x)
                              │  server.py   tools, resource, error handling
                              │  queries.py  SQL with bound parameters, guard for run_sql
                              │  db.py       loads CSVs, then locks the database
                              ▼
                          DuckDB in memory  <── data/*.csv (copied from fjordvik-data,
                                                 checked against SHA-256 checksums)
```

| Tool | Answers |
| --- | --- |
| `describe_dataset` | Sites (with first reporting month), sources, period, row counts, units, caveats |
| `emissions_total` | tCO2e grouped by any of year, quarter, month, site, country, site type, scope, source, category; filtered by year, site, country, scope, source or month range |
| `emissions_intensity` | tCO2e per FTE or per million euros of revenue, by year, site, country or site type |
| `data_quality_report` | Eight checks: unique keys, joins, the tCO2e formula, no negatives, one unit per source, complete monthly grid, emissions and metrics covering the same site-months |
| `run_sql` | Any single read-only `SELECT` against the five tables |

Resources: `fjordvik://schema` (tables, grain and joins) and `fjordvik://source` (the
fjordvik-data commit the bundled data came from).

## How to run

You need Python 3.10 or newer.

```bash
git clone <this repository>
cd fjordvik-mcp
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest
```

### Connect it to Claude Desktop

Claude Desktop rewrites its configuration file when it quits, so an edit made while it
is running is lost. Make the change with the app fully closed:

1. Quit Claude Desktop from the system tray (right-click the Claude icon, Quit).
2. From this repository's folder, run:

   ```powershell
   python scripts\add_to_claude_desktop.py
   ```

   It backs up `%APPDATA%\Claude\claude_desktop_config.json`, adds the `fjordvik`
   entry shown in [claude_desktop_config.example.json](claude_desktop_config.example.json),
   and keeps every other setting. `--remove` takes it out again.
3. Open Claude Desktop. "fjordvik" appears under **+ > Connectors** in a chat.

Try:

- "Using the Fjordvik tools, which site had the highest emissions per million euros of
  revenue in 2025?"
- "Show Tampere Plant's monthly purchased electricity for 2023 and 2025. What changed,
  and why might that be?"
- "Run the data quality report and summarise it."

### Refresh the data

```bash
python scripts/sync_data.py ..\fjordvik-data
```

The script refuses files whose checksum does not match the fjordvik-data manifest, and
records the source commit in `data/SOURCE.json`.

## Test evidence

```
.venv\Scripts\python -m pytest -q
................................................                         [100%]
48 passed in 6.17s
```

| Test file | What it proves |
| --- | --- |
| `test_queries.py` | Every tool's numbers reconcile with an independent calculation from the raw CSVs (totals by year, scope and country, month ranges, intensity per FTE and per euro); bad filters explain the valid values |
| `test_sql_guard.py` | `SELECT` and `WITH` work; `DROP`, `DELETE`, `INSERT`, `UPDATE`, `CREATE`, `SET`, `ATTACH`, `COPY`, `INSTALL` and multiple statements are refused; a `SELECT` cannot read local files |
| `test_quality.py` | All eight checks pass on clean data, and each catches a planted problem: a duplicate row, a missing month, a unit error (kWh entered as MWh), an unknown site, a negative value |
| `test_server.py` | Over the MCP protocol: five tools, all read-only; allowed values appear in the tool schema; results come back as structured content; errors carry a usable message; resources are readable; the server works as a real subprocess over stdio, as Claude Desktop runs it |
| `test_data.py` | The bundled CSVs match the fjordvik-data checksums, and the source commit is recorded |

The safety tests were checked by breaking the code on purpose. With the database lock
removed, the three local-file tests fail. With the error wrapper removed, the two
error-message tests fail. The network test passes even without the lock, because this
DuckDB install has no web extension to fetch with, so it proves less than the file
tests.

## Limitations

- **Local and single-user.** The stdio transport runs on one machine for one person.
  A company-wide connector would run as a remote server over HTTP with sign-in (OAuth)
  and per-user permissions.
- **Loads everything into memory at start-up.** Fine for 1,422 rows; a large dataset
  would use a persistent DuckDB file or query the source system directly.
- **Answers are only as good as Claude's reading of them.** The tools return correct
  numbers, but Claude still chooses which tool to call and how to explain the result.
  Check important answers against the Power BI model.
- Illustrative emission factors and location-based scope 2 only (see fjordvik-data).

## Next steps

- Re-pin the data to the fjordvik-data `v1.0.0` tag once it is created.
- A remote version (Streamable HTTP transport) with OAuth sign-in, as an organisation
  would deploy it.
- A tool that runs Data Analysis Expressions (DAX) queries against the published Power
  BI semantic model, so Claude and the dashboards answer from the same measures.

## Licence

Code: MIT ([LICENSE](LICENSE)). Data: Creative Commons Attribution 4.0 (CC BY 4.0)
([data/LICENSE-DATA.md](data/LICENSE-DATA.md)).
