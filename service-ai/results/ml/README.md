# Phase 3 failure risk results (test)

> **Measured on synthetic data with planted signals: Fjordvik Manufacturing Oy is fictional, and these are not results on real pumps or a real service team.** The warning rise before most failures was planted by the data generator, so these scores show the method finds a known signal, not how it would do on live pumps.

Data checksum `379e6075034a605fc5dac6806d5f6367079ea4dee4083180167bfbc34bfb5b68`, commit `424c16a0784a48f60aabbf234f29b5c0f2a923da`, model version `ml-1.0.0`.

A score is the model's estimate of the chance that the pump has a failure in the 30 days after the day, from readings up to the end of that day.

## Ranking (average precision)

Scored pump-days: 88,274, of which 1,365 (1.55%) have a failure in the next 30 days. The dummy model's average precision equals that share.

| Model | Average precision | Times the dummy's |
| --- | --- | --- |
| Classifier | 0.404 | 26.11 |
| Pump facts only | 0.030 | 1.94 |
| Robust z-score alone | 0.323 | 20.91 |
| Isolation forest alone | 0.236 | 15.29 |
| Dummy (positive share) | 0.015 | 1.00 |

Alert threshold 0.891198 (chosen on validation from the costs, no answer key).

## Alerts and cost (central missed-failure cost)

Failures in the alert window: 55. Warned (from the answer key, evaluation only): 38; unwarned: 17, which no plan can prevent, so the ceiling on catching failures is 69% of them.

Alerts: 38 (28 caught a warned failure 7 to 30 days ahead, 2 wasted, 8 came 1 to 6 days before a failure). Recall of warned failures: 0.737.

| Plan | Visits | Failures caught | Missed | Wasted visits | Cost |
| --- | --- | --- | --- | --- | --- |
| Model alerts | 38 | 28 | 27 | 2 | EUR 24,477 |
| Visit none | 0 | 0 | 55 | 0 | EUR 49,084 |
| Visit every pump every 30 days | 3,600 | 38 | 17 | 3,562 | EUR 693,163 |

Sensitivity to the missed-failure cost (alerts unchanged):

| Missed-failure cost | Model | Visit none | Visit every pump |
| --- | --- | --- | --- |
| low, EUR 339 | EUR 9,537 | EUR 18,652 | EUR 683,756 |
| central, EUR 892 | EUR 24,477 | EUR 49,084 | EUR 693,163 |
| high, EUR 1,785 | EUR 48,573 | EUR 98,169 | EUR 708,334 |

90% ranges from 1,000 resamples of pumps:

- Classifier average precision: 0.320 to 0.480
- Times the dummy's: 19.531 to 35.612
- Recall of warned failures: 0.606 to 0.853
- Model cost: EUR 17,337 to EUR 32,509
- Visit-every-pump cost: EUR 687,368 to EUR 699,746

## Controls

- Shuffled labels (validation): 1.29 times the dummy, limit 1.25.
- Warnings switched off (validation): classifier 1.05, robust z-score 1.01, isolation forest 0.98 times the dummy, limit 1.5; pump facts only 1.11.
- Warnings switched off (test): classifier 1.61, robust z-score 0.97, isolation forest 1.05 times the dummy, limit 1.5; pump facts only 1.94.
- Grouped by pump (5 folds, train and validation): mean average precision 0.388 against 0.421 on the time split.
- Drift: flagged within 14 days: drift_recalibration 0%, drift_unit_change 100% (limit 90%); false flags 0.90% of 3223 pump-months (limit 1%).
- Leakage test: pass (20 pump-days rebuilt with later rows deleted).

## Pass marks

| Mark | Result |
| --- | --- |
| average precision | pass |
| recall of warned failures | pass |
| cost below visit none | pass |
| cost below visit every pump | pass |
| unwarned failures reported apart | pass |
| leakage test | pass |
| shuffled labels | miss |
| control telemetry validation | pass |
| control telemetry test | miss |
| drift detection | miss |
| drift false flags | pass |

All pass marks met: no.

Missed on validation and carried to this single test run by decision: shuffled_labels. Reece, 12 November 2026, question box: record the shuffled-label miss (1.291 times the dummy against 1.25; one shuffle of five at 2.24) and score the test period once with these settings. Diagnosis: evidence/diagnosis-shuffled-labels-2026-11-12.txt.

Accuracy and the area under the ROC (receiver operating characteristic) curve are not shown: with so few positive rows they flatter any model (M4).
