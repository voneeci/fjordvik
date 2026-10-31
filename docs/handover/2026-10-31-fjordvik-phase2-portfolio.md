# Fjordvik phase 2 handover: portfolio reporting (31 October 2026)

**Read at commit** `caa096f` (phase 1, pushed). Research: Jasila's note
`knowledge/raw/inbox/2026-10-31-jasila-fjordvik-erp-portfolio-reporting.md` (modified
31 October 2026, 16:29). **Commits made:** `12e7904` (data), `17fd6ec` (mcp), `9053e55`
(powerbi), `be0b8f7` (docs), and this note.

## What Reece decided (31 October 2026, question box and plan approval)

- Oracle-style zipped CSV extract with a manifest, cleaned by DuckDB SQL inside `data`.
- Price/volume/mix: ACCA F5 sales variances with the prior year as standard.
- A kronor slip, converted at European Central Bank (ECB) rates fetched and cited.
- Weighted scoring; weights as Fjordvik's own input in a table.
- Four sales regions; sustainability per product as use-phase only (no allocation);
  region roles see their own region's sales only.
- Rule change approved with the plan: the simulated ERP extract is an intake file and
  may carry planted problems; `data/tables` stays clean (data/CLAUDE.md updated).

## What changed

- **data:** `dim_product_group`, `dim_product` (4 families, 10 groups, 24 models),
  `dim_region`, `dim_product_code`, `fact_sales` (3,379 rows), `fact_data_issue` (4),
  `fact_use_phase` (1,940, category 11), `dim_score_criterion`, `fact_product_rating`
  (720). `erp-extract/`: 36 months of simulated Oracle Data Extraction tool output (163
  ZIPs, a manifest per month) with legacy item numbers, two unmapped codes, a re-sent
  file and a month with no currency code. `sql/`: six DuckDB scripts (stage,
  deduplicate, currency, classify, publish, reconcile). `reference/`: the classification
  map, business units, region codes, and ECB monthly EUR/SEK rates (series
  `EXR.M.SEK.EUR.SP00.A`, fetched 31 October 2026, raw response kept). Category 11 is
  "Calculated in part" (Rest of world has no factor source). Phase 1 tables keep their
  checksums. DuckDB added to data's dependencies.
- **mcp:** 21 tables, category 11 in `all_emissions`, new `sales_summary` tool, a
  sales-reconcile-to-finance check.
- **powerbi:** 9 tables, 19 relationships, 26 new measures (62 in all), four region
  roles that filter `dim_region` and deny site emission and finance tables, six new pages
  (16 in all). Total Emissions includes category 11.
- **docs:** `docs/portfolio-user-guide.md`, `docs/portfolio-project-plan.md`,
  `docs/scorecard-method.md`, `powerbi/docs/refresh-design.md`; READMEs, learning
  guide, company profile, factor notes, naming conventions, process map (29 steps).
- **Learning document** (claude.ai Docs): main tab figures and a Step 7 section; new tab
  **Portfolio analytics** (11 concepts, each with a Desktop exercise checked live in
  `powerbi/evidence/portfolio-exercises-2026-10-31.txt`).
- Private learning material for Reece was also written outside the repository; nothing
  about it is stored here.

## Figures (illustrative)

| Year | Net sales (EUR million) | Margin | Total emissions (tCO2e) | Of which category 11 |
| --- | --- | --- | --- | --- |
| 2023 | 137.42 | 39.0% | 2,372,794.0 | 2,311,372.6 |
| 2024 | 146.19 | 39.7% | 2,384,992.1 | 2,321,211.9 |
| 2025 | 154.68 | 40.2% | 2,328,686.6 | 2,262,064.1 |

Margin bridge 2025 against 2024 (company): price +4.38 million, mix −13.40 million,
quantity +15.46 million, cost −2.26 million, total +4.18 million. Within Industrial
process pumps: price +1.51, mix −0.69, quantity +0.17, cost −0.79, total +0.20 million.

**Against the plan's estimate.** The plan said Total Emissions would rise to "roughly
1.3 to 1.6 million tCO2e for 2025". The generated figure is 2,328,686.6, because the
synthetic product specifications (yearly kWh at full rated power) give more use-phase
electricity than I estimated. Category 11 is 97% of the total, as planned. This needs
Reece's decision: keep, or lower the yearly kWh in `config.py` (a regeneration).

Spot checks by hand: Gothenburg line `GOT0000393` (March 2024, 4 × `GBG-51522`) is
SEK 300,097.58; at the ECB rate 11.30538 that is EUR 26,544.67. `IPP-SC-160` sold 3
units in Western Europe in March 2025: 3 × 20 years × 640,000 kWh = 38,400,000 kWh ×
0.250 kg ÷ 1,000 = 9,600 tCO2e, as stored. Its 2025 price effect: (41,373.24 −
39,765.87) × 104 units = EUR 167,166.

## Addendum: pump yearly kWh lowered (Reece's decision, 31 October 2026)

Reece chose to lower the category 11 scale. Every product's `kwh_per_year` in
`data/src/fjordvik_data/config.py` was multiplied by 0.6 (rounded to the nearest 100 kWh):
expected use in service is below rated power because pumps run part-loaded. Only
`dim_product.csv`, `fact_use_phase.csv` and the manifest changed; sales, margins and
every other emission source are unchanged.

| Year | Total emissions (tCO2e) | Of which category 11 |
| --- | --- | --- |
| 2023 | 1,448,328.1 | 1,386,906.8 |
| 2024 | 1,456,602.1 | 1,392,821.8 |
| 2025 | 1,423,966.5 | 1,357,344.0 |

Category 11 is now 95% of the 2025 total, inside the plan's 1.3 to 1.6 million range.
Like-for-like change 2025: -2.3%. The figure tables above are the earlier run.
Evidence: `*/evidence/pytest-lower-kwh-2026-10-31.txt`.

## Addendum: page check (Reece asked, 31 October 2026)

All 16 pages were checked by eye in Desktop and fixed in `scripts/build_report.py` (three
rounds): headers tall enough for their notes; smaller page-button text so all 16 names
show; data labels in thousands (category 11 made small bars read 0.0M); short labels on
cards, tables and legends; room for long category names; a Scope slicer on Emissions
breakdown; the Price, volume and mix family view as a table; tables and the margin chart
sized so every row shows. The duplicate-lines issue now names the ZIP that arrived
(`data/sql/05_publish.sql`), not the staging file. Screenshots in `powerbi/docs/images/`
are new, with three portfolio pages added to the Power BI README.

Known and left: the per-product table on Product sustainability (24 rows) and the
classification table scroll; category 11 still dominates the emission charts, which the
Overview and Breakdown notes say.

Evidence: `powerbi/evidence/pytest-layout-live-2026-10-31.txt` (371 passed, live model
refreshed); `data`, `mcp` and `power-automate` in `evidence/pytest-layout-2026-10-31.txt`
(58, 59 and 26 passed).

## Addendum: connector over HTTP with sign-in (Reece's choice, 31 October 2026)

Reece chose to see the connector working rather than build the other designed items:
try the local connector in Claude Desktop, then build the company-style version. The
Power BI Service, Power Automate tenant and data feeds stay as designs.

- `python -m fjordvik_mcp --http` serves the seven tools over Streamable HTTP on
  127.0.0.1:8765 only, behind OAuth 2.1 sign-in (dynamic client registration, PKCE,
  one-hour tokens that name this server as their audience). Code: `mcp/src/fjordvik_mcp/auth.py`,
  `server.py` (`permitted()` in every tool).
- Four demo roles mirror the Power BI security roles: Group analyst (everything),
  Sustainability reviewer (emissions only), Nordics and Western Europe sales managers
  (their region's sales only). `run_sql` is for the group analyst only. The sign-in page
  is a demo: pick a role, no password, nothing secret.
- `mcp/scripts/try_http_connector.py` signs in through the browser and calls three tools.
  Run as Group analyst it returned four regions (Nordics 2025 net sales EUR 67,502,855.20)
  and 3,379 sales rows from `run_sql`; as Nordics sales manager, the Nordics only with the
  same figure, and `run_sql` refused.
- 17 new tests in `mcp/tests/test_http_auth.py` (each OAuth refusal, each role against the
  real server, the SDK's own client end to end). Planting two faults (no region filter,
  `run_sql` open to all) made four fail.

Evidence: `mcp/evidence/pytest-http-auth-2026-10-31.txt` (76 passed),
`mcp/evidence/try-http-connector-group-analyst-2026-10-31.txt`,
`mcp/evidence/try-http-connector-nordics-manager-2026-10-31.txt`.

Not built: hosting, a real identity provider, access from claude.ai or phones (they
connect from Anthropic's cloud and cannot reach localhost), an audit log.

## Addendum: report redesign from the dashboard review (31 October 2026)

A research note reviewed all 16 pages against Microsoft's Power BI guidance, the
International Business Communication Standards (IBCS) and the wiki's dashboard rules.
Reece chose to build its whole top 10, split the report in two on one model, add a budget,
and name the bridge steps as segment reports do.

- **Two errors fixed.** With Year on "All", the Price, volume and mix cards showed the whole
  2025 margin (EUR 62.2 million) as the change; every Year slicer now opens on 2025 alone,
  and the 2025 change reads EUR 4,175,972. The bridge table's columns now add up (mix and
  quantity within each group; a note gives the mix between groups, EUR -12.9 million in 2025).
- **Budget.** `fact_budget` (1,368 rows): Fjordvik's plan by month, site, product group and
  region, worked back from actuals through a planned variance per family and year
  (`config.py`, synthetic client input). 2025 net sales are 0.2% under budget.
- **Two reports, one model.** `FjordvikEmissions.pbip` (10 pages) and
  `FjordvikPortfolio.pbip` (7 pages). Every page: page buttons, a title sentence from the
  data, slicers, comparisons under each card, a footer with caveat, owner, period and
  refresh time. A theme lifts all text to 4.5:1 contrast. New: the margin waterfall, share of
  sales beside share of margin, growth against margin, shaded score matrix with the change on
  the prior quarter, score against margin, margin against use-phase emissions per euro.
- **Model.** 72 new measures (134 in all): comparisons, budget, bridge, scorecard, text;
  `dim_bridge_step` and `dim_refresh` hold no figures. Desktop saved the model in its own
  form on opening it after the change (blank lines, diagram layout, language metadata).
- **Then finished (Reece asked the same evening):** every waterfall step labelled (an invisible
  line along the step tops carries each value through a dynamic format string), Year,
  Country and Region slicers synced across each report's pages, and dashed company-average
  lines on the three scatter charts. Evidence: `powerbi/evidence/pytest-labels-sync-live-2026-10-31.txt`
  (727 passed). All 17 pages are on [powerbi/docs/report-pages.md](../../powerbi/docs/report-pages.md).
- **Not built:** the gap list's forecast, cost split, currency effect, customer segments
  and market share (each needs data Fjordvik does not hold yet).

Evidence: `powerbi/evidence/pytest-redesign-live-2026-10-31.txt` (701 passed, Desktop open
and refreshed), `powerbi/evidence/pytest-redesign-offline-2026-10-31.txt` (553 passed, 148
skipped), `data`, `mcp` and `power-automate` in `evidence/pytest-budget-2026-10-31.txt`
(60, 76 and 26 passed). Screenshots of all 17 pages are in `powerbi/docs/images/` (six of
them) and in the knowledge folder's raw exports.

## Test results (each from its own folder and `.venv`)

| Part | Result | Evidence |
| --- | --- | --- |
| data | 58 passed (nine planted-problem tests) | `data/evidence/pytest-portfolio-2026-10-31.txt` |
| mcp | 59 passed | `mcp/evidence/pytest-portfolio-2026-10-31.txt` |
| powerbi | 371 passed, Desktop open and refreshed (109 live) | `powerbi/evidence/pytest-portfolio-2026-10-31.txt`, `live-measures-2026-10-31-portfolio.txt`, `live-refresh-2026-10-31-portfolio.txt` |
| power-automate | 26 passed | `power-automate/evidence/pytest-portfolio-2026-10-31.txt` |

`build_report.py` and `build_data_dictionary.py` were rerun; rebuild tests pass;
unchanged generated JSON restored; Desktop (opened by me) closed without saving and git
showed no rewrites. One phase 1 live case changed deliberately: category 11 is no longer
blank (`expected.py` says so).

## Open

- Incremental refresh and Service publishing are designed, not built.
- Rest of world category 11 and categories 2, 7 and 12 remain uncalculated.

## Next step

Apply the dashboard design recommendations from the research note when it arrives (the
16 page screenshots it reviews were taken at commit 87faac1).
