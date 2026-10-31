# Portfolio report: a guide for Product Managers and regional users

What the pages of the Fjordvik portfolio report (`FjordvikPortfolio.pbip`) answer, how to
read them, and who to ask. Open the report and start on the **Introduction** page; the
buttons along the top of every page go to every page. Emissions are in a second report on
the same model (`FjordvikEmissions.pbip`).

> **Synthetic data only.** Fjordvik Manufacturing Oy is a fictional company, and the sales
> come from a **simulated** ERP extract. Emission factors are illustrative, not for real
> reporting.

## Before you start

- **Your view.** A sales region manager sees only their own region's sales, margin, scorecard
  and use-phase emissions; the site emission pages show blank. A country manager sees their
  own country's sites. The Group Sustainability Manager and portfolio governance see
  everything.
- **One year at a time.** Each page opens on the latest full year (2025); pick another in
  the **Year** slicer at the top right and every page follows (the Region and Family
  choices too). Charts by month or quarter always show all three years.
- **Under every headline number**: the same months a year earlier and the change on them,
  then the budget and the variance on it. A rate (margin %) moves in percentage points
  (pts).
- **The page title** under the page name is a sentence worked out from the data: read it
  first.
- **One source of truth.** Every figure comes from the same model, refreshed after each
  month-end close. If two pages disagree, report it (see "Who to ask").

## The pages

| Page | It answers | Read it like this |
| --- | --- | --- |
| Portfolio overview | What do we sell and earn, against last year and budget? | Cards are the year's totals with 2024 and budget under them; the bars show each family against budget; the table gives every family and group with prior year, budget and the variances. |
| Price, volume and mix | Why did margin move against last year? | Read the waterfall left to right: last year's margin, then sales prices (we charged more or less), mix (we sold more of higher- or lower-margin products), delivery volumes (we sold more or fewer units), variable costs (units cost more or less to make), and products not comparable, ending at this year's margin. Green raised margin, red lowered it. The tables give each family and group; each row and column adds up. Pick one family: across pumps and spare parts, mix and delivery volumes are large and cancel out. |
| Portfolio balance | Where do sales and margin come from, and what grows? | A group whose blue bar (share of margin) is longer than its grey bar (share of sales) earns above the average. In the bubble chart, top right grows fast at a high margin; bottom left shrinks at a low one. The shaded table shows where each family sells. |
| Quarterly scorecard | How does each product group score? | Opens on the latest quarter. The shaded matrix shows every quarter's weighted score (1 to 10), darker for higher. The table sets the score and its change on the prior quarter beside sales, margin, share, price effect and use-phase emissions; the chart shows score against margin, so a high score with a weak margin stands out for the next review. |
| Product sustainability | How much does each product emit in use? | Use-phase emissions are the lifetime electricity of the units sold, at the grid of the region of use. Per unit compares products; per thousand euros compares them with what they earn, as does the margin chart. Rest of world is not calculated. |
| Classification and data quality | What went wrong in the ERP data? | Open issues are quarantined lines waiting for their item number to be mapped; they are not in the sales figures until then. Each issue has an action. The reconciliation card should read 0.00. |

## How the bridge is worked out

The price, volume and mix page follows the ACCA (Association of Chartered Certified
Accountants) sales variances, with the same months a year earlier as the standard. The
waterfall names the steps the way segment reports usually do:

- **Sales prices** (ACCA price effect) = (this year's price − last year's price) × this year's units.
- **Volume** = (this year's units − last year's units) × last year's margin per unit, split into:
  - **Mix**: the effect of selling a different mix of products, at last year's margins;
  - **Delivery volumes** (ACCA quantity effect): the effect of selling more or fewer units in
    total, at last year's mix.
- **Variable costs** (ACCA cost effect) = (last year's cost per unit − this year's) × this year's units.
- **Not comparable**: products sold in only one of the two periods.

Last year's margin plus these effects equals this year's margin exactly. In the tables, mix
and delivery volumes are worked out within each product group so the columns add up; the
company's mix also holds the shift of sales between groups, which the note under the table
gives.

## Common questions

- **Why is a month's sales lower than finance revenue?** Quarantined lines. They are listed
  on the Classification and data quality page with their value.
- **Why is my region's emissions page blank?** Region roles see sales and budget, not
  site emissions, by design.
- **Why is the budget blank for one product?** The budget is set by product group; pick a
  group, family, region or site.
- **Why does the scorecard not change when sales change?** Ratings come from the quarterly
  review; the figures inform it but do not set it.

## Who to ask

| Question | Ask |
| --- | --- |
| A figure, a page or access to the report | Data and AI Specialist (first point of contact) |
| An item number missing from the classification | Portfolio governance |
| Sales or cost in the ERP | Your regional controller |
| Emissions and factors | Group Sustainability Manager |
