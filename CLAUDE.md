# fjordvik

One portfolio project in four parts over the synthetic Fjordvik dataset, one folder each:
`data` (source of the data), `mcp`, `powerbi` and `power-automate`. Permanent rules in
`C:\Users\reece\Projects\knowledge\RULES.md` override this file. Each folder's own
`CLAUDE.md` holds the rules for that part and applies to any file in it.

## Rules for this repo

- Synthetic data only. Emission factors are illustrative, not cited (Reece's one-off
  exception for the Fjordvik project, 12 October 2026). Every README and doc says so.
- Fjordvik is one project, never "four projects": data, mcp, powerbi and power-automate
  are parts of it (Reece, 31 October 2026). On a CV it is a "portfolio project", never
  client work.
- The shared schema in `data` is a contract the other three folders depend on.
- One shared copy of the data: mcp, powerbi and power-automate read `data/tables/`
  directly, and each part's `tests/test_data.py` checks it against `manifest.json`
  (Reece's choice, 31 October 2026, replacing the per-folder copies of 30 October).
  Never edit `data/tables/` by hand; change it only through the generator in `data`, then
  rerun every part's tests.
- One virtual environment per folder (`<folder>\.venv`); run each folder's tests from
  that folder.
- Combined from four repositories on 30 October 2026 with `git subtree`, so the original
  commit hashes still exist in this history. The old repositories (voneeci/fjordvik-data,
  fjordvik-mcp, fjordvik-powerbi, fjordvik-power-automate) are archived; work happens here.
- Writing: no em dashes, Australian spelling, spell out acronyms on first use.

## Commands

```bash
cd data && .venv\Scripts\python -m pytest -q             # 24 tests
cd mcp && .venv\Scripts\python -m pytest -q              # 48 tests
cd powerbi && .venv\Scripts\python -m pytest -q          # 153 tests (44 need Desktop open)
cd power-automate && .venv\Scripts\python -m pytest -q   # 26 tests
```
