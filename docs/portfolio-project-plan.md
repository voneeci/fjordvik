# Project plan: Fjordvik portfolio reporting

A lightweight plan for building the portfolio layer: the product classification, the ERP
sales extract and its SQL, the Power BI pages, the scorecard and the training. It is
written as Fjordvik would run it; the project itself was built on 31 October 2026 on
synthetic data, so the dates below are the plan, and the status column says what is built.

> **Synthetic data only.** Fjordvik Manufacturing Oy is a fictional company; roles are job
> titles, not people.

## Goal

One trusted set of portfolio figures (volume, price, mix, margin, balance and use-phase
emissions) from the ERP, reconciled to finance, scored each quarter, and used by Product
Managers and regional users without asking an analyst for every number.

## Roles

| Role | Responsible for |
| --- | --- |
| Head of Portfolio (sponsor) | Scope, priorities, sign-off |
| Data and AI Specialist | Project manager and builder: SQL, model, report, documentation, training |
| Portfolio governance | The global product classification and mapping decisions |
| Regional controllers | Sales and cost in the ERP; reconciliation sign-off per region |
| Product Managers | Scorecard ratings; testing the pages with real questions |
| IT (ERP team) | The Oracle extract, staging database and gateway |

## Milestones

| No. | Milestone | Owner | Done when | Status |
| --- | --- | --- | --- | --- |
| M1 | Classification agreed | Portfolio governance | Every business unit's item numbers map to one global product | Built: `data/reference/product_code_map.csv` |
| M2 | Extract running monthly | IT (ERP team) | ZIP and manifest land after each close | Simulated: `data/erp-extract` |
| M3 | SQL cleans and reconciles | Data and AI Specialist | Every check passes; sales + quarantine = finance to the cent | Built: `data/sql`, 9 planted-problem tests |
| M4 | Model and measures | Data and AI Specialist | Every measure matches an independent calculation live | Built: 148 live tests |
| M5 | Pages reviewed with users | Product Managers | Each page answers its question for two Product Managers | Built; review with users not held |
| M6 | First quarterly scorecard | Portfolio governance | Ratings entered; review uses the page | Built with synthetic ratings |
| M7 | Published with security | Data and AI Specialist, IT | Region and country roles have members; refresh scheduled | Designed: `powerbi/docs/refresh-design.md` |
| M8 | Users trained | Data and AI Specialist | Product Managers and regional users trained; guide published | Guide written: `docs/portfolio-user-guide.md` |

## Risks

| Risk | Likelihood | Effect | What we do |
| --- | --- | --- | --- |
| Regions keep using local item numbers | High | Sales quarantined, figures incomplete | SQL quarantines and lists them; governance maps within a week; the page shows the value held back |
| Extract re-sent or late | Medium | Double counting or a stale month | Deduplicate on business unit and line id; manifest check; refresh only after the load passes |
| Currency missing or wrong | Medium | A month 11 times too big (kronor read as euros) | Ledger currency fallback, ECB rate table, and the currency-matches-ledger check stops the load |
| Users read mix across all products | High | Wrong conclusions | Page note and guide: read the bridge within one family |
| Scorecard weights contested | Medium | Scores not trusted | Weights are governance's stated choice, in a table, reviewed yearly |
| Category 11 dominates emissions | Certain | Other changes look small | Report category 11 separately on its own page beside the total |
| Gateway or licence not ready | Medium | No scheduled refresh | Design needs a gateway only for an on-premises database; Pro is enough |

## Ways of working

- Each change goes through git with tests; a test that fails stops the release.
- Every data problem gets a row in `fact_data_issue` and an owner.
- Monthly: refresh after the close, review the data quality page, fix or escalate.
- Quarterly: scorecard cycle (`docs/scorecard-method.md`).
