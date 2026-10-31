# Fjordvik phase 1 handover: value-chain emissions (31 October 2026)

**Read at commit** `43ca8da` (31 October 2026). Research: Jasila's note
`knowledge/raw/inbox/2026-10-31-jasila-fjordvik-emission-categories.md`.
**Commits made:** `f1fabb1` (data), `446d768` (mcp), `89d9298` (powerbi), `8cb4d4e`
(power-automate), `702289c` (docs), and this note.

## What Reece decided (31 October 2026, question box and plan approval)

- Profile: Fjordvik makes electric pumps and pump systems (`docs/company-profile.md`).
- Market-based scope 2 in its own table, not a method column.
- One scope 3 table per data source (purchases, freight, upstream energy).
- Category 11 disclosed now as "Not yet calculated" with a reason; calculated in phase 2.
- Totals: location-based Total Emissions now holds scope 3 categories 1, 3, 4 and 9;
  market-based scope 2 sits beside it, never added.

## What changed

- **data:** seven new tables and two new `dim_source` columns (`scope3_category`,
  `method`) with sources S09 to S13. `fact_emissions`, `dim_date`, `dim_site` and
  `fact_site_metrics` are byte-identical to `43ca8da` (a test checks their old
  checksums). New units: `EUR`, `tonne-km`. `dim_scope3_category` lists all 15
  categories with status and reason. Factors are illustrative; each new one names the
  source a company would cite (`data/docs/emission-factors.md`).
- **mcp:** loads 12 tables and an `all_emissions` view; `emissions_total` gains
  `scope3_category` grouping and `scope2_method`; new `scope3_inventory` tool; 14 data
  quality checks (6 new).
- **powerbi:** 7 new tables, 15 new relationships, 36 measures (12 new), 10 pages (Value
  chain (scope 3) and Scope 2 methods are new). Introduction subtitle is now
  "A portfolio project. " + the caveat.
- **power-automate:** the Sources seed lists only the eight site-reported sources. Intake
  rules and workbooks unchanged.
- **docs:** company profile; README, learning guide and process map (27 steps, new lane
  and steps 16a to 16d) updated with recomputed figures.
- **Learning document** (claude.ai Docs, `JRYeDZ9ByrDvhPcRqGK3ph`): main tab updated
  (profile, totals, scope table, like-for-like figures) and a "Step 6: the value chain"
  section; new tab **Value chain emissions** with six concepts and a Desktop exercise each.
  Every exercise answer was checked live (`powerbi/evidence/learning-exercises-2026-10-31.txt`).

## Figures (illustrative, location-based tCO2e)

| Year | Before | Now | Scope 2 location-based | Scope 2 market-based |
| --- | --- | --- | --- | --- |
| 2023 | 9,454.0 | 61,421.3 | 5,294.0 | 8,003.2 |
| 2024 | 10,158.2 | 63,780.3 | 5,718.1 | 8,437.6 |
| 2025 | 10,921.8 | 66,622.5 | 6,243.6 | 7,383.5 |

Category 1 is 77% of 2025. Like-for-like 2025 change is +3.5% (was +2.9%); including
new sites +4.5% (was +7.5%). Tartu 2025: +13.2% like for like, +138.3% including its
first year.

Spot checks by hand (from the CSVs): Gothenburg's market-based electricity is 0.0 in
every month (hydro GOs cover all of it); purchases of castings and steel in 2025 are
EUR 21.9 million at 1.2 kg per euro = 26,289.7 tCO2e; customer-paid outbound freight in
2025 is 17.65 million tonne-km, all category 9 (634.6 tCO2e).

## Test results (each from its own folder and `.venv`)

| Part | Result | Evidence |
| --- | --- | --- |
| data | 38 passed | `data/evidence/pytest-value-chain-2026-10-31.txt` |
| mcp | 56 passed | `mcp/evidence/pytest-value-chain-2026-10-31.txt` |
| powerbi | 225 passed, Desktop open and refreshed (68 live) | `powerbi/evidence/pytest-value-chain-2026-10-31.txt`, `live-measures-2026-10-31-value-chain.txt`, `live-refresh-2026-10-31-value-chain.txt` |
| power-automate | 26 passed | `power-automate/evidence/pytest-value-chain-2026-10-31.txt` |

`build_report.py` and `build_data_dictionary.py` were rerun; the rebuild and dictionary
tests pass. Unchanged generated JSON was restored. Planted-mistake checks: six for the
new data tests and four for the new connector checks, each caught.

## Found and fixed along the way

- Scope 1 and 2 sources have no scope 3 category, so they land on the blank member of
  `dim_scope3_category`. A "by category" chart of Total Emissions would show a blank bar
  holding scopes 1 and 2; the Value chain chart uses `Scope 3 Emissions (tCO2e)` instead.
- The process map's first layout put a connector line through a new step; moved, and
  checked by script for overlaps and crossings (none).

## Open

- The report pages were not checked by eye in Desktop (slow visual check, left for a
  batch run on request). The screenshots in `powerbi/docs/images/` are still from the
  first version.
- Category 3(b) has no factor source for Finland, Sweden or Estonia; DESNZ transmission
  and distribution factors are UK-only.
- The ERP, transport and contract exports are not designed (gaps on the process map).
- The live process map at GitHub Pages updates once pushed.

## Next step

Phase 2, portfolio reporting: Jasila's ERP note arrived on 31 October 2026
(`knowledge/raw/inbox/2026-10-31-jasila-fjordvik-erp-portfolio-reporting.md`). Write the
phase 2 plan in plan mode and get Reece's approval before changing any file.
