# Fjordvik handover: phase 3 inputs from the data part (11 November 2026)

**Read at commit** `d93fd1b` (main, clean, level with origin). **Commit made:** `0abbabd` on
branch `data/phase3-inputs`, and this note. Nothing pushed, nothing merged.

Fjordvik Manufacturing Oy is fictional and all data is synthetic. Phase 3 of the after-sales
service AI (failure prediction) needs inputs that only the data part may build. This block
built them. No existing table, manual or answer-key file moved, and `GENERATOR_VERSION` is
still 1.4.0, so the checksums phase 2 pinned still hold.

## What Reece decided (11 November 2026, question box and plan approval)

- Travel speed 60 km/h and road-distance factor 1.3: Fjordvik's own planning inputs.
- "Needs to be a rate per country" for labour: used as one rate for each of the four
  countries, by the country the technician is based in (home town). T12, employed by Tartu
  Warehouse and based in Riga, takes the Latvian rate. Reece saw this reading in the plan
  and in the results before the commit.
- Allowed missing share for vibration and bearing temperature: 2%.
- Sources are written as the research note's neutral descriptions with dates, no company
  name and no link. The links are in the research note in the knowledge inbox
  (`2026-11-11-jasila-fjordvik-visit-cost-inputs.md`).

## What changed (`0abbabd`)

- **`data/src/fjordvik_data/scenarios.py`** (new), run as
  `python -m fjordvik_data.scenarios --out <folder outside data>`. It rebuilds the base
  telemetry from the committed dimensions, stops unless it matches `tables/manifest.json`,
  and writes `control/`, `drift_recalibration/` and `drift_unit_change/` (each a
  `fact_asset_telemetry.csv`) and `drift_scenarios.csv`. Without `--record` it checks the
  files against `data/scenarios/manifest.json`. With `--record scenarios` it rewrites the
  two committed files. It refuses to write inside `data/`.
- **`data/scenarios/manifest.json`**: rows and SHA-256 of the four scenario files, the seed,
  the generator version and the base telemetry's checksum.
- **`data/scenarios/planning_inputs.json`**: the two costs, their working, every input and
  its source, and what is left out.
- **`config.py`**: `PUBLISHED_RATES` (labour cost per hour, van running cost, the unplanned
  to planned ratio), Fjordvik's planning inputs, the scenario settings and
  `TELEMETRY_SCHEMA`, each labelled as published or as Fjordvik's own (D7).
- **`service.py`**: `warning_rise=True` on `simulate_asset` and `build_fleet`. Off, no sensor
  rises before a failure; every draw is still made.
- **`localdate.py`** (new): `local_date(timestamp)` for Europe/Helsinki (D14). `tzdata` is
  in the dev libraries, because Windows has no system time zone data.
- **Tests:** `test_scenarios.py` (10), `test_telemetry_schema.py` (3), `test_local_date.py`
  (11), and a `scenario_files` fixture in `conftest.py`.
- **Docs:** `data/README.md` (the scenarios, the two costs, the schema, the test count, and
  three row counts corrected from `tables/manifest.json`: `fact_parts_order` 53,654,
  `fact_portal_event` 39,725, `dim_source` 14), `data/CLAUDE.md`, and the data test count
  in the root `README.md` and `CLAUDE.md`.

## Figures (synthetic)

| Figure | Value |
| --- | --- |
| Wasted visit | EUR 190.34 per event |
| Missed failure | EUR 892.44 central, 339.13 low, 1,784.89 high (ratios 2.0, 1.38, 3.0) |
| Mean straight-line distance, nearest qualified technician to pump | 58.27 km one way |
| Mean road distance, round trip | 151.5 km |
| Mean travel time, round trip | 2.525 hours |
| On-site hours (mean of 562 inspections) | 1.5032 hours |
| Mean planned repair cost (324 failures) | EUR 892.44: labour 230.06, parts at list price 662.38 |
| Wasted visit by the technician's country | Finland 216.46 (369 pumps), Sweden 201.96 (117), Estonia 149.79 (57), Latvia 37.96 (57) |

Scenario files, each 582,996 rows:

| File | SHA-256 (first 12) | What differs from the tables |
| --- | --- | --- |
| `control/fact_asset_telemetry.csv` | `3a56d52674d2` | 5,887 rows, all inside warning windows; all 222 warned failures differ |
| `drift_recalibration/fact_asset_telemetry.csv` | `cf7c3649fa7b` | 4,136 rows at 30 pumps, bearing temperature only |
| `drift_unit_change/fact_asset_telemetry.csv` | `d59d6087548d` | 3,480 rows at 40 pumps, vibration only |
| `drift_scenarios.csv` | `956870a2d30d` | 70 rows |

526 of the 600 pumps have reported since 1 July 2024 or earlier, so they could be picked.

## Test results (each from its own folder and `.venv`)

| Part | Result | Evidence |
| --- | --- | --- |
| data | 120 passed (was 96) | `data/evidence/pytest-phase3-inputs-2026-11-11.txt` |
| mcp | 83 passed | `mcp/evidence/pytest-phase3-inputs-2026-11-11.txt` |
| powerbi | 579 passed, 154 skipped (Desktop closed) | `powerbi/evidence/pytest-phase3-inputs-2026-11-11.txt` |
| power-automate | 30 passed | `power-automate/evidence/pytest-phase3-inputs-2026-11-11.txt` |
| service-ai | 27 passed | `service-ai/evidence/pytest-phase3-inputs-2026-11-11.txt` |

`python guardrails\check.py`: no findings. It skipped the banned-names check (D2) because
the private list is not on this laptop. `python -m fjordvik_data --out tables` was rerun and
git showed no change under `tables/`, `corpus/`, `generator-truth/`, `erp-extract/` or
`reference/`.

## Things to know

- **What the rates are.** The labour figure is the midpoint of two published occupation
  groups, worked out by the research chat and not itself a published value. The van figure
  is a Finnish 2022 value moved to 2026 and used for all four countries. The ratio is a
  programme cost per horsepower from 2010 guidance, not a cost per event. Parts are at the
  2023 list price and labour at 2026 cost. The files say all of this.
- **RULES.md asks for a source link on every number.** These rates carry descriptions and
  dates only, as Reece asked for a public repository. The links are in the research note.
- **The missed-failure cost covers Fjordvik's repair cost only.** The customer's downtime
  and expedited parts are left out: no published figure was found.
- **The wasted-visit formula** applies the road factor to both the van km and the travel
  hours.
- **The unit-change scenario keeps the column's two decimals**, so readings look like 0.09.
  `test_a_silent_unit_change_breaks_the_schema` shows the D13 range catches it.
- **The control rewrites telemetry only.** `fact_service_event` is the same, so technician
  notes still mention rising readings. They are off the feature allowlist (D12).
- **The two drift scenarios pick pumps separately**, so a pump can be in both lists.
- **D14, still missing.** The generator builds telemetry from calendar dates, not from
  timezone-aware timestamps, so nothing in it calls `local_date`. The README now says
  `date_key` is the Europe/Helsinki date for every pump, so a Swedish pump's day starts an
  hour before its own midnight.
- **The scenario tests add about 50 seconds** to the data tests (two fleet simulations).
- Rework: one shell command with two heredocs was rejected before it ran; the same edits
  were made with the file tools. No test failed and no test or tolerance was changed.
  Minutes were not measured.

## Open

- Reece: push `data/phase3-inputs` and merge it when ready. Nothing is pushed.
- Chats open in the repository root (Attena, service-ai, any data chat) restart or `/clear`,
  because `CLAUDE.md` and `data/CLAUDE.md` changed.
- The research note is not yet in the wiki; Forgd ingests it.
- If Reece meant the labour rate to follow the pump's country, change `technician_country`
  in `scenarios.py`, rerun with `--record scenarios` and commit the new figures.

## Next step

Start a fresh service-ai chat for phase 3. It reads `service-ai/docs/phase-rules.md`
("Every phase" and "Phase 3"), `data/scenarios/planning_inputs.json` and this note, then
builds the scenarios into `service-ai/build/ml-scenarios/` with the command above.
