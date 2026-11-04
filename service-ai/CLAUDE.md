# fjordvik-service-ai

The after-sales service AI over the synthetic Fjordvik dataset: forecasting, machine
learning, scheduling, recommendations, a service assistant and an agent, built one phase
at a time (phases 2 to 7). One of five folders in the fjordvik repository: data (source of
the data), mcp, powerbi, power-automate and service-ai. Permanent rules in
`C:\Users\reece\Projects\knowledge\RULES.md` come first, then `..\GUARDRAILS.md`, then
this file.

## Rules for this part

- Before any work on a phase, read `docs/phase-rules.md`: the "Every phase" section and
  that phase's section. They are binding, like `..\GUARDRAILS.md`. The phase's pass-mark
  commit names the sections read.
- Synthetic data only. Read `..\data\tables` and `..\data\corpus` in place; never write
  under `..\data`. `tests/test_data.py` checks the tables against their manifest.
- `..\data\generator-truth` is an answer key for evaluation only: never a model feature.
- Each phase writes its evaluation set and pass mark before the code, never changes them
  to pass, and saves raw results in `evidence/`.
- Keys come from environment variables only (`.env.example` holds names). Tests use stubs
  and run without a key or network; live runs save their full output as evidence.
- Agent drafts go to `outbox/` (git-ignored) with a unique request ID; nothing is applied
  without Reece's approve command, and never twice.
- Each phase ends with its section in the root `docs/learning/service-ai.md`, a handover
  note and an inbox note in the knowledge folder.
- Writing: no em dashes, UK English spelling, spell out acronyms on first use.

## Commands

```bash
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest -q        # 27 tests
.venv\Scripts\python scripts\run_forecast.py --period test   # phase 2, needs the split lock
.venv\Scripts\python scripts\recheck_forecast.py             # independent MASE recheck
```
