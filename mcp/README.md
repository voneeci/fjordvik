# Fjordvik MCP: a Claude connector for emissions data

Fjordvik Manufacturing Oy, a maker of electric pumps and pump systems
([company profile](../docs/company-profile.md)), gets questions about its emissions that
no dashboard page was built for, from its own managers and from customers asking for its
footprint. This connector lets them ask Claude in plain language and
get an answer from the same governed data the Power BI reports use. It is a Model Context
Protocol (MCP) server: Claude calls seven read-only tools, and the server answers from a
locked-down DuckDB database (a file-based analytics database) built from the shared
dataset in [`data/tables`](../data/tables). It runs two ways: inside Claude Desktop for
one person, or over HTTP behind a sign-in, the way a company would share it, where each
role sees only what it should.

> **Synthetic data only.** Fjordvik Manufacturing Oy is a fictional company, and this is a
> portfolio project. No real company, client or person is described. The emission factors
> are **illustrative**, not cited, and must not be used for real reporting.

## Problem

Managers ask questions such as "which site is our worst emitter per euro of revenue?" or
"what changed at Tampere Plant after the solar panels went in?". The answers are in the
data, but each new question waits for an analyst to build a spreadsheet. An AI assistant
can answer straight away, but only if it can reach the data safely: it must not change
anything, must not read files it was not given, and must get the arithmetic right (for
example, averaging headcount over months instead of adding it up).

## Approach

- **Purpose-built tools first, SQL as a fallback.** Six tools answer the common
  questions with tested logic: `describe_dataset`, `emissions_total`,
  `emissions_intensity`, `scope3_inventory`, `sales_summary` and `data_quality_report`.
  A seventh, `run_sql`, handles anything else, but only as a single read-only `SELECT`.
- **One view of the inventory.** An `all_emissions` view stacks the four location-based
  emission tables (site emissions, upstream energy, purchases, freight), so every total
  covers the same rows as the Power BI reports. Market-based scope 2 is an option
  (`scope2_method="market"`) that swaps scope 2 rows; it is never added to the total.
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
- **Sign-in and roles over HTTP.** With `--http` the server runs over Streamable HTTP and
  asks for OAuth 2.1 sign-in, the standard Claude clients use for remote connectors:
  dynamic client registration, an authorisation code protected by PKCE (Proof Key for
  Code Exchange), and an access token that expires after an hour and names this server
  as its audience. Each tool checks the signed-in role, mirroring the Power BI security
  roles (below). The sign-in page is a demo: you pick a role, with no password.

## Architecture

```
Claude Desktop ──stdio──────────────────┐
                                        ▼
HTTP client ──Streamable HTTP──> fjordvik-mcp server (Python, MCP SDK 2.x)
  │  (127.0.0.1:8765 only)            │  server.py   tools, role checks, error handling
  │                                   │  auth.py     OAuth sign-in, demo roles (HTTP only)
  └─ browser: sign-in page            │  queries.py  SQL with bound parameters, run_sql guard
                                      │  db.py       loads CSVs, then locks the database
                                      ▼
                              DuckDB in memory  <── ../data/tables/*.csv (the shared
                                                    dataset, checked against SHA-256 checksums)
```

What each role can use over HTTP (over stdio there is no sign-in: one person, every tool):

| Demo role | Tools |
| --- | --- |
| Group analyst | All seven |
| Sustainability reviewer | `describe_dataset`, `emissions_total`, `emissions_intensity`, `scope3_inventory`, `data_quality_report` |
| Nordics sales manager | `describe_dataset`, and `sales_summary` for the Nordics only |
| Western Europe sales manager | `describe_dataset`, and `sales_summary` for Western Europe only |

`run_sql` is for the group analyst only, because free SQL could read around any filter. A
refused call says which roles can use the tool.

| Tool | Answers |
| --- | --- |
| `describe_dataset` | Sites (with first reporting month), sources, period, row counts, units, caveats |
| `emissions_total` | tCO2e grouped by any of year, quarter, month, site, country, site type, scope, source, category, scope 3 category; filtered by year, site, country, scope, source or month range; scope 2 location-based (default) or market-based |
| `emissions_intensity` | tCO2e per FTE or per million euros of revenue, by year, site, country or site type |
| `scope3_inventory` | All 15 scope 3 categories with status, reason and tCO2e for a year or the whole period |
| `sales_summary` | Units, net sales, margin and margin % from the cleaned ERP sales, by year, quarter, site, family, group, product or region |
| `data_quality_report` | Fifteen checks (the last: sales reconcile to finance): unique keys, joins, the tCO2e formula, no negatives, one unit per source, complete monthly grid, emissions and metrics covering the same site-months; for the value-chain tables, keys, joins, formula, market-based kWh matching location-based kWh, the freight payer split, and a reason for every scope 3 category |
| `run_sql` | Any single read-only `SELECT` against the 22 tables and the `all_emissions` view |

Resources: `fjordvik://schema` (tables, grain and joins) and `fjordvik://source` (the
data's manifest: dataset version, period, row counts and SHA-256 checksums).

## How to run

You need Python 3.10 or newer.

```bash
git clone https://github.com/voneeci/fjordvik.git
cd fjordvik/mcp
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest
```

### Connect it to Claude Desktop

Claude Desktop rewrites its configuration file when it quits, so an edit made while it
is running is lost. Make the change with the app fully closed:

1. Quit Claude Desktop from the system tray (right-click the Claude icon, Quit).
2. From the `mcp` folder, run:

   ```powershell
   python scripts\add_to_claude_desktop.py
   ```

   It finds `claude_desktop_config.json` (in
   `%LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude` for the Microsoft Store
   version, otherwise `%APPDATA%\Claude`), backs it up, adds the `fjordvik`
   entry shown in [claude_desktop_config.example.json](claude_desktop_config.example.json),
   and keeps every other setting. `--remove` takes it out again.
3. Open Claude Desktop. "fjordvik" appears under **+ > Connectors** in a chat.

Try:

- "Using the Fjordvik tools, which site had the highest emissions per million euros of
  revenue in 2025?"
- "Show Tampere Plant's monthly purchased electricity for 2023 and 2025. What changed,
  and why might that be?"
- "Run the data quality report and summarise it."

### Run it over HTTP with sign-in

This is how a company would share the connector: one server, many people, each signed in.
Here it runs on your own computer only (bound to 127.0.0.1, with Host headers checked).

1. In one terminal, from the `mcp` folder, start the server:

   ```powershell
   .venv\Scripts\python -m fjordvik_mcp --http
   ```

   It prints `Fjordvik connector with sign-in at http://127.0.0.1:8765/mcp`. Leave it
   running.
2. In a second terminal, from the `mcp` folder, run the try-it client:

   ```powershell
   .venv\Scripts\python scripts\try_http_connector.py
   ```

   Your browser opens the Fjordvik sign-in page. Pick a role. The browser says "Signed
   in", and the terminal shows what that role got back from three tools.
3. Run the client again and pick another role to compare. Press Ctrl+C in the first
   terminal to stop the server; all registrations and tokens are held in memory and go
   with it.

Behind the scenes the client does what Claude does when you add a connector that needs
sign-in: it reads the server's discovery documents
(`/.well-known/oauth-protected-resource/mcp` and `/.well-known/oauth-authorization-server`),
registers itself, sends you to sign in with a PKCE challenge, swaps the returned code
for a token, and sends the token with every request.

### Where the data comes from

The server reads the repository's shared `..\data\tables` folder, so there is nothing to
refresh here: a data change in `data` reaches the server the next time it starts. To
point it somewhere else, set `FJORDVIK_DATA_DIR` (see [.env.example](.env.example)).

## Test evidence

```
.venv\Scripts\python -m pytest -q
............................................................................ [100%]
76 passed in 7.54s
```

(31 October 2026; raw output in `evidence/pytest-http-auth-2026-10-31.txt`. Two signed-in
runs of the try-it client, as Group analyst and as Nordics sales manager, are in
`evidence/try-http-connector-*-2026-10-31.txt`.)

| Test file | What it proves |
| --- | --- |
| `test_queries.py` | Every tool's numbers reconcile with an independent calculation from the raw CSVs (totals by year, scope and country, month ranges, intensity per FTE and per euro, market-based scope 2, totals by scope 3 category, the 15-category inventory); bad filters explain the valid values |
| `test_sql_guard.py` | `SELECT` and `WITH` work; `DROP`, `DELETE`, `INSERT`, `UPDATE`, `CREATE`, `SET`, `ATTACH`, `COPY`, `INSTALL` and multiple statements are refused; a `SELECT` cannot read local files |
| `test_quality.py` | All fourteen checks pass on clean data, and each catches a planted problem: a duplicate row, a missing month, a unit error (kWh entered as MWh), an unknown site, a negative value, customer-paid freight put in category 4, market-based kWh that no longer match, a scope 3 category with no reason, a purchase from an unknown supplier |
| `test_server.py` | Over the MCP protocol: seven tools, all read-only; allowed values appear in the tool schema; results come back as structured content; errors carry a usable message; resources are readable; the server works as a real subprocess over stdio, as Claude Desktop runs it |
| `test_data.py` | The shared CSVs match their manifest's checksums, and the server reads the shared data folder by default |
| `test_http_auth.py` | Over HTTP with sign-in: no token is refused with a pointer to the discovery document; the discovery documents name the server and PKCE; the sign-in page lists the four roles and asks for no password; a full sign-in gives a one-hour token carrying the role; a wrong PKCE verifier, a reused code, an unregistered redirect address, a reused or unknown-role sign-in, an expired token, a token for another server and a request naming another host are each refused; against the real server started as a subprocess, each role can use exactly its tools, a region manager sees only their region (and the same figure the analyst sees for it), and the SDK's own OAuth client signs in end to end |

The safety tests were checked by breaking the code on purpose. With the region filter
removed and `run_sql` opened to every role, four of the sign-in tests fail. With the database lock
removed, the three local-file tests fail. With the error wrapper removed, the two
error-message tests fail. The network test passes even without the lock, because this
DuckDB install has no web extension to fetch with, so it proves less than the file
tests.

## Limitations

- **The HTTP version is a local demo.** It runs on 127.0.0.1 only, so claude.ai and the
  phone apps (which connect from Anthropic's cloud) cannot reach it. The sign-in page
  lets you pick a role instead of checking who you are; a company would use its identity
  provider (Microsoft Entra ID, for example) and read roles from groups. Registrations and
  tokens live in memory, so a restart signs everyone out, and there is no audit log of
  who asked what.
- **Loads everything into memory at start-up.** Fine for about 10,600 rows; a large dataset
  would use a persistent DuckDB file or query the source system directly.
- **Answers are only as good as Claude's reading of them.** The tools return correct
  numbers, but Claude still chooses which tool to call and how to explain the result.
  Check important answers against the Power BI model.
- Illustrative emission factors, scope 3 categories 2, 7 and 12 not yet calculated, and a
  simulated ERP extract (see the [data README](../data/README.md)).

## Next steps

- Host the HTTP version behind HTTPS, with sign-in through a real identity provider,
  roles from its groups, tokens in a shared store and an audit log, so claude.ai and
  phones can use it.
- A tool that runs Data Analysis Expressions (DAX) queries against the published Power
  BI semantic model, so Claude and the dashboards answer from the same measures.

## Licence

Code: MIT ([LICENSE](LICENSE)). Data: Creative Commons Attribution 4.0 (CC BY 4.0)
([data/LICENSE-DATA.md](../data/LICENSE-DATA.md)).
