# Phase 3 failure risk results (validation)

> **Measured on synthetic data with planted signals: Fjordvik Manufacturing Oy is fictional, and these are not results on real pumps or a real service team.** The warning rise before most failures was planted by the data generator, so these scores show the method finds a known signal, not how it would do on live pumps.

Data checksum `379e6075034a605fc5dac6806d5f6367079ea4dee4083180167bfbc34bfb5b68`, commit `42d73397fd66fd99763c38b977fe27214052a930`, model version `ml-1.0.0`.

A score is the model's estimate of the chance that the pump has a failure in the 30 days after the day, from readings up to the end of that day.

## Ranking (average precision)

Scored pump-days: 83,865, of which 1,721 (2.05%) have a failure in the next 30 days. The dummy model's average precision equals that share.

| Model | Average precision | Times the dummy's |
| --- | --- | --- |
| Classifier | 0.421 | 20.51 |
| Pump facts only | 0.023 | 1.11 |
| Robust z-score alone | 0.345 | 16.80 |
| Isolation forest alone | 0.264 | 12.87 |
| Dummy (positive share) | 0.021 | 1.00 |

Alert threshold 0.891198 (chosen on validation from the costs, no answer key).

## Alerts and cost (central missed-failure cost)

Failures in the alert window: 70. Warned (from the answer key, evaluation only): 48; unwarned: 22, which no plan can prevent, so the ceiling on catching failures is 69% of them.

Alerts: 52 (45 caught a warned failure 7 to 30 days ahead, 4 wasted, 3 came 1 to 6 days before a failure). Recall of warned failures: 0.938.

| Plan | Visits | Failures caught | Missed | Wasted visits | Cost |
| --- | --- | --- | --- | --- | --- |
| Model alerts | 52 | 45 | 25 | 4 | EUR 23,072 |
| Visit none | 0 | 0 | 70 | 0 | EUR 62,471 |
| Visit every pump every 30 days | 3,438 | 48 | 22 | 3,390 | EUR 664,886 |

Sensitivity to the missed-failure cost (alerts unchanged):

| Missed-failure cost | Model | Visit none | Visit every pump |
| --- | --- | --- | --- |
| low, EUR 339 | EUR 9,240 | EUR 23,739 | EUR 652,713 |
| central, EUR 892 | EUR 23,072 | EUR 62,471 | EUR 664,886 |
| high, EUR 1,785 | EUR 45,384 | EUR 124,942 | EUR 684,520 |

90% ranges from 1,000 resamples of pumps:

- Classifier average precision: 0.352 to 0.487
- Times the dummy's: 16.129 to 26.570
- Recall of warned failures: 0.875 to 1.000
- Model cost: EUR 16,445 to EUR 30,212
- Visit-every-pump cost: EUR 657,931 to EUR 672,026

## Controls

- Shuffled labels: 1.29 times the dummy, limit 1.25.
- Warnings switched off: classifier 1.05, robust z-score 1.01, isolation forest 0.98 times the dummy, limit 1.5.
- Grouped by pump (5 folds): mean average precision 0.388 against 0.421 on the time split.
- Drift flag level chosen on base data to the cut-off: 5.801.

Accuracy and the area under the ROC (receiver operating characteristic) curve are not shown: with so few positive rows they flatter any model (M4).
