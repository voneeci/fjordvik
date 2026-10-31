# fjordvik-powerbi

Power BI Project (PBIP: TMDL model + PBIR report) over the synthetic Fjordvik dataset.
One of four folders in the fjordvik repository: data (source of the data), mcp, powerbi,
power-automate. Permanent rules in
`C:\Users\reece\Projects\knowledge\RULES.md` override this file.

## Rules for this repo

- Synthetic data only. Emission factors are illustrative, not cited (Reece's one-off
  exception for the Fjordvik project, 12 October 2026). Every page and doc says so.
- The `DataFolder` parameter points at the repository's shared `data\tables` folder; never
  edit that folder from here. `tests/test_data.py` checks its checksums and the parameter.
- Report JSON is generated: edit `scripts/build_report.py`, never the visual.json files.
  The rebuild test compares JSON content (not bytes), so a Desktop save that changes
  nothing passes; a Desktop save that changes report settings means updating the
  generator to match (as on 16 October 2026). The data dictionary is generated: run
  `scripts/build_data_dictionary.py` after any model change. Tests fail if either is stale.
- TMDL needs tab indentation and UTF-8 without BOM. Measure DAX sits three tabs deep.
- Follow `docs/naming-conventions.md`: measures in `_Measures`, unit in the name,
  `DIVIDE()`, no typed-in rates (only unit conversions and the date-key shift).
- dim_date is monthly, so it can't be a marked date table; no SAMEPERIODLASTYEAR.
- Power BI Desktop holds the model in memory: close it **without saving** before
  regenerating files, or it overwrites them. Desktop's own save form (lineage tags,
  cultures, .platform, diagramLayout.json) is the committed form. `.pbi/cache.abf` and
  `.pbi/localSettings.json` stay out of git.
- `scripts/run_dax_table.ps1 -Refresh` loads the data through the engine with no clicks;
  raw output of every live run goes in `evidence/`.
- Live tests (`tests/test_measures_live.py`) need Desktop open and refreshed; the
  runner finds the local engine's port from the msmdsrv.exe process.
- A deliberate change to an expected value says which change and why.
- Writing: no em dashes, Australian spelling, spell out acronyms on first use.

## Commands

```bash
python scripts/build_report.py            # regenerate report pages
python scripts/build_data_dictionary.py   # regenerate docs/data-dictionary.md
python -m pytest -q                       # 153 tests (44 need Desktop open)
```
