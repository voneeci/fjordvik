# Phase 2 forecast results (validation)

> **Measured on synthetic data with planted signals: Fjordvik Manufacturing Oy is fictional; these are not results on real pumps or warehouses.** The demand drivers were planted by the data generator, so these scores show the method works on a known signal, not how it would do on live demand.

Data checksum `379e6075034a605fc5dac6806d5f6367079ea4dee4083180167bfbc34bfb5b68`, commit `12a43b7f5bd5c842557ac1d9e61a8c07a4121815`, model version `forecast-1.0.0`. Settings chosen on validation: moving average of 6 months; driver model without a season term.

MASE is mean absolute scaled error: each method's error divided by seasonal naive's error on the origin's training months. Below 1 beats that scale.

## 3-month forecast

| Warehouse | Origins | naive | seasonal_naive | moving_average_w6 | driver_base | Driver 80% coverage |
| --- | --- | --- | --- | --- | --- | --- |
| EE02 | 0 | n/a | n/a | n/a | n/a | n/a |
| FI03 | 6 | 1.603 | 1.639 | 1.190 | 1.477 | 0.708 |

Driver model per origin:

| Warehouse | Origin | MASE | 80% coverage | Winkler (scaled) |
| --- | --- | --- | --- | --- |
| FI03 | 2024-03 | 0.954 | n/a | n/a |
| FI03 | 2024-04 | 1.573 | n/a | n/a |
| FI03 | 2024-05 | 1.974 | 0.500 | 6.124 |
| FI03 | 2024-06 | 1.890 | 0.562 | 13.694 |
| FI03 | 2024-07 | 1.120 | 0.792 | 6.399 |
| FI03 | 2024-08 | 1.353 | 0.792 | 6.534 |

## 6-month forecast

| Warehouse | Origins | naive | seasonal_naive | moving_average_w6 | driver_base | Driver 80% coverage |
| --- | --- | --- | --- | --- | --- | --- |
| EE02 | 0 | n/a | n/a | n/a | n/a | n/a |
| FI03 | 3 | 1.752 | 1.943 | 1.371 | 1.784 | 0.500 |

Driver model per origin:

| Warehouse | Origin | MASE | 80% coverage | Winkler (scaled) |
| --- | --- | --- | --- | --- |
| FI03 | 2024-03 | 2.001 | n/a | n/a |
| FI03 | 2024-04 | 1.547 | n/a | n/a |
| FI03 | 2024-05 | 1.804 | 0.500 | 6.124 |
