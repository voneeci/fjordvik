# After-sales service AI: learning notes

Fjordvik's after-sales service is reactive: a pump fails, the customer calls, parts are
ordered after the failure, and technicians are planned in a spreadsheet. The after-sales
service AI is built one phase at a time to change that, and each phase adds a section here
when it ends: the business need, the idea in plain English, how the code does it, the
result, and what would change with live data. Synthetic data only: Fjordvik Manufacturing
Oy is fictional.

## Contents

- [Phase 1: synthetic service data with a planted signal](#phase-1-synthetic-service-data-with-a-planted-signal)
- [Phase 2: forecasting spare parts demand](#phase-2-forecasting-spare-parts-demand)
- [Phase 3: predicting pump failures](#phase-3-predicting-pump-failures)

## Phase 1: synthetic service data with a planted signal

Phase 1, 2 November 2026. Synthetic data only: Fjordvik Manufacturing Oy is fictional.

### The business need

The service AI needs history to learn from: pumps, their daily readings, their failures,
the parts they used and the orders customers placed. Fjordvik is fictional, so that
history has to be made. Made-up data is only useful if it behaves like the real thing,
and if we know exactly what is hidden in it.

### The idea in plain English

**Plant a signal, and keep the answer key.** The generator decides, pump by pump, when
each failure happens. Before about two thirds of them it raises vibration or bearing
temperature over two to six weeks, the way a worn bearing does. Before the rest it does
nothing, as with a sudden seal leak or an electrical trip. It writes down which was which
in an answer key kept outside the tables. Later phases can then measure what a model
found against what was really there, which live data never allows.

**Make the noise honest.** Readings wander with the season (heating pumps run most in
winter), with age (old pumps vibrate a little more), and day to day. A pump sometimes
gives one high reading after a start. A model has to tell these from a real warning.

**Add up to what finance already reports.** Parts orders are not made up freely. Every
month's spare parts and service kit sales already sit in `fact_sales`, so the generator
splits each of those rows into order lines. The lines add up to it in units and to the
cent, so the service data and the sales reports can never disagree.

**Same seed, same files.** Every pump has its own random stream, seeded from its id. Run
the generator twice and the files are identical, byte for byte. A test proves it on every
run, and another proves that none of the 22 earlier tables moved.

### How the code does it

`data/src/fjordvik_data/service.py`, in three passes per pump:

1. **Planned running hours** for each day, from the pump's duty, its seasonal profile and
   weekends.
2. **Events.** Each day has a small chance of failure. It grows by 7% for each year of age
   and with the wear since the last overhaul, and in proportion to the day's running hours.
   Preventive visits (one or two a year, by contract) take wear away. A failure picks a mode
   that fits the pump, decides whether it gives warning, and stops the pump until it is
   repaired: one to three days if the part is in stock, its full lead time if not.
3. **Readings.** Vibration, temperature and power from the pump's baseline, its age, the
   season and noise, plus the warning rise on the days before a warned failure.

Then the parts orders: service parts first, in the month they were ordered, then stock
orders from the wider installed base. The mix of stock orders follows the fleet's running
hours and age, which gives the phase 2 forecast real drivers. When a month runs cheap
against its invoiced value, dearer baskets become likelier, so prices stay close to list.

`corpus.py` writes the manuals from the same settings, so a manual can never quote a part
or an alarm limit the data does not have.

### The result

- 600 pumps, 582,996 daily readings (20 MB), 2,554 service events, 53,654 order lines and
  39,725 portal rows; the 22 earlier tables are unchanged.
- 324 failures over three years (100, 99 and 125 a year); 222 of them (69%) gave warning.
  The median failure stopped its pump for 79 hours.
- **A warned failure** (pump A0505, a bearing failure on 4 May 2024, warning from 27 March):
  vibration 2.14 mm/s two months before, 2.44 a month before, 4.40 two weeks before, 6.46
  three days before. Bearing temperature went from 47 to 65 C.
- **A failure with no warning** (pump A0047, an electrical trip on 1 June 2024): vibration
  stayed between 2.8 and 3.3 mm/s. Its bearing temperature rose from 34 to 40 C, but that
  is the season warming up, not a fault: the kind of change phase 3 must not take for a
  warning.
- **Reconciliation:** Tartu's service kit sales to the Baltics in March 2025 are 258 units
  and EUR 172,469.98 in `fact_sales`; its 70 order lines add up to exactly that.
- Data tests: 96 passed (36 new).

### What would change with live data

- There would be no answer key. Whether a failure "gave warning" would have to be judged
  from the readings after the fact, and labels would be noisier.
- Readings would have gaps, sensor faults, recalibrations and firmware changes. Each needs
  a rule in the intake checks, and a model must cope with them.
- Failures would not follow a neat hazard; some customers report late, and some repairs
  are logged with the wrong mode.
- Orders would come from the ERP, not be split from sales; the reconciliation would be a
  check, not a construction.
- Models trained on this data will look better than they would on live data. Each later
  phase says so next to its results.

## Phase 2: forecasting spare parts demand

Phase 2, 3 November 2026. Measured on synthetic data with planted signals: Fjordvik
Manufacturing Oy is fictional, and nothing here describes real pumps, warehouses or
customers.

**Key points**

- The forecast gives Oulu and Tartu warehouses a monthly figure and an 80% range for each
  of eight part families, three and six months ahead.
- At Oulu it met both of Reece's pass marks on the test period: a mean absolute scaled
  error (MASE) of 0.98 for three months and 1.00 for six, below the best simple forecast
  (1.06 and 1.08), with 84% of actuals inside the 80% ranges.
- The margin is small, and the drivers were planted by the data generator. Tartu has too
  little history to test, so its forecast is reported apart with no accuracy claim.

### The business need

Fjordvik orders spare parts after a pump fails, so the pump waits for the part. A planner
who knows next quarter's demand for each part family can hold stock before the failure
instead. The question this phase answers is whether a forecast that uses what Fjordvik
knows about its pump fleet does better than the simple rules a planner would use anyway,
and by how much it can be trusted.

### The idea in plain English

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

### How the code does it

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

### The result

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

### What would change with live data

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

## Phase 3: predicting pump failures

Phase 3, 12 November 2026. Measured on synthetic data with planted signals: Fjordvik
Manufacturing Oy is fictional, and nothing here describes real pumps or a real service team.

**Key points**

- Every pump gets a daily score: the chance it fails in the next 30 days, from readings up
  to that day. A score at or above an alert level sends a technician.
- On the test period (July to December 2025) it met the three main pass marks: average
  precision 26 times the dummy model's (a guess at the base rate), 28 of the 38 failures
  that gave a warning caught 7 to 30 days ahead, and a cost of EUR 24,477 against
  EUR 49,084 for visiting no pump and EUR 693,163 for visiting every pump every 30 days.
- Three control checks missed their limits, and are reported as they fell: a model trained
  on shuffled labels, the classifier with the warnings switched off, and the drift monitor
  on a small temperature step. 17 of the 55 test failures gave no warning, so no plan
  could prevent them.

### The business need

Fjordvik sends a technician after a pump has failed, so the customer loses the pump and
Fjordvik pays for an unplanned repair. Most failures follow weeks of rising vibration or
bearing temperature. A daily list of the pumps most likely to fail would let a planner send
a technician first. Phase 4 plans visits from this list, so each score needs a plain
meaning and a stated limit.

### The idea in plain English

**Score each pump each day.** The score is the model's estimate of the chance that the
pump has a failure in the next 30 days, using only readings up to the end of that day. A
failure on day t+1 counts; one on day t+31 doesn't.

**Compare a pump with its fleet and with its own normal.** Readings follow the seasons, so
a high bearing temperature in July means little. Each reading is compared with the median
of pumps in the same application on the same day, which takes the season out. The result
is then compared with the pump's own normal over the 90 days ending 8 days earlier. The
robust z-score says how unusual the last week is, in units of that pump's normal spread,
using medians so a one-day spike can't move it.

**Rank first, then decide.** Failures are rare: a failure follows within 30 days on 1.5%
of test pump-days. A model that says "no failure" every day is 98.5% accurate and
useless, so accuracy is never reported. Average precision measures how well the model
ranks the days that lead to a failure above those that don't. The dummy model, which gives
every day the base rate, scores the base rate itself: 0.0155 on test.

**Set the alert level from the costs.** An alert sends one technician, and the pump then
stays quiet for 30 days. An alert 7 to 30 days before a failure catches it; one with no
failure in the next 30 days wastes a visit. The data part worked out both costs from
Fjordvik's synthetic tables and published rates: EUR 190.34 for a wasted visit and
EUR 892.44 for a missed failure (Fjordvik's extra repair cost only). The alert level is
the one with the lowest total cost on validation, chosen without knowing which failures
gave a warning.

**Fix the test before building.** A different chat wrote the dates, the columns the model
may read, the pass marks and the control limits before any code. The model was trained on
data to 1 December 2024; its settings, alert level and drift level were chosen on January
to June 2025; and the test period was scored once, after those choices were locked.

**Check it can't cheat.** Four controls look for a model that learned the wrong thing:
features rebuilt with every later row deleted must not change; a model trained on shuffled
labels must fall to the dummy's level; with the warning rise switched off in the data,
every model must fall to the dummy's level; and a drift monitor must catch a sensor that is
recalibrated or changes unit, without flagging the seasons.

### How the code does it

The package is `service-ai/src/fjordvik_service/ml/`. Every step checks its row counts
against the evaluation set and stops with an error if one differs.

1. **Labels and rows** (`labels.py`): reads four columns of `fact_service_event`. Days with
   an open failure ticket, days the pump didn't run and days with fewer than 60 readings in
   the pump's normal window are left out. Test period: 88,274 pump-days scored, 1,365 of
   them followed by a failure.
2. **Features** (`features.py`): 31 columns from the telemetry, pump, product and customer
   tables only, each on the written allowlist: 7 and 30-day medians, 14-day slopes, change
   against the pump's normal, fleet-adjusted readings, robust z-scores, the highest z-score
   and the days above 3 in the last fortnight, and the pump's age, type, rated power and
   service contract. Every window ends on the day scored.
3. **Anomaly scores** (`anomaly.py`): an isolation forest, which scores how easily a
   pump-day can be told apart from the rest, fitted on training rows only. It is the 32nd
   column.
4. **Classifier** (`model.py`): gradient-boosted trees (scikit-learn's
   `HistGradientBoostingClassifier`), with eight settings tried on validation. The simplest
   won: 15 leaves, 100 rounds, learning rate 0.05, average precision 0.421 on validation.
5. **Alerts and cost** (`alerts.py`): tries every distinct validation score as the alert
   level and keeps the cheapest, 0.891.
6. **Drift** (`drift.py`): each sensor's 7-day median against the same pump's readings in
   the same calendar month of earlier years. Its flag level, 5.80, is the lowest that
   flagged at most 1% of normal pump-months up to June 2025.
7. **Evaluation** (`evaluate.py`): the only module that opens the answer key in
   `data/generator-truth/`, to learn which failures gave a warning, after everything else
   is fixed.
8. **Runs and recheck** (`scripts/run_ml.py`, `scripts/recheck_ml.py`): the test step
   refuses to run without the lock, with uncommitted code, or after a test run with other
   settings. The recheck rebuilds the rows, labels, alerts and costs with the Python
   standard library alone, and matched every headline figure.

Results are in `service-ai/results/ml/`, each file stamped with the data checksum, the
commit and the model version.

### The result

| Test period, July to December 2025 | Result | Pass mark | |
| --- | --- | --- | --- |
| Average precision | 0.404, 26.1 times the dummy's 0.0155 (90% range 19.5 to 35.6 times) | 3 times | Met |
| Warned failures caught 7 to 30 days ahead | 28 of 38, 0.74 (range 0.61 to 0.85) | 0.6 | Met |
| Cost of the model's alerts | EUR 24,477 | Below both plans | Met |
| Cost of visiting no pump | EUR 49,084 (55 failures missed) | | |
| Cost of visiting every pump every 30 days | EUR 693,163 (3,600 visits) | | |

The ranges come from resampling pumps 1,000 times. Of the 38 alerts, 28 caught a failure,
2 wasted a visit, and 8 came 1 to 6 days before a failure, too late for a planned visit.
The model also cost less than visiting no pump at the low (EUR 339) and high (EUR 1,785)
missed-failure costs.

What the headline hides:

- **A ceiling of 69%.** 17 of the 55 test failures (31%) gave no warning in the readings.
  No plan catches them, so recall is measured on the 38 that did.
- **The z-score does most of the work.** Alone, the highest robust z-score reaches average
  precision 0.323 and the isolation forest 0.236. The pump's facts alone reach 0.030.
- **Shuffled labels: missed.** Trained on shuffled labels, the classifier should do no
  better than the dummy. Over five shuffles it averaged 1.29 times the dummy on
  validation, against a limit of 1.25. Four shuffles gave 0.86 to 1.24; one gave 2.24,
  because it memorised a small cluster of unusual pump-days in training, and unusual days
  are where failures sit. The leak checks passed. Reece chose to record the miss and
  score the test period once.
- **Warnings switched off: missed by the classifier.** On telemetry with the warning rise
  removed, the z-score and the forest fell to the dummy's level (0.97 and 1.05 times on
  test), but the classifier reached 1.61 against a limit of 1.5. The pump's facts alone
  score 1.94 times the dummy, because older pumps and some pump types fail more often, and
  the retrained classifier learned them.
- **Drift: the unit change was caught, the recalibration wasn't.** All 40 pumps whose
  vibration switched to inches per second were flagged, after a median of 3 days. None of
  the 30 pumps whose bearing temperature read 3.0 C higher was flagged within 14 days; 8
  were flagged later. The flag level that keeps normal months quiet (0.90% flagged on
  test, limit 1%) sits above a 3 C step.
- **The top tenth carries the signal.** Pump-days in the highest tenth of scores averaged
  a score of 0.095, and 7.3% were followed by a failure. In the other nine tenths, scores
  and observed rates both stayed between 0.2% and 1.3%.
- **Grouped by pump.** On pumps the model never saw in training, average precision on
  validation was 0.388, against 0.421 on the time split.
- **No pump on alert at the end of 2025.** The forward list for 31 December 2025 scores
  590 pumps; the highest is 0.354, below the alert level of 0.891. Those days have no
  complete 30-day window yet, so the list itself can't be scored.

### What would change with live data

- The warning rise was planted by the generator, two to six weeks before most failures. On
  live pumps, warnings may be shorter, weaker or missing, and the share of failures with
  any warning sets the ceiling.
- The two costs are Fjordvik's repair cost only. Counting a customer's downtime would raise
  the cost of a miss and move the alert level down.
- Once technicians act on alerts, prevented failures disappear from the data, so a
  retrained model would learn from a fleet the model itself changed. Phase 4 records that
  loop.
- The drift monitor needs at least a year of history per pump and month. A step smaller
  than the fleet's natural spread needs a level per sensor or the calibration records.
- A minimum leaf size would be the first thing to try against the shuffled-label miss. It
  needs a new evaluation set and a rerun from the start.
