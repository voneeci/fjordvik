# Data model

What Fjordvik's data means and how it is stored: the business things the platform knows
about, the 31 tables that hold them, how they join, and the grain of each fact. Every
report, Claude tool and service AI model reads this one model, so a wrong key or an
unclear grain would show up everywhere at once. It is station 03 of the data product
delivery map; its gate, G2, is the business approving the model and the data dictionary.

The [data README](../data/README.md#architecture) holds the schema contract and the source
of every table; the [Power BI data dictionary](../powerbi/docs/data-dictionary.md)
describes every table and measure in the semantic model; the choices behind the model are
in the [decision log](decision-log.md).

> **Synthetic data only.** Fjordvik Manufacturing Oy is a fictional company, and this is a
> portfolio project. No real company, client or person is described; customer and
> supplier names are invented. The emission factors are **illustrative**, not cited.

## Conceptual model

The business things, and how they relate, in Fjordvik's own words.

```mermaid
flowchart LR
    SITE["Site"] -- "uses energy from" --> SRC["Emission source"]
    SITE -- "buys from" --> SUP["Supplier"]
    SITE -- "holds" --> CON["Energy contract"]
    SRC -- "falls in" --> CAT["Scope 3 category"]
    SITE -- "makes and ships" --> PROD["Product model"]
    PROD -- "belongs to" --> GRP["Product group and family"]
    CODE["Local item number"] -- "maps to" --> PROD
    PROD -- "is sold to" --> REG["Sales region"]
    GRP -- "is rated on" --> CRIT["Scorecard criterion"]
    CUST["Customer"] -- "is in" --> REG
    CUST -- "owns" --> PUMP["Connected pump"]
    PUMP -- "is a" --> PROD
    PUMP -- "sends daily" --> READ["Reading"]
    PUMP -- "has" --> EVT["Service event"]
    TECH["Technician"] -- "carries out" --> EVT
    TECH -- "is based at" --> SITE
    PART["Spare part"] -- "fits" --> GRP
    CUST -- "orders" --> PART
    EVT -- "uses" --> PART
    CUST -- "is shown, clicks" --> PART
```

## Logical and physical model

| Layer | Today | In production (designed) |
| --- | --- | --- |
| Logical | A Kimball star schema: dimensions shared across subjects, facts at a declared grain ([ADR-002](decision-log.md#adr-002-a-star-schema)) | The same |
| Physical | 31 CSV files in `data/tables/` with a manifest of row counts and SHA-256 checksums, written only by the generator | A staging database, engine not chosen ([refresh design](../powerbi/docs/refresh-design.md#the-route)) |
| Integrity | Enforced by tests, not by the store: `data/tests/test_schema.py` (names), the data quality tests (unique keys, joins, no negatives, complete monthly grid) and the connector's `data_quality_report` | Primary keys, foreign keys, check and not-null constraints in the database, so a bad write fails at once |
| Types | Inferred from the values below (CSV holds text) | Declared per column |

## Diagrams

Generated on 19 November 2026 from the CSV headers at commit `790589d`, with each key's
target confirmed by the join check below. Types are inferred from the values. They are not
yet regenerated automatically: a test that rebuilds them and fails when they drift is a
follow-up.

### Emissions

```mermaid
erDiagram
    dim_site ||--o{ dim_contract : "site_id"
    dim_source ||--o{ dim_contract : "source_id"
    dim_scope3_category ||--o{ dim_source : "scope3_category"
    dim_date ||--o{ fact_emissions : "date_key"
    dim_site ||--o{ fact_emissions : "site_id"
    dim_source ||--o{ fact_emissions : "source_id"
    dim_source ||--o{ fact_energy_upstream : "based_on_source_id"
    dim_date ||--o{ fact_energy_upstream : "date_key"
    dim_site ||--o{ fact_energy_upstream : "site_id"
    dim_source ||--o{ fact_energy_upstream : "source_id"
    dim_date ||--o{ fact_freight : "date_key"
    dim_site ||--o{ fact_freight : "site_id"
    dim_source ||--o{ fact_freight : "source_id"
    dim_date ||--o{ fact_purchases : "date_key"
    dim_site ||--o{ fact_purchases : "site_id"
    dim_source ||--o{ fact_purchases : "source_id"
    dim_supplier ||--o{ fact_purchases : "supplier_id"
    dim_contract ||--o{ fact_scope2_market : "contract_id"
    dim_date ||--o{ fact_scope2_market : "date_key"
    dim_site ||--o{ fact_scope2_market : "site_id"
    dim_source ||--o{ fact_scope2_market : "source_id"
    dim_date ||--o{ fact_site_metrics : "date_key"
    dim_site ||--o{ fact_site_metrics : "site_id"
    dim_date {
        int date_key PK
        date date
        int year
        int quarter
        int month
        text month_name
    }
    dim_site {
        text site_id PK
        text site_name
        text country
        text site_type
    }
    dim_source {
        text source_id PK
        text source_name
        int scope
        text category
        int scope3_category FK
        text method
    }
    dim_scope3_category {
        int scope3_category PK
        text category_name
        text status
        text reason
    }
    dim_supplier {
        text supplier_id PK
        text supplier_name
        text country
        text spend_category
    }
    dim_contract {
        text contract_id PK
        text site_id FK
        text source_id FK
        text supplier_name
        text instrument
        int start_date_key FK
        int end_date_key FK
        decimal covered_share
    }
    fact_emissions {
        int date_key FK
        text site_id FK
        text source_id FK
        decimal activity_amount
        text unit
        decimal emission_factor
        decimal tco2e
    }
    fact_site_metrics {
        int date_key FK
        text site_id FK
        decimal revenue_eur
        decimal fte
    }
    fact_scope2_market {
        int date_key FK
        text site_id FK
        text source_id FK
        text contract_id FK
        text instrument
        decimal activity_amount
        text unit
        decimal emission_factor
        decimal tco2e
    }
    fact_energy_upstream {
        int date_key FK
        text site_id FK
        text source_id FK
        text based_on_source_id FK
        decimal activity_amount
        text unit
        decimal emission_factor
        decimal tco2e
    }
    fact_purchases {
        int date_key FK
        text site_id FK
        text source_id FK
        text supplier_id FK
        text spend_category
        text method
        decimal activity_amount
        text unit
        decimal emission_factor
        decimal tco2e
    }
    fact_freight {
        int date_key FK
        text site_id FK
        text source_id FK
        text direction
        text mode
        text paid_by
        decimal tonnes
        int distance_km
        decimal activity_amount
        text unit
        decimal emission_factor
        decimal tco2e
    }
```

### Portfolio

```mermaid
erDiagram
    dim_site ||--o{ dim_product : "made_at_site_id"
    dim_product_group ||--o{ dim_product : "product_group"
    dim_product ||--o{ dim_product_code : "product_id"
    dim_date ||--o{ fact_budget : "date_key"
    dim_product_group ||--o{ fact_budget : "product_group"
    dim_region ||--o{ fact_budget : "region_id"
    dim_site ||--o{ fact_budget : "site_id"
    dim_date ||--o{ fact_data_issue : "date_key"
    dim_site ||--o{ fact_data_issue : "site_id"
    dim_score_criterion ||--o{ fact_product_rating : "criterion_id"
    dim_date ||--o{ fact_product_rating : "date_key"
    dim_product_group ||--o{ fact_product_rating : "product_group"
    dim_date ||--o{ fact_sales : "date_key"
    dim_product ||--o{ fact_sales : "product_id"
    dim_region ||--o{ fact_sales : "region_id"
    dim_site ||--o{ fact_sales : "site_id"
    dim_date ||--o{ fact_use_phase : "date_key"
    dim_product ||--o{ fact_use_phase : "product_id"
    dim_region ||--o{ fact_use_phase : "region_id"
    dim_site ||--o{ fact_use_phase : "site_id"
    dim_source ||--o{ fact_use_phase : "source_id"
    dim_date {
        int date_key PK
        date date
        int year
        int quarter
        int month
        text month_name
    }
    dim_site {
        text site_id PK
        text site_name
        text country
        text site_type
    }
    dim_source {
        text source_id PK
        text source_name
        int scope
        text category
        int scope3_category FK
        text method
    }
    dim_product {
        text product_id PK
        text product_name
        text product_group FK
        text product_family
        text made_at_site_id FK
        int rated_kw
        int kwh_per_year
        int lifetime_years
        int list_price_eur
        int standard_cost_eur
    }
    dim_product_group {
        text product_group PK
        text product_family
    }
    dim_region {
        text region_id PK
        text region_name
    }
    dim_product_code {
        text business_unit PK
        text local_item_number PK
        text product_id FK
    }
    dim_score_criterion {
        text criterion_id PK
        text criterion_name
        int weight
        text source
    }
    fact_sales {
        int date_key FK
        text site_id FK
        text product_id FK
        text region_id FK
        int units
        decimal net_sales_eur
        decimal cost_of_sales_eur
        decimal margin_eur
    }
    fact_data_issue {
        int issue_id PK
        int date_key FK
        text site_id FK
        text business_unit
        text issue_type
        text detail
        int line_count
        decimal amount_eur
        text status
        text action
    }
    fact_use_phase {
        int date_key FK
        text site_id FK
        text source_id FK
        text product_id FK
        text region_id FK
        int units
        decimal net_sales_eur
        decimal activity_amount
        text unit
        decimal emission_factor
        decimal tco2e
    }
    fact_product_rating {
        int date_key FK
        text product_group FK
        text criterion_id FK
        int rating
    }
    fact_budget {
        int date_key FK
        text site_id FK
        text product_group FK
        text region_id FK
        int budget_units
        int budget_net_sales_eur
        int budget_margin_eur
    }
```

### After-sales service

```mermaid
erDiagram
    dim_part ||--o{ bridge_part_compatibility : "part_id"
    dim_customer ||--o{ dim_asset : "customer_id"
    dim_product ||--o{ dim_asset : "product_id"
    dim_region ||--o{ dim_customer : "region_id"
    dim_product ||--o{ dim_part : "sales_product_id"
    dim_site ||--o{ dim_product : "made_at_site_id"
    dim_site ||--o{ dim_technician : "home_site_id"
    dim_asset ||--o{ fact_asset_telemetry : "asset_id"
    dim_asset ||--o{ fact_parts_order : "asset_id"
    dim_customer ||--o{ fact_parts_order : "customer_id"
    dim_date ||--o{ fact_parts_order : "date_key"
    dim_part ||--o{ fact_parts_order : "part_id"
    dim_region ||--o{ fact_parts_order : "region_id"
    dim_product ||--o{ fact_parts_order : "sales_product_id"
    fact_service_event ||--o{ fact_parts_order : "service_event_id"
    dim_site ||--o{ fact_parts_order : "site_id"
    dim_customer ||--o{ fact_portal_event : "customer_id"
    dim_part ||--o{ fact_portal_event : "part_id"
    dim_product ||--o{ fact_portal_event : "product_id"
    dim_asset ||--o{ fact_service_event : "asset_id"
    dim_technician ||--o{ fact_service_event : "technician_id"
    dim_date {
        int date_key PK
        date date
        int year
        int quarter
        int month
        text month_name
    }
    dim_site {
        text site_id PK
        text site_name
        text country
        text site_type
    }
    dim_region {
        text region_id PK
        text region_name
    }
    dim_product {
        text product_id PK
        text product_name
        text product_group FK
        text product_family
        text made_at_site_id FK
        int rated_kw
        int kwh_per_year
        int lifetime_years
        int list_price_eur
        int standard_cost_eur
    }
    dim_customer {
        text customer_id PK
        text customer_name
        text segment
        text country
        text region_id FK
        text town
        decimal latitude
        decimal longitude
        text service_contract
        date customer_since
    }
    dim_asset {
        text asset_id PK
        text serial_number
        text product_id FK
        text customer_id FK
        text country
        text town
        decimal latitude
        decimal longitude
        text application
        date install_date
        date telemetry_from_date
    }
    dim_part {
        text part_id PK
        text part_name
        text part_family
        text sales_product_id FK
        decimal list_price_eur
        int lead_time_days
    }
    bridge_part_compatibility {
        text part_id PK
        text product_group PK
    }
    dim_technician {
        text technician_id PK
        text technician_name
        text home_site_id FK
        text home_town
        decimal latitude
        decimal longitude
        text countries_served
        text skills
        decimal weekly_hours
    }
    fact_asset_telemetry {
        int date_key FK
        text asset_id FK
        decimal running_hours
        decimal vibration_mm_s
        decimal bearing_temp_c
        decimal power_kw
    }
    fact_service_event {
        text event_id PK
        text asset_id FK
        text event_type
        text failure_mode
        date reported_date
        date completed_date
        text technician_id FK
        decimal downtime_hours
        decimal labour_hours
        text parts_used
        text technician_note
    }
    fact_parts_order {
        text order_id PK
        int order_line PK
        date order_date
        int date_key FK
        text site_id FK
        text region_id FK
        text customer_id FK
        text part_id FK
        text sales_product_id FK
        int quantity
        decimal net_amount_eur
        text channel
        text service_event_id FK
        text asset_id FK
    }
    fact_portal_event {
        int event_id PK
        date event_date
        text session_id
        text customer_id FK
        text product_id FK
        text part_id FK
        int rank
        int clicked
    }
```

## Bus matrix

Which dimensions each fact shares. A shared column means two subjects can be read side by
side: date, site and region are the dimensions that conform across emissions, portfolio
and service.

| Fact table | date | site | source | supplier | contract | product | product_group | region | score_criterion | customer | asset | part | technician |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `fact_asset_telemetry` | X |  |  |  |  |  |  |  |  |  | X |  |  |
| `fact_budget` | X | X |  |  |  |  | X | X |  |  |  |  |  |
| `fact_data_issue` | X | X |  |  |  |  |  |  |  |  |  |  |  |
| `fact_emissions` | X | X | X |  |  |  |  |  |  |  |  |  |  |
| `fact_energy_upstream` | X | X | X |  |  |  |  |  |  |  |  |  |  |
| `fact_freight` | X | X | X |  |  |  |  |  |  |  |  |  |  |
| `fact_parts_order` | X | X |  |  |  | X |  | X |  | X | X | X |  |
| `fact_portal_event` |  |  |  |  |  | X |  |  |  | X |  | X |  |
| `fact_product_rating` | X |  |  |  |  |  | X |  | X |  |  |  |  |
| `fact_purchases` | X | X | X | X |  |  |  |  |  |  |  |  |  |
| `fact_sales` | X | X |  |  |  | X |  | X |  |  |  |  |  |
| `fact_scope2_market` | X | X | X |  | X |  |  |  |  |  |  |  |  |
| `fact_service_event` |  |  |  |  |  |  |  |  |  |  | X |  | X |
| `fact_site_metrics` | X | X |  |  |  |  |  |  |  |  |  |  |  |
| `fact_use_phase` | X | X | X |  |  | X |  | X |  |  |  |  |  |

`fact_service_event` and `fact_portal_event` carry dates but no date key, and
`fact_asset_telemetry`'s date key is a day, so none of the three joins the monthly
calendar (see findings).

## Grain

The grain of every emissions and service table is in the
[data README](../data/README.md#architecture). The portfolio tables are not listed there;
their grain, checked unique in code on 19 November 2026:

| Table | Grain | Rows |
| --- | --- | --- |
| `fact_sales` | One row per month, shipping site, product and region | 3,379 |
| `fact_use_phase` | One row per month, shipping site, product and region of use | 1,940 |
| `fact_budget` | One row per month, shipping site, product group and region | 1,368 |
| `fact_product_rating` | One row per quarter (keyed to its first month), product group and criterion | 720 |
| `fact_data_issue` | One row per problem the SQL found | 4 |
| `dim_product_code` | One row per business unit and local item number | 26 |
| `dim_product` | One row per product model | 24 |
| `dim_product_group` | One row per product group | 10 |
| `dim_region` | One row per sales region | 4 |
| `dim_score_criterion` | One row per scorecard criterion | 6 |

The service grains in the data README were checked the same way: telemetry is unique by
day and pump (582,996 rows), parts orders by order and line (53,654), service and portal
events by event.

## Join coverage

Every foreign key checked against its target on 19 November 2026: distinct values, how
many are found in the target table, and blanks.

<details>
<summary>All 68 key columns</summary>

| From | Column | To | Distinct values | Found in target | Blank allowed |
| --- | --- | --- | --- | --- | --- |
| `bridge_part_compatibility` | `part_id` | `dim_part.part_id` | 52 | 52 (100%) | 0 blank rows |
| `bridge_part_compatibility` | `product_group` | `dim_product_group.product_group` | 8 | 8 (100%) | 0 blank rows |
| `dim_asset` | `customer_id` | `dim_customer.customer_id` | 131 | 131 (100%) | 0 blank rows |
| `dim_asset` | `product_id` | `dim_product.product_id` | 18 | 18 (100%) | 0 blank rows |
| `dim_contract` | `end_date_key` | `dim_date.date_key` | 1 | 0 (0%) | 0 blank rows |
| `dim_contract` | `site_id` | `dim_site.site_id` | 2 | 2 (100%) | 0 blank rows |
| `dim_contract` | `source_id` | `dim_source.source_id` | 1 | 1 (100%) | 0 blank rows |
| `dim_contract` | `start_date_key` | `dim_date.date_key` | 2 | 2 (100%) | 0 blank rows |
| `dim_customer` | `region_id` | `dim_region.region_id` | 2 | 2 (100%) | 0 blank rows |
| `dim_part` | `sales_product_id` | `dim_product.product_id` | 2 | 2 (100%) | 0 blank rows |
| `dim_product` | `made_at_site_id` | `dim_site.site_id` | 3 | 3 (100%) | 0 blank rows |
| `dim_product` | `product_group` | `dim_product_group.product_group` | 10 | 10 (100%) | 0 blank rows |
| `dim_product_code` | `product_id` | `dim_product.product_id` | 24 | 24 (100%) | 0 blank rows |
| `dim_source` | `scope3_category` | `dim_scope3_category.scope3_category` | 7 | 7 (100%) | 6 blank rows |
| `dim_technician` | `home_site_id` | `dim_site.site_id` | 6 | 6 (100%) | 0 blank rows |
| `fact_asset_telemetry` | `asset_id` | `dim_asset.asset_id` | 600 | 600 (100%) | 0 blank rows |
| `fact_asset_telemetry` | `date_key` | `dim_date.date_key` | 1096 | 36 (3%) | 0 blank rows |
| `fact_budget` | `date_key` | `dim_date.date_key` | 36 | 36 (100%) | 0 blank rows |
| `fact_budget` | `product_group` | `dim_product_group.product_group` | 10 | 10 (100%) | 0 blank rows |
| `fact_budget` | `region_id` | `dim_region.region_id` | 4 | 4 (100%) | 0 blank rows |
| `fact_budget` | `site_id` | `dim_site.site_id` | 5 | 5 (100%) | 0 blank rows |
| `fact_data_issue` | `date_key` | `dim_date.date_key` | 4 | 4 (100%) | 0 blank rows |
| `fact_data_issue` | `site_id` | `dim_site.site_id` | 3 | 3 (100%) | 0 blank rows |
| `fact_emissions` | `date_key` | `dim_date.date_key` | 36 | 36 (100%) | 0 blank rows |
| `fact_emissions` | `site_id` | `dim_site.site_id` | 6 | 6 (100%) | 0 blank rows |
| `fact_emissions` | `source_id` | `dim_source.source_id` | 8 | 8 (100%) | 0 blank rows |
| `fact_energy_upstream` | `based_on_source_id` | `dim_source.source_id` | 5 | 5 (100%) | 0 blank rows |
| `fact_energy_upstream` | `date_key` | `dim_date.date_key` | 36 | 36 (100%) | 0 blank rows |
| `fact_energy_upstream` | `site_id` | `dim_site.site_id` | 6 | 6 (100%) | 0 blank rows |
| `fact_energy_upstream` | `source_id` | `dim_source.source_id` | 2 | 2 (100%) | 0 blank rows |
| `fact_freight` | `date_key` | `dim_date.date_key` | 36 | 36 (100%) | 0 blank rows |
| `fact_freight` | `site_id` | `dim_site.site_id` | 5 | 5 (100%) | 0 blank rows |
| `fact_freight` | `source_id` | `dim_source.source_id` | 2 | 2 (100%) | 0 blank rows |
| `fact_parts_order` | `asset_id` | `dim_asset.asset_id` | 492 | 492 (100%) | 50854 blank rows |
| `fact_parts_order` | `customer_id` | `dim_customer.customer_id` | 146 | 146 (100%) | 0 blank rows |
| `fact_parts_order` | `date_key` | `dim_date.date_key` | 36 | 36 (100%) | 0 blank rows |
| `fact_parts_order` | `part_id` | `dim_part.part_id` | 52 | 52 (100%) | 0 blank rows |
| `fact_parts_order` | `region_id` | `dim_region.region_id` | 2 | 2 (100%) | 0 blank rows |
| `fact_parts_order` | `sales_product_id` | `dim_product.product_id` | 2 | 2 (100%) | 0 blank rows |
| `fact_parts_order` | `service_event_id` | `fact_service_event.event_id` | 1992 | 1992 (100%) | 50854 blank rows |
| `fact_parts_order` | `site_id` | `dim_site.site_id` | 2 | 2 (100%) | 0 blank rows |
| `fact_portal_event` | `customer_id` | `dim_customer.customer_id` | 131 | 131 (100%) | 0 blank rows |
| `fact_portal_event` | `part_id` | `dim_part.part_id` | 26 | 26 (100%) | 0 blank rows |
| `fact_portal_event` | `product_id` | `dim_product.product_id` | 18 | 18 (100%) | 0 blank rows |
| `fact_product_rating` | `criterion_id` | `dim_score_criterion.criterion_id` | 6 | 6 (100%) | 0 blank rows |
| `fact_product_rating` | `date_key` | `dim_date.date_key` | 12 | 12 (100%) | 0 blank rows |
| `fact_product_rating` | `product_group` | `dim_product_group.product_group` | 10 | 10 (100%) | 0 blank rows |
| `fact_purchases` | `date_key` | `dim_date.date_key` | 36 | 36 (100%) | 0 blank rows |
| `fact_purchases` | `site_id` | `dim_site.site_id` | 6 | 6 (100%) | 0 blank rows |
| `fact_purchases` | `source_id` | `dim_source.source_id` | 1 | 1 (100%) | 0 blank rows |
| `fact_purchases` | `supplier_id` | `dim_supplier.supplier_id` | 14 | 14 (100%) | 0 blank rows |
| `fact_sales` | `date_key` | `dim_date.date_key` | 36 | 36 (100%) | 0 blank rows |
| `fact_sales` | `product_id` | `dim_product.product_id` | 24 | 24 (100%) | 0 blank rows |
| `fact_sales` | `region_id` | `dim_region.region_id` | 4 | 4 (100%) | 0 blank rows |
| `fact_sales` | `site_id` | `dim_site.site_id` | 5 | 5 (100%) | 0 blank rows |
| `fact_scope2_market` | `contract_id` | `dim_contract.contract_id` | 2 | 2 (100%) | 396 blank rows |
| `fact_scope2_market` | `date_key` | `dim_date.date_key` | 36 | 36 (100%) | 0 blank rows |
| `fact_scope2_market` | `site_id` | `dim_site.site_id` | 6 | 6 (100%) | 0 blank rows |
| `fact_scope2_market` | `source_id` | `dim_source.source_id` | 2 | 2 (100%) | 0 blank rows |
| `fact_service_event` | `asset_id` | `dim_asset.asset_id` | 542 | 542 (100%) | 0 blank rows |
| `fact_service_event` | `technician_id` | `dim_technician.technician_id` | 10 | 10 (100%) | 0 blank rows |
| `fact_site_metrics` | `date_key` | `dim_date.date_key` | 36 | 36 (100%) | 0 blank rows |
| `fact_site_metrics` | `site_id` | `dim_site.site_id` | 6 | 6 (100%) | 0 blank rows |
| `fact_use_phase` | `date_key` | `dim_date.date_key` | 36 | 36 (100%) | 0 blank rows |
| `fact_use_phase` | `product_id` | `dim_product.product_id` | 18 | 18 (100%) | 0 blank rows |
| `fact_use_phase` | `region_id` | `dim_region.region_id` | 3 | 3 (100%) | 0 blank rows |
| `fact_use_phase` | `site_id` | `dim_site.site_id` | 3 | 3 (100%) | 0 blank rows |
| `fact_use_phase` | `source_id` | `dim_source.source_id` | 1 | 1 (100%) | 0 blank rows |

</details>

### Findings

1. **Every key resolves**, apart from the two below. Blanks are by design:
   `fact_parts_order.service_event_id` and `asset_id` are blank on orders not tied to a
   service job (50,854 of 53,654 lines); `fact_scope2_market.contract_id` is blank where
   the residual mix applies; `dim_source.scope3_category` is blank for scope 1 and 2
   sources.
2. **Telemetry has no calendar.** `fact_asset_telemetry.date_key` holds 1,096 days;
   `dim_date` holds 36 months, so only first-of-month days match. `fact_service_event`
   and `fact_portal_event` have dates and no key. Proposal: a new daily date table
   ([ADR-029](decision-log.md#adr-029-a-daily-date-table-for-the-service-data)).
3. **Contract end dates sit past the calendar.** Both contracts end on 1 December 2027
   (`end_date_key` 20271201), after the last month in `dim_date`. That is right for a
   contract; the keys are dates, not joins, and the diagram draws no line for them.
4. **Parts fit 8 of the 10 product groups.** The two left out, Spare parts and Service
   kits, are themselves parts, so nothing fits them. No gap.

## History handling

Every dimension is overwritten in place today (slowly changing dimension type 1): a change
rewrites the past. That is right for names and codes, and wrong for a few attributes past
figures depend on:

| Attribute | Why history matters | Proposed handling |
| --- | --- | --- |
| `dim_customer.service_contract` | A customer moving from Basic to Premium changes how many preventive visits were due | Type 2: a row per contract period with valid-from and valid-to dates |
| `dim_technician.skills`, `weekly_hours` | Phase 4 must plan from data as it stood ("as at" dates, rule D16) | Type 2 |
| `dim_asset` town and location | A moved pump's travel cost changes | Type 2 when moves start; none in the data today |
| Emission factors | One factor per source for the whole period; a new factor would rewrite past emissions | Yearly factor versions, already a [next step](learning-guide.md#next-steps) |
| Product specification, prices | Stable in the data | Type 1 |

This is a proposal, [ADR-027](decision-log.md#adr-027-history-handling-for-dimensions),
for Reece to decide. Any change is a new column or table (names never change, rule D4)
made through the generator, and moving an existing checksum needs Reece's yes (rule D5).

## Gate G2

| Check | Status |
| --- | --- |
| Conceptual model agreed with users | First edition above; not reviewed with users |
| Logical and physical model | Built and tested |
| Data dictionary and grain statements | Power BI dictionary generated; grain for every table, now including the portfolio tables |
| Bus matrix | Above |
| History handling decided | Proposed (ADR-027) |
| Wireframes approved | The 17 report pages exist ([report pages](../powerbi/docs/report-pages.md)); review with users is open (portfolio milestone M5) |
| Business approval | **Not given.** Reece approves as the stand-in for the data owners |

## Change history

- 19 November 2026: first edition, during the architecture pause (Reece asked).
