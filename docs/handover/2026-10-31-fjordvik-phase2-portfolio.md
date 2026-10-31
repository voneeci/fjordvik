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

- The category 11 scale above (Reece's call).
- The report pages were not checked by eye in Desktop (a slow visual check, left for a
  batch run on request); `powerbi/docs/images/` still shows the first version.
- Incremental refresh and Service publishing are designed, not built.
- Rest of world category 11 and categories 2, 7 and 12 remain uncalculated.

## Next step

Reece decides on the category 11 scale. Then: a visual check of the 16 pages, and
publishing to a Power BI Service trial to build the refresh design.
