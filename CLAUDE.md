# fjordvik

One repository holding four portfolio projects over the synthetic Fjordvik dataset:
`data` (source of the data), `mcp`, `powerbi` and `power-automate`. Permanent rules in
`C:\Users\reece\Projects\knowledge\RULES.md` override this file. Each folder's own
`CLAUDE.md` holds the rules for that part and applies to any file in it.

## Rules for this repo

- Synthetic data only. Emission factors are illustrative, not cited (Reece's one-off
  exception for the Fjordvik project, 12 October 2026). Every README and doc says so.
- On a CV these are "portfolio projects", never client work.
- The shared schema in `data` is a contract the other three folders depend on.
- Each consumer keeps its own checksum-verified copy of the data (Reece's choice, 30
  October 2026). Refresh with `python scripts/sync_data.py` from that folder (default
  source `..\data`); never edit a `data/` folder by hand.
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
cd powerbi && .venv\Scripts\python -m pytest -q          # 100 tests (31 need Desktop open)
cd power-automate && .venv\Scripts\python -m pytest -q   # 26 tests
```
