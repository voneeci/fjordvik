# fjordvik-data

Synthetic dataset for Fjordvik Manufacturing Oy (fictional), shared by the other three
folders of the fjordvik repository: mcp, powerbi and power-automate. Permanent rules in
`C:\Users\reece\Projects\knowledge\RULES.md` override this file.

## Rules for this repo

- Synthetic data only. No client, council or personal data. No secrets.
- Emission factors are **illustrative**, not cited. Reece gave a one-off exception to the
  RULES.md "real and cited factors" rule for the Fjordvik project only (12 October 2026).
  Every README and doc must say the factors are illustrative and not for real reporting.
- The shared schema is a contract. Never rename a table or column: the other three folders
  depend on the names in `tests/test_schema.py`.
- The clean dataset has no planted errors. Planted errors belong in the intake files of
  power-automate, and in the simulated ERP extract (`erp-extract/`), which is an intake file
  too: the SQL in `sql/` removes, corrects or quarantines each one and lists it in
  `fact_data_issue`, so `tables/` stays clean (Reece's approval of the phase 2 plan,
  31 October 2026).
- `reference/ecb_eur_sek_monthly.csv` is fetched from the ECB, never generated or typed.
- No backfilling: a site's series starts at its first month.
- Change the data only through `src/fjordvik_data/config.py` or `generate.py`, then
  regenerate (`python -m fjordvik_data --out tables`) and commit code and data together.
  `tests/test_reproducible.py` fails if they drift. mcp, powerbi and power-automate read
  `data/tables/` in place (no copies), so rerun their tests after any data change.
- A deliberate change to an expected value in a test says which change and why.
- Writing: no em dashes, Australian spelling, spell out acronyms on first use.

## Commands

```bash
python -m fjordvik_data --out tables   # regenerate (after pip install -e ".[dev]")
python -m pytest -q                  # 58 tests
```
