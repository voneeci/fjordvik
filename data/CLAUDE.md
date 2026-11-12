# fjordvik-data

Synthetic dataset for Fjordvik Manufacturing Oy (fictional), shared by the other four
folders of the fjordvik repository: mcp, powerbi, power-automate and service-ai. Permanent
rules in `C:\Users\reece\Projects\knowledge\RULES.md` come first, then `..\GUARDRAILS.md`,
then this file.

## Rules for this repo

- Synthetic data only. No client, council or personal data. No secrets.
- Emission factors are **illustrative**, not cited. Reece gave a one-off exception to the
  RULES.md "real and cited factors" rule for the Fjordvik project only (12 October 2026).
  Every README and doc must say the factors are illustrative and not for real reporting.
- The shared schema is a contract. Never rename a table or column: the other four folders
  depend on the names in `tests/test_schema.py`. The 22 tables that existed at commit
  `484a158` keep their checksums (`tests/test_reproducible.py`); changing one needs
  Reece's yes.
- The clean dataset has no planted errors. Planted errors belong in the intake files of
  power-automate, and in the simulated ERP extract (`erp-extract/`), which is an intake file
  too: the SQL in `sql/` removes, corrects or quarantines each one and lists it in
  `fact_data_issue`, so `tables/` stays clean (Reece's approval of the phase 2 plan,
  31 October 2026).
- `reference/ecb_eur_sek_monthly.csv` is fetched from the ECB, and
  `reference/geonames_towns.csv` from GeoNames (`python -m fjordvik_data.geonames`), never
  generated or typed.
- No backfilling: a site's series starts at its first month.
- The service data (added 2 November 2026) carries a planted signal, not planted errors:
  most failures follow a warning rise in the readings and some come with none. The answer
  key in `generator-truth/` is for evaluation only, never a model feature.
- `fact_parts_order` must add up to `fact_sales` for the spare parts and service kits, in
  units and to the cent; the generator splits those rows and never changes them.
- Change the data only through `src/fjordvik_data/config.py` or the generator modules
  (`generate.py`, `portfolio.py`, `service.py`, `corpus.py`), then regenerate
  (`python -m fjordvik_data --out tables`) and commit code and data together.
  `tests/test_reproducible.py` fails if they drift. mcp, powerbi, power-automate and
  service-ai read `data/tables/` in place (no copies), so rerun their tests after any data
  change.
- `scenarios/` holds two generated files (added 11 November 2026): `manifest.json`, the
  checksums of the control and drift scenarios, and `planning_inputs.json`, the cost of a
  wasted visit and of a missed failure. Change them only by running the scenarios module
  with `--record scenarios`. The scenario CSV files are built outside `data/` and never
  committed. The published rates and Fjordvik's own planning inputs are labelled in
  `config.py`; never type a rate into a formula. `GENERATOR_VERSION` stays at 1.4.0 unless
  a table changes, because service-ai results pin the tables' manifest.
- A deliberate change to an expected value in a test says which change and why.
- Writing: no em dashes, UK English spelling, spell out acronyms on first use.

## Commands

```bash
python -m fjordvik_data --out tables   # regenerate (after pip install -e ".[dev]")
python -m fjordvik_data.scenarios --out ..\service-ai\build\ml-scenarios   # build and check the scenarios
python -m fjordvik_data.scenarios --out <folder outside data> --record scenarios   # also rewrite scenarios\
python -m pytest -q                  # 120 tests
```
