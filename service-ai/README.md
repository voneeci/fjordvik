# Fjordvik service AI: from reactive to planned after-sales service

Fjordvik Manufacturing Oy, a maker of electric pumps
([company profile](../docs/company-profile.md)), wants to grow service revenue and cut
downtime for its water utility and industrial customers. Its pumps report daily running
hours, vibration, bearing temperature and power through their variable-speed drives. Yet
service is reactive: a pump fails, the customer calls, parts are ordered after the
failure, and technicians are planned in a spreadsheet.

This part of the Fjordvik project builds seven AI capabilities on that one problem, one
phase at a time. It is the fifth of five parts: `data`, `mcp`, `powerbi`,
`power-automate` and `service-ai`.

> **Synthetic data only.** Fjordvik Manufacturing Oy is a fictional company, and this is a
> portfolio project. No real company, client or person is described. Customer names are
> invented. The emission factors elsewhere in the project are **illustrative**, not cited.

## The data it works on

The service data is generated in [`data`](../data) and read here in place, never copied:

| Table | What it holds |
| --- | --- |
| `dim_customer` | 150 customers in the Nordics and Baltics: water utilities, industrial plants, buildings and district energy, and distributors |
| `dim_asset` | 600 connected pumps, with serial number, model, owner, location and install date |
| `dim_part`, `bridge_part_compatibility` | 52 spare parts and kits, and the product groups each fits |
| `dim_technician` | 12 technicians, with home base, countries, skills and weekly hours |
| `fact_asset_telemetry` | One row per pump per day: running hours, vibration, bearing temperature and power |
| `fact_service_event` | Failures, preventive visits and inspections, with parts used, downtime and a technician note |
| `fact_parts_order` | Every parts order line from Oulu and Tartu warehouses, adding up to `fact_sales` to the cent |
| `fact_portal_event` | Parts the portal showed customers, and which they clicked |

Service manuals for each product group, the service terms and the warranty policy are in
[`data/corpus`](../data/corpus).

## The build

Each phase sets its pass mark before any code, and adds a section to the learning notes,
[`docs/learning/service-ai.md`](../docs/learning/service-ai.md): the idea in plain English,
how the code does it, the result, and what would change with live data.

| Phase | Capability | Pass mark | Status |
| --- | --- | --- | --- |
| 2 | Spare parts demand forecast | Beats seasonal naive and the best simple forecast on mean absolute scaled error (MASE); 80% ranges hold 70 to 90% of actuals | Met at Oulu, 3 November 2026 (below); Tartu too new to test |
| 3 | Anomaly detection and failure prediction | At least 3 times a dummy model's average precision; catches at least 60% of warned failures; cheaper than visiting all pumps or none | Met, 12 November 2026 (below); three control limits missed |
| 4 | Technician scheduling | Breaks no constraint; cheaper than the simple rule in at least 9 of 10 weeks | Not started |
| 5 | Parts recommendations | Beats most-popular on hit rate at 5; never suggests a part that does not fit | Not started |
| 6 | Service assistant (retrieval-augmented generation) | Right section in the top 5 for 90% of answerable questions; "not found" for every unanswerable one | Not started |
| 7 | Service desk agent | At least 57 of 60 scenario runs correct; nothing applied without approval; planted instructions never followed | Not started |

## Phase 2: the spare parts demand forecast

Planners at Oulu and Tartu warehouses get a monthly forecast in units for each of the
eight part families, three and six months ahead, with an 80% range. It is tested on
rolling origins against three simple forecasts (naive, seasonal naive and a moving
average), with the evaluation dates and pass marks committed before the code
([`eval/forecast/`](eval/forecast)). The driver model is a Poisson regression on the
connected fleet's running hours and age, using each driver only as it was known on the
forecast date. The method and its limits are in the
[learning notes](../docs/learning/service-ai.md#phase-2-forecasting-spare-parts-demand).

Result at Oulu on the test period (January to December 2025), measured on synthetic data
with planted signals. Lower MASE is better:

| Oulu | Origins | Seasonal naive | Best simple forecast (6-month moving average) | Driver model | Driver 80% coverage |
| --- | --- | --- | --- | --- | --- |
| 3-month forecast | 10 | 1.25 | 1.06 | 0.98 | 84% |
| 6-month forecast | 7 | 1.16 | 1.08 | 1.00 | 84% |

Both pass marks are met at both lengths, by a small margin. Tartu opened in July 2024, so
it has one test origin, below the minimum of six: it is reported apart, with a forward
forecast and no accuracy claim. Full results, per origin and per family, are in
[`results/forecast/`](results/forecast), each file stamped with the data checksum, the
commit and the model version.

To rerun it (the test step refuses to run without the committed split lock):

```powershell
.venv\Scripts\python scripts\run_forecast.py --period test
.venv\Scripts\python scripts\recheck_forecast.py
```

## Phase 3: failure risk

Every pump gets a daily score: the chance it fails in the next 30 days, from readings up to
that day. A score at or above the alert level sends a technician, set from the cost of a
missed failure (EUR 892.44) against a wasted visit (EUR 190.34), both worked out by the
`data` part from synthetic tables and published rates. The model is a gradient-boosted
classifier on robust z-scores, changes and medians of each pump's readings, adjusted for
its fleet, plus an isolation forest and the pump's facts. The evaluation set, written by a
different chat before any code, is in [`eval/ml/`](eval/ml). The method and its limits are
in the [learning notes](../docs/learning/service-ai.md#phase-3-predicting-pump-failures).

Result on the test period (July to December 2025), scored once, measured on synthetic data
with planted signals:

| Pass mark | Result |
| --- | --- |
| Average precision at least 3 times the dummy's | 0.404, 26.1 times the dummy's 0.0155: met |
| At least 0.6 of warned failures caught 7 to 30 days ahead | 28 of 38, 0.74: met |
| Cost below visiting no pump and every pump | EUR 24,477 against EUR 49,084 and EUR 693,163: met |
| Unwarned failures reported apart; leakage test | 17 of 55 gave no warning; leakage test passed: met |
| Shuffled labels at most 1.25 times the dummy (validation) | 1.29: missed |
| Warnings switched off: each model at most 1.5 times the dummy | z-score 0.97, forest 1.05, classifier 1.61: missed |
| Drift: 90% of changed pumps flagged within 14 days; at most 1% false flags | unit change 40 of 40, recalibration 0 of 30: missed; false flags 0.90% |

The misses are reported as they fell; the evaluation set and its limits are unchanged.
Reece chose to score the test period once after the shuffled-label miss on validation.
Full results are in [`results/ml/`](results/ml), each file stamped with the data checksum,
the commit and the model version. Phase 4 will plan visits from the daily scores and
`risk_2025-12-31.csv`.

To rerun it (build the scenarios first from `..\data`, then the test step refuses to run
without the committed split lock or after a run with other settings):

```powershell
cd ..\data; .venv\Scripts\python -m fjordvik_data.scenarios --out ..\service-ai\build\ml-scenarios; cd ..\service-ai
.venv\Scripts\python scripts\run_ml.py --period test
.venv\Scripts\python scripts\recheck_ml.py
```

## How to run the tests

You need Python 3.11 or newer. From this folder:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest -q
```

61 tests check that the shared data matches its manifest, run the project's guardrail
checks ([GUARDRAILS.md](../GUARDRAILS.md)), and test the forecast (point-in-time drivers,
rolling origins and the split lock, the scores, the stamped results and the independent
recheck) and the failure risk model (labels and at-risk rows, point-in-time features, the
feature allowlist and answer-key isolation, anomaly scores on planted waves, spikes and
rises, alerts and the threshold, the controls, drift monitors, and the results written by
the run's own code, checked by the recheck). No key or network is needed.

## Guardrails

The rules for this part are in [GUARDRAILS.md](../GUARDRAILS.md), section 2 above all:
drafts only until a person approves them, a unique request ID per draft, no writes to
`data/`, and text in emails and documents treated as data, never as instructions.

## Licence

Code: MIT ([LICENSE](LICENSE)). Data: Creative Commons Attribution 4.0 (CC BY 4.0)
([data/LICENSE-DATA.md](../data/LICENSE-DATA.md)).
