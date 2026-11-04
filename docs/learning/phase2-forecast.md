# Phase 2: forecasting spare parts demand

Learning note for the after-sales service build. Phase 2, 3 November 2026. Measured on
synthetic data with planted signals: Fjordvik Manufacturing Oy is fictional, and nothing
here describes real pumps, warehouses or customers.

**Key points**

- The forecast gives Oulu and Tartu warehouses a monthly figure and an 80% range for each
  of eight part families, three and six months ahead.
- At Oulu it met both of Reece's pass marks on the test period: a mean absolute scaled
  error (MASE) of 0.98 for three months and 1.00 for six, below the best simple forecast
  (1.06 and 1.08), with 84% of actuals inside the 80% ranges.
- The margin is small, and the drivers were planted by the data generator. Tartu has too
  little history to test, so its forecast is reported apart with no accuracy claim.

## The business need

Fjordvik orders spare parts after a pump fails, so the pump waits for the part. A planner
who knows next quarter's demand for each part family can hold stock before the failure
instead. The question this phase answers is whether a forecast that uses what Fjordvik
knows about its pump fleet does better than the simple rules a planner would use anyway,
and by how much it can be trusted.

## The idea in plain English

**Beat the simple forecasts first.** Three simple forecasts set the bar: next month equals
this month (naive), next month equals the same month last year (seasonal naive), and next
month equals the average of the last few months (moving average). They're hard to beat on
noisy monthly figures, so a model that can't beat them shouldn't be used, however clever
it looks.

**Forecast the way a planner would.** A backtest pretends to stand at a past date (an
origin), forecasts the next six months using only what was known then, and compares the
forecast with what happened. Doing this from every month in turn (rolling origins) means
one lucky month can't decide the result.

**Fix the test before building.** The months used to choose settings (validation, April to
November 2024) are kept apart from the months used to judge the result (test, January to
December 2025), with December 2024 left out of both so nothing tuned on validation leaks
into the test. The dates, the minimum number of origins and the pass marks were committed
before any code, and the chosen settings were locked before the test ran once.

**Score errors on a fair scale.** MASE divides each forecast's average error by the error
seasonal naive made on that origin's training months. A score of 1 means "as far off as
seasonal naive usually was"; 0.8 means 20% closer. The scale makes a family selling 30
overhaul kits a month comparable with one selling 1,700 consumables.

**Use drivers only as they were known.** The planted drivers are the fleet's running hours
and its age. Age is known ahead: today's pumps will be six months older in six months.
Running hours aren't, so the model forecasts them with the same month a year earlier
rather than using the actual future hours no planner would have. Every driver value is
saved with the date it became known.

**Give a range, and check it.** Each forecast comes with an 80% range built from the
model's own past errors, using only errors whose months had already happened. A good 80%
range holds about eight actuals in ten: far fewer means it's overconfident, far more means
it's too wide to plan with.

## How the code does it

The package is `service-ai/src/fjordvik_service/forecast/`; each step checks its row count,
unique keys and missing values, and stops with an error if one fails.

1. **Demand** (`demand.py`): every order line from `fact_parts_order`, service technician
   lines included, summed to units per warehouse, part family and month. Each warehouse's
   series starts in its first month with orders (Tartu in July 2024).
2. **Drivers** (`drivers.py`): mean running hours per pump-day and mean pump age, for the
   Nordic pumps (Finland and Sweden) and the Baltic pumps (Estonia and Latvia), blended for
   each warehouse by its share of units to each region. `drivers_at` builds everything a
   forecast may use at its forecast date, and nothing later.
3. **Methods** (`benchmarks.py`, `model.py`): the three simple forecasts, and the driver
   model, a Poisson regression (a model for counts) per warehouse and family on running
   hours and age.
4. **Backtest and scores** (`backtest.py`, `metrics.py`, `intervals.py`): every method
   forecasts from every origin with at least 15 training months; MASE, interval coverage
   and the Winkler score (the range's width plus a penalty for each miss) per series and
   per origin.
5. **Runs** (`scripts/run_forecast.py`): the validation step ran on data up to November
   2024 only and chose a 6-month moving average and no season term for the driver model.
   It wrote `eval/forecast/split_lock.json`. The test step refuses to run without that
   lock or with uncommitted code, so every result names the commit it ran on. It ran
   twice with the same frozen settings: an independent review found the result files had
   Windows line endings, which broke their checksums in a fresh copy, and the second run
   after the fix reproduced every score exactly.
6. **Recheck** (`scripts/recheck_forecast.py`): rebuilds demand from the raw order lines
   with the standard library and recomputes every MASE from the saved forecasts. It
   matched all 160 test and validation series.

Results are in `service-ai/results/forecast/`, each file stamped with the data checksum,
the commit and the model version, with a manifest of checksums.

## The result

On Oulu's test origins, the driver model met both pass marks for both forecast lengths.
Read the table across: lower MASE is better, and the driver model must sit below seasonal
naive and below the best of the three simple forecasts.

| Oulu, test period | Origins | Naive | Seasonal naive | Moving average (6 months) | Driver model | Driver 80% coverage |
| --- | --- | --- | --- | --- | --- | --- |
| 3-month forecast | 10 | 1.40 | 1.25 | 1.06 | **0.98** | 84% (201 of 240) |
| 6-month forecast | 7 | 1.40 | 1.16 | 1.08 | **1.00** | 84% (283 of 336) |

What the averages hide:

- **The margin is small.** The driver model's MASE is 7% to 8% below the moving average's.
  It beats the moving average in five of the eight families and is best outright in four:
  the moving average stays ahead for bearings and consumables, and seasonal naive is best
  for overhaul kits and service kits.
- **Not every origin passes.** Five of the ten 3-month origins, those from January to May
  2025, score above 1. At the April 2025 origin only 67% of actuals fell inside the
  ranges. The later origins, with more history behind them, score 0.77 to 0.88.
- **History matters.** On validation, with 15 to 17 training months, the driver model lost
  to the moving average (6-month MASE 1.78 against 1.37). It moved ahead on the test
  origins, which have 24 to 33 training months. A likely reason is that one odd month, a
  spike in motor parts in July 2023, steers a short fit far more than a long one.
- **Tartu is untested.** With 18 months of history it has one 3-month test origin and no
  6-month one, below the minimum of six. At that origin naive did best (0.43) and the
  driver model worst (0.77). Tartu's scale includes its July to September 2024 opening
  ramp, so those scores look better than they are, and its ranges are 1.1 to 3.7 times as
  wide as they would be without the ramp months. Its forward forecast for January to June
  2026 is in `forecast_2026h1.csv` with ranges borrowed from Oulu's errors, labelled so,
  and should not be relied on until Tartu has more history.

The forward forecast for both warehouses, January to June 2026, is in
`service-ai/results/forecast/forecast_2026h1.csv`. For example, Oulu's March 2026 bearings
forecast is 487 units, with an 80% range of 356 to 659.

## What would change with live data

- The drivers here were planted by the generator, so a model that uses them was always
  likely to help. With live data, running hours and age may explain far less of the mix,
  and the driver model may not beat a moving average at all.
- The connected fleet is a sample of the installed base. A live forecast would need to
  check that the sample still represents the base as customers and pump models change.
- Live orders arrive late and get corrected. The forecast would have to use the order book
  as it stood on each forecast date, not as it was later revised.
- Promotions, price changes, a big customer's stock build or a new warehouse would break
  the patterns. Each would need its own driver or a planner's override.
- Two or three more years of history would allow a season term, more origins and a fair
  test for Tartu.
