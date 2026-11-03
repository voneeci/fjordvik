# Fjordvik phase 2 handover: spare parts demand forecast (3 November 2026)

**Read at commit** `73604c6` on `guardrails/first-update` (clean). **Branch**
`service-ai/phase2-forecast`, made from `73604c6`. **Commits made:** `72551d0`
(evaluation set and pass marks, before any code), `71a13e4` (code and tests), `4e524c7`
(validation results and the split lock, before the test run), `bce2ea8` (the test run,
results, evidence and docs), and this note. Nothing pushed.

Measured on synthetic data with planted signals: Fjordvik Manufacturing Oy is fictional.

## What Reece decided (3 November 2026, question boxes)

- Demand counts every order line, service technician lines included (2,841 of about
  239,000 units), so it matches `fact_sales`.
- The moving-average window is picked on validation from 3, 6 or 12 months (it chose 6).
- 80% intervals come from rolling backtest errors.
- A warehouse needs 6 test origins per forecast length to count in the pass mark.
- E1's 30-day gap is one gap month, December 2024, scored in neither period.
- A new branch for phase 2. The Desktop config session (same checkout) ended without
  committing, so Reece chose to branch at once.

## What changed

- **Evaluation first** (`72551d0`): `service-ai/eval/forecast/evaluation.json` and its
  README fix the demand, the dates, the minimum origins, the candidate settings and Reece's
  pass marks. `service-ai/.gitattributes` keeps `eval/` and `results/` in Unix line endings,
  so their checksums hold on every checkout.
- **Code** (`71a13e4`): `service-ai/src/fjordvik_service/forecast/` (demand, drivers,
  benchmarks, Poisson driver model, intervals, metrics, backtest, report, stamps, lock),
  `scripts/run_forecast.py` and `scripts/recheck_forecast.py`; 21 tests; libraries pinned in
  `pyproject.toml` (numpy 2.5, pandas 3.1, scipy 1.18, statsmodels 0.14.6), Python 3.11 or
  newer.
- **Validation and lock** (`4e524c7`): the validation step ran on data up to November 2024
  only and chose a 6-month moving average and no season term. `split_lock.json` pins the
  dates, the evaluation hash and the settings.
- **Test run** (`bce2ea8`): run once at `4e524c7`; results in
  `service-ai/results/forecast/`, the run log in `eval/forecast/test_runs.jsonl`;
  `docs/learning/phase2-forecast.md`; the phase 2 section in `service-ai/README.md`; the test
  count, status and Python version in the root `README.md`; test counts in both `CLAUDE.md`
  files.

## Result (synthetic data with planted signals)

| Oulu, test period | Origins | Naive | Seasonal naive | Moving average (6) | Driver model | Driver 80% coverage |
| --- | --- | --- | --- | --- | --- | --- |
| 3-month forecast | 10 | 1.404 | 1.253 | 1.062 | 0.983 | 83.8% (201 of 240) |
| 6-month forecast | 7 | 1.399 | 1.159 | 1.082 | 0.999 | 84.2% (283 of 336) |

Both pass marks are met at both lengths. The margin over the moving average is 7% to 8%,
and the driver model wins in 5 of 8 families. Five of the ten 3-month origins (January to
May 2025) score above 1, and one origin (April 2025) has 67% coverage. On validation, with
15 to 17 training months, the driver model lost to the moving average (6-month MASE 1.784
against 1.371). Tartu has one 3-month test origin and no 6-month one: reported apart. At
that origin naive scored 0.435 and the driver model 0.770. The independent recheck matches
all 160 saved series.

## Test results (each from its own folder and `.venv`)

| Part | Result | Evidence |
| --- | --- | --- |
| service-ai | 27 passed (was 6) | `service-ai/evidence/pytest-forecast-2026-11-03.txt` |
| data | 96 passed | `data/evidence/pytest-forecast-2026-11-03.txt` |
| mcp | 83 passed | `mcp/evidence/pytest-forecast-2026-11-03.txt` |
| power-automate | 30 passed | `power-automate/evidence/pytest-forecast-2026-11-03.txt` |
| powerbi | 579 passed, 154 skipped (Desktop closed) | `powerbi/evidence/pytest-forecast-2026-11-03.txt` |

Runs: `service-ai/evidence/run-forecast-validation-2026-11-03.txt`,
`run-forecast-test-2026-11-03.txt`, `recheck-forecast-validation-2026-11-03.txt` and
`recheck-forecast-2026-11-03.txt`. `python guardrails\check.py`: no findings.

## Things to know

- **Windows Application Control** on this laptop blocks one statsmodels compiled file
  (`statsmodels/robust/_qn`), which `statsmodels.api` loads. `model.py` imports the
  regression directly instead. No security setting was changed.
- **Line count in the docs.** `data/README.md` and the phase 1 handover say
  `fact_parts_order` has 53,570 lines; `data/tables/manifest.json` says 53,654. I didn't
  write under `data`; the data chat should correct the README.
- **I didn't read the generator's demand code** or `data/generator-truth/`, so the model
  wasn't tuned to known settings (Jasila's risk R20, D10).
- **The E1 gap for monthly forecasts.** E1's "30-day gap" was written for daily labels.
  Reece chose one gap month before test. Attena may want E1 to say how it applies to
  monthly forecasts; I didn't write a proposal, since the hook and checks didn't get in
  the way.
- **The Desktop config session's** untracked file
  `mcp/evidence/pytest-desktop-config-entry-2026-11-03.txt` is still in the folder,
  untouched. That session ended before committing.
- The hook blocked nothing in this phase.

## Files no longer used (L6)

None. `results/forecast/validation/` stays as the record of how the settings were chosen.

## Open

- Push `service-ai/phase2-forecast` when Reece says.
- From phase 1, still open: `docs/learning-guide.md` and the process map need a service AI
  section.
- Tartu's forecast needs more history before any accuracy claim: rerun the backtest once
  it has six test origins of its own.

## Next step

Start a fresh chat for phase 3 (anomaly detection and failure prediction in `service-ai`),
reading `GUARDRAILS.md`, `service-ai/docs/phase-rules.md` ("Every phase" and "Phase 3"),
`service-ai/CLAUDE.md` and this note first.
