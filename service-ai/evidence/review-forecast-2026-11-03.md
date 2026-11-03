# Fjordvik phase 2 code review: spare parts demand forecast

Jinny, 3 November 2026. An independent review: the review changed no code, results or docs. Reece
asked for this report and its key raw output to be committed here, in `service-ai/evidence/`.

- **Reviewed:** `main` (`73604c6`) to `3ae1f0d` on `service-ai/phase2-forecast`: commits `72551d0`,
  `71a13e4`, `4e524c7`, `bce2ea8`, `3ae1f0d`. Read and run in a separate clone, never in the
  working checkout.
- **Spec:** the approved plan `buzzing-percolating-yao.md`, `GUARDRAILS.md` (D10, D11, A9, E1),
  `service-ai\docs\phase-rules.md` ("Every phase" and "Phase 2"), `eval\forecast\evaluation.json`.
- **Raw output:** `service-ai/evidence/review-*-2026-11-03.txt`, listed at the end.
- Fjordvik Manufacturing Oy is fictional; every figure here is from synthetic data with planted signals.

## Verdict: fix first

One blocker. The forecast logic, the point-in-time drivers, the split lock and the scores are sound,
and the results reproduce byte for byte. But the results' own checksums fail on any fresh checkout,
so the service-ai suite goes red on `main` for anyone who clones it. A small fix, then one rerun.

| Severity | Count |
| --- | --- |
| Blocker | 1 |
| Should fix | 0 |
| Minor | 6 |

## Findings

| # | Severity | Source | File and line | Problem | Why it matters in use | Rule | Suggested fix |
|---|---|---|---|---|---|---|---|
| 1 | Blocker | Tests, review | `service-ai/src/fjordvik_service/forecast/report.py:104`, `:107`, `:112`; `lock.py:24`; `scripts/run_forecast.py:110` | `Path.write_text` and `open("a")` write Windows line endings (CRLF, carriage return and line feed). The manifests hash those CRLF bytes, but `service-ai/.gitattributes` (`results/** text eol=lf`, `eval/** text eol=lf`) makes git store and check out LF. In a clean clone, `summary.json` and `README.md` (test and validation) never match their manifest, the lock's `validation_manifest_sha256` doesn't match `validation/manifest.json`, and `test_committed_test_results_match_their_manifest_and_recheck` fails (26 passed, 1 failed). The builder's checkout still holds the CRLF files, which is why it passed there. Proof: turning the clone's LF `summary.json` back into CRLF gives exactly the manifest hash `bc986d60...`; the content is otherwise identical. | Once merged and pushed, every fresh clone (and any CI) fails the suite, and the integrity record can't be checked by anyone but the original folder. | G10 (every saved result names checksums that hold); plan: "the manifest checksums match" | Write every text result with `newline="\n"` (`Path.write_text(text, encoding="utf-8", newline="\n")`, `RUN_LOG.open("a", encoding="utf-8", newline="\n")`). Then rerun validation and the locked test run at the fixed commit; both are deterministic, and the run log's G10 check will confirm identical `metrics_by_series.csv`. Commit the new lock, results and manifests, and say in the commit message why the test period ran a second time with the same frozen settings. |
| 2 | Minor | Review | `service-ai/src/fjordvik_service/forecast/backtest.py:91-92` (with `metrics.py:10`) | Tartu's scale q includes its three ramp months (July to September 2024). At the forward origin q is 2.5 to 3.7 times what it is without them for consumables, service kits, and wear rings and gaskets, and 1.1 to 1.6 times for the rest. Tartu's borrowed 80% ranges in `forecast_2026h1.csv` are q times Oulu's scaled errors, so they're that much wider, and Tartu's MASE (mean absolute scaled error) of 0.43 to 0.77 is flattered. The code follows the evaluation set exactly. | Tartu is reported apart with no accuracy claim, so no pass mark is wrong, but a planner reading the Tartu ranges or the 0.43 would be misled. | F1 (scale on each origin's training data); the plan's own definition | No change to `evaluation.json` in this phase (A9). Add one line to the learning note and results README that Tartu's ramp inflates its scale and ranges. For phase 3 or a later rerun, Reece could decide whether q should skip a warehouse's ramp months. |
| 3 | Minor | Review (claims check) | `docs/learning/phase2-forecast.md:104-105`; `docs/handover/2026-11-03-fjordvik-phase2-forecast.md:50` | "Wins in five of the eight families" is true against the moving average only. Outright, the driver model is best in four: seasonal naive is also best for service kits (3-month 0.967 against 0.969; 6-month 0.851 against 0.898), but the note lists only bearings, consumables and overhaul kits as losses. | A reader takes "wins" as best of all methods. | W8 (results stated as measured) | "Beats the moving average in five of eight families and is best outright in four; seasonal naive is best for overhaul kits and service kits." |
| 4 | Minor | Review (claims check) | `docs/learning/phase2-forecast.md:111` | "Test origins, which have 24 to 30 training months": true for the 6-month length; the 3-month test origins run to September 2025, which has 33. | Small factual slip in the explanation. | W8 | "24 to 33 training months". |
| 5 | Minor | Review | `service-ai/pyproject.toml:13-18` | Libraries are pinned to a minor range (as the approved plan said), with no lock or constraints file, and the results don't record the installed versions. This install got numpy 2.5.4, pandas 3.1.0, scipy 1.18.1, statsmodels 0.14.6 and patsy 1.0.3 (unpinned). `pytest>=8` is open. | A patch release could change the output bytes; the test run's G10 check would then refuse with "test scores differ", and nobody could tell which versions made the committed results. | G10 (library versions pinned) | Add a constraints file with the exact versions used for the committed run, or write them into `manifest.json`. |
| 6 | Minor | Review (test tampering check) | `service-ai/tests/test_forecast_metrics.py:31-32` | "Scale uses training months only" filters the series inside the test, then calls `scale_q`, so it tests the code against itself: it can't fail if `forecast_origin` passed future months. The real path is covered by the independent recheck, which rebuilds q from the raw orders and matched all 160 series. | The named F1 test gives less protection than its name says. | F1; review rule on tests that can't fail | Call `forecast_origin` on a toy series with a huge value after the origin and assert q is unchanged. |
| 7 | Minor | Review (test tampering check) | `service-ai/tests/test_forecast_results.py:107` | `skipif` when `results/forecast/summary.json` is missing. The results are now committed, so a deleted or renamed results folder would turn the one end-to-end results test into a silent skip. | The check that caught finding 1 could disappear without a failure. | Review rule on skipped tests | Drop the `skipif` now that the results exist. |

Static analysis found nothing worth an item (counts below).

## Requirements

| Requirement | Status | Evidence |
| --- | --- | --- |
| F1: each origin's last training month is before its first forecast month | Met | `backtest.py:91` (`train = series[series.index <= origin]`), horizons start at 1; `test_each_origin_forecasts_only_months_after_its_training` passes |
| F1: MASE scaled by seasonal naive on each origin's training months only | Met | `backtest.py:91-92`; independent recheck rebuilds q from the raw order lines: 160 series, 0 mismatches (`review-recheck-forecast-2026-11-03.txt`) |
| F1: coverage and Winkler per origin | Met | `metrics_by_origin.csv` (coverage, raw and scaled Winkler per origin); per-origin table in the results README |
| F1: Tartu reported apart, never pooled | Met | `report.py:37-62` judges only in-scope warehouses; Tartu has 1 test origin (3-month) and 0 (6-month); `summary.json` marks it `in_scope: false`; the test with a failing Tartu still gives "pass" |
| F1: test origins never used to choose | Met | `backtest.choose` filters `period == "validation"`; the test step reads settings only from the lock |
| F2, D11: no driver uses data after its forecast date | Met | `drivers.py:75` and `:92`, a loud check at `:98`; the delete-later-rows rebuild test passes; 0 of 2,824 saved driver rows are known after their forecast date (`review-validation-data-cut-2026-11-03.txt`) |
| F2: running hours in forecasts are forecasts | Met | `drivers.py:84-91` uses month m minus 12, known from m minus 11; every saved forecast-month row has `kind = forecast` |
| F2: every driver value has `known_from` | Met | 0 missing in `drivers.csv` |
| E1, A9: `evaluation.json` unchanged from `72551d0` to `3ae1f0d` | Met | `git diff 72551d0 3ae1f0d -- service-ai/eval/forecast/evaluation.json` is empty (`review-git-history-2026-11-03.txt`); the lock's evaluation hash matches |
| E1: split lock committed before the test results | Met | Lock in `4e524c7` (12:48:39), results in `bce2ea8` (12:57:30); the run log has one entry, commit `4e524c7`, 12:48:55 |
| E1: validation used data up to November 2024 only | Met | `load_inputs(last_month="2024-11")`; saved validation forecasts have no actual after 2024-11 and no driver known after 2024-12-01 |
| E1: nothing chose a setting from test scores | Met as far as the repo can show | Settings 6-month moving average, no season term, from validation origins March to August 2024; the test step can't choose |
| D15: steps fail loudly | Met | `check_frame` on every step; GLM warnings raised as errors; empty, missing and duplicate inputs tested |
| G10: pinned, stamped, reproducible | Partly met | Stamps on every file (checked); rerun at `4e524c7` matches all 7 committed files; but findings 1 and 5 |
| W8: every result says synthetic data with planted signals | Met | Stamp column in every CSV, `statement` in `summary.json`, the results README's first line |
| D10: `data/generator-truth/` never read | Met | `git grep` finds no reference in `service-ai/src`, `scripts` or `tests` at `3ae1f0d`; not opened by me |

## Static analysis (changed Python files only, 22 files)

| Tool | Result |
| --- | --- |
| Ruff 0.17.0, Jinny's `config/ruff.toml` (likely mistakes only) | 5 findings, all low: B007 twice (unused loop names in `recheck_forecast.py`), B904 (`raise SystemExit` without `from`), B905 (`zip` without `strict` at `backtest.py:103`; every method returns one value per horizon, so no truncation happens), PLW1510 (test subprocess, return code asserted after). None new to the baseline, which accepts none; none is a likely bug in practice. |
| Bandit 1.9.4 | 0 high, 0 medium, 62 low (`assert` in tests, `subprocess` with fixed `git` arguments). |
| Vulture 2.16 (changed modules) | 0. The `vulture.exe` launcher was refused ("Permission denied"); ran as `python -m vulture`. |
| Gitleaks 8.30.1, Jinny's config, `origin/main..3ae1f0d` | 5 commits scanned, no leaks. |
| pip-audit | Not run: no requirements file changed (only version ranges in `pyproject.toml`). |
| SQLFluff, ESLint, TypeScript | Not applicable: no SQL or chart code in the change. |

## Tests and evidence

| Check | My result | Builder's claim |
| --- | --- | --- |
| service-ai `pytest -q` at `3ae1f0d`, clean clone | **26 passed, 1 failed** (finding 1) | 27 passed |
| data `pytest -q` at `3ae1f0d` | 96 passed | 96 passed |
| `scripts\recheck_forecast.py` at `3ae1f0d` | "OK: saved MASE matches the independent recomputation", 160 series | Same |
| Reproducibility: `run_forecast.py --period test` at `4e524c7` | 7 of 7 files match the manifest committed at `3ae1f0d`; stamps equal; run took 9.5 seconds | Reproducible |
| `python guardrails\check.py` in the clone | No findings (the private banned-names list isn't in a clone, so D2 was skipped) | No findings |
| Figures in the learning note and handover against `summary.json` and the results tables | All match (MASE 0.983, 1.062, 1.253, 1.404 and 0.999, 1.082, 1.159, 1.399; coverage 201 of 240 and 283 of 336; margins 7.4% and 7.6%; five 3-month origins above 1, January to May 2025; April 2025 at 16 of 24; later origins 0.770 to 0.879; validation 1.784 against 1.371; Tartu 0.435 and 0.770; Oulu March 2026 bearings 487, range 356 to 659; the July 2023 motor parts spike, 553 units; 53,654 lines and 238,910 units; technician lines 2,841 units), except findings 3 and 4 | |

**Tampering flags:** no existing test, fixture or expected value changed (only new test files). Two weak
tests (findings 6 and 7). No loosened tolerance or deleted assertion.

## Not checked

I didn't read the data generator, `data/generator-truth/` or the old historical folders, didn't run the
mcp, powerbi or power-automate suites, and didn't judge the driver model's design beyond the spec.

## Worth considering later

1. **A9 evidence.** `72551d0` and the 1,300-line code commit are 21 seconds apart, so the code was in the
   working tree when the evaluation set was committed, and the builder chat wrote it. Every claim in the
   docs says "committed before any code", which is accurate, and the dates and pass marks were Reece's.
   But A9's "written before the code" and "by a different chat" can't be shown from git. Attena may want
   A9 to say how it applies to an evaluation set that isn't a question set.
2. **One test run per frozen configuration (E1).** The test step logs every run and refuses only when the
   same settings give different scores. Nothing refuses a second lock written after a test run; the run
   log is the only record. A refusal when the log already holds a different `settings_sha256` would make
   E1 checkable.
3. The validation results' `summary.json` shows `test_origins: 0` for Oulu, because it counts on data cut
   at November 2024. Harmless, but it reads oddly beside the test summary's 10 and 7.

## Raw output (`service-ai/evidence/`)

| File | What it backs |
| --- | --- |
| `review-pytest-service-ai-2026-11-03.txt` | service-ai tests in a clean clone: 26 passed, 1 failed (finding 1) |
| `review-pytest-data-2026-11-03.txt` | data tests: 96 passed |
| `review-line-endings-2026-11-03.txt` | Carriage returns per file and the checksum proof behind finding 1 |
| `review-recheck-forecast-2026-11-03.txt` | Independent MASE recheck at `3ae1f0d` |
| `review-run-forecast-test-4e524c7-2026-11-03.txt` | The test period rerun at `4e524c7` |
| `review-reproducibility-2026-11-03.txt` | The rerun's 7 files against the manifest committed at `3ae1f0d` |
| `review-git-history-2026-11-03.txt` | Commit order and times, the empty `evaluation.json` diff, the lock, the run log (E1, A9) |
| `review-validation-data-cut-2026-11-03.txt` | Validation data cut at November 2024; driver `known_from` dates; stamps per file |
| `review-tartu-ramp-scale-2026-11-03.txt` | Tartu's scale with and without its ramp months (finding 2) |
| `review-ruff-2026-11-03.txt`, `review-bandit-2026-11-03.txt`, `review-gitleaks-2026-11-03.txt` | Static analysis |

The setup logs, Vulture, the claims check script and the other raw files are kept in Jinny's own
repository history, outside this repository. Checked for secrets and client data: none (synthetic data only; Gitleaks clean).
