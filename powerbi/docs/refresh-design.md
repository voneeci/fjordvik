# Refresh design: from the ERP extract to the published report

How Fjordvik's portfolio and emissions report would be refreshed in the Power BI Service.
This is a design: the model is not published, and in this repository Power BI Desktop
reads the CSV files in `data/tables` through the `DataFolder` parameter. Facts about
Oracle and Power BI come from the official pages listed under Sources, read on
31 October 2026 (research note of that date).

> **Synthetic data only.** Fjordvik Manufacturing Oy is a fictional company, and the ERP
> extract in `data/erp-extract` is **simulated**. The emission factors are illustrative.

## The route

```
Oracle Fusion Cloud ERP ──Data Extraction tool, monthly──> ZIP files + manifest (SHA-256)
        │                                                    in object storage
        ▼
Staging database ──SQL (data/sql): check manifest, stage, deduplicate, convert currency,
        │           map to the global classification, validate, reconcile to finance
        ▼
Power BI semantic model ──scheduled refresh (Power BI Service)──> report and scorecard
```

- **Why not connect Power BI to Oracle directly.** Microsoft's connector list has no
  connector for Oracle's extraction routes. Its "Oracle ERP" connector is in Preview and
  its page does not say what it reads. Oracle's own pages advise against bulk extraction
  through Oracle Transactional Business Intelligence (OTBI) or Analytics Publisher, and say
  REST APIs are "Not suitable for large volumes". So the extract lands as files, is loaded
  to a staging database, and Power BI refreshes from there.
- **Which Oracle tool.** Oracle's 26D documentation calls the Data Extraction tool "the
  long-term replacement for Business Intelligence Cloud Connector (BICC)". Its output is ZIP
  files of CSV with a manifest of SHA-256 checksums, the shape `data/erp-extract` copies.
  One older 26D page still calls BICC the tool for all bulk retrieval; the pages conflict.

## Schedule

| Step | When | Owner | Check before the next step |
| --- | --- | --- | --- |
| ERP month-end close | Working day 3 | Group Financial Controller | Close signed off |
| Data Extraction tool run | Working day 4, early morning | IT (ERP team) | Manifest written |
| SQL load into staging | After the extract lands | Data and AI Specialist | Every check in `data/sql` passes; sales reconcile to finance to the cent |
| Power BI refresh | Daily at 06:00, and on demand after the load | Data and AI Specialist | Refresh history shows success; Data quality pages reviewed |
| Quarterly scorecard ratings | After each quarter's review | Portfolio governance | Every group rated on every criterion |

A failed SQL check stops the load, so the report keeps last month's figures rather than
showing wrong ones. Issues the SQL can resolve (duplicates, a missing currency code) are
corrected and listed in `fact_data_issue`; unmapped item numbers are quarantined until
portfolio governance maps them.

## Power BI Service limits that shape the design

| Limit | What Microsoft says | Effect here |
| --- | --- | --- |
| Refreshes a day, Pro (shared capacity) | "eight scheduled daily semantic model refreshes" | One daily refresh plus one on demand fits easily |
| Refreshes a day, Premium Per User (PPU), Premium, Fabric | "up to 48 refreshes per day" | Not needed for a monthly close |
| Refresh time | "less than two hours on shared capacity"; five hours on Premium | The model is small (about 10,000 rows today) |
| Failures | the schedule is turned off after "four consecutive failures" | The owner gets the failure email and must fix and re-enable it |
| Model size | "The default size limit is 1 GB" | Far below |

## Gateway

A gateway is needed only when the Power BI Service cannot reach the source directly:
"If your semantic model uses a data source that Power BI can't access over a direct
network connection, you must configure a gateway connection." A cloud staging database
the Service can reach needs none; a database inside the company network needs an
on-premises data gateway (standard mode, not personal mode, which "Supports one Power BI
user"). Microsoft's Oracle database connector notes that from June 2026 a cloud connection
to Oracle Autonomous Database needs no gateway.

## Incremental refresh

`fact_sales` and `fact_use_phase` grow by a month at a time, so they suit incremental
refresh by month: keep, say, five years and refresh only the last three months.

- It works on Pro: "Incremental refresh is supported for Power BI Premium, Premium per
  user, Power BI Pro, and Power BI Embedded models."
- It needs two Power Query parameters, `RangeStart` and `RangeEnd`, which "must be the
  date/time data type", and a filter on the table's date column between them.
- The source must apply that filter itself. If it cannot, the engine "might compensate
  and apply the filter locally, which requires retrieving all rows", "effectively
  defeating the purpose of incremental refresh". A staging database filters at source;
  the CSV folder used in this repository would be read in full every time.

**Not built here.** `RangeStart` and `RangeEnd` need a published model and a database
source to be worth having; with CSV files they would add nothing. They are the first
change when the model is published against the staging database.

## Row-level security in the Service

The model's seven roles (three countries, four sales regions) are defined and tested
live in Desktop. In the Service, each role gets members (security groups, not named
people) on the semantic model's Security page, and the certification checklist records
who approved each membership.

## Sources

All read on 31 October 2026; Microsoft page dates are the pages' own.

- Oracle, Data Extraction tool (26D): https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26d/faips/scm-data-extraction-tool.html
- Oracle, extract output and manifest: https://docs.oracle.com/en/cloud/saas/applications-common/faude/extract-output-file-and-manifest-details.html
- Oracle, BICC (26D): https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26d/faips/business-intelligence-cloud-connector.html
- Oracle, REST services (26D): https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26d/faips/scm-rest-services.html
- Microsoft, Power Query connectors (8 October 2026): https://learn.microsoft.com/en-us/power-query/connectors/
- Microsoft, Oracle database connector (4 August 2026): https://learn.microsoft.com/en-us/power-query/connectors/oracle-database
- Microsoft, Data refresh in Power BI (18 September 2026): https://learn.microsoft.com/en-us/power-bi/connect-data/refresh-data
- Microsoft, Configure scheduled refresh (13 February 2026): https://learn.microsoft.com/en-us/power-bi/connect-data/refresh-scheduled-refresh
- Microsoft, Large semantic models (17 June 2025): https://learn.microsoft.com/en-us/fabric/enterprise/powerbi/service-premium-large-models
- Microsoft, On-premises data gateway (18 September 2026): https://learn.microsoft.com/en-us/power-bi/connect-data/service-gateway-onprem
- Microsoft, Incremental refresh (24 September 2025): https://learn.microsoft.com/en-us/power-bi/connect-data/incremental-refresh-overview
