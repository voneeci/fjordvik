# Phase 2 forecast results (test)

> **Measured on synthetic data with planted signals: Fjordvik Manufacturing Oy is fictional; these are not results on real pumps or warehouses.** The demand drivers were planted by the data generator, so these scores show the method works on a known signal, not how it would do on live demand.

Data checksum `379e6075034a605fc5dac6806d5f6367079ea4dee4083180167bfbc34bfb5b68`, commit `d7d236149e0dec30c1b568a2541557b803bbf87a`, model version `forecast-1.0.0`. Settings chosen on validation: moving average of 6 months; driver model without a season term.

MASE is mean absolute scaled error: each method's error divided by seasonal naive's error on the origin's training months. Below 1 beats that scale.

## 3-month forecast

| Warehouse | Origins | naive | seasonal_naive | moving_average_w6 | driver_base | Driver 80% coverage |
| --- | --- | --- | --- | --- | --- | --- |
| EE02 | 1 | 0.435 | 0.503 | 0.446 | 0.770 | 0.958 |
| FI03 | 10 | 1.404 | 1.253 | 1.062 | 0.983 | 0.838 |

Pass marks: MASE pass; coverage pass.

EE02 is reported apart: fewer than 6 test origins; not pooled into the pass mark. Its first months (from 2024-07) are in every scale q, so if trade was still ramping up then, its ranges are wider and its MASE lower than they would otherwise be.

Driver model per origin:

| Warehouse | Origin | MASE | 80% coverage | Winkler (scaled) |
| --- | --- | --- | --- | --- |
| EE02 | 2025-09 | 0.770 | 0.958 | 3.480 |
| FI03 | 2024-12 | 0.971 | 0.833 | 4.057 |
| FI03 | 2025-01 | 1.008 | 0.833 | 4.451 |
| FI03 | 2025-02 | 1.211 | 0.750 | 5.034 |
| FI03 | 2025-03 | 1.093 | 0.833 | 4.538 |
| FI03 | 2025-04 | 1.177 | 0.667 | 4.989 |
| FI03 | 2025-05 | 1.052 | 0.792 | 4.564 |
| FI03 | 2025-06 | 0.770 | 0.917 | 3.543 |
| FI03 | 2025-07 | 0.864 | 0.875 | 3.841 |
| FI03 | 2025-08 | 0.879 | 0.958 | 3.538 |
| FI03 | 2025-09 | 0.801 | 0.917 | 3.506 |

## 6-month forecast

| Warehouse | Origins | naive | seasonal_naive | moving_average_w6 | driver_base | Driver 80% coverage |
| --- | --- | --- | --- | --- | --- | --- |
| EE02 | 0 | n/a | n/a | n/a | n/a | n/a |
| FI03 | 7 | 1.399 | 1.159 | 1.082 | 0.999 | 0.842 |

Pass marks: MASE pass; coverage pass.

EE02 is reported apart: fewer than 6 test origins; not pooled into the pass mark. Its first months (from 2024-07) are in every scale q, so if trade was still ramping up then, its ranges are wider and its MASE lower than they would otherwise be.

Driver model per origin:

| Warehouse | Origin | MASE | 80% coverage | Winkler (scaled) |
| --- | --- | --- | --- | --- |
| FI03 | 2024-12 | 1.067 | 0.854 | 4.794 |
| FI03 | 2025-01 | 1.095 | 0.812 | 4.898 |
| FI03 | 2025-02 | 1.140 | 0.771 | 4.781 |
| FI03 | 2025-03 | 0.999 | 0.875 | 4.433 |
| FI03 | 2025-04 | 0.995 | 0.812 | 4.598 |
| FI03 | 2025-05 | 0.941 | 0.833 | 4.273 |
| FI03 | 2025-06 | 0.756 | 0.938 | 3.773 |
