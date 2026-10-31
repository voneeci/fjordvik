# Portfolio report: a guide for Product Managers and regional users

What the six portfolio pages of the Fjordvik Power BI report answer, how to read them,
and who to ask. Open the report and start on the **Introduction** page; the buttons at the
top go to every page.

> **Synthetic data only.** Fjordvik Manufacturing Oy is a fictional company, and the sales
> come from a **simulated** ERP extract. Emission factors are illustrative, not for real
> reporting.

## Before you start

- **Your view.** A sales region manager sees only their own region's sales, margin, scorecard
  and use-phase emissions; the site emission pages show blank. A country manager sees their
  own country's sites. The Group Sustainability Manager and portfolio governance see
  everything.
- **Slicers** at the top right of each page filter that page only. Pick a **Year** first:
  most figures compare the year with the same months a year earlier.
- **One source of truth.** Every figure comes from the same model, refreshed after each
  month-end close. If two pages disagree, report it (see "Who to ask").

## The pages

| Page | It answers | Read it like this |
| --- | --- | --- |
| Portfolio overview | What do we sell, at what price and margin? | Cards are the year's totals; the table gives each family and group. Average price mixes very different products, so compare it within one group. |
| Price, volume and mix | Why did margin move against last year? | Start with the change card, then the bars: price (we charged more or less), mix (we sold more of higher- or lower-margin products), quantity (we sold more or fewer units), cost (units cost more or less to make). Pick one family: across pumps and spare parts, mix and quantity are large and cancel out. |
| Portfolio balance | Where do sales and margin come from? | Shares add to 100% across families and regions. A family with a bigger share of margin than of sales earns above the average. |
| Product sustainability | How much does each product emit in use? | Use-phase emissions are the lifetime electricity of the units sold, at the grid of the region of use. Per unit compares products; per thousand euros compares them with what they earn. Rest of world is not calculated. |
| Quarterly scorecard | How does each product group score? | The matrix shows each quarter's weighted score (1 to 10). The table sets it beside sales, margin, share, price effect and use-phase emissions, to prepare the next review. |
| Classification and data quality | What went wrong in the ERP data? | Each issue has an action. Quarantined lines are not in the sales figures until their item number is mapped. The reconciliation card should read 0.00. |

## How the bridge is worked out

The price, volume and mix page follows the ACCA (Association of Chartered Certified
Accountants) sales variances, with the same months a year earlier as the standard:

- **Price** = (this year's price − last year's price) × this year's units.
- **Volume** = (this year's units − last year's units) × last year's margin per unit, split into:
  - **Mix**: the effect of selling a different mix of products, at last year's margins;
  - **Quantity**: the effect of selling more or fewer units in total, at last year's mix.
- **Cost** = (last year's cost per unit − this year's) × this year's units.
- **Not comparable**: products sold in only one of the two periods.

Last year's margin plus these effects equals this year's margin exactly.

## Common questions

- **Why is a month's sales lower than finance revenue?** Quarantined lines. They are listed
  on the Classification and data quality page with their value.
- **Why is my region's emissions page blank?** Region roles see sales, not site
  emissions, by design.
- **Why does the scorecard not change when sales change?** Ratings come from the quarterly
  review; the figures inform it but do not set it.

## Who to ask

| Question | Ask |
| --- | --- |
| A figure, a page or access to the report | Data and AI Specialist (first point of contact) |
| An item number missing from the classification | Portfolio governance |
| Sales or cost in the ERP | Your regional controller |
| Emissions and factors | Group Sustainability Manager |
