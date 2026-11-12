# Fjordvik phase 3 handover: failure risk (12 November 2026)

**Read at commit** `bc7b4ff` on `main` (clean, level with `origin/main`). The evaluation set
in `service-ai/eval/ml/` was committed at `3ea666b` by a different chat, before any phase 3
code (A9). **Branch** `service-ai/phase3-ml`, made from `bc7b4ff`. **Commits made:**

| Commit | What |
| --- | --- |
| `beed974` | Shared code moved to `src/fjordvik_service/common/`; phase 2's names kept as re-exports (27 passed) |
| `568e463` | Phase 3 code and tests (61 passed) |
| `44b21a0` | `run_ml.py --accept-missed-control`: the lock records a decision to go on after a missed control |
| `42d7339` | The model card names the random generator by its seed, not its memory address |
| `424c16a` | Validation results and the split lock, before any test run (E1) |
| `6e326a2` | The single test run: results, run log, evidence |
| (this commit) | Docs, the Attena proposal, test evidence and this note |

Nothing pushed, nothing merged. Measured on synthetic data with planted signals: Fjordvik
Manufacturing Oy is fictional.

## What Reece decided (12 November 2026, question boxes)

- **The data part's test log** goes outside `data/` (the chat limit), and the existing
  cross-part test logs should move too. Both go to Attena as a proposal; nothing moved yet.
  This chat saved data's test run as `service-ai/evidence/pytest-ml-data-2026-11-12.txt`.
- **The shuffled-label control missed on validation** (1.291 times the dummy against the
  fixed limit of 1.25). Reece chose to record the miss in the lock and score the test period
  once, rather than stop or investigate further first.

## What changed

- `service-ai/src/fjordvik_service/common/`: `checks.py`, `lock.py`, `stamps.py` (model
  version and library list as arguments) and `results.py` (the writer, with a short
  `stamp_id` for row-level files). `forecast/` keeps every phase 2 name.
- `service-ai/src/fjordvik_service/ml/`: `splits`, `labels`, `features`, `anomaly`, `model`,
  `alerts`, `drift`, `evaluate` (the only reader of `data/generator-truth/`), `report`, and
  `pipeline.py`, which joins the steps (not in the plan's module list; added so the tests
  and the run script share one path).
- `service-ai/scripts/run_ml.py` and `recheck_ml.py` (standard library only).
- `pyproject.toml`: `scikit-learn>=1.9,<1.10` (installed 1.9.1, joblib 1.6.0, threadpoolctl
  3.8.0).
- 34 new tests in `tests/test_ml_*.py` and `tests/ml_fixtures.py`.
- `eval/ml/split_lock.json` and `test_runs.jsonl`; `results/ml/` and `results/ml/validation/`.
- Docs: the phase 3 section in `docs/learning/service-ai.md` (and line 73 there: 39,725
  portal rows, from `data/tables/manifest.json`), `service-ai/README.md`, the root
  `README.md`, test counts in `service-ai/CLAUDE.md` and the root `CLAUDE.md`. The private
  Docs copy of the learning notes has a "Phase 3 Failure risk" tab, the Overview row, and
  the same 39,725 fix in its Phase 1 tab.
- `guardrails/proposals/2026-11-12-fjordvik-code-test-log-home.md`.

## Result (test period, July to December 2025, scored once)

| Pass mark | Result | |
| --- | --- | --- |
| Average precision at least 3 times the dummy's | 0.404 against 0.0155: 26.1 times (90% range 19.5 to 35.6) | Met |
| Recall of warned failures at least 0.6 | 28 of 38: 0.74 (range 0.61 to 0.85) | Met |
| Cost below visit none and visit every pump | EUR 24,477 against 49,084 and 693,163 | Met |
| Unwarned failures apart; leakage test | 17 of 55; 20 pump-days rebuilt unchanged, allowlist, answer key isolated | Met |
| Shuffled labels at most 1.25 times the dummy (validation) | 1.291 (shuffles 1.08, 1.24, 1.04, 0.86, 2.24) | Missed |
| E2: each model at most 1.5 times the dummy | validation 1.05, 1.01, 0.98; test classifier 1.61, z-score 0.97, forest 1.05 | Missed on test |
| M5: 90% of changed pumps flagged within 14 days | unit change 40 of 40 (median 3 days); recalibration 0 of 30 | Missed |
| M5: at most 1% false flags | 0.90% of 3,223 pump-months | Met |

All pass marks met: no. The independent recheck matches every headline metric for both
periods. On 31 December 2025 no pump is at or above the alert level (highest 0.354 against
0.891).

## Test results

| Run | Result | Evidence (all in `service-ai/evidence/`) |
| --- | --- | --- |
| service-ai, own `.venv` | 61 passed (was 27) | `pytest-ml-2026-11-12.txt` |
| data, from `data/` with its own `.venv` | 120 passed | `pytest-ml-data-2026-11-12.txt` (outside `data/`, see the proposal) |
| Fresh clone of the branch at `6e326a2`, new `.venv`, no scenario files | 61 passed | `pytest-ml-fresh-clone-2026-11-12.txt` |
| Validation runs | three, identical scores | `run-ml-validation-2026-11-12.txt`, `-rerun-`, `-model-card-fix-` |
| Test run | once, no fault | `run-ml-test-2026-11-12.txt` |
| Independent recheck | every headline metric matches, both periods | `recheck-ml-validation-2026-11-12.txt`, `recheck-ml-2026-11-12.txt` |
| Shuffled-label diagnosis | reproduced exactly | `diagnosis-shuffled-labels-2026-11-12.txt` |

`python guardrails\check.py`: no findings (the private banned-names list is not on this
laptop, so D2 was skipped). mcp, powerbi and power-automate were not rerun: no file they
read changed (`data/` is untouched).

## Things to know

- **What I read that touches the answer key.** I never opened `data/generator-truth/`,
  `service.py` or the failure settings in `config.py`. To name the answer key's columns in
  `evaluate.py` I read `data/tests/test_service_story.py` lines 15 to 69. Besides the
  column names, that test states the share of warned failures is between 0.60 and 0.85,
  and it refers to a constant for the longest warning without its value. I saw it after the
  evaluation set was fixed; no setting, feature or threshold uses it. The plan chat's own
  disclosure (it saw the failure settings) stands as written in the plan.
- **Validation's last scored day looks one day past its cut-off.** 1 June 2025 plus 30 days
  is 1 July; the cut-off is 30 June. The validation step reads no event after 30 June. No
  failure was reported on 1 July 2025, so no label differs. `test_ml_splits.py` records it.
  The evaluation chat may want to say so in a later set.
- **Drift method choices made on base data to 30 June 2025.** After a first look, I
  required each reference month to hold readings on two thirds of its days (the baseline's
  own share, 60 of 90), had the monitor skip days with an open failure ticket, and fixed a
  bug in the flag-level count. No scenario or test-period data was looked at for these.
- **Floating-point noise.** Fleet-adjusted readings are rounded to 9 decimal places before
  the spread is taken; without it a zero spread became about 1e-16 and z-scores of 1e14.
  The model card says so.
- **Three validation runs, identical scores**: `568e463` (stopped at the miss, no lock),
  `44b21a0` (lock with Reece's decision) and `42d7339` (model card fix; the committed lock).
- **The test step was tested before the lock** only on a copy of the dates shifted before
  30 June 2025, so no test-period row was scored outside the one run. The validation scores
  the frozen model reproduced in the test run are logged in `test_runs.jsonl`.
- **E2 and the pump facts.** The classifier retrained on control telemetry still uses age,
  type and contract, which alone score 1.94 times the dummy; the evaluation set expected
  this explanation but kept the classifier under the 1.5 limit.
- **Recalibration not caught.** The flag level that keeps normal months at 1% (5.80 on a
  robust scale) sits above a 3.0 C step for most pumps. A per-sensor level would be the
  first thing to try in a later set.
- **Early stopping.** Outside the grid, `HistGradientBoostingClassifier` stays at its
  defaults, which hold out 10% of training rows for early stopping. The shuffled-label
  models stopped after 10 to 19 rounds.
- Score files are 9.6 MB (validation) and 10.2 MB (test), under the 50 MB limit (D9).
- The hook blocked nothing. One shell command with a heredoc was refused by the shell
  (an apostrophe in the text); the same edit was made with the file tools.
- Rework: the floating-point fix, the drift changes and the flag-level bug before
  validation; the model-card fix after it. No test or tolerance was loosened. Minutes were
  not measured.

## Files no longer used (L6)

None.

## Open

- Reece: push `service-ai/phase3-ml` and merge it when ready. Nothing is pushed.
- Jinny: review the branch against the approved plan and `eval/ml/`.
- Attena: `guardrails/proposals/2026-11-12-fjordvik-code-test-log-home.md` (a home for
  cross-part test logs, and moving the existing ones).
- The three missed controls belong to a later evaluation set (a new chat), not to a change
  here: a minimum leaf size for the shuffled-label miss, the pump-facts effect in E2, and a
  per-sensor drift level.

## Next step

Phase 4 (technician scheduling) reads `service-ai/results/ml/scores_test.csv`,
`risk_2025-12-31.csv` and the model card, and records the feedback loop (E3). Start a fresh
service-ai chat in the repository root that reads `service-ai/docs/phase-rules.md` ("Every
phase" and "Phase 4") and this note.
