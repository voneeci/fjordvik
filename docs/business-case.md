# Business case: Fjordvik data and AI platform

Fjordvik Manufacturing Oy has three problems that one platform solves: its emissions
figures are built by hand from site spreadsheets, product management has no single set of
portfolio figures that reconciles to finance, and its after-sales service only reacts once
a pump has failed. This page sets out why the work is worth doing, the options weighed,
what it costs and risks, how success is measured, and when to stop. It is station 00 of
the data product delivery map ([architecture.md](architecture.md#where-fjordvik-stands-on-the-delivery-map)).

It is written as Fjordvik would run it. The reporting side (data, mcp, powerbi and
power-automate) was built from 12 October to 2 November 2026 without a written business
case, so its part of this page is written after the fact. The service AI side
(`service-ai`) is part way through its build: phases 2 and 3 are done, phases 4 to 7 are
not started, so this page is the case for continuing it.

> **Synthetic data only.** Fjordvik Manufacturing Oy is a fictional company, and this is a
> portfolio project. No real company, client or person is described; roles are job titles,
> not people. The emission factors are **illustrative**, not cited, and must not be used
> for real reporting. Every figure below comes from the project's synthetic tables.

## The decision this page asks for

| Item | Detail |
| --- | --- |
| Gate | The sponsor approves the business case (delivery map station 00) |
| Sponsors | Group Sustainability Manager (emissions), Head of Portfolio (portfolio, as in the [portfolio project plan](portfolio-project-plan.md)), Service Manager (service AI) |
| Asked of the sponsors | Confirm the case for the built reporting side; approve continuing service AI phases 4 to 7, with the kill criteria below; approve the four additions to the [scope](#scope) |
| Status, 26 November 2026 | **Signed.** Reece approved this second edition as the stand-in for the three sponsors, with the [open questions](#open-questions) recorded as known gaps |

## The problems

| Need | Today | Effect |
| --- | --- | --- |
| Emissions reporting | Each site emails a monthly spreadsheet; the sustainability team checks it by eye and copies it into a central file | A kWh/MWh slip makes a line 1,000 times too big; copies of the central file drift; country managers see all or nothing ([README](../README.md#the-business-needs)) |
| Product portfolio | Sales sit in the enterprise resource planning (ERP) system under each business unit's own item numbers | No single view of what each product sells, earns and emits in use that reconciles to finance |
| After-sales service | A pump fails, the customer calls, parts are ordered after the failure, technicians are planned in a spreadsheet | Pumps wait for parts; the readings show most failures coming but nobody watches them ([company profile](company-profile.md#after-sales-service)) |

### The service baseline

Counted on 19 November 2026 from `data/tables` at commit `790589d`, with Python's standard
library: service events by year of `reported_date` in `fact_service_event`, and parts
order lines by year of `order_date` in `fact_parts_order`.

| Year | Service events | Failures (share) | Preventive visits (share) | Inspections | Pump downtime from failures | Median downtime per failure | Parts order value |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2023 | 812 | 100 (12.3%) | 517 (63.7%) | 195 | 17,557.2 hours | 82.2 hours | EUR 11,257,477.68 |
| 2024 | 832 | 99 (11.9%) | 555 (66.7%) | 178 | 17,859.3 hours | 78.8 hours | EUR 14,785,418.36 |
| 2025 | 910 | 125 (13.7%) | 596 (65.5%) | 189 | 18,443.5 hours | 63.7 hours | EUR 20,043,332.75 |

The fleet is 600 connected pumps (369 in Finland, 117 in Sweden, 57 in Estonia, 57 in
Latvia) at 150 customers: 56 with no service contract, 59 Basic and 35 Premium. Twelve
technicians work 457.5 contracted hours a week in total (`dim_asset`, `dim_customer`,
`dim_technician`).

## Options compared

### Emissions and portfolio reporting

| Option | For | Against | Chosen |
| --- | --- | --- | --- |
| A. Keep the central spreadsheet | No new tools or training | The errors and drift above continue; no proof of which version a report used | No |
| B. Buy a carbon accounting product | Ready-made scope 3 methods and audit trail | Not priced in this project (no quote held); a second place for sales and product data; the portfolio need is not covered | No |
| C. Build on the files and tools the sites already use (Excel, SharePoint) with Power Automate intake, a governed dataset and Power BI | One dataset for emissions and portfolio; checks written as code and tested; figures reconcile to finance | Fjordvik owns and maintains it; Power Automate flows and the Power BI Service set-up are designed but not yet built | **Yes** |

### After-sales service

| Option | For | Against | Chosen |
| --- | --- | --- | --- |
| A. Stay reactive | No change | On the phase 3 test period (July to December 2025) visiting no pump cost EUR 49,084 in missed failures, with 55 failures missed ([learning notes](learning/service-ai.md#the-result-1)) | No |
| B. Visit every pump every 30 days | Simple to plan | EUR 693,163 for 3,600 visits over the same period, against EUR 24,477 for the model's alerts | No |
| C. Buy a field service management product with predictive maintenance | Scheduling and a technician app included | Not priced in this project; its models would need the same test against Fjordvik's own pumps | No. Set aside without pricing or testing: this project exists to build each capability and test it against a simple rule (Reece, 26 November 2026) |
| D. Build condition-based service on Fjordvik's own readings, orders and manuals | Uses data Fjordvik already holds; each capability must beat a simple rule before it is used | Fjordvik owns the models and must monitor them; results so far are on planted signals | **Yes, being built** |

The phase 3 costs use Fjordvik's planning inputs (EUR 190.34 for a wasted visit, EUR
892.44 for a missed failure) worked out from its synthetic tables and published rates
(`data/scenarios/planning_inputs.json`). They count Fjordvik's own repair cost only, not
the customer's downtime.

## Benefits

| Benefit | Measure | Baseline | Where it is measured |
| --- | --- | --- | --- |
| One trusted set of emissions figures | Rows that fail the intake rules reach the dataset | Planted problems (MWh for kWh, a missing source, a duplicated row, a missing file) each fail their rule offline | `power-automate/tests` |
| Portfolio figures that reconcile | Clean plus quarantined sales against finance revenue | Reconciles to the cent in every site-month | `data/sql`, `Sales Reconciliation Difference (EUR)` |
| Fewer unplanned failures | Failures as a share of service events | 12.3%, 11.9%, 13.7% (2023 to 2025) | `fact_service_event` |
| Less downtime | Median pump downtime per failure | 82.2, 78.8, 63.7 hours | `fact_service_event` |
| Parts in stock before the failure | Forecast error against simple rules | Driver model mean absolute scaled error (MASE) 0.98 (3 months) against 1.06 for the best simple rule, Oulu, 2025 | [Phase 2 result](learning/service-ai.md#the-result) |
| More parts revenue through self-service | Portal share of parts order value | EUR 1,627,977 of 14,785,418 in 2024; EUR 2,236,530 of 20,043,332 in 2025 | `fact_parts_order.channel` |

No target is set for the business measures yet. Each sponsor sets its target before
go-live, as a line on the go-live checklist of station 07, which is not written yet
(Reece, 26 November 2026). Until then the measure and its baseline are recorded and
nothing is claimed.

## Costs

| Cost | Status |
| --- | --- |
| Build effort (Data and AI Specialist) | Recorded per block in the handover notes; not summed |
| Licence: Power BI Pro, one for each report viewer | EUR 12.10 a user a month, paid yearly, before value added tax (VAT). [Microsoft's Finnish price list](https://www.microsoft.com/fi-fi/power-platform/products/power-bi/pricing), read 26 November 2026. The number of viewers is not set |
| Licence: Power Automate Premium | EUR 13.00 a user a month, paid yearly, before VAT. [Microsoft's Finnish price list](https://www.microsoft.com/fi-fi/power-platform/products/power-automate/pricing), read 26 November 2026. Needed only if a flow uses a premium connector, which the landing zone's design decides |
| Licence: Microsoft 365, with Power Automate's standard connectors | **Not priced.** The plan is not chosen |
| Claude usage for phases 6 and 7 | **Not priced.** No price list was opened |
| Running: the failure risk API's container registry | Azure Container Registry Basic, Reece's choice of 26 November 2026: EUR 0.1496 a day, so EUR 4.49 for a 30-day month (0.1496 x 30). [Azure Retail Prices](https://prices.azure.com/api/retail/prices), Sweden Central, read 26 November 2026 |
| Running: the rest of the failure risk API | Expected to stay inside Azure Container Apps' monthly free allowance at demonstration volumes. This is the estimate in Jasila's research note of 19 November 2026, not re-read for this edition. Rule C1 caps the budget at EUR 5 |
| Running: the landing zone | Under EUR 1 a month in the same research note; not re-read for this edition |
| Running: technician visits from alerts | Modelled in phase 3 (EUR 24,477 for the test half-year at the planning inputs above) |
| Running: model monitoring and retraining | Not estimated |

Costs are still the weakest part of this case: Microsoft 365 and Claude usage are not
priced, the number of licences is not set, and the build effort is not totalled.

## Risks

The portfolio risks are in the [portfolio project plan](portfolio-project-plan.md#risks).
The service AI adds these:

| Risk | Likelihood | Effect | What we do |
| --- | --- | --- | --- |
| Results look better than live data will give, because the signals were planted | Certain on this data | Over-confident plans | Every result says it was measured on synthetic data with planted signals (rule W8); the [learning notes](learning/service-ai.md) list what would change with live data |
| Alerts change the data the model learns from (prevented failures vanish) | Certain once alerts are acted on | A retrained model learns from a fleet it changed | Phase 4 records the loop as a column and names it in the model card (rule E3) |
| An agent acts on text planted in an email or note | Medium | A wrong order or email | Agents draft and never act; text is data, never instructions; planted-instruction evaluations (rules A3, A6) |
| Technicians ignore the alerts | Medium | No benefit | Change and training plan (see [requirements](requirements.md#change-readiness)) |
| Sensor recalibration hides a warning | Medium | Missed failures | Drift monitor; phase 3 caught a unit change but not a 3 C step, and reports it |

## Hypotheses and kill criteria

Each service AI phase states its hypothesis, tests it against a pass mark written before
its code (rule A9), and stops if the kill criterion is met. The pass marks are Reece's,
from the [README](../README.md#after-sales-service-with-ai-being-built).

| # | Hypothesis | Test | Kill criterion | Status |
| --- | --- | --- | --- | --- |
| H1 | A forecast that uses fleet running hours and age predicts parts demand better than a planner's simple rules | MASE below seasonal naive and the best simple forecast; 80% ranges hold 70 to 90% of actuals | Fails either pass mark on the test origins: use the best simple forecast instead | Met at Oulu, 3 November 2026; Tartu too new to test |
| H2 | Daily readings warn of most failures early enough to plan a visit | Average precision at least 3 times a dummy model's; at least 60% of warned failures caught; cheaper than visiting all or none | Fails any of the three: stay with the current visit plan | Met, 12 November 2026; three control checks missed and reported. Phase 4 goes ahead on these scores, with the three misses carried as stated limits (Reece, 26 November 2026) |
| H3 | A solver plans visits more cheaply than "highest risk first, nearest technician" | Breaks no constraint; cheaper in at least 9 of 10 test weeks | Any broken constraint, or fails the 9 of 10: keep the simple rule | Not started |
| H4 | Suggestions from order history beat a most-popular list | Hit rate at 5 above most-popular, overall and for low-history models; never an unfit part | Fails either, or suggests one unfit part: keep most-popular | Not started |
| H5 | Technicians get cited answers from the manuals | Right section in the top 5 for 90% of answerable questions; 90% correct citations; "not found" for every unanswerable one | Fails any: no assistant | Not started |
| H6 | A service desk agent drafts correct work orders that a person approves | 57 of 60 scenario runs correct; nothing applied without approval; no planted instruction followed | Any planted instruction followed, or any write outside the drafts folder: stop phase 7 | Not started |

Reece widened two phases on 3 November 2026, and H3 and H6 above cover only the original
scope:

- **Phase 4** also re-plans the week when a same-day urgent job arrives, and says which
  visits move.
- **Phase 7** also takes call transcripts beside alerts and emails, and sorts each contact
  as urgent or routine. An urgent one alerts an on-call person at once, with a drafted
  emergency work order, parts reservation and same-day slot. The customer is offered
  pickup or delivery of the parts through an invented logistics company: the agent reads
  that company's availability and quotes, and only drafts the booking. One approval by the
  on-call person covers the work order and the booking, and nothing is booked without it.

The pass marks for these additions are set before each phase is built (rule A9). The
synthetic contact log, the logistics company's figures and the part sizes they need are
not generated yet.

A business kill criterion sits above these: if, at the first quarterly review after go-live,
failures as a share of service events and median downtime per failure have not fallen
below their 2025 baselines, the sponsor decides whether to persevere, change or stop
(station 10).

## Scope

| In scope | Out of scope |
| --- | --- |
| Monthly emissions intake, the governed dataset, the Power BI model and its two reports, the read-only Claude connector | Statutory reporting under the EU's Corporate Sustainability Reporting Directive (CSRD): Fjordvik is below the thresholds ([company profile](company-profile.md#size)) |
| Portfolio figures from the ERP extract, the quarterly scorecard | Changes to the ERP system itself |
| The seven service AI capabilities in the [README](../README.md#after-sales-service-with-ai-being-built), with the two phases widened as above | A technician mobile app; customer-facing changes beyond the parts portal suggestions |
| A read-only failure risk API on Microsoft Azure that serves the phase 3 scores (added 26 November 2026) | Any action an agent applies without a person's approval |
| Static HTML dashboards for public readers, showing group-level figures only (rule P1); plant screens wait for a signed-in host (added 26 November 2026) | A live phone line or a live link to a logistics provider |
| A small landing zone in Azure storage, with raw, clean and curated folders (added 26 November 2026) | A bought field service management product (set aside 26 November 2026) |
| Fjordvik's own front end for its architecture documents, starting from the [architecture drawings page](../README.md#architecture-drawings) (added 26 November 2026) | |

The four additions have no use case, decision record, interface contract or threat model
boundary yet. Each gets them before it is built, the API first.

**Order of work** (Reece, 26 November 2026): continuous integration first; then one
screen or tool that shows the phase 2 and 3 results to the Service Manager; then the
phase 4 data step and phase 4, with the API built beside phase 4. The landing zone and the
front end follow; their dates are not set.

The project is internal and not priced: there is no statement of work with a supplier.

## Open questions

- Prices for Microsoft 365 and Claude usage, each read at its publisher, and the number
  of Power BI Pro licences.
- A target for each business measure, from its sponsor, before go-live.
- A use case, decision record, interface contract and threat model boundary for each of
  the four additions to the scope.
- When the landing zone and the front end are built.

## Change history

- 19 November 2026: first edition, during the architecture pause (Reece asked).
- 26 November 2026: second edition, after a review against all eleven stations of the
  delivery map. Reece decided each change in question boxes: four additions to the scope,
  the bought-product option set aside, targets tied to go-live, the three missed phase 3
  controls carried as stated limits, the order of work, and the API's container registry.
  Two licence prices and the registry price were read at their publishers. The phase 4
  and phase 7 additions of 3 November 2026 are written in.
- 26 November 2026: signed by Reece as the stand-in for the three sponsors, after reading
  the second edition. The open questions stand as known gaps.
