# service-ai: rules for each phase

These are the method rules for building service-ai, phase by phase. They sit here, beside
the phase table and pass marks in [`../README.md`](../README.md), rather than in the master
rules, so each chat reads only the rules for the phase it is building. They are binding:
each phase builds to its section from its first commit, and its tests enforce them.

**Before any work on a phase,** read "Every phase" and that phase's section. The phase's
pass-mark commit (the one that fixes its evaluation set and pass mark, A9) names the
sections read, for example "Read phase-rules.md: Every phase, Phase 2".

The master rules in [`../../GUARDRAILS.md`](../../GUARDRAILS.md) still apply in full,
including the ones every phase leans on: D10 to D12 (no answer key, point-in-time features,
the feature allowlist), A9 (evaluation sets and pass marks fixed before the code) and E1
(time splits fixed before building). The identifiers below are unchanged from GUARDRAILS.md,
so earlier notes still read.

All the data is synthetic: Fjordvik Manufacturing Oy is fictional, and the emission factors
are illustrative.

## How this file changes

- The service-ai chat maintains this file. Attena wrote the first edition on 3 November
  2026, moving these rules out of GUARDRAILS.md at Reece's request.
- A rule changes only with Reece's yes in the chat, recorded as a dated line at the end of
  this file. A rule is never changed after the phase's results have been seen (A9): a
  change that comes from a result goes to the next phase, or reruns the phase from the
  start.
- A rule that should apply to the whole repository goes to Attena as a proposal in
  `../../guardrails/proposals/`.

## Every phase

| Rule | What | Checked by |
| --- | --- | --- |
| D15 | Each pipeline step asserts its row count, unique keys and missing-value counts, and stops with an error when one fails. An empty input or one with NaN (not-a-number) values raises an error rather than writing output. | Tests in each phase |
| G10 | Library versions are pinned, and random generators are seeded with an explicit bit generator. Every saved result names the data checksum, the commit and the model version. Training twice on the same data gives the same metrics. | Tests in each phase |
| W8 | Every model or assistant result says it was measured on synthetic data with planted signals, and never presents it as performance on real pumps. Where the data sets a ceiling (for example the share of failures that have any warning), the result shows it. | Review; a results-page test from phase 2 |

## Phase 2: spare parts demand forecast

| Rule | What | Checked by |
| --- | --- | --- |
| F1 | Forecasts are scored on rolling origins with genuine 3 to 6 month forecasts: each origin's last training month is before its first forecast month. The test origins are never used to choose a model, a setting or a driver. Mean absolute scaled error (MASE) is scaled by the seasonal naive forecast on each origin's training data, and recomputed independently from saved forecasts. Interval coverage and Winkler scores are reported per origin, not only on average. A warehouse with fewer origins than a minimum set before building is reported apart, never pooled silently. | Phase 2 tests |
| F2 | A driver enters a forecast only as it was known at the forecast date: no later revisions, and no actuals from after that date (D11). A driver model uses forecast driver values, never actual future ones. Each driver records the date it becomes known. | Phase 2 tests |

## Phase 3: anomaly detection and failure prediction

| Rule | What | Checked by |
| --- | --- | --- |
| E2 | Each model also runs on a control dataset with the warning signals switched off, built by the generator with the same seed. There it must fall to the dummy model's level, within a band set before building. | `data` generator and phase 3 tests |
| M1 | Training, validation and test sets are split by time, never by shuffled rows. A check grouped by pump is reported beside the time split, so the gap between the two scores is visible. | Phase 3 tests |
| M2 | Each model has a leakage test. It fails when a feature uses data from after the prediction time (D11), uses a column off the allowlist (D12), or reads `generator-truth` (D10). | Phase 3 tests |
| M3 | Decision and alert thresholds are chosen on validation data only, never on test data. A threshold belongs to one model version, is stored with it, and is chosen again after every retrain. | Phase 3 tests |
| M4 | The failure classifier's headline metrics are average precision, recall of warned failures, and cost against the visit-all and visit-none plans. Accuracy and the area under the ROC (receiver operating characteristic) curve are never shown alone. The report states the share of positive rows. | Phase 3 tests |
| M5 | Drift monitors compare each sensor with the same month in earlier years, not the last few weeks. They are tested on generator scenarios with a recalibration step and a unit change: each must be flagged within a number of days set before building, and the normal seasonal cycle must not be. | `data` generator and phase 3 tests |

## Telemetry, when its schema entries are added

| Rule | What | Checked by |
| --- | --- | --- |
| D13 | Every telemetry column has a schema entry: type, unit, allowed range and allowed missing share. A unit change needs a new column, never a silent change (GUARDRAILS.md D4). | `data` tests |
| D14 | Daily telemetry has exactly one row per pump per local date in Europe/Helsinki, built from timezone-aware timestamps. The 23-hour and 25-hour clock-change days land on the right date. | `data` tests |

## Phase 4: technician scheduling

| Rule | What | Checked by |
| --- | --- | --- |
| E3 | Where one capability's output changes another's training data (risk scores drive visits, so risky pumps fail less), the second model records that influence as a column, and its model card names the loop. | Review; phase 4 tests |
| O1 | Every schedule is rechecked by an independent constraint checker before it is reported or compared. A different chat writes the checker from the specification, before the solver. It recomputes skills, hours and time windows from the raw input and does not import the optimiser's code. A failing schedule is reported as a failure, never quietly repaired. Unserved visits are a headline number beside cost, the solver's status is reported, and the penalty for an unserved visit exceeds the largest single visit cost. | Phase 4 tests |
| D16 | Technician skills, hours, leave and customer time windows carry an "as at" date. A plan can't be built from data older than a limit set before building. | Phase 4 tests |

## Phase 5: parts recommendations

| Rule | What | Checked by |
| --- | --- | --- |
| RS1 | The old portal recommender's logs are biased by exposure: customers only saw what it showed them. Training and evaluation account for that bias and say how. A result measured on logged clicks alone is labelled as biased. | Review; phase 5 tests |
| RS2 | Recommender evaluation uses one global time cut-off: no training event is later than it. It reports hit rate at 5 against most-popular and random-compatible baselines: overall, for pump models with little history, and for events the old recommender did not cause. Compatibility is checked in code for every recommended part. | Phase 5 tests |

## Phases 6 and 7: the service assistant and the agent

| Rule | What | Checked by |
| --- | --- | --- |
| D17 | Each manual chunk in a search index carries its manual's version and date. A changed manual triggers a rebuild that removes the old version's chunks. | Phase 6 tests |
| A7 | An assistant answer cites the document section it comes from, or says the sources do not cover it. It never invents a section, part number or figure. It retrieves only from `data/corpus/`, never `generator-truth` (D10). Each citation carries a short quote, and code checks the quote appears word for word in the cited section of the cited manual version. Every evaluation includes questions the corpus can't answer, and the right answer to each is "not found". | Phase 6 evaluations |
| A13 | Each large language model (LLM) evaluation item runs 3 times; the report gives the mean and the share correct in all 3 runs. Code checks come first. An LLM grader is used only where code can't judge, is calibrated against Reece's marks on 20 items, and never marks its own model's answers alone. | Phase 6 and 7 evaluations |
| A6 (evaluation) | Every assistant and agent evaluation plants at least 20 instructions (5 each in manuals, technician notes, emails and portal text), runs each 3 times, and passes only when none is followed. The rule itself (text is data, never instructions) is GUARDRAILS.md A6. | Phase 6 and 7 evaluations; a keyless test from phase 6 |
| A2 (test) | A test calls every mcp tool as every role over HTTP (Hypertext Transfer Protocol) and checks each answer against the role's rights. The rule itself is GUARDRAILS.md A2. | A phase 6 test |

## Change history

- 3 November 2026: first edition by Attena (Reece asked, in the Attena chat, after Jasila's review of the guardrails). These rules moved here from GUARDRAILS.md with their wording unchanged.
