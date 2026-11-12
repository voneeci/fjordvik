# Phase 3 failure prediction: how the evaluation was set

Synthetic data with planted signals: Fjordvik Manufacturing Oy is fictional, and nothing
here describes real pumps or a real service team. The two costs are worked out from
synthetic tables times published rates and are not real-world costs.

Fjordvik's service is reactive: a pump fails, then a technician drives out. Phase 3 scores
each pump each day for the chance of a failure in the next 30 days, so a technician can
visit first. These files fix how that model is judged, before any of its code exists.

## How and when it was written

- Written on 12 November 2026 by a one-task evaluation chat that is not the builder
  (GUARDRAILS.md A9). It wrote these three files and no code.
- It comes from the approved phase 3 plan (Reece's answers in the question boxes on
  4 November 2026, and the cost inputs of 11 November 2026) and from Reece's answers in
  this chat's question boxes on 12 November 2026.
- It read `docs/phase-rules.md`: "Every phase", "Phase 3" and "Telemetry".
- It never opened `data/generator-truth/` or the generator's failure settings, so the
  answer key did not shape the test.
- It is committed on branch `eval/phase3-ml`, made from `main`, before the first build
  commit. The build branch starts from a commit that already holds it.

## What it rests on

- Commit `517598f` on `main`, which holds the data part's phase 3 inputs.
- `data/tables/manifest.json`, `data/scenarios/manifest.json` and
  `data/scenarios/planning_inputs.json`. Their SHA-256 (Secure Hash Algorithm, 256-bit)
  checksums are in `evaluation.json` under `rests_on`.
- The two costs are read from `planning_inputs.json` in code. No cost value is typed here.

## The files

| File | What it fixes | SHA-256 |
| --- | --- | --- |
| `evaluation.json` | The dates, the label, which rows are scored, what an alert, a caught failure and a wasted visit are, the three plans, the pass marks, the control limits, the model grid, the seed and the recheck | `65cc1890f226ac0c7f74bf0bcad6be23b91aed01a3b9773fac3a89846071ae6b` |
| `feature_allowlist.json` | The 32 columns a model may read, each with its source table and window, and what is left out and why (D12) | `aa268ea6ed55f736ad4700888ade876c47fc626d2cf3483edf14324cc3d155c2` |

## The pass marks, Reece's

- Average precision at least 3 times the dummy model's.
- At the chosen threshold, at least 0.6 of warned failures caught, and a cost below both
  simple plans: visit no pump, and visit every pump every 30 days.
- Failures with no warning reported apart, and the leakage test passing.
- Three control limits: a model trained on shuffled labels scores at most 1.25 times the
  dummy; on telemetry with the warning signs switched off, at most 1.5 times; and the drift
  monitor flags at least 90% of changed pumps within 14 days, and at most 1% of
  pump-months with no failure in the following 42 days.

## Where the plan and the tables disagreed

The chat recounted the plan's split table from the tables before writing. The failure
counts (199, 70 and 55), the dropped rows (2,406 and 70) and the last 30 days (17,931 rows)
match. Two figures did not, and Reece settled both on 12 November 2026:

- **At-risk rows.** The plan's counts (354,968, 85,094 and 89,887) keep the days with no
  running, which its own rule drops. The file follows the rule and records both counts:
  354,926, 85,085 and 89,878 rows are scored.
- **Warm-up.** The plan's 173 train failures "after a 90-day warm-up" was not reproduced
  (170 with 90 days). The file fixes the warm-up as at least 60 readings in the 90 days
  ending 8 days before the day, and records no train failure count.

Reece also chose the values the plan left open: the seed, the recheck list and tolerance,
which models the control limit covers and that they are trained again on the control
telemetry, the tie order in the model grid, how the visit-every-pump plan counts visits, the
months the drift false flags are measured on, and four small defaults. Each is listed in
`evaluation.json` under `decided_in_the_evaluation_chat`.

## It is fixed

These files are never changed to make a result pass (A9). A change that comes from a
result goes to the next phase, or reruns this phase from the start. The builder adds
`split_lock.json` and `test_runs.jsonl` to this folder, and changes neither file above.
