# fjordvik

One portfolio project in five parts over the synthetic Fjordvik dataset, one folder each:
`data` (source of the data), `mcp`, `powerbi`, `power-automate` and `service-ai`.
Permanent rules in `C:\Users\reece\Projects\knowledge\RULES.md` come first, then
[GUARDRAILS.md](GUARDRAILS.md) (the project's master rules), then this file. Each folder's
own `CLAUDE.md` holds the rules for that part and applies to any file in it.

## Rules for this repo

- **GUARDRAILS.md is the master rule set** (Reece, 2 November 2026). Attena, the
  guardrails code chat, maintains it, `GUARDRAILS.sha256` and `guardrails/`. Every other
  chat follows them and suggests changes as a new file in `guardrails/proposals/`; never
  edit them yourself. Every part's `tests/test_guardrails.py` runs the checks, and
  `.claude/settings.json` runs `guardrails/claude_hook.py` before each tool call.
- Synthetic data only. Emission factors are illustrative, not cited (Reece's one-off
  exception for the Fjordvik project, 12 October 2026). Every README and doc says so.
- Fjordvik is one project, never "four projects" or "five projects": data, mcp, powerbi,
  power-automate and service-ai are parts of it (Reece, 31 October and 2 November 2026). On
  a CV it is a "portfolio project", never client work.
- The shared schema in `data` is a contract the other four folders depend on.
- One shared copy of the data: mcp, powerbi, power-automate and service-ai read
  `data/tables/` directly, and each part's `tests/test_data.py` checks it against
  `manifest.json` (Reece's choice, 31 October 2026, replacing the per-folder copies of
  30 October). Never edit `data/tables/` by hand; change it only through the generator in
  `data`, then rerun every part's tests.
- One virtual environment per folder (`<folder>\.venv`); run each folder's tests from
  that folder.
- Combined from four repositories on 30 October 2026 with `git subtree`, so the original
  commit hashes still exist in this history. Reece deleted the four old GitHub repositories
  on 2 November 2026; work happens here. A local copy of them sits in
  `old historical folders/`, kept out of git by `.git/info/exclude`: never commit it.
- Writing: no em dashes, UK English spelling, spell out acronyms on first use.

## Commands

```bash
cd data && .venv\Scripts\python -m pytest -q             # 96 tests
cd mcp && .venv\Scripts\python -m pytest -q              # 83 tests
cd powerbi && .venv\Scripts\python -m pytest -q          # 733 tests (154 need Desktop open)
cd power-automate && .venv\Scripts\python -m pytest -q   # 30 tests
cd service-ai && .venv\Scripts\python -m pytest -q       # 27 tests
python guardrails/check.py                               # the guardrail checks on their own
```
